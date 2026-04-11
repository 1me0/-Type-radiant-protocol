"""
plot_convergence.py

Runs the Master Formula example and plots the error contraction over iterations.
"""

import numpy as np
import matplotlib.pyplot as plt
from master_formula import converge, is_stable

# Reuse the projection and muF from the example
def project_line(P: np.ndarray) -> np.ndarray:
    x, y = P
    avg = (x + y) / 2
    return np.array([avg, avg])

def muF_identity(x: np.ndarray) -> np.ndarray:
    return x

# Parameters
beta = 0.7
alpha = 0.5
assert is_stable(alpha, beta), "Stability condition violated"

# Initial state
P0 = np.array([10.0, 0.0])

# Run convergence and get error history
final_state, errors = converge(P0, project_line, muF_identity, beta, alpha)

# Plot error on semilogarithmic scale
plt.figure(figsize=(8, 5))
plt.semilogy(errors, linewidth=2)
plt.xlabel("Iteration")
plt.ylabel("Error norm (log scale)")
plt.title("Master Formula: Error Contraction")
plt.grid(True, which="both", linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig("convergence.png", dpi=150)
plt.show()

print(f"Final error after {len(errors)} iterations: {errors[-1]:.6e}")
