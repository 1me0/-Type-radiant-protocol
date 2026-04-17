"""
adaptive_falsification_engine.py

A falsification-driven engine that discovers the survivability kernel
by probing extremes, adapting to failure asymmetries, and recursively
re-centering the origin at the Chebyshev center of the current kernel.

Based on the principle: truth is the intersection of constraints revealed
by failure boundaries when the origin is corrupted.

Author: Radiant Protocol
License: MIT
"""

import numpy as np
from scipy.optimize import linprog
from typing import List, Tuple, Optional, Callable, Dict
import warnings


# ============================================================
# UTILITIES
# ============================================================
def normalize(v: np.ndarray) -> np.ndarray:
    """Return unit vector in the same direction; zero vector remains unchanged."""
    norm = np.linalg.norm(v)
    if norm < 1e-12:
        return v
    return v / norm


def is_independent(d: np.ndarray, basis: List[np.ndarray], tol: float = 1e-6) -> bool:
    """
    Check if direction d is linearly independent of the existing orthonormal basis.
    For an orthonormal basis, independence is equivalent to d having negligible
    projection onto each basis vector.
    """
    for b in basis:
        if abs(np.dot(d, b)) > tol:
            return False
    return True


def orthogonalize(vectors: List[np.ndarray]) -> List[np.ndarray]:
    """Gram–Schmidt orthogonalization, returning orthonormal basis (ignores zero vectors)."""
    basis = []
    for v in vectors:
        w = v.copy()
        for b in basis:
            w -= np.dot(w, b) * b
        if np.linalg.norm(w) > 1e-8:
            basis.append(normalize(w))
    return basis


# ============================================================
# BOUNDARY SEARCH (linear mode)
# ============================================================
def find_failure_boundary_linear(
    failure_func: Callable[[np.ndarray], bool],
    simulate_linear: Callable[[np.ndarray, np.ndarray, float], np.ndarray],
    P: np.ndarray,
    d: np.ndarray,
    t_max: float = 10.0,
    refine_iter: int = 20,
    stochastic_trials: int = 1,
) -> Optional[np.ndarray]:
    """
    Binary search for failure boundary along a straight line from P in direction d.
    Assumes failure_func is deterministic or we take majority vote over trials.
    Returns boundary state or None if no failure within t_max.
    """
    if failure_func(P):
        return None

    # Check if there is a failure at t_max (with optional stochastic checks)
    has_failure = False
    for _ in range(stochastic_trials):
        if failure_func(simulate_linear(P, d, t_max)):
            has_failure = True
            break
    if not has_failure:
        return None

    t_low, t_high = 0.0, t_max
    for _ in range(refine_iter):
        t_mid = (t_low + t_high) / 2.0
        P_mid = simulate_linear(P, d, t_mid)
        if failure_func(P_mid):
            t_high = t_mid
        else:
            t_low = t_mid
    return simulate_linear(P, d, t_high)


# ============================================================
# BOUNDARY SEARCH (local dynamics mode)
# ============================================================
def find_failure_boundary_local(
    failure_func: Callable[[np.ndarray], bool],
    local_step: Callable[[np.ndarray, np.ndarray], np.ndarray],
    P: np.ndarray,
    d: np.ndarray,
    weight: float = 0.0,
    max_steps: int = 200,
    base_step_size: float = 0.1,
    min_step_size: float = 1e-6,
    stochastic_trials: int = 1,
) -> Optional[np.ndarray]:
    """
    Find failure boundary by stepping in direction d using a local dynamics step,
    with adaptive step size that shrinks when failure is approached or when direction is dangerous.

    Args:
        failure_func: returns True if state is a failure.
        local_step: function (P, delta) -> P_next (nonlinear step).
        P: starting safe state.
        d: unit direction vector.
        weight: directional weight (higher → more dangerous, smaller initial step).
        max_steps: maximum number of steps.
        base_step_size: initial step size when weight=0.
        min_step_size: smallest step allowed.
        stochastic_trials: number of trials for stochastic failure detection.

    Returns:
        Boundary state (first failure) or None if no failure found within max_steps.
    """
    if failure_func(P):
        return None

    # Adaptive initial step size: inverse proportional to (1 + weight)
    step_size = base_step_size / (1.0 + weight)
    if step_size < min_step_size:
        step_size = min_step_size

    P_safe = P.copy()
    P_current = P_safe
    for _ in range(max_steps):
        P_next = local_step(P_current, d * step_size)
        # Check failure (stochastic majority)
        failed = False
        for _ in range(stochastic_trials):
            if failure_func(P_next):
                failed = True
                break
        if failed:
            # Failure detected – reduce step size and backtrack to last safe point
            if step_size <= min_step_size:
                # Already at minimum, perform binary search between P_safe and P_current
                P_low, P_high = P_safe, P_current
                for _ in range(15):
                    P_mid = (P_low + P_high) / 2.0
                    if failure_func(P_mid):
                        P_high = P_mid
                    else:
                        P_low = P_mid
                return P_high
            else:
                # Halve step size and try again from last safe point
                step_size = max(step_size / 2.0, min_step_size)
                P_current = P_safe
                continue
        else:
            # Still safe – move forward
            P_safe = P_current
            P_current = P_next

    return None


