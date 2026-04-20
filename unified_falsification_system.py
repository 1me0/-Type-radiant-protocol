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
    """Return unit vector in the same direction; zero vector unchanged."""
    norm = np.linalg.norm(v)
    if norm < 1e-12:
        return v
    return v / norm


def is_independent(d: np.ndarray, basis: List[np.ndarray], tol: float = 1e-6) -> bool:
    """
    Check if direction d is linearly independent of the orthonormal basis.
    For an orthonormal basis, independence ⇔ projection residual > tol.
    """
    for b in basis:
        if abs(np.dot(d, b)) > tol:
            return False
    return True


def orthogonalize(vectors: List[np.ndarray]) -> List[np.ndarray]:
    """Gram–Schmidt orthogonalisation, returning orthonormal basis (ignores zero vectors)."""
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
        """
        Args:
            dim: dimension of the state space.
            epsilon: safety margin added to each constraint.
            weight_decay: exponential decay factor for failure weights (recent directions have higher weight).
        """
        self.dim = dim
        self.epsilon = epsilon
        self.weight_decay = weight_decay
        self.constraints: List[Tuple[np.ndarray, float]] = []   # (normal, bound)
        self._basis: List[np.ndarray] = []                     # orthonormal basis of normals
        self._failure_weights: Dict[Tuple, float] = {}         # key: direction tuple, value: weight
        self._cached_center: Optional[np.ndarray] = None
        self._cache_valid: bool = False

    def add_constraint(self, normal: np.ndarray, boundary_point: np.ndarray, weight: float = 1.0) -> None:
        """Add a half-space constraint derived from a failure boundary."""
        normal = normalize(normal)
        bound = np.dot(normal, boundary_point) - self.epsilon
        self.constraints.append((normal, bound))

        key = tuple(np.round(normal, 6))
        self._failure_weights[key] = self._failure_weights.get(key, 0) + weight

        self._basis = orthogonalize([normal] + self._basis)
        self._cache_valid = False

    def get_weight(self, d: np.ndarray) -> float:
        """Return accumulated failure weight for direction d or its opposite."""
        d = normalize(d)
        key = tuple(np.round(d, 6))
        key_neg = tuple(np.round(-d, 6))
        return max(self._failure_weights.get(key, 0), self._failure_weights.get(key_neg, 0))

    def is_safe(self, P: np.ndarray) -> bool:
        """Check if point satisfies all constraints (with numerical tolerance)."""
        return all(np.dot(n, P) <= b + 1e-9 for n, b in self.constraints)

    def project(self, P: np.ndarray, max_iter: int = 50) -> np.ndarray:
        """Project a point onto the feasible set using POCS (alternating projections)."""
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
        Caches result for performance.
        """
        if self._cache_valid and not force_recompute:
            return self._cached_center

        if not self.constraints:
            self._cached_center = np.zeros(self.dim)
            self._cache_valid = True
            return self._cached_center

        # Variables: [P, r] where r is the radius (maximise r)
        c = np.zeros(self.dim + 1)
        c[-1] = -1   # maximise r

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
            # Fallback: project zero (geometric median of feasible set)
            center = self.project(np.zeros(self.dim))
            self._cached_center = center
            self._cache_valid = True
            return center


# ============================================================
# INTERPRETATION MODEL
# ============================================================
class Interpretation:
    """Simple learnable mapping from input to latent state (tanh(linear layer))."""

    def __init__(self, dim: int, rng: np.random.Generator = None):
        """
        Args:
            dim: dimension of input and output.
            rng: random number generator for initialisation.
        """
        if rng is None:
            rng = np.random.default_rng()
        self.W = rng.normal(0, 0.1, size=(dim, dim))

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass: tanh(W @ x)."""
        return np.tanh(self.W @ x)

    def update(self, grad: np.ndarray, lr: float = 0.01) -> None:
        """Update weights using gradient descent."""
        self.W -= lr * grad


