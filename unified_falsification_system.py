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
from typing import List, Tuple, Optional, Callable, Dict


# ============================================================
# UTILITIES
# ============================================================
def normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm < 1e-12:
        return v
    return v / norm


def is_independent(d: np.ndarray, basis: List[np.ndarray], tol: float = 1e-6) -> bool:
    for b in basis:
        if abs(np.dot(d, b)) > tol:
            return False
    return True


def orthogonalize(vectors: List[np.ndarray]) -> List[np.ndarray]:
    basis = []
    for v in vectors:
        w = v.copy()
        for b in basis:
            w -= np.dot(w, b) * b
        if np.linalg.norm(w) > 1e-8:
            basis.append(normalize(w))
    return basis


# ============================================================
# SURVIVABILITY KERNEL (Convex Polytope)
# ============================================================
class SurvivabilityKernel:
    """
    Convex polytope defined by half-spaces n_i · P ≤ b_i.
    Supports adding constraints, safety checking, projection (POCS),
    Chebyshev center computation, and failure weight tracking.
    """

    def __init__(self, dim: int, epsilon: float = 1e-6, weight_decay: float = 0.95):
        self.dim = dim
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.constraints: List[Tuple[np.ndarray, float]] = []   # (normal, bound)
        self._basis: List[np.ndarray] = []                     # orthonormal basis of normals
        self._failure_weights: Dict[Tuple, float] = {}         # key: direction tuple, value: weight
        self._cached_center: Optional[np.ndarray] = None
        self._cache_valid: bool = False

    def add_constraint(self, normal: np.ndarray, boundary_point: np.ndarray, weight: float = 1.0) -> None:
        normal = normalize(normal)
        bound = np.dot(normal, boundary_point) - self.epsilon
        self.constraints.append((normal, bound))

        key = tuple(np.round(normal, 6))
        self._failure_weights[key] = self._failure_weights.get(key, 0) + weight

        self._basis = orthogonalize([normal] + self._basis)
        self._cache_valid = False

    def get_weight(self, d: np.ndarray) -> float:
        d = normalize(d)
        key = tuple(np.round(d, 6))
        key_neg = tuple(np.round(-d, 6))
        return max(self._failure_weights.get(key, 0), self._failure_weights.get(key_neg, 0))

    def is_safe(self, P: np.ndarray) -> bool:
        return all(np.dot(n, P) <= b + 1e-9 for n, b in self.constraints)

    def project(self, P: np.ndarray, max_iter: int = 50) -> np.ndarray:
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
        if self._cache_valid and not force_recompute:
            return self._cached_center

        if not self.constraints:
            self._cached_center = np.zeros(self.dim)
            self._cache_valid = True
            return self._cached_center

        # Variables: [P, r] where r is the radius
        c = np.zeros(self.dim + 1)
        c[-1] = -1   # maximize r

        A_ub = []
        b_ub = []
        for n, b in self.constraints:
            row = np.append(n, np.linalg.norm(n))
            A_ub.append(row)
            b_ub.append(b)
        # r >= 0
        A_ub.append(np.append(np.zeros(self.dim), -1))
        b_ub.append(0)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = linprog(c, A_ub=A_ub, b_ub=b_ub, method='highs')
        if res.success:
            self._cached_center = res.x[:-1]
            self._cache_valid = True
            return self._cached_center
        else:
            center = self.project(np.zeros(self.dim))
            self._cached_center = center
            self._cache_valid = True
            return center


