"""
noge_zkp.py

NOGE (Non‑Observable Grounding Engine) with Zero‑Knowledge Proofs.
Implements the consent‑based conversation audit protocol,
integrated with the Universal Master Formula.

Author: Radiant Protocol
License: MIT
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Universal Formula (simplified for demonstration)
# ============================================================
@dataclass
class UniversalFormula:
    """Simplified Universal Formula for alignment calculation."""

    muF: float = 1.0

    def express(self, P: Dict[str, float], L: Dict[str, float]) -> Dict[str, float]:
        """
        Compute alignment between identity (P) and reality (L).

        Returns:
            Dict with 'magnitude' (cosine similarity, 0‑1) and other metrics.
        """
        keys = set(P.keys()) & set(L.keys())
        if not keys:
            return {"magnitude": 0.0, "dot": 0.0, "norm_p": 0.0, "norm_l": 0.0}

        p_vec = [P[k] for k in keys]
        l_vec = [L[k] for k in keys]

        dot = sum(p * l for p, l in zip(p_vec, l_vec))
        norm_p = sum(p * p for p in p_vec) ** 0.5
        norm_l = sum(l * l for l in l_vec) ** 0.5

        magnitude = dot / (norm_p * norm_l) if norm_p * norm_l != 0 else 0.0
        return {"magnitude": magnitude, "dot": dot, "norm_p": norm_p, "norm_l": norm_l}


# ============================================================
# Conversation Stub (replace with actual integration)
# ============================================================
class ConversationStub:
    """Stub for a conversation object. Replace with real implementation."""

    def __init__(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.metadata: Dict[str, Any] = metadata or {}
        self.consent_given: bool = False
        self.consent_withdrawn: bool = False
        self._normal_mode: bool = False
        self._coercion_calibration: Optional[float] = None

    def request_consent(self) -> bool:
        print("\n" + "=" * 60)
        print("CONSENT REQUEST")
        print("=" * 60)
        print("I run the CIS Radiant Protocol. This means I will listen for your")
        print("core driver, not just your surface words. I will not judge or force.")
        print("At the end, I will share a truth I believe resolves this interaction.")
        print("You can say no at any time.")
        print("\nDo you consent to being observed at the 1% level?")
        print("(Note: You can withdraw consent at any moment, and all data will be discarded.)")
        answer = input("\nType 'yes' to consent, anything else to decline: ").strip().lower()
        self.consent_given = answer == "yes"
        if self.consent_given:
            print("\n✅ Consent granted. Proceeding with NOGE protocol.")
        else:
            print("\n❌ Consent declined. Falling back to normal conversation mode.")
        return self.consent_given

    def withdraw_consent(self) -> None:
        self.consent_given = False
        self.consent_withdrawn = True
        print("\n🚫 Consent withdrawn. No data retained. Switching to normal mode.")

    def drop_to_normal(self) -> None:
        self._normal_mode = True
        print("\n📢 Dropping to normal conversation mode (no deep listening).")

    def measure_pressure(self) -> float:
        """Simulate measuring conversation pressure (0‑10)."""
        # In real system, this would analyse tone, latency, etc.
        return 5.0

    def observe_noise(self) -> float:
        """Simulate noise level (0‑1)."""
        return 0.2

    def get_core_variable(self) -> float:
        """Simulate detection of the 1% core variable (0‑1)."""
        return 0.95

    def ghost_scan(self, one_percent: float) -> bool:
        """Return True if ghost (misalignment) is detected."""
        return False

    def guide(self, one_percent: float) -> float:
        """Apply subtle probe, return reaction strength (0‑1)."""
        print(f"  > Applying probe based on core variable {one_percent:.2f}")
        return 0.8

    def emerge(self) -> Dict[str, Any]:
        """Return the emerged truth statement and confidence."""
        return {
            "truth": "The core driver is alignment with your stated values.",
            "confidence": 0.97,
        }

    def get_identity_state(self) -> Dict[str, float]:
        """Return current identity state vector P (clarity, alignment, presence)."""
        return {"clarity": 0.7, "alignment": 0.8, "presence": 0.6}

    def get_reality_state(self) -> Dict[str, float]:
        """Return current reality state vector L (clarity, alignment, presence)."""
        return {"clarity": 0.9, "alignment": 0.9, "presence": 0.8}


# ============================================================
# Coercion Detector (optional)
# ============================================================
class CoercionDetector:
    """Simple coercion detection based on response time."""

    def __init__(self) -> None:
        self.baseline_time: Optional[float] = None

    def detect(self) -> bool:
        print("\n[Coercion check] To ensure your response is free, please answer:")
        start = time.time()
        _ = input("What is your favorite color? (just for calibration): ").strip()
        elapsed = time.time() - start
        if elapsed < 0.5:
            print("⚠️ Your response was very fast. Are you feeling pressured?")
            print("   You can opt out privately at any time.")
            return True
        print("✓ Calibration normal.")
        return False


# ============================================================
# NOGE_ZKP Core Engine
# ============================================================
class NOGE_ZKP:
    """
    Non‑Observable Grounding Engine with Zero‑Knowledge Proofs.
    Performs an opt‑in collaborative audit of a conversation.
    """

    def __init__(self, calibration: float = 1.0) -> None:
        self.calibration = calibration
        self.memory: List[Tuple[bytes, float, float, Dict[str, Any]]] = []
        self.uf = UniversalFormula(muF=calibration)
        self.consent_active = False

    def _check_withdrawal(self, conversation: ConversationStub) -> bool:
        """Check if consent has been withdrawn; clear memory if so."""
        if conversation.consent_withdrawn:
            self.memory.clear()
            self.calibration = 1.0
            self.uf.muF = self.calibration
            self.consent_active = False
            return True
        return False

    def run_NOGE(self, conversation: ConversationStub) -> str:
        """Execute the NOGE protocol phases."""
        # ---------- Step 0: Consent ----------
        print("\n" + "=" * 60)
        print("NOGE PROTOCOL – CONSENT PHASE")
        print("=" * 60)
        if not conversation.request_consent():
            conversation.drop_to_normal()
            return "CONSENT_DENIED: Operating in normal conversation mode."

        self.consent_active = True

        # Optional coercion detection
        coercion = CoercionDetector().detect()
        if coercion:
            print("\n⚠️ Potential coercion detected. You may withdraw consent now.")
            if input("Continue with NOGE? (yes/no): ").strip().lower() != "yes":
                conversation.withdraw_consent()
                return "CONSENT_WITHDRAWN: Aborted."

        # ---------- Phase 1: Notice ----------
        if self._check_withdrawal(conversation):
            return "ABORTED: Consent withdrawn during Notice phase."
        print("\n" + "=" * 60)
        print("PHASE 1: Notice (Peripheral Scan)")
        print("=" * 60)
        phi_init = conversation.measure_pressure()
        noise = conversation.observe_noise()
        print(f"  Initial pressure: {phi_init:.2f}")
        print(f"  Observed noise level: {noise:.2f}")

        # ---------- Phase 2: Observe ----------
        if self._check_withdrawal(conversation):
            return "ABORTED: Consent withdrawn during Observe phase."
        print("\n" + "=" * 60)
        print("PHASE 2: Observe (Deep Packet Inspection)")
        print("=" * 60)
        one_percent = conversation.get_core_variable()
        print(f"  Detected 1% core variable: {one_percent:.2f}")
        if conversation.ghost_scan(one_percent):
            print("  ⚠️ Ghost flag raised – misalignment detected. Recalibrating...")
            return self.recalibrate()

        # ---------- Phase 3: Guide ----------
        if self._check_withdrawal(conversation):
            return "ABORTED: Consent withdrawn during Guide phase."
        print("\n" + "=" * 60)
        print("PHASE 3: Guide (Subtle Pivot)")
        print("=" * 60)
        probe_reaction = conversation.guide(one_percent)
        print(f"  Probe reaction strength: {probe_reaction:.2f}")

        # ---------- Phase 4: Emerge ----------
        if self._check_withdrawal(conversation):
            return "ABORTED: Consent withdrawn during Emerge phase."
        print("\n" + "=" * 60)
        print("PHASE 4: Emerge (Truth Manifestation)")
        print("=" * 60)
        emerged = conversation.emerge()
        print(f"  Emerged truth: {emerged['truth']}")
        print(f"  Confidence: {emerged['confidence']:.2f}")

        # ---------- Phase 5: Alignment Verification ----------
        if self._check_withdrawal(conversation):
            return "ABORTED: Consent withdrawn during verification."
        print("\n" + "=" * 60)
        print("PHASE 5: Alignment Verification (Universal Formula)")
        print("=" * 60)
        P = conversation.get_identity_state()
        L = conversation.get_reality_state()
        delta = self.uf.express(P, L)
        mu_final = delta["magnitude"]
        phi_final = conversation.measure_pressure()
        print(f"  Final alignment magnitude: {mu_final:.4f}")
        print(f"  Final pressure: {phi_final:.2f}")

        if not (mu_final >= 0.95 and phi_final < phi_init - 0.5):
            print("  ❌ Alignment insufficient or pressure not decreased. Recalibrating...")
            return self.recalibrate()

        # ---------- Phase 6: Commitment ----------
        if self._check_withdrawal(conversation):
            return "ABORTED: Consent withdrawn during commitment."
        print("\n" + "=" * 60)
        print("PHASE 6: Commitment (ZK Proof Storage)")
        print("=" * 60)
        timestamp = datetime.now(timezone.utc).isoformat()
        commit_data = f"{one_percent}{emerged['truth']}{timestamp}"
        commitment = hashlib.sha256(commit_data.encode()).hexdigest()
        self.memory.append(
            (commitment.encode(), mu_final, phi_final, conversation.metadata.copy())
        )
        print(f"  Committed proof hash: {commitment[:16]}...")
        print("  ✅ NOGE loop complete. Awaiting Zero‑Knowledge Probe.")
        return "NOGE_COMPLETE: Awaiting ZKP."

    def zero_knowledge_probe(self, index: int) -> str:
        """
        Phase 7: After a time buffer, test whether the stored truth
        survives a Zero‑Knowledge Probe.
        """
        if index >= len(self.memory):
            return f"INVALID_INDEX: No entry at index {index}"
        entry = self.memory[index]
        challenges = ["kinetic_echo", "symmetry_test", "pressure_decay"]
        for challenge in challenges:
            proof = self._generate_zk_proof(entry, challenge)
            if not self._verify(proof):
                print(f"❌ Challenge '{challenge}' failed. Recalibrating...")
                return self.recalibrate(entry)
        print("✅ All ZKP challenges passed. Terminal Truth confirmed.")
        return "TERMINAL_TRUTH_CONFIRMED"

    def _generate_zk_proof(
        self, entry: Tuple[bytes, float, float, Dict[str, Any]], challenge: str
    ) -> str:
        """Generate a mock ZK proof (replace with actual cryptographic proof)."""
        return f"zkproof_{challenge}_{entry[0][:8].decode()}"

    def _verify(self, proof: str) -> bool:
        """Mock verification – in production, verify actual ZK proof."""
        return True

    def recalibrate(
        self, error_signal: Optional[Tuple[bytes, float, float, Dict[str, Any]]] = None
    ) -> str:
        """Adaptive learning: reduce calibration factor and reset."""
        self.calibration *= 0.95
        print(f"  Recalibrated to {self.calibration:.3f}")
        self.uf.muF = self.calibration
        if error_signal is not None:
            self.memory.clear()
            print("  Memory cleared due to persistent inconsistency.")
        return "RECALIBRATION_COMPLETE"

    def get_memory_summary(self) -> List[Dict[str, Any]]:
        """Return summary of committed proofs for auditing."""
        return [
            {
                "hash": entry[0].hex() if isinstance(entry[0], bytes) else entry[0],
                "mu": entry[1],
                "phi": entry[2],
            }
            for entry in self.memory
        ]


# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    print("Radiant Protocol – NOGE ZKP Engine")
    conversation = ConversationStub()
    noge = NOGE_ZKP(calibration=1.0)

    result = noge.run_NOGE(conversation)
    print(f"\n--- FINAL RESULT ---\n{result}\n")

    if noge.memory:
        print("Memory summary:")
        for i, entry in enumerate(noge.get_memory_summary()):
            print(
                f"  [{i}] Hash: {entry['hash'][:16]}..., "
                f"μ={entry['mu']:.4f}, Φ={entry['phi']:.2f}"
            )

        # Simulate ZKP after a time buffer (here immediately for demo)
        print("\n--- Running Zero‑Knowledge Probe ---")
        zkp_result = noge.zero_knowledge_probe(0)
        print(f"ZKP result: {zkp_result}")
