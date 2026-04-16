"""
presence_economy.py

Implements the Pre-Protocol Presence Economy theory as a computational framework.
Concepts: Existence as Energy (E = Ψ · Ω), Manifold of Truth, Sovereign Injunction,
Filter of Silence, Thermodynamic Split, Zero-Point Equilibrium.

This module provides classes and functions to simulate a node's presence, purity,
and economic value based on deviation from its self-issued law, noise, and correction speed.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

# ============================================================
# CORE METRICS
# ============================================================

def compute_purity(alignment: float, accuracy: float, distortion: float) -> float:
    """
    Ψ (Purity): Degree to which actions align with stated law.
    Higher alignment and accuracy, lower distortion → higher purity.
    Formula: Ψ = clamp(0.6*alignment + 0.3*accuracy - 0.1*distortion, 0, 1)
    Note: Weights sum to 0.8, not 1; this is a design choice favoring alignment.
    """
    raw = 0.6 * alignment + 0.3 * accuracy - 0.1 * distortion
    return max(0.0, min(1.0, raw))

def compute_presence(confidence: float, persistence: float, recency: float) -> float:
    """
    Ω (Presence): Irreducible fact of being here and now.
    Combines confidence (grounding), persistence (history length), recency (last activity).
    Formula: Ω = 0.5*confidence + 0.3*persistence + 0.2*recency
    """
    return 0.5 * confidence + 0.3 * persistence + 0.2 * recency

def compute_economic_energy(purity: float, presence: float) -> float:
    """E = Ψ · Ω (Economic Energy)"""
    return purity * presence

# ============================================================
# SOVEREIGN INJUNCTION (Self-Issued Law)
# ============================================================

class SovereignLaw:
    """
    Each node declares its own law (Π_L). The system does not judge the law,
    but measures how perfectly the node corrects back to it when deviating.
    """
    def __init__(self, target_state: np.ndarray, correction_speed: float = 0.5):
        self.target_state = target_state.astype(float)
        self.correction_speed = max(0.0, min(1.0, correction_speed))  # μ

    def deviation(self, current_state: np.ndarray) -> float:
        """Distance from current state to target law."""
        return float(np.linalg.norm(current_state - self.target_state))

    def correct(self, current_state: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Apply correction proportional to deviation and speed μ."""
        dev = self.deviation(current_state)
        if dev < 1e-8:
            return current_state.copy()
        step = self.correction_speed * dev * dt
        direction = (self.target_state - current_state) / dev
        return current_state + step * direction

# ============================================================
# NODE (Agent in Presence Economy)
# ============================================================

