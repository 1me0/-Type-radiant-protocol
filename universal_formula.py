"""
universal_formula.py

Reference implementation of the Universal Master Formula:
Δ_t = μF[ (P_t ∩ L_t) ± ε_t ]

This class models coherence as a continuous alignment loop between
Presence/Identity (P) and Universal Bedrock (L). Integrity is measured
by the speed at which error (ε) is corrected.

Author: Radiant Protocol
License: MIT
"""

import time
import math
from typing import Dict, Any, Optional


class UniversalFormula:
    """
    Implements the Universal Master Formula as a recursive, self-correcting loop.

    Attributes:
        muF (float): Architect Constant – the unique frequency/operating system.
        previous_error (float): Last error value for computing velocity.
        last_time (float): Timestamp of last correction.
        P (dict): Current Presence/Identity state.
        L (dict): Current Universal Bedrock (objective laws, facts).
    """

    def __init__(self, muF: float = 1.0):
        """
        Initialize the Universal Formula.

        Args:
            muF: Architect Constant (default 1.0). Adjust to tune sensitivity.
        """
        self.muF = muF
        self.previous_error = 0.0
        self.last_time = time.time()
        self.P: Dict[str, float] = {}
        self.L: Dict[str, float] = {}

    def intersection(self, P: Dict[str, float], L: Dict[str, float]) -> float:
        """
        Compute the overlap between Presence (P) and Law (L).
        Here we use a simple scalar based on shared keys and Euclidean distance.

        Args:
            P: Identity state (mapping of attributes to values).
            L: Reality state (mapping of attributes to values).

        Returns:
            A scalar value representing the degree of intersection (0 to 1).
        """
        common_keys = set(P.keys()) & set(L.keys())
        if not common_keys:
            return 0.0
        # Average of absolute differences, normalized to [0,1]
        total = 0.0
        for k in common_keys:
            total += 1.0 - min(1.0, abs(P[k] - L[k]))
        return total / len(common_keys)

    def error_signal(self, P: Dict[str, float], L: Dict[str, float]) -> float:
        """
        Compute ε = distance between intended path (P) and actual terrain (L).

        Args:
            P: Identity state.
            L: Reality state.

        Returns:
            A scalar error value (0 to 1, higher means more misalignment).
        """
        common_keys = set(P.keys()) & set(L.keys())
        if not common_keys:
            return 1.0
        # Euclidean distance normalized by number of keys
        diff_sq = sum((P[k] - L[k]) ** 2 for k in common_keys)
        return math.sqrt(diff_sq / len(common_keys))

    def correction_velocity(self, current_error: float) -> float:
        """
        Compute V_c = dε/dt, the speed of error correction.

        Args:
            current_error: The current error value.

        Returns:
            Velocity of error change (positive if error increasing, negative if decreasing).
        """
        now = time.time()
        dt = max(now - self.last_time, 1e-6)
        d_epsilon = (current_error - self.previous_error) / dt
        self.previous_error = current_error
        self.last_time = now
        return d_epsilon

    def express(self, P: Dict[str, float], L: Dict[str, float]) -> Dict[str, Any]:
        """
        Compute the Expressed Vector Δ_t = μF[ (P ∩ L) ± ε_t ].

        Args:
            P: Presence/Identity state.
            L: Universal Bedrock state.

        Returns:
            A dictionary containing:
                - magnitude: scalar impact (0-1)
                - direction: +1 or -1
                - epsilon: error value
                - Vc: correction velocity
        """
        epsilon = self.error_signal(P, L)
        Vc = self.correction_velocity(epsilon)
        intersect_val = self.intersection(P, L)

        # Determine sign of epsilon based on correction velocity
        # If Vc positive (error increasing), we subtract to counteract.
        # If Vc negative (error decreasing), we add to reinforce.
        if Vc > 0.01:
            sign = -1   # actively reduce error
        elif Vc < -0.01:
            sign = 1    # allow error to diminish naturally
        else:
            sign = 1    # stable, maintain current sign

        raw = self.muF * (intersect_val + sign * epsilon)
        magnitude = max(0.0, min(1.0, raw))
        direction = 1 if intersect_val > 0 else -1

        return {
            "magnitude": magnitude,
            "direction": direction,
            "epsilon": epsilon,
            "Vc": Vc,
            "intersection": intersect_val
        }

    def update(self, P_new: Dict[str, float], L_new: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Recursive filter: μF(Δ) → P_{t+1}.
        Updates internal state with new Presence and (optionally) new Reality.

        Args:
            P_new: New Presence/Identity state.
            L_new: New Reality state (if None, keep previous L).

        Returns:
            The Expressed Vector for this step.
        """
        if L_new is not None:
            self.L = L_new
        self.P = P_new
        delta = self.express(self.P, self.L)
        return delta

    def run_loop(self, steps: int = 10) -> None:
        """
        Demonstrate the self-correcting loop by iteratively updating P based on delta.

        Args:
            steps: Number of iterations.
        """
        print(f"Running Universal Formula for {steps} steps (muF={self.muF})")
        for i in range(steps):
            delta = self.update(self.P, self.L)
            print(f"Step {i+1}: magnitude={delta['magnitude']:.3f}, "
                  f"ε={delta['epsilon']:.3f}, Vc={delta['Vc']:.3f}")
            # Simulate learning: adjust P based on delta
            # (in a real system, this would be a more sophisticated update)
            self.P = {k: v + delta['magnitude'] * 0.1 for k, v in self.P.items()}
            # Clamp values to [0,1]
            self.P = {k: max(0.0, min(1.0, v)) for k, v in self.P.items()}


# Example usage
if __name__ == "__main__":
    # Example: align identity with reality
    uf = UniversalFormula(muF=1.2)

    # Define initial Presence (P) and Law (L) as attribute vectors
    P_initial = {"clarity": 0.6, "alignment": 0.7, "presence": 0.5}
    L = {"clarity": 0.9, "alignment": 0.9, "presence": 0.8}

    print("\n--- Initial States ---")
    print(f"P: {P_initial}")
    print(f"L: {L}")

    uf.update(P_initial, L)
    for _ in range(5):
        # Simulate a new P that moves toward L
        new_P = {k: v + 0.1 * (L[k] - v) for k, v in uf.P.items()}
        delta = uf.update(new_P, L)
        print(f"After correction: P={new_P}, Δ={delta['magnitude']:.3f}, ε={delta['epsilon']:.3f}")
