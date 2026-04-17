"""
plot_convergence.py

Runs the Master Formula example and plots the error contraction over iterations.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Callable, Tuple


# ============================================================
# Master Formula helper functions (self‑contained)
# ============================================================
def converge(
    P0: np.ndarray,
    project: Callable[[np.ndarray], np.ndarray],
    muF: Callable[[np.ndarray], np.ndarray],
    beta: float,
    alpha: float,
    max_iter: int = 1000,
    tol: float = 1e-6
) -> Tuple[np.ndarray, list]:
    """
    Iteratively apply the deterministic Master Formula until convergence.
    Returns final state and list of errors.
    """
    P = P0.copy()
    errors = []
    for _ in range(max_iter):
        Pi = project(P)
        err = np.linalg.norm(P - Pi)
        errors.append(err)
        if err < tol:
            break
        # Correction term: (1+β)Π(P) - βP
        correction = (1 + beta) * Pi - beta * P
        P = P + alpha * muF(correction)
    return P, errors


def is_stable(alpha: float, beta: float) -> bool:
    """Check stability condition: α(1+β) < 1."""
    return alpha * (1 + beta) < 1.0


# ============================================================
# Example system: projection onto line y = x
# ============================================================
def project_line(P: np.ndarray) -> np.ndarray:
    x, y = P
    avg = (x + y) / 2
    return np.array([avg, avg])


def muF_identity(x: np.ndarray) -> np.ndarray:
    return x


# ============================================================
# Main script
# ============================================================
def main():
    # Parameters (must satisfy stability)
    beta = 0.7
    alpha = 0.5
    if not is_stable(alpha, beta):
        raise ValueError(f"Stability condition violated: α(1+β) = {alpha*(1+beta)} ≥ 1")

    # Initial state far from the constraint line
    P0 = np.array([10.0, 0.0])

    # Run convergence
    final_state, errors = converge(P0, project_line, muF_identity, beta, alpha)

    # Plot error on semilogarithmic scale
    plt.figure(figsize=(8, 5))
    plt.semilogy(errors, linewidth=2, color='#2c7da0')
    plt.xlabel("Iteration", fontsize=12)
    plt.ylabel("Error norm $||P_t - \\Pi(P_t)||$ (log scale)", fontsize=12)
    plt.title("Master Formula: Exponential Error Contraction", fontsize=14)
    plt.grid(True, which="both", linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig("convergence.png", dpi=150)
    plt.show()

    print(f"Final error after {len(errors)} iterations: {errors[-1]:.6e}")
    print(f"Final state: {final_state}")


if __name__ == "__main__":
    main()
