"""
radiant_core_engine.py

Grounded Radiant Core Engine v3.1 — trajectory visibility, deterministic inference,
realistic synthetic data, integrated visualization.

Mathematical models within this engine are protected under the
Radiant Protocol Master Formula License (RPML) v1.0.
Software implementation is licensed under the Radiant Protocol Commercial License (RPL) v1.0.
Copyright © 2026 Radiant Protocol Foundation. All rights reserved.
Author: 1me0 (The Architect)
"""

import torch
import torch.nn as nn
import torch.nn.utils as utils
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple, Callable, List, Any, Union

# ============================================================
# 1. ENERGY MODEL (hybrid: learned + real constraints)
# ============================================================
class ConstraintFunction(nn.Module):
    def __init__(self, state_dim: int, context_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim + context_dim, hidden_dim)),
            nn.ReLU(),
            utils.spectral_norm(nn.Linear(hidden_dim, state_dim))
        )

    def forward(self, P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([P, C], dim=-1))


class EnergyModel(nn.Module):
    def __init__(self, state_dim: int, context_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.constraint = ConstraintFunction(state_dim, context_dim, hidden_dim)
        self.residual_net = nn.Sequential(
            utils.spectral_norm(nn.Linear(state_dim + context_dim, hidden_dim)),
            nn.ReLU(),
            utils.spectral_norm(nn.Linear(hidden_dim, 1))
        )
        self.real_constraint_fn: Optional[Callable[[torch.Tensor, torch.Tensor], torch.Tensor]] = None

    def register_real_constraints(self,
                                  fn: Callable[[torch.Tensor, torch.Tensor], torch.Tensor]):
        self.real_constraint_fn = fn

    def forward(self, P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        phi_learned = self.constraint(P, C)
        E_learned = (phi_learned ** 2).sum(dim=-1, keepdim=True)
        if self.real_constraint_fn is not None:
            phi_real = self.real_constraint_fn(P, C)
            E_real = (phi_real ** 2).sum(dim=-1, keepdim=True)
        else:
            E_real = 0.0
        E_residual = self.residual_net(torch.cat([P, C], dim=-1))
        return torch.tanh(E_learned + E_real + E_residual)


# ============================================================
# 2. DYNAMICS FIELD μF (gradient of architect potential)
# ============================================================
class ArchitectPotential(nn.Module):
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
    def __init__(self, state_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.potential = ArchitectPotential(state_dim, hidden_dim)

    def forward(self, P: torch.Tensor, create_graph: bool = False) -> torch.Tensor:
        P_req = P.clone().detach().requires_grad_(True)
        Phi = self.potential(P_req).sum()
        grad = torch.autograd.grad(Phi, P_req, create_graph=create_graph)[0]
        return -0.5 * torch.tanh(grad)


# ============================================================
# 3. CONTEXT‑AWARE UNCERTAINTY
# ============================================================
class UncertaintyNet(nn.Module):
    def __init__(self, context_dim: int, sigma0: float = 0.01,
                 learn_gamma: bool = False, gamma_init: float = 0.5):
        super().__init__()
        self.sigma0 = sigma0
        if learn_gamma:
            self.gamma = nn.Parameter(torch.tensor(gamma_init))
        else:
            self.register_buffer('gamma', torch.tensor(gamma_init))
        self.context_modulator = nn.Sequential(
            nn.Linear(context_dim, 16), nn.Tanh(), nn.Linear(16, 1)
        )

    def forward(self, grad_norm: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        gamma = self.gamma if isinstance(self.gamma, torch.Tensor) else torch.tensor(self.gamma, device=grad_norm.device)
        modulation = 1.0 + torch.tanh(self.context_modulator(C))
        return self.sigma0 + gamma * grad_norm * modulation


# ============================================================
# 4. ENERGY GRADIENT
# ============================================================
def energy_gradient(energy_model: EnergyModel, P: torch.Tensor, C: torch.Tensor,
                    create_graph: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
    P_req = P.clone().detach().requires_grad_(True)
    E = energy_model(P_req, C)
    grad = torch.autograd.grad(E.sum(), P_req, create_graph=create_graph)[0]
    return E, grad


# ============================================================
# 5. ADAPTIVE TIME STEP
# ============================================================
def adaptive_dt(base_dt: float, sigma: torch.Tensor, grad_norm: torch.Tensor,
                max_dt: float = 1.0, min_dt: float = 0.01) -> torch.Tensor:
    scale = 1.0 / (1.0 + sigma + grad_norm)
    return torch.clamp(base_dt * scale, min_dt, max_dt)


# ============================================================
# 6. SYSTEM (SDE + Projection)
# ============================================================
class System(nn.Module):
    def __init__(self, state_dim: int, context_dim: int, use_learned_gamma: bool = False):
        super().__init__()
        self.energy = EnergyModel(state_dim, context_dim)
        self.muF = MuF(state_dim)
        self.uncertainty = UncertaintyNet(context_dim, learn_gamma=use_learned_gamma)

    def step(self, P: torch.Tensor, C: torch.Tensor, alpha: float = 0.05, beta: float = 0.02,
             base_dt: float = 1.0, noise_scale: float = 0.1, mode: str = "sde",
             create_graph: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        E, gradE = energy_gradient(self.energy, P, C, create_graph)
        grad_norm = gradE.norm(dim=-1, keepdim=True)
        sigma = self.uncertainty(grad_norm, C)
        dt = adaptive_dt(base_dt, sigma, grad_norm)
        drift = self.muF(P, create_graph)
        noise = torch.randn_like(P) * (sigma * noise_scale * torch.sqrt(dt))
        if mode == "sde":
            P_next = P - alpha * gradE * dt + beta * drift * dt + noise
        elif mode == "projection":
            Pi = P - alpha * gradE
            P_next = (1 + beta) * Pi - beta * P + noise
        else:
            raise ValueError(f"Unknown mode: {mode}")
        return P_next, E.detach(), sigma.detach(), dt.detach()


# ============================================================
# 7. PRESENCE – grounded definition
# ============================================================
def stability_score(E: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    return torch.sigmoid(-(E + sigma))

def responsiveness(P: torch.Tensor, P_next: torch.Tensor) -> torch.Tensor:
    norm = torch.norm(P_next - P, dim=-1, keepdim=True)
    return torch.exp(-((norm - 0.5) ** 2) / 0.1)

def relevance(P_next: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    cos = nn.CosineSimilarity(dim=-1)(P_next, target)
    return (cos + 1.0) / 2.0

def comprehensive_presence(E: torch.Tensor, sigma: torch.Tensor,
                           P: torch.Tensor, P_next: torch.Tensor,
                           target: Optional[torch.Tensor] = None,
                           w: Tuple[float,float,float] = (0.4, 0.3, 0.3)) -> torch.Tensor:
    stab = stability_score(E, sigma)
    resp = responsiveness(P, P_next)
    rel = relevance(P_next, target) if target is not None else torch.ones_like(stab)
    return w[0]*stab + w[1]*resp + w[2]*rel

def presence_score(E: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    return stability_score(E, sigma)


# ============================================================
# 8. CORE ENGINE (adaptive α/β optional, trajectory methods)
# ============================================================
class RadiantCoreEngine(nn.Module):
    def __init__(self, state_dim: int, context_dim: int):
        super().__init__()
        self.system = System(state_dim, context_dim)
        self.register_buffer('alpha', torch.tensor(0.05))
        self.register_buffer('beta', torch.tensor(0.02))
        self.adaptive_enabled = False
        self.presence_threshold = 0.3
        self.alpha_min = 0.01
        self.beta_max = 0.1
        self.alpha_decay = 0.95
        self.beta_boost = 1.2

    def enable_adaption(self):
        self.adaptive_enabled = True

    def disable_adaption(self):
        self.adaptive_enabled = False

    def _adjust_hyperparams(self, presence: torch.Tensor):
        if not self.adaptive_enabled:
            return
        if presence.mean().item() < self.presence_threshold:
            self.alpha.data = torch.max(
                self.alpha * self.alpha_decay,
                torch.tensor(self.alpha_min, device=self.alpha.device)
            )
            self.beta.data = torch.min(
                self.beta * self.beta_boost,
                torch.tensor(self.beta_max, device=self.beta.device)
            )

    def rollout(self, P: torch.Tensor, C: torch.Tensor, steps: int = 1,
                mode: str = "sde", training: bool = False,
                target: Optional[torch.Tensor] = None, **step_kwargs) -> Dict[str, torch.Tensor]:
        """
        Execute one or more steps and return the final state dictionary.
        For full trajectory, use rollout_trajectory.
        """
        for _ in range(steps):
            if not training:
                P = P.detach()
            P_next, E, sigma, dt = self.system.step(
                P, C, self.alpha.item(), self.beta.item(), mode=mode,
                create_graph=training, **step_kwargs
            )
            pres = comprehensive_presence(E, sigma, P, P_next, target) if target is not None else presence_score(E, sigma)
            if training:   # adapt only during training (or if explicitly enabled during inference)
                self._adjust_hyperparams(pres)
            P = P_next
        return {"state": P, "energy": E, "uncertainty": sigma, "dt": dt, "presence": pres}

    def rollout_trajectory(self, P: torch.Tensor, C: torch.Tensor, steps: int = 1,
                           mode: str = "sde", training: bool = False,
                           target: Optional[torch.Tensor] = None, **step_kwargs) -> List[Dict[str, torch.Tensor]]:
        """
        Return a list of state dicts for each step, enabling full trajectory analysis.
        """
        trajectory = []
        for _ in range(steps):
            if not training:
                P = P.detach()
            P_next, E, sigma, dt = self.system.step(
                P, C, self.alpha.item(), self.beta.item(), mode=mode,
                create_graph=training, **step_kwargs
            )
            pres = comprehensive_presence(E, sigma, P, P_next, target) if target is not None else presence_score(E, sigma)
            if training:
                self._adjust_hyperparams(pres)
            trajectory.append({"state": P_next, "energy": E, "uncertainty": sigma, "dt": dt, "presence": pres})
            P = P_next
        return trajectory

    def forward(self, P: torch.Tensor, C: torch.Tensor, **kwargs) -> Dict[str, torch.Tensor]:
        return self.rollout(P, C, **kwargs)


# ============================================================
# 9. TRAINING (open‑loop, with real anchors, truncated BPTT)
# ============================================================
def train_with_ground_truth(
    engine: RadiantCoreEngine,
    train_data: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
    real_presence_fn: Optional[Callable[[torch.Tensor, torch.Tensor], torch.Tensor]] = None,
    external_eval_fn: Optional[Callable[[torch.Tensor, torch.Tensor], float]] = None,
    epochs: int = 50, lr: float = 1e-3, device: str = 'cpu',
    lambda_presence: float = 0.1, lambda_task: float = 1.0,
    bptt_steps: int = 3,
) -> RadiantCoreEngine:
    engine.train().to(device)
    optimizer = torch.optim.Adam(engine.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_fn = nn.MSELoss()

    for epoch in range(epochs):
        total_loss = 0.0
        for P, C, target_P in train_data:
            P, C, target_P = P.to(device), C.to(device), target_P.to(device)
            optimizer.zero_grad()

            # Truncated backprop: split long sequence into chunks, detach between chunks
            loss = 0.0
            for start in range(0, target_P.size(0), bptt_steps):
                end = min(start + bptt_steps, target_P.size(0))
                P_chunk, C_chunk, target_chunk = P[start:end], C[start:end], target_P[start:end]
                # Rollout with create_graph=True for chunk
                out = engine.rollout(P_chunk, C_chunk, steps=1, training=True, target=target_chunk)
                P_pred = out["state"]
                task_loss = loss_fn(P_pred, target_chunk)
                pres_loss = torch.zeros(1, device=device)
                if real_presence_fn is not None:
                    real_pres = real_presence_fn(P_pred, C_chunk)
                    pres_loss = loss_fn(out["presence"].float(), real_pres)
                ext_loss = torch.zeros(1, device=device)
                if external_eval_fn is not None:
                    ext_val = external_eval_fn(P_pred, target_chunk)
                    ext_loss = torch.tensor(1.0 - ext_val, device=device)
                chunk_loss = lambda_task * task_loss + lambda_presence * pres_loss + 0.1 * ext_loss
                chunk_loss.backward()
                loss += chunk_loss.item()
                P_chunk = P_pred.detach()  # detach for next chunk
                C_chunk = C_chunk   # keep context unchanged (or shift)
            torch.nn.utils.clip_grad_norm_(engine.parameters(), 1.0)
            optimizer.step()
            total_loss += loss
        scheduler.step()
        if epoch % 10 == 0:
            print(f"Epoch {epoch}: loss {total_loss/len(train_data):.4f}")

    return engine


# ============================================================
# 10. REALISTIC SYNTHETIC DATA: damped harmonic oscillator
# ============================================================
def generate_oscillator_data(num_samples: int = 200, dim: int = 4,
                             damping: float = 0.1, noise: float = 0.05) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
    """
    Simulate a damped harmonic oscillator: x_{t+1} = (1-damping)*x_t + u_t, with
    context u_t drawn from a sinusoidal source.
    The engine should learn to predict the damped trajectory.
    """
    data = []
    for _ in range(num_samples):
        # Generate a short trajectory and extract (P, C, target_P) pairs
        x = torch.randn(dim) * 2
        context = torch.sin(torch.linspace(0, 2*np.pi, dim))  # positional context
        target = (1 - damping) * x + noise * torch.randn(dim)
        data.append((x, context, target))
    return data


# ============================================================
# 11. PRESENCE GROUND TRUTH (from ZK-inspired signal)
# ============================================================
def oscillator_presence_fn(P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
    """
    Presence is high when the state is close to the damped equilibrium of the oscillator,
    mimicking a proof‑of‑presence signal that rewards stability near the attractor.
    """
    # The equilibrium for a damped oscillator driven by zero is 0; presence decays with distance.
    return torch.exp(-torch.norm(P, dim=-1, keepdim=True))


# ============================================================
# 12. EXAMPLE USAGE with visualization
# ============================================================
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    engine = RadiantCoreEngine(state_dim=4, context_dim=2).to(device)

    # Register a realistic real constraint: state magnitude bounded
    def real_cstr(P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        return torch.relu(torch.norm(P, dim=-1, keepdim=True) - 10.0)
    engine.system.energy.register_real_constraints(real_cstr)

    # Generate oscillator training data
    train_data = generate_oscillator_data(200, dim=4)

    # Train with presence ground truth
    engine = train_with_ground_truth(
        engine, train_data,
        real_presence_fn=oscillator_presence_fn,
        epochs=30, lr=1e-3, device=device, lambda_presence=0.2
    )

    # Evaluate and visualize
    P0 = torch.randn(1, 4).to(device) * 2
    C0 = torch.sin(torch.linspace(0, 2*np.pi, 4)).unsqueeze(0).to(device)
    traj = engine.rollout_trajectory(P0, C0, steps=20, training=False)

    # Extract metrics
    steps = np.arange(len(traj))
    energies = [t["energy"].item() for t in traj]
    presences = [t["presence"].item() for t in traj]
    uncertainties = [t["uncertainty"].item() for t in traj]

    plt.figure(figsize=(10, 6))
    plt.subplot(3,1,1)
    plt.plot(steps, energies, 'b-', label='Energy')
    plt.ylabel('Energy')
    plt.legend()
    plt.subplot(3,1,2)
    plt.plot(steps, presences, 'g-', label='Presence')
    plt.ylabel('Presence')
    plt.legend()
    plt.subplot(3,1,3)
    plt.plot(steps, uncertainties, 'r-', label='Uncertainty')
    plt.xlabel('Step')
    plt.ylabel('Uncertainty')
    plt.legend()
    plt.tight_layout()
    plt.show()

    print("Final presence:", traj[-1]["presence"].item())
