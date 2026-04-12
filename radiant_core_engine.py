"""
radiant_core_engine.py

Deep learning implementation of the Radiant Core Engine with:
- Energy model (distance to constraint)
- Lipschitz‑constrained dynamics μF
- State‑dependent uncertainty
- Adaptive time step
- SDE and projection modes
- Presence score
- 2D visualization (energy landscape + vector field)
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
from typing import Dict, Optional, Tuple, Union, Callable
import os

# ==================================================
# 1. ENERGY MODEL
# ==================================================
class EnergyModel(nn.Module):
    """Neural net approximating distance to constraint manifold."""
    def __init__(self, state_dim: int, context_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim + context_dim, hidden_dim)),
            nn.ReLU(),
            utils.spectral_norm(nn.Linear(hidden_dim, 1))
        )

    def forward(self, P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        x = torch.cat([P, C], dim=-1)
        E = self.net(x)
        return torch.tanh(E)   # bounded energy


# ==================================================
# 2. DYNAMICS FIELD μF
# ==================================================
class MuF(nn.Module):
    """Lipschitz‑constrained operator representing Architect Constant."""
    def __init__(self, state_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim, hidden_dim)),
            nn.Tanh(),
            utils.spectral_norm(nn.Linear(hidden_dim, state_dim))
        )

    def forward(self, P: torch.Tensor) -> torch.Tensor:
        return 0.5 * torch.tanh(self.net(P))


# ==================================================
# 3. UNCERTAINTY MODEL (γ‑controlled)
# ==================================================
class UncertaintyNet(nn.Module):
    def __init__(self, sigma0: float = 0.01, learn_gamma: bool = False, gamma_init: float = 0.5):
        super().__init__()
        self.sigma0 = sigma0
        if learn_gamma:
            self.gamma = nn.Parameter(torch.tensor(gamma_init))
        else:
            self.register_buffer('gamma', torch.tensor(gamma_init))

    def forward(self, grad_norm: torch.Tensor) -> torch.Tensor:
        gamma = self.gamma if isinstance(self.gamma, torch.Tensor) else torch.tensor(self.gamma)
        return self.sigma0 + gamma * grad_norm


# ==================================================
# 4. ENERGY GRADIENT
# ==================================================
def energy_gradient(energy_model: EnergyModel, P: torch.Tensor, C: torch.Tensor, create_graph: bool = False):
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
        self.uncertainty = UncertaintyNet(learn_gamma=use_learned_gamma)

    def step(self, P: torch.Tensor, C: torch.Tensor,
             alpha: float = 0.05, beta: float = 0.02,
             base_dt: float = 1.0, noise_scale: float = 0.1,
             mode: str = "sde") -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        E, gradE = energy_gradient(self.energy, P, C, create_graph=False)
        grad_norm = gradE.norm(dim=-1, keepdim=True)
        sigma = self.uncertainty(grad_norm)
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
    return torch.sigmoid(-(E + sigma))


# ==================================================
# 8. CORE ENGINE (with adaptive α/β correction)
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
# 9. VISUALIZATION (2D landscape + vector field)
# ==================================================
def plot_2d_landscape(engine: RadiantCoreEngine, context: np.ndarray,
                      xlim=(-3,3), ylim=(-3,3), resolution=100,
                      save_path="energy_landscape.png"):
    """Plot energy landscape and vector field for a 2D slice of state space."""
    device = next(engine.parameters()).device
    x = np.linspace(xlim[0], xlim[1], resolution)
    y = np.linspace(ylim[0], ylim[1], resolution)
    X, Y = np.meshgrid(x, y)
    points = np.stack([X.ravel(), Y.ravel()], axis=1)
    # zero pad to full state_dim (assuming state_dim >=2)
    state_dim = engine.system.energy.net[0].in_features - engine.system.energy.net[0].in_features? Actually we need context_dim. Let's compute.
    # Better: get state_dim from the first linear layer's input size minus context_dim.
    first_linear = engine.system.energy.net[0]
    total_in = first_linear.in_features
    context_dim = engine.system.energy.net[0].in_features - 2  # rough, but we'll pass context explicitly
    # We'll use a given context vector (repeat for all points)
    C_tensor = torch.tensor(context, dtype=torch.float32).to(device).unsqueeze(0).repeat(resolution*resolution, 1)
    P_tensor = torch.tensor(points, dtype=torch.float32).to(device)
    with torch.no_grad():
        E_vals = engine.system.energy(P_tensor, C_tensor).cpu().numpy().reshape(resolution, resolution)
        # Compute gradient field (for vector field)
        P_req = P_tensor.clone().detach().requires_grad_(True)
        E_sum = engine.system.energy(P_req, C_tensor).sum()
        grad = torch.autograd.grad(E_sum, P_req)[0].cpu().numpy()
        U = grad[:, 0].reshape(resolution, resolution)
        V = grad[:, 1].reshape(resolution, resolution)

    plt.figure(figsize=(10,8))
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
# 10. ONNX EXPORT + RUST BINDINGS
# ==================================================
def export_to_onnx(engine: RadiantCoreEngine, state_dim: int, context_dim: int,
                   sample_inputs: Tuple[torch.Tensor, torch.Tensor],
                   onnx_path: str = "radiant_engine.onnx"):
    """Export the engine's step function to ONNX for Rust integration."""
    engine.eval()
    P, C = sample_inputs
    # We'll export the inner system.step function (single step)
    class StepWrapper(nn.Module):
        def __init__(self, system):
            super().__init__()
            self.system = system
        def forward(self, P, C, alpha, beta, base_dt, noise_scale, mode):
            # mode as integer: 0 for 'sde', 1 for 'projection'
            mode_str = 'sde' if mode == 0 else 'projection'
            P_next, E, sigma, dt = self.system.step(P, C, alpha, beta, base_dt, noise_scale, mode_str)
            return P_next, E, sigma, dt
    wrapper = StepWrapper(engine.system)
    # Dummy inputs for ONNX
    alpha = torch.tensor(0.05).to(P.device)
    beta = torch.tensor(0.02).to(P.device)
    base_dt = torch.tensor(1.0).to(P.device)
    noise_scale = torch.tensor(0.1).to(P.device)
    mode = torch.tensor(0, dtype=torch.long).to(P.device)
    torch.onnx.export(wrapper, (P, C, alpha, beta, base_dt, noise_scale, mode), onnx_path,
                      input_names=['P', 'C', 'alpha', 'beta', 'base_dt', 'noise_scale', 'mode'],
                      output_names=['P_next', 'E', 'sigma', 'dt'],
                      dynamic_axes={'P': {0: 'batch'}, 'C': {0: 'batch'}, 'P_next': {0: 'batch'}},
                      opset_version=14)
    print(f"Exported ONNX model to {onnx_path}")

    # Rust binding example (as comment)
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
# 11. TRAINING LOOP (with bifurcation loss + human supervision)
# ==================================================
def train_radiant_engine(engine: RadiantCoreEngine, train_loader, val_loader,
                         epochs=100, lr=1e-3, device='cpu',
                         lambda_bifurcation=0.01, lambda_supervision=1.0):
    """Train the engine with optional human-target supervision and bifurcation condition."""
    optimizer = torch.optim.Adam(engine.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    engine.train()

    for epoch in range(epochs):
        total_loss = 0.0
        for batch in train_loader:
            P, C, target_P = batch   # target_P is optional (human supervision)
            P = P.to(device); C = C.to(device); target_P = target_P.to(device)

            optimizer.zero_grad()
            # Rollout for a few steps
            out = engine.rollout(P, C, steps=5, training=True)
            P_pred = out["state"]
            # Supervised loss
            loss_sup = loss_fn(P_pred, target_P) if target_P is not None else 0.0

            # Bifurcation loss: encourage gamma < gamma_c (stability)
            gamma = engine.system.uncertainty.gamma
            # approximate critical gamma for given alpha, beta (simplified)
            alpha_val = engine.alpha.item()
            beta_val = engine.beta.item()
            L = 1.0  # Lipschitz bound of μF (approx)
            dim = P.shape[-1]
            numerator = 2 * alpha_val * (1 + beta_val) * L - (alpha_val ** 2) * ((1 + beta_val) ** 2) * (L ** 2)
            if numerator > 0:
                gamma_c = np.sqrt(numerator) / (alpha_val * L * np.sqrt(dim))
            else:
                gamma_c = 0.0
            gamma_tensor = gamma if isinstance(gamma, torch.Tensor) else torch.tensor(gamma)
            loss_bif = torch.relu(gamma_tensor - gamma_c) * lambda_bifurcation

            loss = loss_sup * lambda_supervision + loss_bif
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(train_loader):.4f}")

    return engine


# ==================================================
# 12. EXAMPLE USAGE
# ==================================================
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    engine = RadiantCoreEngine(state_dim=4, context_dim=2).to(device)

    # Dummy training data (random)
    train_loader = [(torch.randn(8,4), torch.randn(8,2), torch.randn(8,4)) for _ in range(10)]
    val_loader = []
    # Uncomment to train:
    # engine = train_radiant_engine(engine, train_loader, val_loader, epochs=2, device=device)

    # 2D visualization (needs state_dim >=2)
    ctx = np.random.randn(2)
    plot_2d_landscape(engine, ctx, save_path="radiant_landscape.png")

    # ONNX export
    sample_P = torch.randn(1,4).to(device)
    sample_C = torch.randn(1,2).to(device)
    export_to_onnx(engine, state_dim=4, context_dim=2,
                   sample_inputs=(sample_P, sample_C),
                   onnx_path="radiant_engine.onnx")

    print("All done.")
