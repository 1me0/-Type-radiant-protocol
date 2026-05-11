"""
radiant_dynamics.py

Load‑Governed Stability Framework – Radiant Protocol core computation.

Mathematical models covered by the Radiant Protocol Master Formula License (RPML) v1.0.
Code: MIT License.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple
import numpy as np


class Manifold(ABC):
    """Riemannian manifold with exponential map."""
    @abstractmethod
    def exp(self, base: np.ndarray, tangent: np.ndarray, step: float = 1.0) -> np.ndarray:
        """Retraction: P_{t+1} = Exp_{P_t}^{FR}( η * v )."""
        pass


class EuclideanManifold(Manifold):
    """Flat Euclidean space as a trivial manifold."""
    def exp(self, base: np.ndarray, tangent: np.ndarray, step: float = 1.0) -> np.ndarray:
        return base + step * tangent


class RadiantDynamics:
    """
    Load‑Governed Stability engine.

    Definitions:
        α (alpha)   – regulatory capacity ( > 0 )
        β (beta)    – disturbance amplification ( ≥ 0 )
        Λ (Lambda)  – systemic load = (1 + β) / α

    Mercy Memory:
        M_{t+1} = (1-κ) M_t + η·φ(P_t) - λ·ν_t
        ε_t = ε_0 + c·M_t·U_t

    Relaxed Projection:
        Π̃(P) = Π_{M_t^{ε_t}}(P)

    Transformation:
        T_t(P; ξ) = (1+β_t) Π̃(P) - β_t P + ξ

    Master Equation:
        P_{t+1} = Exp_{P_t}( η₀·(1-Λ_t)_+ · ∇_P 𝔼_ξ[ F( T_t(P_t;ξ) ) ] )
    """

    def __init__(
        self,
        alpha_init: float = 0.8,
        beta_init: float = 0.2,
        kappa: float = 0.1,
        eta_memory: float = 0.8,
        lambda_conf: float = 0.2,
        epsilon0: float = 0.01,
        c_mercy: float = 0.2,
        eta0: float = 0.05,
        manifold: Optional[Manifold] = None,
    ):
        # System parameters
        self.alpha = float(alpha_init)
        self.beta = float(beta_init)

        # Mercy memory parameters
        self.kappa = kappa
        self.eta_mem = eta_memory
        self.lamb = lambda_conf
        self.eps0 = epsilon0
        self.c_mercy = c_mercy

        # Base learning rate
        self.eta0 = eta0

        # Internal state
        self.M = 0.0          # mercy memory
        self.U = 0.2          # uncertainty (can be updated externally)
        self.epsilon = self.eps0
        self.manifold = manifold or EuclideanManifold()

    @property
    def Lambda(self) -> float:
        """Systemic load."""
        return (1.0 + self.beta) / self.alpha

    def load_brake(self) -> float:
        """Load brake factor: max(0, 1 - Lambda). Zero when Lambda >= 1."""
        return max(0.0, 1.0 - self.Lambda)

    def update_mercy(self, phi: float, nu: float) -> None:
        """
        Update mercy memory and resulting relaxation radius.

        Args:
            phi: constraint violation measure ≥ 0.
            nu: confidence signal (prediction accuracy, reward) ∈ [0,1].
        """
        self.M = (1 - self.kappa) * self.M + self.eta_mem * phi - self.lamb * nu
        # Clamp mercy to non-negative
        if self.M < 0.0:
            self.M = 0.0
        self.epsilon = self.eps0 + self.c_mercy * self.M * self.U

    def relaxed_projection(self, P: np.ndarray,
                           target_set: Optional[Callable[[np.ndarray], np.ndarray]] = None) -> np.ndarray:
        """
        Compute the relaxed projection Π̃(P) = projection onto M_t^{ε_t}.

        If target_set is None, identity is returned.
        Otherwise, implement the projection onto the ε-relaxed set using the given
        projection function and the current ε value.
        For simplicity, this base version uses a simple clamp toward the target.
        Override in subclasses for specific constraint sets.
        """
        if target_set is None:
            # No constraint set: projection is identity
            return P.copy()
        # Example: target_set(P) returns the projection onto the unrelaxed set.
        proj = target_set(P)
        diff = P - proj
        dist = np.linalg.norm(diff)
        if dist <= self.epsilon:
            return P.copy()
        return proj + self.epsilon * diff / (dist + 1e-12)

    def transform(self, P: np.ndarray,
                  target_set: Optional[Callable[[np.ndarray], np.ndarray]] = None,
                  xi: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply the transformation T_t(P; xi) = (1+β)Π̃(P) - β P + ξ.
        """
        Pi = self.relaxed_projection(P, target_set)
        transformed = (1.0 + self.beta) * Pi - self.beta * P
        if xi is not None:
            transformed += xi
        return transformed

    def step(self, P: np.ndarray,
             grad_expected: np.ndarray,
             target_set: Optional[Callable[[np.ndarray], np.ndarray]] = None,
             xi: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Execute one master step:

            P_next = Exp_{P}( η₀ · (1-Λ)_+ · ∇_P E[F] )

        Also after the step, update the mercy memory. The caller should provide
        the violation φ and confidence ν to update_mercy().
        """
        brake = self.load_brake()
        effective_step = self.eta0 * brake
        if effective_step <= 0:
            return P  # brake fully engaged, no movement

        # The manifold exponential map moves the state along the scaled gradient.
        P_next = self.manifold.exp(P, grad_expected, step=effective_step)

        # Optional: we could apply a transformation if needed, but the master equation
        # already uses expected gradient. We return updated state.
        return P_next


# =============================================================================
# Example usage
# =============================================================================
if __name__ == "__main__":
    # Example: simple 2D quadratic objective F(Q) = -||Q||^2, maximisation.
    # The gradient ∇F = -2Q, so ascent moves toward zero.
    engine = RadiantDynamics(alpha_init=0.8, beta_init=0.1, eta0=0.1)

    # Simulate abstract step with a dummy gradient and violation/confidence.
    P = np.array([2.0, 2.0])

    # Fake constraint projection: clamp to sphere of radius 5.
    def proj_sphere(x, radius=5.0):
        norm = np.linalg.norm(x)
        if norm > radius:
            return x * radius / norm
        return x

    for t in range(30):
        # Gradient: expected gradient of F(T(P)) (we ignore noise for illustration)
        # For simplicity, treat F(Q) = -||Q||^2, and T(P) = (1+β)Π(P) - β P.
        # So compute gradient directly: dF/dQ = -2Q, then chain rule.
        Pi = engine.relaxed_projection(P, lambda x: proj_sphere(x))
        T = engine.transform(P, lambda x: proj_sphere(x))
        # Approximation: gradient w.r.t P of F(T(P)) ≈ (dT/dP)^T · dF/dQ
        # For the demo, we use a numerical gradient.
        # Instead, we use the fact that the natural gradient points toward improving F.
        # We'll just compute an analytic gradient for the simple case:
        grad = -2.0 * T  # derivative w.r.t T (since objective F(T) = -||T||^2)
        # Jacobian of T w.r.t P: (1+β) * JPi - β * I. JPi is projection Jacobian.
        # We approximate by differentiating through a numerical perturbation.
        # For demonstration, we just take grad as a rough direction.
        P_new = engine.step(P, grad)

        # After step, compute violation (distance from sphere boundary squared) and confidence.
        violation = max(0.0, np.linalg.norm(P_new) - 5.0) ** 2
        confidence = 0.5  # dummy
        engine.update_mercy(violation, confidence)

        P = P_new
        print(f"t={t:2d}, Λ={engine.Lambda:.3f}, ε={engine.epsilon:.4f}, P={P.round(4)}")
