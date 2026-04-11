# ============================================================
# 🌌 MASTER FORMULA (Publication-Ready Implementation)
# Projection-Driven Error-Contracting Dynamical System
# ============================================================

import numpy as np
from typing import Callable, Tuple

# ------------------------------------------------------------
# 1. MATHEMATICAL MODEL
# ------------------------------------------------------------
# Δ_t = μF( Π_L(P_t) − β (P_t − Π_L(P_t)) )
# P_{t+1} = P_t + α Δ_t
#
# ε_t = (I − Π_L)P_t
#
# Stability condition (sufficient, not necessary):
# α(1 + β) < 1
#
# Lyapunov function: V(P) = ||P - Π_L(P)||^2
# Under the stability condition and boundedness of the iterates,
# V(P_t) is non-increasing and converges to zero.
#
# Convergence is to the constraint subspace Im(Π_L), not necessarily a unique point.
# Fixed points satisfy: P* = Π_L(P*)   (i.e., P* lies in the constraint subspace).

# ------------------------------------------------------------
# 2. LIPSCHITZ CHECK (HEURISTIC)
# ------------------------------------------------------------
def check_lipschitz(muF: Callable, dim: int = 5, samples: int = 100, tol: float = 1e-6) -> bool:
    """
    Heuristic check that muF is 1-Lipschitz: ||muF(x) - muF(y)|| <= ||x - y||.
    Returns True if condition holds for all random samples.
    
    NOTE: This is a heuristic check only.
    Lipschitz continuity must be established analytically for guarantees.
    """
    for _ in range(samples):
        x = np.random.randn(dim)
        y = np.random.randn(dim)
        lhs = np.linalg.norm(muF(x) - muF(y))
        rhs = np.linalg.norm(x - y)
        if lhs > rhs + tol:
            return False
    return True


# ------------------------------------------------------------
# 3. MASTER FORMULA UPDATE (OPTIMIZED)
# ------------------------------------------------------------
def master_formula_update(
    P: np.ndarray,
    Pi: np.ndarray,                # Precomputed projection Π_L(P)
    muF: Callable[[np.ndarray], np.ndarray],
    beta: float,
    alpha: float
) -> np.ndarray:
    """
    Perform one iteration of the Master Formula using precomputed projection.

    Parameters:
        P       : Current state vector
        Pi      : Π_L(P) (projection onto constraint subspace)
        muF     : Lipschitz transformation (||μF|| <= 1 recommended)
        beta    : Error contraction parameter (0 < beta < 1)
        alpha   : Step size (must satisfy α(1+β) < 1)

    Returns:
        P_next  : Updated state
    """
    error = P - Pi
    # Core innovation: correction = (1+β)Π_L(P) - βP
    correction = Pi - beta * error
    delta = muF(correction)
    return P + alpha * delta


# ------------------------------------------------------------
# 4. ERROR MEASUREMENT
# ------------------------------------------------------------
def compute_error(P: np.ndarray, project: Callable) -> float:
    """
    Compute ||(I - Π_L)P||, distance to constraint subspace.
    """
    Pi = project(P)
    return np.linalg.norm(P - Pi)


# ------------------------------------------------------------
# 5. STABILITY CHECK
# ------------------------------------------------------------
def is_stable(alpha: float, beta: float) -> bool:
    """
    Check sufficient (but not necessary) stability condition.
    """
    return alpha * (1 + beta) < 1.0


# ------------------------------------------------------------
# 6. ITERATIVE CONVERGENCE PROCESS
# ------------------------------------------------------------
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
    Run Master Formula until convergence to constraint subspace.

    Returns:
        final_state, error_history
    """
    P = P0.copy()
    errors = []

    for _ in range(max_iter):
        Pi = project(P)                # Compute projection once
        err = np.linalg.norm(P - Pi)   # Error norm
        errors.append(err)

        if err < tol:
            break

        P = master_formula_update(P, Pi, muF, beta, alpha)

    return P, errors


# ------------------------------------------------------------
# 7. LINEAR OPERATOR FORM (OPTIONAL)
# ------------------------------------------------------------
def linear_operator(M: np.ndarray, A: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """
    Constructs operator:
    T = I + α A ((1+β)M − βI)

    Where:
        M = projection matrix
        A = linear μF operator
    """
    I = np.eye(M.shape[0])
    return I + alpha * A @ ((1 + beta) * M - beta * I)


# ------------------------------------------------------------
# 8. EXAMPLE: 2D PROJECTION ONTO LINE y = x
# ------------------------------------------------------------
if __name__ == "__main__":

    # Projection onto line y = x
    def project_line(P: np.ndarray) -> np.ndarray:
        x, y = P
        avg = (x + y) / 2
        return np.array([avg, avg])

    # Identity transformation (μF)
    def muF_identity(x: np.ndarray) -> np.ndarray:
        return x

    # Check Lipschitz property (heuristic)
    lipschitz_ok = check_lipschitz(muF_identity, dim=2)
    print(f"μF is 1-Lipschitz (heuristic): {lipschitz_ok}")

    # Parameters (stable choice)
    beta = 0.7
    alpha = 0.5   # α(1+β) = 0.85 < 1 → stable
    print("Stability condition satisfied (sufficient):", is_stable(alpha, beta))

    # Initial state
    P0 = np.array([10.0, 0.0])

    # Run convergence
    final_state, error_history = converge(
        P0,
        project_line,
        muF_identity,
        beta,
        alpha
    )

    print("\nInitial state:", P0)
    print("Final state:  ", final_state)
    print("Final error:  ", error_history[-1])
    print("Iterations:   ", len(error_history))


# ============================================================
# 🌌 FINAL INTERPRETATION (IN CODE FORM)
# ============================================================
# State_next = State_now + α * μF( (1+β)Π_L(P) − βP )
#
# Lyapunov function: V(P) = ||P - Π_L(P)||²
# Under the stability condition and boundedness of the iterates,
# V(P_t) is non-increasing and converges to zero.
#
# Fixed points satisfy: P* = Π_L(P*) → equilibrium lies in the constraint subspace.
#
# Additional note:
# Convergence rate depends on α, β, and the spectral properties of μF.
# Tighter bounds can be derived from the spectral radius of the induced operator.
# ============================================================
