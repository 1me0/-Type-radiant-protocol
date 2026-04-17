"""
meta_structural_validity.py

Computational framework for testing meta-structural stability of stochastic dynamical systems.

Features:
1. Lyapunov consistency (empirical check that V ≈ 0 on M and V > 0 outside)
2. Global Foster–Lyapunov drift condition (empirical estimate over multiple states)
3. Empirical stationarity via Wasserstein distance (proxy for invariant measure)
4. Support containment via violation rate

All thresholds are configurable. The module provides empirical diagnostics,
not theoretical proofs of existence of invariant measures.

Author: Radiant Protocol
License: MIT
"""

import numpy as np
from typing import Callable, Tuple, Optional
from dataclasses import dataclass
from scipy.stats import wasserstein_distance


@dataclass
class ValidityReport:
    """Report containing all validity flags and diagnostic details."""
    lyapunov_consistent: bool
    foster_lyapunov_holds: bool
    empirical_stationarity: bool
    support_violation_rate_ok: bool
    is_valid: bool
    details: dict


class MetaStructuralValidity:
    """
    Empirical verifier for meta-structural stability.

    A system is defined by:
        T: transition function (state, noise) -> next state
        V: Lyapunov / coherence functional (state -> non‑negative float)
        M: invariant/coherent set indicator (state -> bool)
        ξ: noise sampler (returns a noise vector)
        state_dim: dimension of the state space
    """

    def __init__(
        self,
        transition: Callable[[np.ndarray, np.ndarray], np.ndarray],
        lyapunov: Callable[[np.ndarray], float],
        invariant_set: Callable[[np.ndarray], bool],
        noise_sampler: Callable[[], np.ndarray],
        state_dim: int,
        seed: Optional[int] = None,
    ):
        self.T = transition
        self.V = lyapunov
        self.in_M = invariant_set
        self.noise = noise_sampler
        self.n = state_dim
        if seed is not None:
            np.random.seed(seed)

    # ------------------------------------------------------------
    # 1. LYAPUNOV CONSISTENCY (empirical)
    # ------------------------------------------------------------
    def check_lyapunov_consistency(self, samples: int = 2000, eps: float = 1e-6) -> Tuple[bool, str]:
        """
        Checks whether V behaves consistently with M:
        - V ≈ 0 on M
        - V > 0 outside M

        Returns:
            (bool, message): True if consistent, plus diagnostic message.
        """
        for _ in range(samples):
            P = np.random.randn(self.n)
            v = self.V(P)
            inM = self.in_M(P)

            if inM and v > eps:
                return False, f"Violation: V={v:.2e} > {eps} inside M"
            if not inM and v < eps:
                return False, f"Violation: V≈0 ({v:.2e}) outside M"
        return True, "Lyapunov consistency satisfied (empirical)."

    # ------------------------------------------------------------
    # 2. LOCAL FOSTER–LYAPUNOV DRIFT (single point)
    # ------------------------------------------------------------
    def check_foster_lyapunov(self, P: np.ndarray, samples: int = 100) -> Tuple[bool, float]:
        """
        Estimates δ(P) = V(P) - E[V(T(P,ξ))].
        Condition: δ(P) > 0 for P ∉ M.

        Returns:
            (holds, drift_estimate): True if drift > 0, plus the drift value.
        """
        if self.in_M(P):
            return True, 0.0

        V0 = self.V(P)
        V_next = [self.V(self.T(P, self.noise())) for _ in range(samples)]
        drift = V0 - np.mean(V_next)
        return drift > 0, drift

    # ------------------------------------------------------------
    # 2b. GLOBAL FOSTER–LYAPUNOV DRIFT (multi‑state)
    # ------------------------------------------------------------
    def check_foster_lyapunov_global(
        self,
        num_states: int = 20,
        samples_per_state: int = 50,
        violation_tolerance: float = 0.05,
    ) -> Tuple[bool, float]:
        """
        Global drift test: sample multiple initial states, estimate drift for each.
        Returns (holds, violation_rate) where violation_rate = fraction of states with drift ≤ 0.
        The condition is considered satisfied if violation_rate < violation_tolerance.
        """
        violations = 0
        total = 0
        for _ in range(num_states):
            P = np.random.randn(self.n)
            if self.in_M(P):
                continue
            ok, _ = self.check_foster_lyapunov(P, samples_per_state)
            if not ok:
                violations += 1
            total += 1
        violation_rate = violations / total if total > 0 else 1.0
        return violation_rate < violation_tolerance, violation_rate

    # ------------------------------------------------------------
    # 3. EMPIRICAL STATIONARITY (Wasserstein distance)
    # ------------------------------------------------------------
    def check_empirical_stationarity(
        self,
        steps: int = 10000,
        burn_in: int = 1000,
        split_ratio: float = 0.5,
        stationarity_threshold: float = 0.5,
    ) -> Tuple[bool, float, np.ndarray]:
        """
        Simulate a long trajectory, discard burn‑in, split into two halves,
        and compare distributions via Wasserstein distance (averaged over dimensions).
        Returns:
            (stationary, wasserstein_distance, trajectory)
        """
        P = np.zeros(self.n)
        traj = []

        for t in range(steps + burn_in):
            P = self.T(P, self.noise())
            if t >= burn_in:
                traj.append(P.copy())

        traj = np.array(traj)
        if len(traj) == 0:
            return False, np.inf, traj

        # Basic sanity: trajectory should not diverge to infinity
        if np.any(np.abs(traj) > 1e6):
            return False, np.inf, traj

        split = int(len(traj) * split_ratio)
        if split == 0 or split == len(traj):
            return False, np.inf, traj

        first_half = traj[:split]
        second_half = traj[split:]

        # Compute average Wasserstein distance across dimensions
        dists = []
        for d in range(self.n):
            dists.append(wasserstein_distance(first_half[:, d], second_half[:, d]))
        avg_wass = np.mean(dists)

        stationary = avg_wass < stationarity_threshold
        return stationary, avg_wass, traj

    # ------------------------------------------------------------
    # 4. SUPPORT VIOLATION TEST
    # ------------------------------------------------------------
    def check_support_violation(
        self,
        traj: np.ndarray,
        violation_tolerance: float = 0.01,
    ) -> Tuple[bool, float]:
        """
        Checks that the empirical frequency of states outside M is below tolerance.
        Returns (ok, violation_rate).
        """
        if len(traj) == 0:
            return False, 1.0
        violations = np.mean([not self.in_M(p) for p in traj])
        return violations < violation_tolerance, violations

    # ------------------------------------------------------------
    # FULL VALIDATION PIPELINE
    # ------------------------------------------------------------
    def validate(
        self,
        lyapunov_samples: int = 2000,
        lyapunov_eps: float = 1e-6,
        foster_num_states: int = 20,
        foster_samples_per_state: int = 50,
        foster_violation_tolerance: float = 0.05,
        stationarity_steps: int = 10000,
        stationarity_burn_in: int = 1000,
        stationarity_threshold: float = 0.5,
        support_violation_tolerance: float = 0.01,
    ) -> ValidityReport:
        """
        Run all empirical tests and produce a ValidityReport.

        Parameters can be adjusted to control the sensitivity of each test.
        """
        # 1. Lyapunov consistency
        lyap_ok, lyap_msg = self.check_lyapunov_consistency(
            samples=lyapunov_samples, eps=lyapunov_eps
        )

        # 2. Global Foster–Lyapunov drift
        drift_ok, violation_rate = self.check_foster_lyapunov_global(
            num_states=foster_num_states,
            samples_per_state=foster_samples_per_state,
            violation_tolerance=foster_violation_tolerance,
        )

        # 3. Empirical stationarity
        stat_ok, wasserstein_dist, traj = self.check_empirical_stationarity(
            steps=stationarity_steps,
            burn_in=stationarity_burn_in,
            stationarity_threshold=stationarity_threshold,
        )

        # 4. Support violation
        supp_ok, support_violation = self.check_support_violation(
            traj=traj, violation_tolerance=support_violation_tolerance
        )

        is_valid = lyap_ok and drift_ok and stat_ok and supp_ok

        return ValidityReport(
            lyapunov_consistent=lyap_ok,
            foster_lyapunov_holds=drift_ok,
            empirical_stationarity=stat_ok,
            support_violation_rate_ok=supp_ok,
            is_valid=is_valid,
            details={
                "lyapunov_message": lyap_msg,
                "global_drift_violation_rate": float(violation_rate),
                "wasserstein_distance": float(wasserstein_dist),
                "support_violation_rate": float(support_violation),
                "trajectory_length": len(traj),
            },
        )


