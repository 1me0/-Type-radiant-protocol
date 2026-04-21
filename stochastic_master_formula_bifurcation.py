"""
🌌 MASTER FORMULA — FINAL STABILIZED PUBLICATION VERSION
State‑dependent stochastic projection + Lyapunov bifurcation

This module implements the Master Formula:
    P_{t+1} = P_t + α μF( (1+β)Π̃(P_t) − β P_t )
with state‑dependent noise and a convex projection operator.
It includes Monte Carlo simulation, Lyapunov exponent estimation,
and a bifurcation scan over the noise‑error coupling γ.

Author: Radiant Protocol
License: MIT
"""

import numpy as np
from typing import Callable, Dict, List, Tuple, Union, Optional


# ============================================================
# 1. PROJECTION OPERATOR (bounded + non‑expansive assumption)
# ============================================================
class ProjectionOperator:
    """
    Π: ℝⁿ → C (closed convex approximation)

    Optional radius enforces boundedness (Assumption A4).
    """

    def __init__(self, project_fn: Callable[[np.ndarray], np.ndarray], radius: Optional[float] = None):
        """
        Args:
            project_fn: Function that projects a point onto the constraint set.
            radius: If not None, projects the result onto a ball of this radius.
        """
        self.project_fn = project_fn
        self.radius = radius

    def __call__(self, P: np.ndarray) -> np.ndarray:
        Pi = self.project_fn(P)
        if self.radius is not None:
            norm = np.linalg.norm(Pi)
            if norm > self.radius:
                Pi = Pi * (self.radius / (norm + 1e-12))
        return Pi


# ============================================================
# 2. STATE‑DEPENDENT NOISE MODEL
# ============================================================
def sigma(P: np.ndarray, Pi: np.ndarray, sigma0: float, gamma: float) -> float:
    """Standard deviation of state‑dependent noise."""
    return sigma0 + gamma * np.linalg.norm(P - Pi)


def noisy_projection(
    P: np.ndarray,
    proj: ProjectionOperator,
    sigma0: float,
    gamma: float,
    rng: np.random.Generator
) -> np.ndarray:
    """
    Returns noisy projection: Π̃(P) = Π(P) + ξ,
    with ξ ~ N(0, σ(P)² I).
    """
    Pi = proj(P)
    noise_scale = sigma(P, Pi, sigma0, gamma)
    noise = rng.normal(0.0, noise_scale, size=P.shape)
    return Pi + noise


# ============================================================
# 3. DYNAMICAL SYSTEM
# ============================================================
def step(
    P: np.ndarray,
    proj: ProjectionOperator,
    muF: Callable[[np.ndarray], np.ndarray],
    alpha: float,
    beta: float,
    sigma0: float,
    gamma: float,
    rng: np.random.Generator
) -> np.ndarray:
    """
    One step of the Master Formula:
        P_{t+1} = P_t + α μF( (1+β)Π̃(P_t) − β P_t )
    """
    Pi_tilde = noisy_projection(P, proj, sigma0, gamma, rng)
    u = (1.0 + beta) * Pi_tilde - beta * P
    return P + alpha * muF(u)


# ============================================================
# 4. LYAPUNOV FUNCTION
# ============================================================
def lyapunov(P: np.ndarray, proj: ProjectionOperator) -> float:
    """Distance squared to the constraint set: V(P) = ||P - Π(P)||²."""
    Pi = proj(P)
    return float(np.linalg.norm(P - Pi) ** 2)


# ============================================================
# 5. LYAPUNOV EXPONENT (mean exponential rate)
# ============================================================
def lyapunov_exponent(history: np.ndarray, burn_in: int = 0) -> float:
    """
    Estimate the Lyapunov exponent from a history of Lyapunov values.
    λ < 0 → stable, λ > 0 → unstable.

    Fits log(V_t) = λ t + const via linear regression.
    """
    h = history[burn_in:]
    if len(h) < 2:
        return 0.0
    # Avoid log(0) by clipping to a small positive value
    log_h = np.log(np.maximum(h, 1e-12))
    t = np.arange(len(h))
    slope = np.polyfit(t, log_h, 1)[0]
    return float(slope)


