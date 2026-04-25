"""
radiant_core_engine.py

Grounded Radiant Core Engine v3.0 — presence learned from reality,
energy anchored to real constraints, open‑loop task accountability.

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
from typing import Dict, Optional, Tuple, Callable, List, Any

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
    """
    E = ||φ_learned||² + ||φ_real||² + residual.
    φ_real is given by an external callable (register_real_constraints).
    """
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
    """Basic stability: low energy + low noise."""
    return torch.sigmoid(-(E + sigma))

def responsiveness(P: torch.Tensor, P_next: torch.Tensor) -> torch.Tensor:
    """Controlled activity: moderate change between steps."""
    norm = torch.norm(P_next - P, dim=-1, keepdim=True)
    # Optimal response near 0.5 after sigmoid scaling
    return torch.exp(-((norm - 0.5) ** 2) / 0.1)

def relevance(P_next: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Cosine similarity to a target (e.g., next real state)."""
    if target is None or target.numel() == 0:
        return torch.ones_like(P_next[:, :1])
    cos = nn.CosineSimilarity(dim=-1)(P_next, target)
    return (cos + 1.0) / 2.0  # map [-1,1] to [0,1]

def comprehensive_presence(E: torch.Tensor, sigma: torch.Tensor,
                           P: torch.Tensor, P_next: torch.Tensor,
                           target: Optional[torch.Tensor] = None,
                           w: Tuple[float,float,float] = (0.4, 0.3, 0.3)) -> torch.Tensor:
    """
    Presence = w1 * stability + w2 * responsiveness + w3 * relevance.
    """
    stab = stability_score(E, sigma)
    resp = responsiveness(P, P_next)
    rel = relevance(P_next, target) if target is not None else torch.ones_like(stab)
    return w[0]*stab + w[1]*resp + w[2]*rel

# Legacy compatibility: simple stability presence
def presence_score(E: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
    return stability_score(E, sigma)


# ============================================================
# 8. CORE ENGINE (adaptive α/β, real presence ground truth)
# ============================================================
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
        for _ in range(steps):
            if not training:
                P = P.detach()
            P_next, E, sigma, dt = self.system.step(
                P, C, self.alpha.item(), self.beta.item(), mode=mode,
                create_graph=training, **step_kwargs
            )
            pres = comprehensive_presence(E, sigma, P, P_next, target) if target is not None else presence_score(E, sigma)
            if not training:
                self.adjust_hyperparams(pres)
            P = P_next
        return {"state": P, "energy": E, "uncertainty": sigma, "dt": dt, "presence": pres}

    def forward(self, P: torch.Tensor, C: torch.Tensor, **kwargs) -> Dict[str, torch.Tensor]:
        return self.rollout(P, C, **kwargs)


# ============================================================
# 9. TRAINING (open‑loop, with real anchors)
# ============================================================
def train_with_ground_truth(
    engine: RadiantCoreEngine,
    train_data: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],  # (P, C, target_P)
    real_presence_fn: Optional[Callable[[torch.Tensor, torch.Tensor], torch.Tensor]] = None,
    external_eval_fn: Optional[Callable[[torch.Tensor, torch.Tensor], float]] = None,
    epochs: int = 50, lr: float = 1e-3, device: str = 'cpu',
    lambda_presence: float = 0.1, lambda_task: float = 1.0,
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
            out = engine.rollout(P, C, steps=3, training=True, target=target_P)
            P_pred = out["state"]

            # Task loss
            task_loss = loss_fn(P_pred, target_P) if target_P is not None else torch.zeros(1, device=device)

            # Presence alignment loss (optional)
            presence_loss = torch.zeros(1, device=device)
            if real_presence_fn is not None:
                real_pres = real_presence_fn(P_pred, C)  # external ground truth
                presence_loss = loss_fn(out["presence"].float(), real_pres)

            # External evaluation (optional)
            ext_loss = torch.zeros(1, device=device)
            if external_eval_fn is not None:
                ext_score = external_eval_fn(P_pred, target_P)
                ext_loss = torch.tensor(1.0 - ext_score, device=device)  # maximize external score

            loss = lambda_task * task_loss + lambda_presence * presence_loss + 0.1 * ext_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(engine.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        if epoch % 10 == 0:
            print(f"Epoch {epoch}: loss {total_loss/len(train_data):.4f}")

    return engine


# ============================================================
# 10. EXAMPLE: structured synthetic task (stability detection)
# ============================================================
def generate_stability_data(num_samples: int = 200, dim: int = 4) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
    """
    Synthetic task: classify/regress stability of dynamics.
    Returns (P, C, target_P) where target_P is the next stable state.
    """
    data = []
    for _ in range(num_samples):
        P = torch.randn(dim) * 2
        C = torch.randn(2)  # context vector
        # Simulate stability: target is a damped version of P
        target_P = 0.6 * P + 0.1 * torch.randn(dim)
        data.append((P, C, target_P))
    return data


# ============================================================
# 11. EXAMPLE USAGE
# ============================================================
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    engine = RadiantCoreEngine(state_dim=4, context_dim=2).to(device)

    # Generate structured training data
    train_data = generate_stability_data(100, dim=4)
    # Train with a simple real constraint: state norm should not explode
    def real_cstr(P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        return torch.relu(torch.norm(P, dim=-1, keepdim=True) - 5.0)  # violation if norm > 5

    engine.system.energy.register_real_constraints(real_cstr)

    # Define a dummy real presence signal (here based on distance to origin)
    def real_presence_fn(P: torch.Tensor, C: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(-torch.norm(P, dim=-1, keepdim=True))

    # Train with presence alignment
    engine = train_with_ground_truth(
        engine, train_data, real_presence_fn=real_presence_fn,
        epochs=20, lr=1e-3, device=device, lambda_presence=0.1
    )

    # Evaluate
    P0 = torch.randn(1, 4).to(device)
    C0 = torch.randn(1, 2).to(device)
    out = engine(P0, C0, target=0.6*P0)  # target for comprehensive presence
    print("Presence:", out["presence"].item())
