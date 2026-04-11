# ============================================================
# 🌌 MASTER FORMULA — FINAL STABILIZED PUBLICATION VERSION
# State-dependent stochastic projection + Lyapunov bifurcation
# ============================================================

import numpy as np
from typing import Callable, Dict, List, Tuple


# ============================================================
# 1. PROJECTION OPERATOR (bounded + non-expansive assumption)
# ============================================================
class ProjectionOperator:
    """
    Π: ℝⁿ → C (closed convex approximation)

    Optional radius enforces boundedness (Assumption A4).
    """

    def __init__(self, project_fn: Callable[[np.ndarray], np.ndarray], radius: float = None):
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
# 2. STATE-DEPENDENT NOISE MODEL
# ============================================================
def sigma(P: np.ndarray, Pi: np.ndarray, sigma0: float, gamma: float) -> float:
    return sigma0 + gamma * np.linalg.norm(P - Pi)


def noisy_projection(
    P: np.ndarray,
    proj: ProjectionOperator,
    sigma0: float,
    gamma: float,
    rng: np.random.Generator
) -> np.ndarray:
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

    Pi_tilde = noisy_projection(P, proj, sigma0, gamma, rng)
    u = (1.0 + beta) * Pi_tilde - beta * P
    return P + alpha * muF(u)


# ============================================================
# 4. LYAPUNOV FUNCTION
# ============================================================
def lyapunov(P: np.ndarray, proj: ProjectionOperator) -> float:
    Pi = proj(P)
    return float(np.linalg.norm(P - Pi) ** 2)


# ============================================================
# 5. LYAPUNOV EXPONENT (mean exponential rate)
# ============================================================
def lyapunov_exponent(history: np.ndarray, burn_in: int = 0) -> float:
    h = history[burn_in:]
    log_h = np.log(h + 1e-12)

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

    rng = np.random.default_rng(seed)
    P = P0.copy()
    V = np.zeros(steps)

    for t in range(steps):
        V[t] = lyapunov(P, proj)
        P = step(P, proj, muF, alpha, beta, sigma0, gamma, rng)

    return V


# ============================================================
# 7. MONTE CARLO STATISTICS (true expectation proxy)
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

    exponents = []
    final_vals = []

    for i in range(runs):
        hist = simulate(P0, proj, muF, alpha, beta, sigma0, gamma, steps, seed=i)

        exponents.append(lyapunov_exponent(hist, burn_in))
        final_vals.append(np.mean(hist[-50:]))

    return {
        "E_lambda": float(np.mean(exponents)),
        "std_lambda": float(np.std(exponents)),
        "E_V_inf": float(np.mean(final_vals)),
        "std_V_inf": float(np.std(final_vals))
    }


# ============================================================
# 8. BIFURCATION SCAN (zero-crossing of Lyapunov exponent)
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
# 9. EXAMPLE SYSTEM
# ============================================================
if __name__ == "__main__":

    def project_line(P):
        x, y = P
        m = (x + y) / 2
        return np.array([m, m])

    def muF_identity(x):
        return x

    alpha = 0.4
    beta = 0.6
    sigma0 = 0.0
    dim = 2
    radius = 100.0

    proj = ProjectionOperator(project_line, radius)

    P0 = np.array([8.0, -3.0])

    gammas = np.linspace(0.0, 1.0, 11)

    results = bifurcation_scan(
        gammas, runs=40,
        P0=P0,
        proj=proj,
        muF=muF_identity,
        alpha=alpha,
        beta=beta,
        sigma0=sigma0,
        steps=250,
        burn_in=30
    )

    print("\nγ | λ (Lyapunov exponent) | E[V∞]")
    print("----------------------------------------")

    for r in results:
        mark = " <-- bifurcation region" if abs(r["lyapunov_exponent"]) < 0.02 else ""
        print(f"{r['gamma']:.3f} | {r['lyapunov_exponent']:+.5f} | {r['asymptotic_mean']:.5f}{mark}")
