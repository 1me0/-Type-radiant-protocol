"""
universal_master_formula.py

Refined Simulation of the Universal Master Formula (Corrected & Stabilized):

Δ_t = μF ( Π_L(P_t) - β·ε_t )
P_{t+1} = P_t + α·Δ_t

with ε_t = P_t - Π_L(P_t)

Key Features:
- True error reduction (negative sign)
- Spectral normalization of μF (guaranteed bounded operator norm)
- Stability condition: α·(1+β) < 1 prevents oscillation
- Correction velocity tracking (core integrity metric)
- Optional time‑varying law subspace L_t (tracking filter test)
- Clean ZK-compatible linear structure
- Convergence detection and alignment ratio
"""

import numpy as np


class UniversalMasterFormula:
    """Discrete-time dynamical system implementing coherent alignment."""

    def __init__(self, dim: int, alpha: float = 0.1, beta: float = 0.7, seed: int = 42):
        np.random.seed(seed)
        self.dim = dim
        self.alpha = alpha
        self.beta = beta

        # Stability condition: α·(1+β) < 1
        if alpha * (1 + beta) >= 1:
            raise ValueError(f"Stability condition violated: α·(1+β) = {alpha*(1+beta)} >= 1. Reduce α or β.")

        # Create μF and normalize using spectral norm (largest singular value)
        A = np.random.randn(dim, dim)
        u, s, vh = np.linalg.svd(A)
        self.muF = A / s[0]     # ensures ||μF|| <= 1

    def projection_matrix(self, L_basis: np.ndarray) -> np.ndarray:
        """
        Precompute projection matrix Π_L = Q Q^T
        """
        Q, _ = np.linalg.qr(L_basis, mode='reduced')
        return Q @ Q.T

    def step(self, P: np.ndarray, M: np.ndarray):
        """
        Perform one update step and return detailed information.

        Args:
            P: Current state
            M: Projection matrix (Π_L)

        Returns:
            P_next, info_dict
        """
        P_proj = M @ P
        epsilon = P - P_proj

        # Corrected Universal Master Formula (true error reduction)
        Delta = self.muF @ (P_proj - self.beta * epsilon)

        P_next = P + self.alpha * Delta

        info = {
            "error": np.linalg.norm(epsilon),
            "epsilon": epsilon,
            "projection": P_proj,
            "delta": Delta,
            "alignment": np.linalg.norm(P_proj) / (np.linalg.norm(P) + 1e-8)
        }
        return P_next, info


# -----------------------------
# Metrics
# -----------------------------
def correction_velocity(errors):
    """Vectorized discrete correction velocity V_c = Δ(error) per step."""
    errors = np.array(errors)
    return errors[:-1] - errors[1:]


def has_converged(errors, tol=1e-5):
    """Check if the error has stabilized (converged) within tolerance."""
    return len(errors) > 1 and abs(errors[-1] - errors[-2]) < tol


# -----------------------------
# Simulation
# -----------------------------
if __name__ == "__main__":
    dim = 5
    max_steps = 100
    convergence_tol = 1e-5

    umf = UniversalMasterFormula(dim=dim, alpha=0.1, beta=0.7)

    # Initial state
    P = np.random.randn(dim)

    # Initial law subspace (2‑dimensional subspace in 5‑dimensional space)
    L_basis = np.random.randn(dim, 2)
    M = umf.projection_matrix(L_basis)

    errors = []
    alignments = []

    # Uncomment the following line to test dynamic law tracking:
    # dynamic_law = True

    for t in range(max_steps):
        # Optional: slowly vary L_t (tracking filter test)
        # if dynamic_law and t % 10 == 0:
        #     L_basis += 0.05 * np.random.randn(*L_basis.shape)
        #     M = umf.projection_matrix(L_basis)

        P, info = umf.step(P, M)
        errors.append(info["error"])
        alignments.append(info["alignment"])
        print(f"Step {t:2d}: error = {info['error']:.6f}, alignment = {info['alignment']:.6f}")

        if has_converged(errors, tol=convergence_tol):
            print(f"Converged at step {t}")
            break

    velocities = correction_velocity(errors)

    print(f"\nFinal error: {errors[-1]:.6f}")
    print(f"Final alignment: {alignments[-1]:.6f}")
    print(f"Average correction velocity: {np.mean(velocities):.6f}")
    print("Final state:", P)


# -----------------------------
# ZK Circuit Structure (Refined)
# -----------------------------
"""
ZK-Friendly Formulation:

Precompute projection matrix M = Q Q^T off‑circuit.

Witness per step: P_t, P_proj_t, ε_t, Δ_t

Constraints:
    P_proj_t = M * P_t
    ε_t = P_t - P_proj_t
    Δ_t = μF * (P_proj_t - β * ε_t)
    P_{t+1} = P_t + α * Δ_t

Final constraint:
    ε_T = P_T - M * P_T
    sum(ε_T^2) <= δ^2   (inequality can be implemented via a range proof or equality constraint with a slack variable)

Stability recommendation:
    Choose α and β such that α·(1+β) < 1 to ensure the discrete system does not oscillate.

Properties:
- All constraints are linear except final norm check (quadratic).
- Efficient for R1CS / Plonkish systems.
- Compatible with Nova‑style folding.

Folding:
- Each step proves (P_t → P_{t+1})
- Recursively compress into one constant‑size proof.

Result:
- O(1) proof size
- Verifiable iterative alignment
- Private state evolution
"""
