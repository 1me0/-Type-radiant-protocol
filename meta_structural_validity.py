"""
meta_structural_validity.py (FINAL RIGOROUS VERSION)

Computational framework for testing meta-structural stability
of stochastic dynamical systems using:

1. Lyapunov consistency (not existence)
2. Global Foster–Lyapunov drift condition (empirical estimate)
3. Empirical stationarity via Wasserstein distance (proxy for invariant measure)
4. Support containment via violation rate

NOTE:
This module does NOT prove theoretical existence of invariant measures.
It provides empirical diagnostics for stochastic stability.
"""

import numpy as np
from typing import Callable, Tuple, Optional
from dataclasses import dataclass
from scipy.stats import wasserstein_distance


@dataclass
class ValidityReport:
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
        T: transition function
        V: Lyapunov / coherence functional
        M: invariant/coherent set indicator
        ξ: noise sampler
    """

    def __init__(
        self,
        transition: Callable[[np.ndarray, np.ndarray], np.ndarray],
        lyapunov: Callable[[np.ndarray], float],
        invariant_set: Callable[[np.ndarray], bool],
        noise_sampler: Callable[[], np.ndarray],
        state_dim: int,
    ):
        self.T = transition
        self.V = lyapunov
        self.in_M = invariant_set
        self.noise = noise_sampler
        self.n = state_dim

    # ============================================================
    # 1. LYAPUNOV CONSISTENCY (NOT EXISTENCE)
    # ============================================================
    def check_lyapunov_consistency(self, samples: int = 2000) -> Tuple[bool, str]:
        """
        Checks whether V behaves consistently with M:
        - V ≈ 0 on M
        - V > 0 outside M
        (empirical test only)
        """
        eps = 1e-6

        for _ in range(samples):
            P = np.random.randn(self.n)
            v = self.V(P)
            inM = self.in_M(P)

            if inM and v > eps:
                return False, "Violation: V>0 inside M"
            if not inM and v < eps:
                return False, "Violation: V≈0 outside M"

        return True, "Lyapunov consistency satisfied (empirical)."

    # ============================================================
    # 2. LOCAL FOSTER–LYAPUNOV DRIFT (single point)
    # ============================================================
    def check_foster_lyapunov(self, P: np.ndarray, samples: int = 100) -> Tuple[bool, float]:
        """
        Estimates:
            δ(P) = V(P) - E[V(T(P,ξ))]
        Condition:
            δ(P) > 0 for P ∉ M
        """
        if self.in_M(P):
            return True, 0.0

        V0 = self.V(P)
        V_next = []

        for _ in range(samples):
            xi = self.noise()
            Pn = self.T(P, xi)
            V_next.append(self.V(Pn))

        drift = V0 - np.mean(V_next)

        return drift > 0, drift

    # ============================================================
    # 2b. GLOBAL FOSTER–LYAPUNOV DRIFT
    # ============================================================
    def check_foster_lyapunov_global(
        self, num_states: int = 20, samples_per_state: int = 50
    ) -> Tuple[bool, float]:
        """
        Global drift test: sample multiple initial states, compute average drift.
        Returns (holds, violation_rate) where violation_rate = fraction of states with drift <= 0.
        """
        violations = 0
        for _ in range(num_states):
            P = np.random.randn(self.n)
            ok, _ = self.check_foster_lyapunov(P, samples_per_state)
            if not ok:
                violations += 1
        violation_rate = violations / num_states
        # We consider the condition satisfied if less than 5% of states violate
        return violation_rate < 0.05, violation_rate

    # ============================================================
    # 3. EMPIRICAL STATIONARITY (INVARIANT MEASURE PROXY)
    # ============================================================
    def check_empirical_stationarity(
        self,
        steps: int = 10000,
        burn_in: int = 1000,
        split_ratio: float = 0.5
    ) -> Tuple[bool, float, np.ndarray]:
        """
        Approximates invariant measure via trajectory sampling.
        Tests stationarity by comparing distribution of early vs late segments using Wasserstein distance.
        Returns (stationary, wasserstein_distance, trajectory).
        """
        P = np.zeros(self.n)
        traj = []

        for t in range(steps + burn_in):
            P = self.T(P, self.noise())
            if t >= burn_in:
                traj.append(P.copy())

        traj = np.array(traj)
        # Check boundedness (non-divergence) as a basic sanity
        bounded = np.all(np.abs(traj) < 1e6)
        if not bounded:
            return False, np.inf, traj

        # Split trajectory into two halves and compute Wasserstein distance per dimension
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

        # If distributions are close (small Wasserstein), we consider it stationary
        stationary = avg_wass < 0.5  # threshold, may need tuning
        return stationary, avg_wass, traj

    # ============================================================
    # 4. SUPPORT VIOLATION TEST
    # ============================================================
    def check_support_violation(self, traj: np.ndarray) -> Tuple[bool, float]:
        """
        Checks:
            P(P_t ∉ M) → 0
        """
        if len(traj) == 0:
            return False, 1.0

        violations = np.mean([not self.in_M(p) for p in traj])

        return violations < 0.01, violations

    # ============================================================
    # FULL VALIDATION PIPELINE
    # ============================================================
    def validate(self) -> ValidityReport:
        """
        Full meta-structural validation pipeline.

        Combines:
        1. Lyapunov consistency check
        2. Global Foster–Lyapunov drift test
        3. Empirical stationarity test
        4. Support violation test
        """

        # 1. Lyapunov consistency (V aligned with M)
        lyap_ok, lyap_msg = self.check_lyapunov_consistency()

        # 2. Global Foster–Lyapunov condition
        drift_ok, violation_rate = self.check_foster_lyapunov_global()

        # 3. Empirical stationarity (distributional convergence)
        stat_ok, wasserstein_dist, traj = self.check_empirical_stationarity()

        # 4. Support containment (violation rate of M)
        supp_ok, support_violation = self.check_support_violation(traj)

        # 5. Global validity decision
        is_valid = (
            lyap_ok
            and drift_ok
            and stat_ok
            and supp_ok
        )

        # 6. Structured report
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
# EXAMPLE SYSTEM (STOCHASTIC PROJECTION DYNAMICS)
# ============================================================
if __name__ == "__main__":

    # Invariant manifold: diagonal line y = x
    def project(P):
        m = (P[0] + P[1]) / 2
        return np.array([m, m])

    def V(P):
        return np.linalg.norm(P - project(P)) ** 2

    def in_M(P):
        return V(P) < 1e-6

    def T(P, xi):
        alpha, beta = 0.4, 0.6
        Pi = project(P)
        correction = (1 + beta) * Pi - beta * P
        return P + alpha * correction + 0.05 * xi

    def noise():
        return np.random.randn(2)

    system = MetaStructuralValidity(
        transition=T,
        lyapunov=V,
        invariant_set=in_M,
        noise_sampler=noise,
        state_dim=2,
    )

    report = system.validate()

    print("\n=== META-STRUCTURAL VALIDITY REPORT ===")
    for k, v in report.__dict__.items():
        print(f"{k}: {v}")
