"""
Sovereign Adaptive Projected Stochastic System (APSS)

A mathematically correct implementation with:
- Proper relaxed projection onto convex sets
- Cross‑domain resonance (synergy matrix)
- Entropy harvesting (noise → exploration)
- Teleological anchoring (meaning‑driven bias)

Author: Sovereign APSS
"""

import numpy as np
from typing import Dict, List, Callable, Tuple, Optional


# ============================================================
# Convex Set Abstraction
# ============================================================
class ConvexSet:
    """A convex set with projection and distance functions."""
    def __init__(self,
                 proj: Callable[[np.ndarray], np.ndarray],
                 dist: Callable[[np.ndarray], float]):
        self.proj = proj
        self.dist = dist


def relaxed_projection(x: np.ndarray, C: ConvexSet, eps: float) -> np.ndarray:
    """
    Project x onto the relaxed set M^eps = {z : dist(z, M) <= eps}.
    """
    p = C.proj(x)
    d = np.linalg.norm(x - p)
    if d <= eps:
        return x
    return p + eps * (x - p) / (d + 1e-12)


# ============================================================
# Sovereign APSS
# ============================================================
class SovereignAPSS:
    """
    The 10/10 system: convex relaxation + resonance + entropy + teleology.
    """
    def __init__(
        self,
        domains: List[str],
        sets: Dict[str, ConvexSet],
        targets: Dict[str, np.ndarray],
        T: int,
        teleological: Optional[np.ndarray] = None,
        teleo_weight: float = 0.05,
        resonance: Optional[Dict[Tuple[str, str], float]] = None,
        alpha: float = 0.1,
        alpha_max: float = 0.3,
        beta_0: float = 1.0,
        gamma: float = 0.5,
        kappa: float = 0.1,
        eta: float = 1.0,
        eps_0: float = 0.01,
        c: float = 0.1,
        noise_std: float = 0.01,
        entropy_gain: float = 0.05,
        entropy_thresh: float = 0.8,
        entropy_cap: float = 0.05,
    ):
        self.domains = domains
        self.sets = sets
        self.targets = targets
        self.T = T

        self.teleological = teleological
        self.teleo_weight = teleo_weight

        # Resonance matrix (default: mild cross‑synergy)
        if resonance is None:
            self.resonance = {(d1, d2): 1.0 if d1 == d2 else 0.2
                              for d1 in domains for d2 in domains}
        else:
            self.resonance = resonance

        self.alpha = alpha
        self.alpha_max = alpha_max
        self.beta_0 = beta_0
        self.gamma = gamma
        self.kappa = kappa
        self.eta = eta
        self.eps_0 = eps_0
        self.c = c
        self.noise_std = noise_std
        self.entropy_gain = entropy_gain
        self.entropy_thresh = entropy_thresh
        self.entropy_cap = entropy_cap

        # State
        self.F = {d: np.zeros_like(targets[d]) for d in domains}
        self.M = {d: 0.0 for d in domains}
        self.history = {d: {"F": [], "phi": [], "M": [], "entropy": []} for d in domains}

    # --------------------------------------------------------
    # Satisfaction
    # --------------------------------------------------------
    def _phi(self, domain: str) -> float:
        dist = self.sets[domain].dist(self.F[domain])
        return 1.0 / (1.0 + dist)

    # --------------------------------------------------------
    # Teleological pull (stable, small)
    # --------------------------------------------------------
    def _teleo(self, x: np.ndarray) -> np.ndarray:
        if self.teleological is None:
            return np.zeros_like(x)
        direction = self.teleological - x
        norm = np.linalg.norm(direction)
        if norm < 1e-8:
            return np.zeros_like(x)
        return self.teleo_weight * direction / norm

    # --------------------------------------------------------
    # Single step (all domains)
    # --------------------------------------------------------
    def step(self) -> Dict[str, Dict]:
        # Compute all satisfactions first (needed for synergy)
        phi = {d: self._phi(d) for d in self.domains}
        results = {}

        for d in self.domains:
            x = self.F[d]
            base_phi = phi[d]

            # ----- Cross‑domain synergy -----
            synergy = sum(self.resonance.get((other, d), 0.0) * phi[other]
                          for other in self.domains if other != d)
            # Boost effective step size based on synergy
            eff_alpha_base = self.alpha * (1.0 + synergy)

            # ----- Memory update -----
            self.M[d] = (1 - self.kappa) * self.M[d] + self.eta * base_phi

            # ----- Relaxation radius & resistance -----
            eps = self.eps_0 + self.c * self.M[d]
            beta = self.beta_0 * np.exp(-self.gamma * self.M[d])

            # ----- Proper relaxed projection -----
            Pi = relaxed_projection(x, self.sets[d], eps)

            # ----- Teleological correction -----
            teleo = self._teleo(x)

            # ----- Noise -----
            xi = np.random.normal(0, self.noise_std, size=x.shape)
            xi_norm = min(np.linalg.norm(xi), self.entropy_cap)

            # ----- Entropy harvesting -----
            harvested = False
            if base_phi > self.entropy_thresh:
                eff_alpha = eff_alpha_base + self.entropy_gain * xi_norm
                harvested = True
            else:
                eff_alpha = eff_alpha_base
            eff_alpha = min(eff_alpha, self.alpha_max)

            # ----- State update (matches theoretical APSS structure) -----
            self.F[d] = (
                (1 - eff_alpha * beta) * x
                + eff_alpha * (1 + beta) * Pi
                + teleo
                + xi
            )

            # ----- History -----
            self.history[d]["F"].append(self.F[d].copy())
            self.history[d]["phi"].append(base_phi)
            self.history[d]["M"].append(self.M[d])
            self.history[d]["entropy"].append(harvested)

            results[d] = {"F": self.F[d].copy(), "phi": base_phi, "synergy": synergy}

        return results

    # --------------------------------------------------------
    # Run full simulation
    # --------------------------------------------------------
    def run(self) -> Dict:
        for _ in range(self.T):
            self.step()
        return self.history