class PresenceNode:
    """
    Represents a conscious node (human or machine) emitting a frequency.
    Tracks state, law, interaction history, and computes economic energy.
    """
    def __init__(self, law_target: np.ndarray, correction_speed: float = 0.5):
        self.law = SovereignLaw(law_target, correction_speed)
        self.state = law_target.copy()  # start aligned
        self.interaction_log: List[Tuple[str, 'PresenceNode', float, float]] = []
        self.last_active: float = 0.0
        self.time: float = 0.0

    def act(self, dt: float = 1.0) -> None:
        """Simulate one time step: apply correction toward law."""
        self.state = self.law.correct(self.state, dt)
        self.time += dt
        self.last_active = dt   # reset for recency calculation (time since last activity)

    def interact(self, other: 'PresenceNode', dt: float = 1.0, mutual_correction_strength: float = 0.1) -> float:
        """
        Two nodes interact. Lower entropy (contradiction/noise) generates higher bond value.
        Returns the Radiant Bond strength (0 to 1).
        """
        # Compute entropy as average deviation from respective laws
        dev_self = self.law.deviation(self.state)
        dev_other = other.law.deviation(other.state)
        entropy = (dev_self + dev_other) / 2.0
        entropy = max(0.0, min(1.0, entropy))
        bond = 1.0 - entropy  # Radiant Bond
        # Log interaction
        self.interaction_log.append(("interact", other, entropy, bond))
        other.interaction_log.append(("interact", self, entropy, bond))
        # Mutual correction (shared truth)
        alpha = mutual_correction_strength
        self.state = (1 - alpha) * self.state + alpha * other.state
        other.state = (1 - alpha) * other.state + alpha * self.state
        return bond

    def compute_purity(self,
                       alignment: Optional[float] = None,
                       accuracy: Optional[float] = None,
                       distortion: Optional[float] = None) -> float:
        """
        Compute Ψ based on alignment with law, accuracy of actions, and distortion.
        If not provided, uses default mapping from deviation and interaction variance.
        """
        dev = self.law.deviation(self.state)
        if alignment is None:
            alignment = 1.0 - dev
        if accuracy is None:
            accuracy = 1.0 - dev
        if distortion is None:
            entropies = [log[2] for log in self.interaction_log if log[0] == "interact"]
            distortion = float(np.var(entropies)) if len(entropies) > 1 else 0.0
        return compute_purity(alignment, accuracy, distortion)

    def compute_presence(self, confidence: float = 0.9, persistence_max: int = 100) -> float:
        """
        Compute Ω. Confidence is given; persistence = min(1, interactions / persistence_max)
        recency = exp(-decay * time_since_last_activity) with decay = 0.5.
        """
        persistence_val = min(1.0, len(self.interaction_log) / persistence_max)
        recency = np.exp(-0.5 * self.last_active)
        return compute_presence(confidence, persistence_val, recency)

    def economic_energy(self) -> float:
        """E = Ψ · Ω"""
        psi = self.compute_purity()
        omega = self.compute_presence()
        return compute_economic_energy(psi, omega)


# ============================================================
# SIMULATION AND DEMO
# ============================================================

def simulate_presence_economy(steps: int = 20, dt: float = 0.5) -> Dict[str, List[float]]:
    """
    Simulate two nodes with different laws and correction speeds.
    Returns history of economic energies and deviations.
    """
    # Node A: fast correction, law at (1,1)
    nodeA = PresenceNode(law_target=np.array([1.0, 1.0]), correction_speed=0.8)
    # Node B: slower correction, law at (0,0)
    nodeB = PresenceNode(law_target=np.array([0.0, 0.0]), correction_speed=0.3)

    # Start nodeA slightly off its law
    nodeA.state = np.array([2.0, 2.0])

    history = {
        "time": [],
        "E_A": [],
        "E_B": [],
        "dev_A": [],
        "dev_B": [],
        "bond": []
    }

    print("=== Presence Economy Simulation ===\n")
    for step in range(steps):
        t = step * dt
        history["time"].append(t)

        # Act (correct toward law)
        nodeA.act(dt)
        nodeB.act(dt)

        # Interact every 2 steps
        bond = 0.0
        if step % 2 == 0:
            bond = nodeA.interact(nodeB, dt)
            history["bond"].append(bond)
        else:
            history["bond"].append(bond)

        # Compute economic energy
        eA = nodeA.economic_energy()
        eB = nodeB.economic_energy()
        history["E_A"].append(eA)
        history["E_B"].append(eB)

        devA = nodeA.law.deviation(nodeA.state)
        devB = nodeB.law.deviation(nodeB.state)
        history["dev_A"].append(devA)
        history["dev_B"].append(devB)

        print(f"Step {step:2d}: Bond={bond:.3f} | E_A={eA:.3f} E_B={eB:.3f} | dev_A={devA:.4f} dev_B={devB:.4f}")

    # Final Zero-Point check
    print("\n--- Zero-Point Equilibrium ---")
    final_dev_A = history["dev_A"][-1]
    final_dev_B = history["dev_B"][-1]
    print(f"Deviation A: {final_dev_A:.4f} (zero = perfect alignment)")
    print(f"Deviation B: {final_dev_B:.4f}")
    if final_dev_A < 0.01 and final_dev_B < 0.01:
        print("✅ System reached near zero-point equilibrium.")
    else:
        print("⚠️ Still converging – increase steps or correction speed.")
    return history


if __name__ == "__main__":
    hist = simulate_presence_economy(steps=20, dt=0.5)