# ============================================================
# INTERPRETATION MODEL
# ============================================================
class Interpretation:
    def __init__(self, dim: int):
        self.W = np.random.randn(dim, dim) * 0.1

    def forward(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(self.W @ x)

    def update(self, grad: np.ndarray, lr: float = 0.01) -> None:
        self.W -= lr * grad


# ============================================================
# LEARNER
# ============================================================
class Learner:
    @staticmethod
    def loss(pred: np.ndarray, target: np.ndarray) -> float:
        return float(np.mean((pred - target) ** 2))

    @staticmethod
    def grad(pred: np.ndarray, target: np.ndarray, x: np.ndarray) -> np.ndarray:
        error = pred - target
        return np.outer(error, x)


# ============================================================
# EXPLORATION POLICY
# ============================================================
class ExplorationPolicy:
    def __init__(self, threshold: float = 1.0, probe_prob: float = 0.2):
        self.threshold = threshold
        self.probe_prob = probe_prob

    def decide(self, uncertainty: float, kernel: SurvivabilityKernel, dim: int) -> Tuple[str, Optional[np.ndarray]]:
        if uncertainty > self.threshold:
            # structured exploration: try existing basis directions first
            for d in kernel._basis:
                return "PROBE", d
            # stochastic exploration
            if np.random.rand() < self.probe_prob:
                d = normalize(np.random.randn(dim))
                if is_independent(d, kernel._basis):
                    return "PROBE", d

        if uncertainty <= self.threshold:
            return "ACT", None

        return "SILENCE", None


# ============================================================
# EXAMPLE SYSTEM (for demonstration)
# ============================================================
class SimpleSystem:
    """Example system: failure if norm > 10 (ball of radius 10)."""
    @staticmethod
    def failure(P: np.ndarray) -> bool:
        return np.linalg.norm(P) > 10.0


# ============================================================
# UNIFIED FALSIFICATION SYSTEM
# ============================================================
class UnifiedFalsificationSystem:
    def __init__(self, system, kernel: SurvivabilityKernel, dim: int):
        self.system = system
        self.kernel = kernel
        self.dim = dim

        self.model = Interpretation(dim)
        self.learner = Learner()
        self.policy = ExplorationPolicy()

        self.seed = self._find_safe_seed()

    def _find_safe_seed(self) -> np.ndarray:
        for _ in range(100):
            p = np.random.randn(self.dim) * 5.0
            if not self.system.failure(p):
                return p
        return np.zeros(self.dim)

    def uncertainty(self, P: np.ndarray) -> float:
        if not self.kernel.constraints:
            return np.linalg.norm(P)
        proj = self.kernel.project(P)
        # refined uncertainty: distance to kernel + small bias
        return np.linalg.norm(P - proj) + 0.1 * np.linalg.norm(P)

    def probe(self, direction: np.ndarray) -> Optional[np.ndarray]:
        weight = self.kernel.get_weight(direction)
        t_max = 10.0 * (1 + weight)
        steps = 25 + int(10 * weight)

        t_low, t_high = 0.0, t_max
        if not self.system.failure(self.seed + t_high * direction):
            return None

        for _ in range(steps):
            t_mid = (t_low + t_high) / 2.0
            P_mid = self.seed + t_mid * direction
            if self.system.failure(P_mid):
                t_high = t_mid
            else:
                t_low = t_mid

        boundary = self.seed + t_high * direction
        self.kernel.add_constraint(direction, boundary)
        return boundary

    def step(self, x: np.ndarray, target: Optional[np.ndarray] = None) -> Dict:
        # 1. Interpretation
        interpreted = self.model.forward(x)

        # 2. Uncertainty (before projection)
        u = self.uncertainty(interpreted)

        # 3. Decision
        decision, info = self.policy.decide(u, self.kernel, self.dim)

        # 4. Projection (safe state)
        reflected = self.kernel.project(interpreted) if self.kernel.constraints else interpreted

        output = None
        loss = None

        if decision == "ACT":
            output = reflected
            if target is not None:
                loss_val = self.learner.loss(output, target)
                grad = self.learner.grad(output, target, x)
                # consistency gradient: pull interpretation toward its projection
                proj = self.kernel.project(interpreted)
                consistency_grad = np.outer(interpreted - proj, x)
                total_grad = grad + 0.1 * consistency_grad
                self.model.update(total_grad)
                loss = loss_val

        elif decision == "PROBE":
            boundary = self.probe(info)
            if boundary is not None:
                # reset origin to Chebyshev center
                center = self.kernel.chebyshev_center()
                if not self.kernel.is_safe(center):
                    center = self.kernel.project(center)
                if self.system.failure(center):
                    center = self._find_safe_seed()
                self.seed = center
                # learn from boundary
                proj_boundary = self.kernel.project(boundary)
                grad = self.learner.grad(interpreted, proj_boundary, x)
                self.model.update(0.5 * grad)

        # SILENCE: no update

        return {
            "interpreted": interpreted,
            "reflected": reflected,
            "uncertainty": u,
            "decision": decision,
            "output": output,
            "loss": loss,
            "seed": self.seed.copy()
        }


# ============================================================
# DEMONSTRATION
# ============================================================
if __name__ == "__main__":
    # Create a simple system (failure outside ball of radius 10)
    system = SimpleSystem()
    dim = 5
    kernel = SurvivabilityKernel(dim)
    ufs = UnifiedFalsificationSystem(system, kernel, dim)

    # Simulate some random inputs and targets
    for t in range(20):
        x = np.random.randn(dim)
        target = np.zeros(dim)   # we want to learn to map to zero
        result = ufs.step(x, target)
        print(f"Step {t}: decision={result['decision']}, uncertainty={result['uncertainty']:.4f}")
        if result['loss'] is not None:
            print(f"  loss={result['loss']:.6f}")

    print("\nFinal kernel constraints:", len(kernel.constraints))
