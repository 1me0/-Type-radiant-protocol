"""
radiant_core_engine.py

Deep learning implementation of the Radiant Core Engine with:
- Energy model grounded in explicit constraints: E = ||φ(P,C)||² + E_residual
- μF defined as gradient of a scalar architect potential (conservative structure)
- State‑ and context‑dependent uncertainty
- Adaptive time step
- SDE and projection modes
- Presence score
- 2D visualisation (energy landscape + vector field)
- ONNX export + Rust binding example
- Training with bifurcation loss and human supervision
- Adaptive α/β correction based on presence score

Author: Radiant Protocol
License: MIT
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.utils as utils
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple, Union, Callable, List
import os

# ==================================================
# 1. ENERGY MODEL (grounded in constraints)
# ==================================================
class ConstraintFunction(nn.Module):
    """
    Learns a constraint manifold φ(P, C) = 0.
    The energy is E = ||φ(P, C)||² + E_residual(P, C),
    ensuring that low energy corresponds to satisfying the constraint.
    """
    def __init__(self, state_dim: int, context_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim + context_dim, hidden_dim)),
            nn.ReLU(),
            utils.spectral_norm(nn.Linear(hidden_dim, state_dim))  # output same dim as state for residual
        )

    def forward(self, P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        x = torch.cat([P, C], dim=-1)
        return self.net(x)


class EnergyModel(nn.Module):
    """
    Energy = ||φ(P, C)||² + residual_net(P, C)
    The residual allows modelling additional structure while the squared norm
    anchors the energy to the constraint manifold.
    """
    def __init__(self, state_dim: int, context_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.constraint = ConstraintFunction(state_dim, context_dim, hidden_dim)
        self.residual_net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim + context_dim, hidden_dim)),
            nn.ReLU(),
            utils.spectral_norm(nn.Linear(hidden_dim, 1))
        )

    def forward(self, P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        phi = self.constraint(P, C)
        E_constraint = (phi ** 2).sum(dim=-1, keepdim=True)
        E_residual = self.residual_net(torch.cat([P, C], dim=-1))
        # Bounded energy via tanh for numerical stability
        return torch.tanh(E_constraint + E_residual)


# ==================================================
# 2. DYNAMICS FIELD μF (gradient of architect potential)
# ==================================================
class ArchitectPotential(nn.Module):
    """Scalar potential Φ(P) whose gradient gives the structured drift μF."""
    def __init__(self, state_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim, hidden_dim)),
            nn.Tanh(),
            utils.spectral_norm(nn.Linear(hidden_dim, 1))
        )

    def forward(self, P: torch.Tensor) -> torch.Tensor:
        return self.net(P)


class MuF(nn.Module):
    """
    μF(P) = -∇_P Φ(P)   (conservative vector field)
    Lipschitz constraint is enforced via spectral normalisation.
    """
    def __init__(self, state_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.potential = ArchitectPotential(state_dim, hidden_dim)

    def forward(self, P: torch.Tensor) -> torch.Tensor:
        P_req = P.clone().detach().requires_grad_(True)
        Phi = self.potential(P_req).sum()
        grad = torch.autograd.grad(Phi, P_req, create_graph=False)[0]
        # Scale to keep magnitude controlled (Lipschitz constant <= 1 by spectral norm)
        return -0.5 * torch.tanh(grad)


# ==================================================
# 3. CONTEXT‑AWARE UNCERTAINTY MODEL
# ==================================================
class UncertaintyNet(nn.Module):
    """
    σ(P, C) = σ₀ + γ * ||∇E|| * (1 + tanh(ψ(C)))
    where ψ(C) is a small network that modulates uncertainty based on context.
    γ is either fixed or learnable.
    """
    def __init__(self, context_dim: int, sigma0: float = 0.01,
                 learn_gamma: bool = False, gamma_init: float = 0.5):
        super().__init__()
        self.sigma0 = sigma0
        if learn_gamma:
            self.gamma = nn.Parameter(torch.tensor(gamma_init))
        else:
            self.register_buffer('gamma', torch.tensor(gamma_init))
        self.context_modulator = nn.Sequential(
            nn.Linear(context_dim, 16),
            nn.Tanh(),
            nn.Linear(16, 1)
        )

    def forward(self, grad_norm: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        gamma = self.gamma if isinstance(self.gamma, torch.Tensor) else torch.tensor(self.gamma)
        modulation = 1.0 + torch.tanh(self.context_modulator(C))
        return self.sigma0 + gamma * grad_norm * modulation


# ==================================================
# 4. ENERGY GRADIENT
# ==================================================
def energy_gradient(energy_model: EnergyModel, P: torch.Tensor, C: torch.Tensor,
                    create_graph: bool = False):
    P_req = P.clone().detach().requires_grad_(True)
    E = energy_model(P_req, C).sum()
    grad = torch.autograd.grad(E, P_req, create_graph=create_graph)[0]
    E = E.view(-1, 1) if E.dim() == 0 else E
    return E, grad


# ==================================================
# 5. ADAPTIVE TIME STEP
# ==================================================
def adaptive_dt(base_dt: float, sigma: torch.Tensor, grad_norm: torch.Tensor,
                max_dt: float = 1.0, min_dt: float = 0.01) -> torch.Tensor:
    scale = 1.0 / (1.0 + sigma + grad_norm)
    dt = base_dt * scale
    return torch.clamp(dt, min_dt, max_dt)


# ==================================================
# 6. SYSTEM (SDE + Projection)
# ==================================================
class System(nn.Module):
    def __init__(self, state_dim: int, context_dim: int, use_learned_gamma: bool = False):
        super().__init__()
        self.energy = EnergyModel(state_dim, context_dim)
        self.muF = MuF(state_dim)
        self.uncertainty = UncertaintyNet(context_dim, learn_gamma=use_learned_gamma)

    def step(self, P: torch.Tensor, C: torch.Tensor,
             alpha: float = 0.05, beta: float = 0.02,
             base_dt: float = 1.0, noise_scale: float = 0.1,
             mode: str = "sde") -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Perform one step of the dynamics.
        Returns:
            P_next: updated state
            E: current energy
            sigma: uncertainty value
            dt: adaptive time step used
        """
        E, gradE = energy_gradient(self.energy, P, C, create_graph=False)
        grad_norm = gradE.norm(dim=-1, keepdim=True)
        sigma = self.uncertainty(grad_norm, C)
        dt = adaptive_dt(base_dt, sigma, grad_norm)
        drift = self.muF(P)
        noise = torch.randn_like(P) * (sigma * noise_scale * torch.sqrt(dt))

        if mode == "sde":
            P_next = P - alpha * gradE * dt + beta * drift * dt + noise
        elif mode == "projection":
            Pi = P - alpha * gradE
            correction = (1 + beta) * Pi - beta * P
            P_next = correction + noise
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return P_next, E.detach(), sigma.detach(), dt.detach()


