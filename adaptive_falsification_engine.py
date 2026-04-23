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
from typing import List, Tuple, Optional, Callable, Dict, Any, Union
import warnings


# ============================================================
# UTILITIES
# ============================================================
def normalize(v: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    """Return unit vector in the same direction; zero vector unchanged."""
    norm = np.linalg.norm(v)
    if norm < tol:
        return v
    return v / norm


def is_independent(d: np.ndarray, basis: List[np.ndarray], tol: float = 1e-6) -> bool:
    """
    Check if direction d is linearly independent of the orthonormal basis.
    For an orthonormal basis, independence ⇔ projection residual > tol.
    """
    w = d.copy()
    for b in basis:
        w -= np.dot(w, b) * b
    return np.linalg.norm(w) > tol


def orthogonalize(vectors: List[np.ndarray]) -> List[np.ndarray]:
    """Gram–Schmidt orthogonalisation, returning orthonormal basis (ignores zero vectors)."""
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

    Args:
        failure_func: Returns True if state is a failure.
        simulate_linear: Function (P, d, t) -> P(t) (linear extrapolation).
        P: Starting safe state.
        d: Unit direction vector.
        t_max: Maximum search distance.
        refine_iter: Number of binary refinement steps.
        stochastic_trials: Number of trials for stochastic failure detection.

    Returns:
        Boundary state (first failure) or None if no failure within t_max.
    """
    if failure_func(P):
        return None

    # Check if there is a failure at t_max
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
    with adaptive step size that shrinks when failure is approached.

    Args:
        failure_func: Returns True if state is a failure.
        local_step: Function (P, delta) -> P_next (nonlinear step).
        P: Starting safe state.
        d: Unit direction vector.
        weight: Directional weight (higher → more dangerous, smaller initial step).
        max_steps: Maximum number of steps.
        base_step_size: Initial step size when weight=0.
        min_step_size: Smallest allowed step.
        stochastic_trials: Number of trials for stochastic failure detection.

    Returns:
        Boundary state (first failure) or None if no failure found within max_steps.
    """
    if failure_func(P):
        return None

    # Adaptive initial step size: inversely proportional to (1 + weight)
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
            if step_size <= min_step_size:
                # Binary search between last safe and current point
                P_low, P_high = P_safe, P_current
                for _ in range(15):
                    P_mid = (P_low + P_high) / 2.0
                    if failure_func(P_mid):
                        P_high = P_mid
                    else:
                        P_low = P_mid
                return P_high
            else:
                step_size = max(step_size / 2.0, min_step_size)
                P_current = P_safe
                continue
        else:
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
        self.constraints: List[Tuple[np.ndarray, float]] = []
        self._basis: List[np.ndarray] = []
        self._failure_weights: Dict[Tuple[float, ...], float] = {}
        self._cached_center: Optional[np.ndarray] = None
        self._cache_valid: bool = False

    def add_constraint(self, normal: np.ndarray, boundary_point: np.ndarray, weight: float = 1.0) -> None:
        """Add a half-space constraint derived from a failure boundary."""
        normal = normalize(normal)
        bound = np.dot(normal, boundary_point) - self.epsilon
        self.constraints.append((normal, bound))

        key = tuple(np.round(normal, 6))
        self._failure_weights[key] = self._failure_weights.get(key, 0.0) + weight

        self._basis = orthogonalize([normal] + self._basis)
        self._cache_valid = False

    def decay_weights(self) -> None:
        """Apply exponential decay to all failure weights."""
        for k in list(self._failure_weights.keys()):
            self._failure_weights[k] *= self.weight_decay
        # Remove negligible weights
        self._failure_weights = {k: v for k, v in self._failure_weights.items() if v > 1e-6}

    def get_weight(self, d: np.ndarray) -> float:
        """Return accumulated failure weight for direction d or its opposite."""
        d = normalize(d)
        key = tuple(np.round(d, 6))
        key_neg = tuple(np.round(-d, 6))
        return max(self._failure_weights.get(key, 0.0), self._failure_weights.get(key_neg, 0.0))

    def is_safe(self, P: np.ndarray) -> bool:
        """Check if point satisfies all constraints (with numerical tolerance)."""
        return all(np.dot(n, P) <= b + 1e-9 for n, b in self.constraints)

    def project(self, P: np.ndarray, max_iter: int = 50, tol: float = 1e-8) -> np.ndarray:
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
        Compute the Chebyshev center (center of largest inscribed ball) via linear programming.
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
        c[-1] = -1.0  # maximise r

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
        simulate_func: Union[
            Callable[[np.ndarray, np.ndarray, float], np.ndarray],  # linear
            Callable[[np.ndarray, np.ndarray], np.ndarray]           # local
        ],
        dim: int,
        simulation_type: str = "linear",
        stochastic_trials: int = 1,
        weight_decay: float = 0.95,
        seed: Optional[int] = None,
    ):
        if simulation_type not in ("linear", "local"):
            raise ValueError("simulation_type must be 'linear' or 'local'")
        self.failure = failure_func
        self.sim_type = simulation_type
        self.simulate_func = simulate_func
        self.stochastic_trials = stochastic_trials
        self.dim = dim
        self.kernel = SurvivabilityKernel(dim, weight_decay=weight_decay)
        self._seed_state: np.ndarray = np.zeros(dim)  # will be set in run()
        self._rng = np.random.default_rng(seed)

    def _get_initial_safe_state(self, max_attempts: int = 100) -> np.ndarray:
        """Find a random safe state; fallback to zero."""
        for _ in range(max_attempts):
            P = self._rng.normal(0.0, 5.0, self.dim)
            if not self.failure(P):
                return P
        return np.zeros(self.dim)

    def _probe_direction(self, d: np.ndarray) -> None:
        """Probe direction d (and its opposite) using appropriate boundary finder."""
        d_norm = normalize(d)
        for direction in (d_norm, -d_norm):
            weight = self.kernel.get_weight(direction)
            if self.sim_type == "linear":
                t_max = 10.0 * (1.0 + weight)
                refine_iter = 20 + int(10 * weight)

                def sim_linear(P: np.ndarray, dir_vec: np.ndarray, t: float) -> np.ndarray:
                    # simulate_func is assumed to have signature (P, d, t)
                    return self.simulate_func(P, dir_vec, t)  # type: ignore[call-arg]

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
                    self.simulate_func,  # type: ignore[arg-type]
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

    def run(self, iterations: int = 100, reset_every: int = 10, verbose: bool = False) -> SurvivabilityKernel:
        """
        Main exploration loop.

        Args:
            iterations: Total number of random direction attempts.
            reset_every: After this many direction probes, reset origin to Chebyshev center.
            verbose: If True, print progress updates.
        Returns:
            The final SurvivabilityKernel.
        """
        self._seed_state = self._get_initial_safe_state()
        self.kernel.decay_weights()  # initial decay

        for i in range(iterations):
            d = normalize(self._rng.normal(0.0, 1.0, self.dim))

            if is_independent(d, self.kernel._basis):
                self._probe_direction(d)

            if (i + 1) % reset_every == 0:
                center = self.kernel.chebyshev_center()
                if not self.kernel.is_safe(center):
                    center = self.kernel.project(center)
                self._seed_state = center
                if verbose:
                    print(f"[{i+1}] Reset → center norm: {np.linalg.norm(center):.4f}")
                self.kernel.decay_weights()

        return self.kernel


# ============================================================
# EXAMPLE USAGE
# ============================================================
if __name__ == "__main__":
    # Define a simple nonlinear system: failure if norm > 10
    def failure_func(P: np.ndarray) -> bool:
        return bool(np.linalg.norm(P) > 10.0)

    def local_step(P: np.ndarray, delta: np.ndarray) -> np.ndarray:
        return P + delta

    def linear_sim(P: np.ndarray, d: np.ndarray, t: float) -> np.ndarray:
        return P + t * d

    explorer = FalsificationExplorer(
        failure_func=failure_func,
        simulate_func=local_step,
        dim=2,
        simulation_type="local",
        stochastic_trials=1,
        weight_decay=0.95,
        seed=42,
    )

    kernel = explorer.run(iterations=200, reset_every=20, verbose=True)

    # Test points
    test_points = [np.array([5.0, 0.0]), np.array([9.0, 0.0]), np.array([11.0, 0.0])]
    for p in test_points:
        print(f"Point {p}: safe = {kernel.is_safe(p)}")