# ============================================================
# KERNEL (Convex Polytope)
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
        """Add a half-space constraint derived from a failure boundary."""
        normal = normalize(normal)
        bound = np.dot(normal, boundary_point) - self.epsilon
        self.constraints.append((normal, bound))

        key = tuple(np.round(normal, 6))
        self._failure_weights[key] = self._failure_weights.get(key, 0) + weight

        # Update orthonormal basis
        self._basis = orthogonalize([normal] + self._basis)

        # Invalidate cached Chebyshev center
        self._cache_valid = False

    def decay_weights(self) -> None:
        """Apply exponential decay to all failure weights to prioritize recent directions."""
        for k in list(self._failure_weights.keys()):
            self._failure_weights[k] *= self.weight_decay
        # Remove near-zero weights to keep dictionary small
        self._failure_weights = {k: v for k, v in self._failure_weights.items() if v > 1e-6}

    def get_weight(self, d: np.ndarray) -> float:
        """Return the accumulated failure weight for direction d or its opposite."""
        d = normalize(d)
        key = tuple(np.round(d, 6))
        key_neg = tuple(np.round(-d, 6))
        return max(self._failure_weights.get(key, 0), self._failure_weights.get(key_neg, 0))

    def is_safe(self, P: np.ndarray) -> bool:
        """Check if point satisfies all constraints (with small numerical tolerance)."""
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
        Compute the Chebyshev center (center of largest inscribed ball)
        by solving a linear program. Caches result.
        """
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
            # constraint: n·P + r·||n|| ≤ b
            row = np.append(n, np.linalg.norm(n))
            A_ub.append(row)
            b_ub.append(b)
        # r ≥ 0
        A_ub.append(np.append(np.zeros(self.dim), -1))
        b_ub.append(0)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = linprog(c, A_ub=A_ub, b_ub=b_ub, method='highs')
        if res.success:
            self._cached_center = res.x[:-1]
            self._cache_valid = True
            return self._cached_center
        else:
            # Fallback: project zero (the geometric median of feasible set)
            center = self.project(np.zeros(self.dim))
            self._cached_center = center
            self._cache_valid = True
            return center

    def __repr__(self) -> str:
        return f"SurvivabilityKernel(dim={self.dim}, constraints={len(self.constraints)}, basis_size={len(self._basis)})"


# ============================================================
# EXPLORER
# ============================================================
class FalsificationExplorer:
    """
    Adaptive falsification engine. Probes random independent directions,
    records failure boundaries, and recursively re-centers the origin
    to the Chebyshev center of the current kernel.
    """

    def __init__(
        self,
        failure_func: Callable[[np.ndarray], bool],
        simulate_func: Callable,
        dim: int,
        simulation_type: str = "linear",   # "linear" or "local"
        stochastic_trials: int = 1,
        weight_decay: float = 0.95,
        seed: Optional[int] = None,
    ):
        """
        Args:
            failure_func: function returning True if state is a failure.
            simulate_func: for linear mode: simulate_linear(P, d, t) -> P(t).
                           for local mode: local_step(P, delta) -> P_next.
            dim: state dimension.
            simulation_type: "linear" or "local".
            stochastic_trials: number of trials for stochastic failure detection.
            weight_decay: decay factor for directional weights (0 < weight_decay < 1).
            seed: random seed for reproducibility.
        """
        if simulation_type not in ("linear", "local"):
            raise ValueError("simulation_type must be 'linear' or 'local'")
        self.failure = failure_func
        self.sim_type = simulation_type
        self.simulate_func = simulate_func
        self.stochastic_trials = stochastic_trials
        self.dim = dim
        self.kernel = SurvivabilityKernel(dim, weight_decay=weight_decay)
        self._seed_state = None
        self._rng = np.random.default_rng(seed)

    def _get_initial_safe_state(self, max_attempts: int = 100) -> np.ndarray:
        """Find a random safe state; fallback to zero."""
        for _ in range(max_attempts):
            P = self._rng.normal(0, 5.0, self.dim)
            if not self.failure(P):
                return P
        return np.zeros(self.dim)

    def _probe_direction(self, d: np.ndarray) -> None:
        """Probe direction d (and its opposite) using appropriate boundary finder."""
        d_norm = normalize(d)
        for direction in (d_norm, -d_norm):
            weight = self.kernel.get_weight(direction)
            if self.sim_type == "linear":
                t_max = 10.0 * (1 + weight)
                refine_iter = 20 + int(10 * weight)

                def sim_linear(P, dir_vec, t):
                    return self.simulate_func(P, dir_vec, t)

                boundary = find_failure_boundary_linear(
                    self.failure,
                    sim_linear,
                    self._seed_state,
                    direction,
                    t_max=t_max,
                    refine_iter=refine_iter,
                    stochastic_trials=self.stochastic_trials,
                )
            else:  # local
                boundary = find_failure_boundary_local(
                    self.failure,
                    self.simulate_func,
                    self._seed_state,
                    direction,
                    weight=weight,
                    max_steps=200,
                    base_step_size=0.1,
                    min_step_size=1e-6,
                    stochastic_trials=self.stochastic_trials,
                )
            if boundary is not None:
                self.kernel.add_constraint(direction, boundary, weight=1.0)

    def run(self, iterations: int = 100, reset_every: int = 10) -> SurvivabilityKernel:
        """
        Main exploration loop.

        Args:
            iterations: total number of random direction attempts.
            reset_every: after this many direction probes, reset origin to Chebyshev center.
        Returns:
            The final SurvivabilityKernel.
        """
        self._seed_state = self._get_initial_safe_state()
        self.kernel.decay_weights()  # initial decay

        for i in range(iterations):
            d = normalize(self._rng.normal(0, 1, self.dim))

            # Only explore if independent of existing normals
            if is_independent(d, self.kernel._basis):
                self._probe_direction(d)

            # Periodic origin reset to Chebyshev center
            if (i + 1) % reset_every == 0:
                center = self.kernel.chebyshev_center()
                if not self.kernel.is_safe(center):
                    center = self.kernel.project(center)
                self._seed_state = center
                print(f"[{i}] Reset → center norm: {np.linalg.norm(center):.4f}")
                # Decay weights periodically to focus on recent directions
                self.kernel.decay_weights()

        return self.kernel


# ============================================================
# EXAMPLE USAGE (Nonlinear 2D system)
# ============================================================
if __name__ == "__main__":
    # Define a simple nonlinear system: failure if state leaves a circular region of radius 10
    def failure_func(P):
        return np.linalg.norm(P) > 10.0

    # Local step function (Euler integration) for nonlinear dynamics
    def local_step(P, delta):
        # For demonstration, we simply add delta (i.e., control directly affects state)
        # In a real system, this would be more complex.
        return P + delta

    # Linear simulation for straight‑line extrapolation (for comparison)
    def linear_sim(P, d, t):
        return P + t * d

    # Create explorer with local simulation (more accurate for nonlinear boundaries)
    explorer = FalsificationExplorer(
        failure_func=failure_func,
        simulate_func=local_step,
        dim=2,
        simulation_type="local",
        stochastic_trials=1,
        weight_decay=0.95,
        seed=42,
    )

    kernel = explorer.run(iterations=200, reset_every=20)

    # Test a few points
    test_points = [np.array([5.0, 0.0]), np.array([9.0, 0.0]), np.array([11.0, 0.0])]
    for p in test_points:
        print(f"Point {p}: safe = {kernel.is_safe(p)}")