# ============================================================
# LEARNER
# ============================================================
class Learner:
    """Simple MSE learner with gradient computation."""

    @staticmethod
    def loss(pred: np.ndarray, target: np.ndarray) -> float:
        """Mean squared error loss."""
        return float(np.mean((pred - target) ** 2))

    @staticmethod
    def grad(pred: np.ndarray, target: np.ndarray, x: np.ndarray) -> np.ndarray:
        """
        Gradient of MSE loss w.r.t. the weight matrix of a linear layer:
        dL/dW = 2 * (pred - target) * x^T   (but with a factor 2 omitted for simplicity).
        Here we return the outer product of error and input.
        """
        error = pred - target
        return np.outer(error, x)


# ============================================================
# EXPLORATION POLICY
# ============================================================
class ExplorationPolicy:
    """Decides whether to ACT (use current interpretation), PROBE (explore), or SILENCE."""

    def __init__(self, threshold: float = 1.0, probe_prob: float = 0.2):
        self.threshold = threshold
        self.probe_prob = probe_prob

    def decide(self, uncertainty: float, kernel: SurvivabilityKernel, dim: int) -> Tuple[str, Optional[np.ndarray]]:
        """
        Returns (decision, info). Decision is one of 'ACT', 'PROBE', 'SILENCE'.
        If PROBE, info is the direction to probe.
        """
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
    """
    Main engine integrating interpretation, kernel learning, and falsification.
    """

    def __init__(self, system, kernel: SurvivabilityKernel, dim: int, seed: Optional[int] = None):
        """
        Args:
            system: object with method `failure(state)`.
            kernel: SurvivabilityKernel instance.
            dim: dimension of state space.
            seed: random seed for reproducibility.
        """
        self.system = system
        self.kernel = kernel
        self.dim = dim
        self.rng = np.random.default_rng(seed)

        self.model = Interpretation(dim, rng=self.rng)
        self.learner = Learner()
        self.policy = ExplorationPolicy()

        self.seed_state = self._find_safe_seed()

    def _find_safe_seed(self) -> np.ndarray:
        """Find a safe initial state (not in failure)."""
        for _ in range(100):
            p = self.rng.normal(0, 5.0, size=self.dim)
            if not self.system.failure(p):
                return p
        return np.zeros(self.dim)

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
        t_max = 10.0 * (1 + weight)
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
        self.kernel.add_constraint(direction, boundary)
        return boundary

    def step(self, x: np.ndarray, target: Optional[np.ndarray] = None) -> Dict:
        """
        One step of the system: interpret input, decide action, update state.

        Args:
            x: input vector (e.g., raw observation).
            target: optional target for supervised learning (used in ACT mode).

        Returns:
            Dictionary containing interpreted state, reflected state, uncertainty,
            decision, output, loss, and current seed state.
        """
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
                # Consistency gradient: pull interpretation toward its projection
                proj = self.kernel.project(interpreted)
                consistency_grad = np.outer(interpreted - proj, x)
                total_grad = grad + 0.1 * consistency_grad
                self.model.update(total_grad)
                loss = loss_val

        elif decision == "PROBE":
            boundary = self.probe(info)
            if boundary is not None:
                # Reset origin to Chebyshev center
                center = self.kernel.chebyshev_center()
                if not self.kernel.is_safe(center):
                    center = self.kernel.project(center)
                if self.system.failure(center):
                    center = self._find_safe_seed()
                self.seed_state = center
                # Learn from boundary: treat projected boundary as pseudo-target
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
            "seed": self.seed_state.copy()
        }


# ============================================================
# DEMONSTRATION
# ============================================================
if __name__ == "__main__":
    # Create a simple system (failure outside ball of radius 10)
    system = SimpleSystem()
    dim = 5
    kernel = SurvivabilityKernel(dim)
    ufs = UnifiedFalsificationSystem(system, kernel, dim, seed=42)

    # Simulate some random inputs and targets
    for t in range(20):
        x = np.random.randn(dim)
        target = np.zeros(dim)   # we want to learn to map to zero
        result = ufs.step(x, target)
        print(f"Step {t}: decision={result['decision']}, uncertainty={result['uncertainty']:.4f}")
        if result['loss'] is not None:
            print(f"  loss={result['loss']:.6f}")

    print("\nFinal kernel constraints:", len(kernel.constraints))