# ============================================================
# 6. SIMULATION (single trajectory)
# ============================================================
def simulate(
    P0: np.ndarray,
    proj: ProjectionOperator,
    muF: Callable[[np.ndarray], np.ndarray],
    alpha: float,
    beta: float,
    sigma0: float,
    gamma: float,
    steps: int,
    seed: int
) -> np.ndarray:
    """
    Run a single stochastic trajectory for 'steps' iterations.
    Returns array of Lyapunov values V_t.
    """
    rng = np.random.default_rng(seed)
    P = P0.copy()
    V = np.zeros(steps)

    for t in range(steps):
        V[t] = lyapunov(P, proj)
        P = step(P, proj, muF, alpha, beta, sigma0, gamma, rng)

    return V


# ============================================================
# 7. MONTE CARLO STATISTICS (expectation proxy)
# ============================================================
def monte_carlo(
    runs: int,
    P0: np.ndarray,
    proj: ProjectionOperator,
    muF: Callable,
    alpha: float,
    beta: float,
    sigma0: float,
    gamma: float,
    steps: int,
    burn_in: int = 20
) -> Dict[str, float]:
    """
    Run multiple independent simulations and return averaged statistics.
    """
    exponents = []
    final_vals = []

    # Use at most the last 50 steps, but not more than available after burn‑in
    tail_len = min(50, steps - burn_in)
    if tail_len <= 0:
        tail_len = max(1, steps // 10)

    for i in range(runs):
        hist = simulate(P0, proj, muF, alpha, beta, sigma0, gamma, steps, seed=i)
        exponents.append(lyapunov_exponent(hist, burn_in))
        final_vals.append(np.mean(hist[-tail_len:]))

    return {
        "E_lambda": float(np.mean(exponents)),
        "std_lambda": float(np.std(exponents)),
        "E_V_inf": float(np.mean(final_vals)),
        "std_V_inf": float(np.std(final_vals))
    }


# ============================================================
# 8. BIFURCATION SCAN (zero‑crossing of Lyapunov exponent)
# ============================================================
def bifurcation_scan(
    gammas: List[float],
    runs: int,
    P0: np.ndarray,
    proj: ProjectionOperator,
    muF: Callable,
    alpha: float,
    beta: float,
    sigma0: float,
    steps: int,
    burn_in: int = 20
) -> List[Dict]:
    """
    Scan over gamma values and compute mean Lyapunov exponent and asymptotic mean.
    """
    results = []
    for g in gammas:
        stats = monte_carlo(
            runs, P0, proj, muF,
            alpha, beta, sigma0, g,
            steps, burn_in
        )
        results.append({
            "gamma": g,
            "lyapunov_exponent": stats["E_lambda"],
            "asymptotic_mean": stats["E_V_inf"],
            "std_lambda": stats["std_lambda"],
            "std_V": stats["std_V_inf"]
        })
    return results


# ============================================================
# 9. EXAMPLE SYSTEM & DEMONSTRATION
# ============================================================
if __name__ == "__main__":
    # Define projection onto the line y = x
    def project_line(P: np.ndarray) -> np.ndarray:
        x, y = P
        m = (x + y) / 2.0
        return np.array([m, m])

    # Identity transformation (no additional drift)
    def muF_identity(x: np.ndarray) -> np.ndarray:
        return x

    # Parameters
    alpha = 0.4
    beta = 0.6
    sigma0 = 0.0          # exact theory validation (no constant noise floor)
    dim = 2
    radius = 100.0        # boundedness radius

    proj = ProjectionOperator(project_line, radius)
    P0 = np.array([8.0, -3.0])

    # Gamma scan
    gammas = np.linspace(0.0, 1.0, 11)

    print("Running bifurcation scan...")
    results = bifurcation_scan(
        gammas, runs=40,
        P0=P0, proj=proj, muF=muF_identity,
        alpha=alpha, beta=beta, sigma0=sigma0,
        steps=250, burn_in=30
    )

    print("\nγ     | Lyapunov exponent λ | E[V∞]")
    print("----------------------------------------")
    for r in results:
        mark = "  <-- bifurcation region" if abs(r["lyapunov_exponent"]) < 0.02 else ""
        print(f"{r['gamma']:.3f} | {r['lyapunov_exponent']:+.5f}           | {r['asymptotic_mean']:.5f}{mark}")