# ==================================================
# 7. PRESENCE SCORE
# ==================================================
def presence_score(E: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    """High presence when both energy and uncertainty are low."""
    return torch.sigmoid(-(E + sigma))


# ==================================================
# 8. STABILITY ANALYSIS (γ_c computation)
# ==================================================
def compute_critical_gamma(energy_model: EnergyModel, muF: MuF,
                           alpha: float, beta: float) -> float:
    """
    Compute the critical noise amplification γ_c for stochastic stability.

    Derivation (simplified for readability, see extended description):
        For the linearised SDE dP = A P dt + γ B P dW,
        stability in mean‑square requires ||I + A dt||² + γ² ||B||² dt < 1.
        Using Lipschitz bounds L_E (for ∇E) and L_μ (for μF), we obtain:
            γ_c = sqrt( 2α(1+β)L_μ - α²(1+β)² L_μ² ) / (α L_E)
        when the numerator is positive, else γ_c = 0.

    This implementation extracts Lipschitz constants from spectral norms.
    """
    # Estimate Lipschitz constant of ∇E (gradient of energy)
    # For a network with spectral normalisation, product of spectral norms is an upper bound.
    L_E = 1.0
    for module in energy_model.modules():
        if isinstance(module, nn.Linear) and hasattr(module, 'weight'):
            L_E *= torch.linalg.norm(module.weight, ord=2).item()

    # Lipschitz constant of μF (gradient of potential) similarly bounded
    L_mu = 1.0
    for module in muF.modules():
        if isinstance(module, nn.Linear) and hasattr(module, 'weight'):
            L_mu *= torch.linalg.norm(module.weight, ord=2).item()

    numerator = 2 * alpha * (1 + beta) * L_mu - (alpha ** 2) * ((1 + beta) ** 2) * (L_mu ** 2)
    if numerator <= 0:
        return 0.0
    gamma_c = np.sqrt(numerator) / (alpha * L_E)
    return gamma_c


# ==================================================
# 9. CORE ENGINE (with adaptive α/β correction)
# ==================================================
class RadiantCoreEngine(nn.Module):
    def __init__(self, state_dim: int, context_dim: int):
        super().__init__()
        self.system = System(state_dim, context_dim)
        self.register_buffer('alpha', torch.tensor(0.05))
        self.register_buffer('beta', torch.tensor(0.02))
        self.presence_threshold = 0.3
        self.alpha_min = 0.01
        self.beta_max = 0.1
        self.alpha_decay = 0.95
        self.beta_boost = 1.2

    def adjust_hyperparams(self, presence: torch.Tensor):
        """Increase β and decrease α when presence is low (adaptive correction)."""
        if presence.mean() < self.presence_threshold:
            self.alpha.data = torch.max(self.alpha * self.alpha_decay, torch.tensor(self.alpha_min))
            self.beta.data = torch.min(self.beta * self.beta_boost, torch.tensor(self.beta_max))

    def rollout(self, P: torch.Tensor, C: torch.Tensor,
                steps: int = 1, mode: str = "sde",
                training: bool = False, **step_kwargs) -> Dict[str, torch.Tensor]:
        for _ in range(steps):
            if not training:
                P = P.detach()
            P, E, sigma, dt = self.system.step(P, C,
                                               alpha=self.alpha.item(),
                                               beta=self.beta.item(),
                                               mode=mode, **step_kwargs)
            pres = presence_score(E, sigma)
            if not training:
                self.adjust_hyperparams(pres)
        return {"state": P, "energy": E, "uncertainty": sigma, "dt": dt, "presence": pres}

    def forward(self, P: torch.Tensor, C: torch.Tensor, **kwargs) -> Dict[str, torch.Tensor]:
        return self.rollout(P, C, **kwargs)


# ==================================================
# 10. VISUALISATION (2D landscape + vector field)
# ==================================================
def plot_2d_landscape(engine: RadiantCoreEngine, context: np.ndarray,
                      xlim=(-3, 3), ylim=(-3, 3), resolution=100,
                      save_path="energy_landscape.png"):
    """
    Plot energy landscape and vector field for a 2D slice of state space.
    Assumes state_dim >= 2. Higher dimensions are set to zero for visualisation.
    """
    device = next(engine.parameters()).device

    # Infer dimensions from the engine
    # Energy model's first linear layer input size = state_dim + context_dim
    first_linear = engine.system.energy.constraint.net[0]
    total_in = first_linear.in_features
    # We need context_dim; we can get it from the context_modulator's input size
    context_dim = engine.system.uncertainty.context_modulator[0].in_features
    state_dim = total_in - context_dim
    if state_dim < 2:
        raise ValueError("State dimension must be at least 2 for 2D visualisation.")

    x = np.linspace(xlim[0], xlim[1], resolution)
    y = np.linspace(ylim[0], ylim[1], resolution)
    X, Y = np.meshgrid(x, y)
    points = np.stack([X.ravel(), Y.ravel()], axis=1)
    # Pad with zeros for remaining state dimensions
    if state_dim > 2:
        zeros = np.zeros((points.shape[0], state_dim - 2))
        points = np.concatenate([points, zeros], axis=1)

    C_tensor = torch.tensor(context, dtype=torch.float32).to(device).unsqueeze(0).repeat(resolution*resolution, 1)
    P_tensor = torch.tensor(points, dtype=torch.float32).to(device)

    with torch.no_grad():
        E_vals = engine.system.energy(P_tensor, C_tensor).cpu().numpy().reshape(resolution, resolution)

        # Compute gradient field (only the first two components)
        P_req = P_tensor.clone().detach().requires_grad_(True)
        E_sum = engine.system.energy(P_req, C_tensor).sum()
        grad_full = torch.autograd.grad(E_sum, P_req)[0].cpu().numpy()
        U = grad_full[:, 0].reshape(resolution, resolution)
        V = grad_full[:, 1].reshape(resolution, resolution)

    plt.figure(figsize=(10, 8))
    plt.contourf(X, Y, E_vals, levels=50, cmap='viridis')
    plt.colorbar(label='Energy')
    plt.streamplot(X, Y, U, V, density=1.5, color='white', linewidth=0.5)
    plt.title('Energy Landscape + Gradient Flow')
    plt.xlabel('State dim 1')
    plt.ylabel('State dim 2')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved 2D landscape to {save_path}")


# ==================================================
# 11. ONNX EXPORT + RUST BINDINGS
# ==================================================
def export_to_onnx(engine: RadiantCoreEngine, state_dim: int, context_dim: int,
                   sample_inputs: Tuple[torch.Tensor, torch.Tensor],
                   onnx_path: str = "radiant_engine.onnx"):
    """Export the engine's step function to ONNX for Rust integration."""
    engine.eval()
    P, C = sample_inputs

    class StepWrapper(nn.Module):
        def __init__(self, system):
            super().__init__()
            self.system = system

        def forward(self, P, C, alpha, beta, base_dt, noise_scale, mode):
            mode_str = 'sde' if mode == 0 else 'projection'
            P_next, E, sigma, dt = self.system.step(P, C, alpha, beta, base_dt, noise_scale, mode_str)
            return P_next, E, sigma, dt

    wrapper = StepWrapper(engine.system)
    alpha = torch.tensor(0.05).to(P.device)
    beta = torch.tensor(0.02).to(P.device)
    base_dt = torch.tensor(1.0).to(P.device)
    noise_scale = torch.tensor(0.1).to(P.device)
    mode = torch.tensor(0, dtype=torch.long).to(P.device)

    torch.onnx.export(
        wrapper,
        (P, C, alpha, beta, base_dt, noise_scale, mode),
        onnx_path,
        input_names=['P', 'C', 'alpha', 'beta', 'base_dt', 'noise_scale', 'mode'],
        output_names=['P_next', 'E', 'sigma', 'dt'],
        dynamic_axes={'P': {0: 'batch'}, 'C': {0: 'batch'}, 'P_next': {0: 'batch'}},
        opset_version=14
    )
    print(f"Exported ONNX model to {onnx_path}")

    rust_code = '''
    // Rust example using tract-onnx
    use tract_onnx::prelude::*;
    fn load_engine() -> Result<SimplePlan<Box<dyn TypedOp>>, TractError> {
        let model = tract_onnx::onnx()
            .model_for_path("radiant_engine.onnx")?
            .into_optimized()?
            .into_runnable()?;
        Ok(model)
    }
    // Usage: feed tensors for P, C, alpha, beta, base_dt, noise_scale, mode
    '''
    with open("rust_bindings_example.rs", "w") as f:
        f.write(rust_code)
    print("Rust binding example saved to rust_bindings_example.rs")


# ==================================================
# 12. TRAINING LOOP (with bifurcation loss + human supervision)
# ==================================================
def train_radiant_engine(engine: RadiantCoreEngine, train_loader, val_loader,
                         epochs=100, lr=1e-3, device='cpu',
                         lambda_bifurcation=0.01, lambda_supervision=1.0):
    """
    Train the engine.
    - Supervised loss: MSE between predicted state and target (optional).
    - Bifurcation loss: encourages γ < γ_c for stochastic stability.
    """
    optimizer = torch.optim.Adam(engine.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    engine.train()

    for epoch in range(epochs):
        total_loss = 0.0
        for batch in train_loader:
            P, C, target_P = batch
            P = P.to(device)
            C = C.to(device)
            target_P = target_P.to(device)

            optimizer.zero_grad()
            out = engine.rollout(P, C, steps=5, training=True)
            P_pred = out["state"]

            loss_sup = loss_fn(P_pred, target_P) if target_P is not None else 0.0

            # Stability regularisation
            gamma_c = compute_critical_gamma(engine.system.energy, engine.system.muF,
                                             engine.alpha.item(), engine.beta.item())
            gamma = engine.system.uncertainty.gamma
            gamma_tensor = gamma if isinstance(gamma, torch.Tensor) else torch.tensor(gamma)
            loss_bif = torch.relu(gamma_tensor - gamma_c) * lambda_bifurcation

            loss = loss_sup * lambda_supervision + loss_bif
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(train_loader):.4f}")

    return engine


# ==================================================
# 13. EXAMPLE USAGE
# ==================================================
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    engine = RadiantCoreEngine(state_dim=4, context_dim=2).to(device)

    # Dummy training data (random)
    train_loader = [(torch.randn(8, 4), torch.randn(8, 2), torch.randn(8, 4)) for _ in range(10)]
    val_loader = []
    # Uncomment to train:
    # engine = train_radiant_engine(engine, train_loader, val_loader, epochs=2, device=device)

    # 2D visualisation (needs state_dim >=2)
    ctx = np.random.randn(2)
    plot_2d_landscape(engine, ctx, save_path="radiant_landscape.png")

    # ONNX export
    sample_P = torch.randn(1, 4).to(device)
    sample_C = torch.randn(1, 2).to(device)
    export_to_onnx(engine, state_dim=4, context_dim=2,
                   sample_inputs=(sample_P, sample_C),
                   onnx_path="radiant_engine.onnx")

    print("All done.")