# ============================================================
# Example: Ball Constraint
# ============================================================
def make_ball(center: np.ndarray, radius: float) -> ConvexSet:
    def proj(x):
        diff = x - center
        norm = np.linalg.norm(diff)
        if norm <= radius:
            return x
        return center + radius * diff / (norm + 1e-12)

    def dist(x):
        return max(0.0, np.linalg.norm(x - center) - radius)

    return ConvexSet(proj, dist)


# ============================================================
# Demonstration
# ============================================================
if __name__ == "__main__":
    np.random.seed(42)

    domains = ["English", "History"]
    sets = {
        "English": make_ball(np.array([1.0, 0.8]), 0.5),
        "History": make_ball(np.array([0.9, 0.7]), 0.4),
    }
    targets = {
        "English": np.array([1.0, 0.8]),
        "History": np.array([0.9, 0.7]),
    }

    # Teleological "Still Center": Master Communicator
    teleo = np.array([0.95, 0.85])

    # Strong synergy: English mastery boosts History narrative skills
    resonance = {
        ("English", "English"): 1.0,
        ("History", "History"): 1.0,
        ("English", "History"): 0.7,
        ("History", "English"): 0.4,
    }

    sov = SovereignAPSS(
        domains=domains,
        sets=sets,
        targets=targets,
        T=50,
        teleological=teleo,
        teleo_weight=0.05,
        resonance=resonance,
        alpha=0.1,
        entropy_gain=0.05,
        entropy_thresh=0.8,
    )

    # Initial states (novice)
    sov.F["English"] = np.array([0.0, 0.0])
    sov.F["History"] = np.array([0.0, 0.0])

    history = sov.run()

    print("=== Sovereign APSS: Convex Relaxation + Resonance + Entropy + Teleology ===\n")
    for d in domains:
        final_dist = sets[d].dist(sov.F[d])
        final_phi = history[d]["phi"][-1]
        entropy_count = sum(history[d]["entropy"])
        print(f"{d:8s} | final dist = {final_dist:.4f} | phi = {final_phi:.3f} | entropy harvested = {entropy_count} times")
