"""
meta_master_formula.py — Stochastic Meta‑Master Formula

P_{t+1} = Exp_{P_t}( η_t ∇_P E_ξ[ F( T_t(P; ξ) ) ] )

Mathematical models: RPML v1.0. Code: MIT.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional, Union
import numpy as np

# ---------------------------------------------------------------------------
# Manifold abstraction (extensible to spheres, hyperbolic, etc.)
# ---------------------------------------------------------------------------
class Manifold(ABC):
    @abstractmethod
    def exp(self, base: np.ndarray, tangent: np.ndarray) -> np.ndarray: ...
    def __repr__(self): return self.__class__.__name__

class EuclideanSpace(Manifold):
    """Flat space: Exp_{P}(v) = P + v."""
    def exp(self, base, tangent): return base + tangent

# ---------------------------------------------------------------------------
# Gradient estimators
# ---------------------------------------------------------------------------
def _finite_diff_grad(P, T, F, noise, nsamples=10, eps=1e-6):
    grad = np.zeros_like(P, dtype=float)
    for _ in range(nsamples):
        xi = noise()
        grad += (F(T(P + eps, xi)) - F(T(P - eps, xi))) / (2 * eps)
    return grad / nsamples

def _torch_grad(P_np, T_torch, F_torch, noise_torch, nsamples, device):
    """Gradient via PyTorch autograd (batched)."""
    import torch
    P = torch.tensor(P_np, dtype=torch.float32, device=device, requires_grad=True)
    # expand P to batch
    Pb = P.unsqueeze(0).expand(nsamples, -1)
    # sample noise batch (using noise_torch function)
    xi = noise_torch()
    if not isinstance(xi, torch.Tensor):
        xi = torch.tensor(xi, dtype=torch.float32, device=device)
    if xi.ndim == 1:
        xi = xi.unsqueeze(0).expand(nsamples, -1)
    else:
        xi = xi[:nsamples]  # ensure batch size
    Q = T_torch(Pb, xi)
    loss = F_torch(Q).mean()
    grad = torch.autograd.grad(loss, P)[0]
    return grad.cpu().numpy()

# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------
class MetaMasterFormula:
    def __init__(self,
                 manifold: Manifold,
                 transformation: Callable[[np.ndarray, object], np.ndarray],
                 objective: Callable[[np.ndarray], float],
                 noise_sampler: Callable[[], object],
                 eta: float = 1.0,
                 direction: str = 'maximize',
                 use_torch: bool = False,
                 torch_device: str = 'cpu',
                 grad_samples: int = 10,
                 # optional torch‑compatible versions
                 torch_transformation: Optional[Callable] = None,
                 torch_objective: Optional[Callable] = None,
                 torch_noise: Optional[Callable] = None):
        self.manifold = manifold
        self.T = transformation
        self.F = objective
        self.noise = noise_sampler
        self.eta = eta
        self.sign = 1.0 if direction == 'maximize' else -1.0
        self.use_torch = use_torch
        self.device = torch_device
        self.grad_samples = grad_samples
        self.T_torch = torch_transformation
        self.F_torch = torch_objective
        self.noise_torch = torch_noise

    def step(self, P):
        grad = self._gradient(P)
        return self.manifold.exp(P, self.sign * self.eta * grad)

    def _gradient(self, P):
        if self.use_torch and self.T_torch and self.F_torch and self.noise_torch:
            return _torch_grad(P, self.T_torch, self.F_torch,
                               self.noise_torch, self.grad_samples, self.device)
        else:
            return _finite_diff_grad(P, self.T, self.F, self.noise,
                                     self.grad_samples)

# ---------------------------------------------------------------------------
# Quick demo (finite‑difference)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # maximise –(Q–3)^2  →  expected optimum at Q≈3
    def T(P, xi): return P + xi
    def F(Q):      return -(Q - 3.0)**2
    def noise():   return np.random.randn(1) * 1.0

    engine = MetaMasterFormula(
        manifold=EuclideanSpace(),
        transformation=T,
        objective=F,
        noise_sampler=noise,
        eta=0.1,
        direction='maximize',
    )
    P = np.array([0.0])
    for t in range(20):
        P = engine.step(P)
        print(f"Step {t:2d}: P = {P[0]:.4f}")
    print(f"Final P ≈ {P[0]:.4f} (expected optimum ~3.0)")
