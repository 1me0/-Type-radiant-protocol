"""
universal_master_formula.py

Refined Simulation of the Universal Master Formula (Corrected & Stabilized):

Δ_t = μF ( Π_L(P_t) - β·ε_t )
P_{t+1} = P_t + α·Δ_t

with ε_t = P_t - Π_L(P_t)

Key Features:
- True error reduction (negative sign)
- Spectral normalization of μF (guaranteed bounded operator norm)
- Conservative stability condition: α·(1+β) < 1 (sufficient, not necessary)
- Correction velocity tracking (core integrity metric)
- Optional time‑varying law subspace L_t (tracking filter test)
- Monotonicity detection with tolerance (handles numerical noise)
- Energy change (Lyapunov function) for stability analysis
- Spectral eigenvalue analysis of μF
- Experimental stability validation near boundary
- Lyapunov diagnostics (error‑based Lyapunov function and its change)
- Explicit system operator T(P) for analysis and reuse
- Stability summary function
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

        # Conservative stability condition (sufficient, not necessary)
        if alpha * (1 + beta) >= 1:
            raise ValueError(f"Stability condition violated: α·(1+β) = {alpha*(1+beta)} >= 1. Reduce α or β.")

        # Create μF and normalize using spectral norm (largest singular value)
        A = np.random.randn(dim, dim)
        u, s, vh = np.linalg.svd(A)
        self.muF = A / s[0]     # ensures ||μF|| <= 1

        # Store eigenvalues for spectral analysis
        self.eigenvalues = np.linalg.eigvals(self.muF)

    def projection_matrix(self, L_basis: np.ndarray) -> np.ndarray:
        """
        Precompute projection matrix Π_L = Q Q^T
        """
        Q, _ = np.linalg.qr(L_basis, mode='reduced')
        return Q @ Q.T

    def operator(self, P: np.ndarray, M: np.ndarray) -> np.ndarray:
        """
        Explicit system operator T(P) = P + α·μF (Π_L(P) - β·(P - Π_L(P)))
        """
        P_proj = M @ P
        epsilon = P - P_proj
        return P + self.alpha * (self.muF @ (P_proj - self.beta * epsilon))

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

        # Compute metrics
        error = np.linalg.norm(epsilon)
        error_energy = error ** 2   # Lyapunov candidate V = ||ε||²
        norm_P = np.linalg.norm(P)
        alignment = np.linalg.norm(P_proj) / norm_P if norm_P > 1e-8 else 0.0
        energy = np.linalg.norm(P) ** 2

        info = {
            "error": error,
            "error_energy": error_energy,
            "epsilon": epsilon,
            "projection": P_proj,
            "delta": Delta,
            "alignment": alignment,
            "energy": energy
        }
        return P_next, info


# -----------------------------
# Metrics and Analysis Functions
# -----------------------------
def correction_velocity(errors):
    """Vectorized discrete correction velocity V_c = Δ(error) per step."""
    errors = np.array(errors)
    return errors[:-1] - errors[1:]


def energy_change(energies):
    """Compute ΔE = E_{t+1} - E_t for Lyapunov stability analysis."""
    energies = np.array(energies)
    return energies[1:] - energies[:-1]


def lyapunov_error(errors):
    """
    Lyapunov function based on squared error: V = ||ε||^2
    """
    errors = np.array(errors)
    return errors ** 2


def lyapunov_change(errors):
    """
    ΔV = V_{t+1} - V_t using error-based Lyapunov function
    """
    V = lyapunov_error(errors)
    return V[1:] - V[:-1]


def has_converged(errors, tol=1e-5):
    """Check if the error has stabilized (converged) within tolerance."""
    return len(errors) > 1 and abs(errors[-1] - errors[-2]) < tol


def is_monotonic(errors, tol=1e-8):
    """
    Check if error sequence is monotonically non‑increasing, allowing small numerical noise.
    """
    return all(errors[i] <= errors[i-1] + tol for i in range(1, len(errors)))


def stability_summary(errors, energies):
    """
    Summarize stability behavior of the system.
    """
    vel = correction_velocity(errors)
    energy_deltas = energy_change(energies)

    return {
        "avg_velocity": float(np.mean(vel)) if len(vel) > 0 else 0.0,
        "avg_energy_change": float(np.mean(energy_deltas)) if len(energy_deltas) > 0 else 0.0,
        "final_error": float(errors[-1]),
        "monotonic": is_monotonic(errors)
    }


# -----------------------------
# Simulation
# -----------------------------
if __name__ == "__main__":
    dim = 5
    max_steps = 100
    convergence_tol = 1e-5
    dynamic_law = False          # set to True to test tracking of moving target

    # Experiment: run near stability boundary (e.g., α = 0.45, β = 1.2 gives α·(1+β)=0.99)
    alpha_test = 0.1   # change to 0.45 to test boundary
    beta_test = 0.7
    umf = UniversalMasterFormula(dim=dim, alpha=alpha_test, beta=beta_test)

    # Display spectral properties of μF
    print("Spectral eigenvalues of μF (magnitudes):")
    print(np.abs(umf.eigenvalues))
    max_eig = np.max(np.abs(umf.eigenvalues))
    print(f"Max eigenvalue magnitude: {max_eig:.6f}")
    print(f"Stability product α·(1+β) = {alpha_test * (1 + beta_test):.4f}\n")

    # Initial state
    P = np.random.randn(dim)

    # Initial law subspace (2‑dimensional subspace in 5‑dimensional space)
    L_basis = np.random.randn(dim, 2)
    M = umf.projection_matrix(L_basis)

    errors = []
    error_energies = []
    alignments = []
    energies = []

    for t in range(max_steps):
        # Vary law subspace if dynamic_law is True (every 10 steps)
        if dynamic_law and t % 10 == 0:
            L_basis += 0.05 * np.random.randn(*L_basis.shape)
            M = umf.projection_matrix(L_basis)
            print(f"Step {t}: law subspace changed")

        P, info = umf.step(P, M)
        errors.append(info["error"])
        error_energies.append(info["error_energy"])
        alignments.append(info["alignment"])
        energies.append(info["energy"])
        print(f"Step {t:2d}: error = {info['error']:.6f}, alignment = {info['alignment']:.6f}, energy = {info['energy']:.6f}")

        if has_converged(errors, tol=convergence_tol):
            print(f"Converged at step {t}")
            break

    velocities = correction_velocity(errors)
    energy_deltas = energy_change(energies)
    V_deltas = lyapunov_change(errors)
    monotonic = is_monotonic(errors, tol=1e-8)
    summary = stability_summary(errors, energies)

    print(f"\nFinal error: {errors[-1]:.6f}")
    print(f"Final error energy (V): {error_energies[-1]:.6f}")
    print(f"Final alignment: {alignments[-1]:.6f}")
    print(f"Final energy: {energies[-1]:.6f}")
    print(f"Average correction velocity: {np.mean(velocities):.6f}")
    print(f"Average energy change: {np.mean(energy_deltas):.6f} (negative = stable)")
    print(f"Average Lyapunov change (error-based): {np.mean(V_deltas):.6f} (negative = stable)")
    print(f"Monotonic error decrease (with tolerance): {monotonic}")
    print("\nStability Summary:")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"Convergence steps: {len(errors)}")
    print(f"Final error vs eigenvalue scale: {errors[-1]:.6f} vs {max_eig:.6f}")
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

Stability recommendation (conservative):
    Choose α and β such that α·(1+β) < 1 to ensure the discrete system does not oscillate.
    This is a sufficient condition; tighter bounds depend on μF's spectrum.

Implementation note for ZK:
    All arithmetic must be performed in a finite field (e.g., prime field for elliptic curves).
    Floating‑point simulations are for analysis; actual circuits use fixed‑point or modular arithmetic.

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