# ============================================================
# EXAMPLE SYSTEM: Projection onto line y = x
# ============================================================
if __name__ == "__main__":
    # Define projection onto the invariant manifold (line y = x)
    def project(P: np.ndarray) -> np.ndarray:
        m = (P[0] + P[1]) / 2
        return np.array([m, m])

    # Lyapunov function: squared distance to manifold
    def V(P: np.ndarray) -> float:
        return np.linalg.norm(P - project(P)) ** 2

    # Invariant set indicator (within 1e-6 of the line)
    def in_M(P: np.ndarray) -> bool:
        return V(P) < 1e-6

    # Stochastic transition (Master Formula with projection)
    def T(P: np.ndarray, xi: np.ndarray) -> np.ndarray:
        alpha, beta = 0.4, 0.6
        Pi = project(P)
        correction = (1 + beta) * Pi - beta * P
        return P + alpha * correction + 0.05 * xi

    def noise() -> np.ndarray:
        return np.random.randn(2)

    # Create validity checker with fixed seed for reproducibility
    checker = MetaStructuralValidity(
        transition=T,
        lyapunov=V,
        invariant_set=in_M,
        noise_sampler=noise,
        state_dim=2,
        seed=42,
    )

    # Run validation
    report = checker.validate()

    print("\n=== META-STRUCTURAL VALIDITY REPORT ===")
    for k, v in report.__dict__.items():
        print(f"{k}: {v}")
