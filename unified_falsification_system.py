"""
unified_falsification_system.py

A falsification-driven engine that learns a survivability kernel by probing extreme directions,
adapting to failure asymmetries, and recursively re-centering the origin at the Chebyshev center.

Based on the principle: truth is the intersection of constraints revealed by failure boundaries
when the origin is corrupted.

Author: Radiant Protocol
License: MIT
"""

import numpy as np
from scipy.optimize import linprog
from typing import List, Tuple, Optional, Dict, Union
import warnings


# ============================================================
# UTILITIES
# ============================================================
def normalize(v: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    """Return unit vector; zero vector unchanged."""
    norm = np.linalg.norm(v)
    if norm < tol:
        return v
    return v / norm


def is_independent(d: np.ndarray, basis: List[np.ndarray], tol: float = 1e-6) -> bool:
    """
    Check if direction d is linearly independent of the orthonormal basis.
    For an orthonormal basis, d is dependent iff the residual after projecting
    onto the basis has near‑zero norm.
    """
    w = d.copy()
    for b in basis:
        w -= np.dot(w, b) * b
    return np.linalg.norm(w) > tol


def orthogonalize(vectors: List[np.ndarray]) -> List[np.ndarray]:
    """Gram–Schmidt orthogonalisation, returning orthonormal basis."""
    basis = []
    for v in vectors:
        w = v.copy()
        for b in basis:
            w -= np.dot(w, b) * b
        norm = np.linalg.norm(w)
        if norm > 1e-8:
            basis.append(w / norm)
    return basis


# ============================================================
# SURVIVABILITY KERNEL (Convex Polytope)
# ============================================================
class SurvivabilityKernel:
    """
    Convex polytope defined by half‑spaces n_i · P ≤ b_i.
    Supports adding constraints, safety checks, projection (POCS),
    Chebyshev center computation, and failure weight tracking.
    """

    def __init__(self, dim: int, epsilon: float = 1e-6, weight_decay: float = 0.95):
        """
        Args:
            dim: Dimension of the state space.
            epsilon: Safety margin added to each constraint.
            weight_decay: Exponential decay factor for failure weights.
        """
        self.dim = dim
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.constraints: List[Tuple[np.ndarray, float]] = []   # (normal, bound)
        self._basis: List[np.ndarray] = []                      # orthonormal basis of normals
        self._failure_weights: Dict[Tuple, float] = {}          # key: rounded normal tuple
        self._cached_center: Optional[np.ndarray] = None
        self._cache_valid: bool = False

    def add_constraint(self, normal: np.ndarray, boundary_point: np.ndarray, weight: float = 1.0) -> None:
        """Add a half‑space constraint derived from a failure boundary."""
        normal = normalize(normal)
        bound = np.dot(normal, boundary_point) - self.epsilon
        self.constraints.append((normal, bound))

        key = tuple(np.round(normal, 6))
        self._failure_weights[key] = self._failure_weights.get(key, 0) + weight

        # Maintain orthonormal basis (for efficient independence checks)
        self._basis = orthogonalize([normal] + self._basis)
        self._cache_valid = False

    def get_weight(self, d: np.ndarray) -> float:
        """Return accumulated failure weight for direction d or its opposite."""
        d = normalize(d)
        key = tuple(np.round(d, 6))
        key_neg = tuple(np.round(-d, 6))
        return max(self._failure_weights.get(key, 0.0),
                   self._failure_weights.get(key_neg, 0.0))

    def is_safe(self, P: np.ndarray) -> bool:
        """Check if point satisfies all constraints (with numerical tolerance)."""
        return all(np.dot(n, P) <= b + 1e-9 for n, b in self.constraints)

    def project(self, P: np.ndarray, max_iter: int = 50) -> np.ndarray:
        """Project a point onto the feasible set using alternating projections (POCS)."""
        P_proj = P.copy()
        for _ in range(max_iter):
            changed = False
            for n, b in self.constraints:
                val = np.dot(n, P_proj)
                if val > b:
                    P_proj -= (val - b) * n
                    changed = True
            if not changed:
                break
        return P_proj

    def chebyshev_center(self, force_recompute: bool = False) -> np.ndarray:
        """
        Compute the Chebyshev center (center of largest inscribed ball) by solving a linear program.
        Caches result.
        """
        if self._cache_valid and not force_recompute:
            return self._cached_center

        if not self.constraints:
            self._cached_center = np.zeros(self.dim)
            self._cache_valid = True
            return self._cached_center

        # Variables: [P, r] where r is the radius (maximise r)
        c = np.zeros(self.dim + 1)
        c[-1] = -1.0   # maximise r

        A_ub = []
        b_ub = []
        for n, b in self.constraints:
            row = np.append(n, np.linalg.norm(n))
            A_ub.append(row)
            b_ub.append(b)
        # r >= 0
        A_ub.append(np.append(np.zeros(self.dim), -1.0))
        b_ub.append(0.0)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = linprog(c, A_ub=A_ub, b_ub=b_ub, method='highs')

        if res.success:
            self._cached_center = res.x[:-1]
            self._cache_valid = True
            return self._cached_center
        else:
            # Fallback: project zero (geometric median of feasible set)
            center = self.project(np.zeros(self.dim))
            self._cached_center = center
            self._cache_valid = True
            return center


# ============================================================
# INTERPRETATION MODEL
# ============================================================
class Interpretation:
    """Learnable mapping from input to latent state: P = tanh(W @ x)."""

    def __init__(self, dim: int, rng: Optional[np.random.Generator] = None):
        if rng is None:
            rng = np.random.default_rng()
        self.W = rng.normal(0, 0.1, size=(dim, dim))

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass: tanh(W @ x)."""
        z = self.W @ x
        self._z = z                     # cache for gradient computation
        return np.tanh(z)

    def backward(self, grad_output: np.ndarray, x: np.ndarray) -> np.ndarray:
        """
        Compute gradient of loss w.r.t. W given gradient w.r.t. output (dL/dP).
        dL/dW = (dL/dP * (1 - tanh(z)^2)) @ x^T
        """
        # derivative of tanh is 1 - tanh(z)^2
        tanh_z = np.tanh(self._z)
        dtanh = 1.0 - tanh_z * tanh_z
        grad_z = grad_output * dtanh
        return np.outer(grad_z, x)

    def update(self, grad_W: np.ndarray, lr: float = 0.01) -> None:
        """Update weights using gradient descent."""
        self.W -= lr * grad_W


# ============================================================
# EXPLORATION POLICY
# ============================================================
class ExplorationPolicy:
    """
    Decides whether to ACT (use current interpretation), PROBE (explore), or SILENCE.
    When probing, it selects a direction from the kernel's basis with probability
    proportional to failure weight, or a random independent direction.
    """

    def __init__(self, threshold: float = 1.0, probe_prob: float = 0.2, temperature: float = 0.5):
        self.threshold = threshold
        self.probe_prob = probe_prob
        self.temperature = temperature

    def decide(self, uncertainty: float, kernel: SurvivabilityKernel, dim: int,
               rng: np.random.Generator) -> Tuple[str, Optional[np.ndarray]]:
        """
        Returns (decision, info). Decision is one of 'ACT', 'PROBE', 'SILENCE'.
        If PROBE, info is the direction to probe.
        """
        if uncertainty > self.threshold:
            # Structured exploration: sample from basis with weights
            if kernel._basis:
                weights = np.array([kernel.get_weight(d) + 1e-6 for d in kernel._basis])
                probs = np.exp(weights / self.temperature)
                probs /= probs.sum()
                idx = rng.choice(len(kernel._basis), p=probs)
                return "PROBE", kernel._basis[idx]

            # Stochastic exploration: random independent direction
            if rng.random() < self.probe_prob:
                d = normalize(rng.normal(0, 1, size=dim))
                if is_independent(d, kernel._basis):
                    return "PROBE", d

        if uncertainty <= self.threshold:
            return "ACT", None

        return "SILENCE", None


# ============================================================
# LEARNER (Loss and Gradient Utilities)
# ============================================================
class Learner:
    @staticmethod
    def mse_loss(pred: np.ndarray, target: np.ndarray) -> float:
        return float(np.mean((pred - target) ** 2))

    @staticmethod
    def mse_grad(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
        """Gradient of MSE w.r.t. prediction: 2*(pred - target)/N."""
        return 2.0 * (pred - target) / pred.size


# ============================================================
# UNIFIED FALSIFICATION SYSTEM
# ============================================================
class UnifiedFalsificationSystem:
    """
    Main engine integrating interpretation, kernel learning, and falsification.
    """

    def __init__(self, system, kernel: SurvivabilityKernel, dim: int, seed: Optional[int] = None):
        """
        Args:
            system: Object with method `failure(state) -> bool`.
            kernel: SurvivabilityKernel instance.
            dim: Dimension of state space.
            seed: Random seed for reproducibility.
        """
        self.system = system
        self.kernel = kernel
        self.dim = dim
        self.rng = np.random.default_rng(seed)

        self.model = Interpretation(dim, rng=self.rng)
        self.learner = Learner()
        self.policy = ExplorationPolicy()

        self.seed_state = self._find_safe_seed()

    def _find_safe_seed(self, max_attempts: int = 500) -> np.ndarray:
        """Find a safe initial state (not in failure)."""
        for _ in range(max_attempts):
            p = self.rng.normal(0, 5.0, size=self.dim)
            if not self.system.failure(p):
                return p
        # Ultimate fallback: project zero (might still be unsafe)
        return self.kernel.project(np.zeros(self.dim))

    def uncertainty(self, P: np.ndarray) -> float:
        """Compute uncertainty as distance to kernel plus a small bias."""
        if not self.kernel.constraints:
            return np.linalg.norm(P)
        proj = self.kernel.project(P)
        return np.linalg.norm(P - proj) + 0.1 * np.linalg.norm(P)

    def probe(self, direction: np.ndarray) -> Optional[np.ndarray]:
        """
        Probe a direction from the current seed state, find failure boundary,
        add constraint, and return boundary point.
        """
        weight = self.kernel.get_weight(direction)
        t_max = 10.0 * (1.0 + weight)
        steps = 25 + int(10 * weight)

        t_low, t_high = 0.0, t_max
        # Check if failure occurs at t_max
        if not self.system.failure(self.seed_state + t_high * direction):
            return None

        for _ in range(steps):
            t_mid = (t_low + t_high) / 2.0
            P_mid = self.seed_state + t_mid * direction
            if self.system.failure(P_mid):
                t_high = t_mid
            else:
                t_low = t_mid

        boundary = self.seed_state + t_high * direction
        self.kernel.add_constraint(direction, boundary, weight=1.0)
        return boundary

    def step(self, x: np.ndarray, target: Optional[np.ndarray] = None) -> Dict:
        """
        One step of the system: interpret input, decide action, update state.

        Returns:
            Dictionary with keys: interpreted, reflected, uncertainty, decision,
            output, loss, seed.
        """
        # 1. Interpretation
        interpreted = self.model.forward(x)

        # 2. Uncertainty (before projection)
        u = self.uncertainty(interpreted)

        # 3. Decision
        decision, info = self.policy.decide(u, self.kernel, self.dim, self.rng)

        # 4. Projection (safe state)
        reflected = self.kernel.project(interpreted) if self.kernel.constraints else interpreted

        output = None
        loss = None

        if decision == "ACT":
            output = reflected
            if target is not None:
                # Supervised gradient
                grad_pred = self.learner.mse_grad(output, target)
                grad_W = self.model.backward(grad_pred, x)
                # Consistency gradient: pull interpretation toward its projection
                consistency_grad_pred = 0.1 * (interpreted - reflected)
                grad_W += self.model.backward(consistency_grad_pred, x)
                self.model.update(grad_W)
                loss = self.learner.mse_loss(output, target)

        elif decision == "PROBE":
            boundary = self.probe(info)
            if boundary is not None:
                # Recenter origin at Chebyshev center
                center = self.kernel.chebyshev_center()
                if not self.kernel.is_safe(center):
                    center = self.kernel.project(center)
                if self.system.failure(center):
                    center = self._find_safe_seed()
                self.seed_state = center

                # Learn from boundary: treat projected boundary as pseudo‑target
                proj_boundary = self.kernel.project(boundary)
                grad_pred = 0.5 * (interpreted - proj_boundary)   # pull toward projected boundary
                grad_W = self.model.backward(grad_pred, x)
                self.model.update(grad_W)

        # SILENCE: no update

        return {
            "interpreted": interpreted,
            "reflected": reflected,
            "uncertainty": u,
            "decision": decision,
            "output": output,
            "loss": loss,
            "seed": self.seed_state.copy()
        }


# ============================================================
# EXAMPLE SYSTEM AND DEMONSTRATION
# ============================================================
class SimpleSystem:
    """Example system: failure if norm > 10 (ball of radius 10)."""
    @staticmethod
    def failure(P: np.ndarray) -> bool:
        return np.linalg.norm(P) > 10.0


if __name__ == "__main__":
    dim = 5
    kernel = SurvivabilityKernel(dim)
    system = SimpleSystem()
    ufs = UnifiedFalsificationSystem(system, kernel, dim, seed=42)

    print("Running falsification-driven learning...")
    for t in range(50):
        x = np.random.randn(dim)
        target = np.zeros(dim)   # we want to learn to map to zero
        result = ufs.step(x, target)
        print(f"Step {t:2d}: decision={result['decision']:6s}, uncertainty={result['uncertainty']:.4f}",
              end="")
        if result['loss'] is not None:
            print(f", loss={result['loss']:.6f}")
        else:
            print()

    print(f"\nFinal kernel constraints: {len(kernel.constraints)}")
    print("Chebyshev center:", ufs.kernel.chebyshev_center())
    print("All done.")
