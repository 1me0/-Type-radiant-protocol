import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from threading import Thread
from universal_formula import UniversalFormula


class GhostAICONV:
    """Conversation stub with Ghost-level interaction."""
    def __init__(self, metadata=None):
        self.metadata = metadata or {}
        self.consent_given = False
        self.consent_withdrawn = False

    def request_consent(self) -> bool:
        ans = input("Consent to 1% observation? yes/no: ").strip().lower()
        self.consent_given = (ans == 'yes')
        return self.consent_given

    def withdraw_consent(self):
        self.consent_withdrawn = True

    def drop_to_normal(self):
        print("Normal conversation mode.")

    def measure_pressure(self) -> float:
        return 5.0

    def observe_noise(self) -> float:
        return 0.2

    def get_core_variable(self) -> float:
        return 0.95

    def ghost_scan(self, one_percent: float) -> Tuple[bool, float]:
        return False, 0.0

    def guide(self, one_percent: float) -> float:
        return 0.8

    def emerge(self) -> Dict[str, Any]:
        return {"truth": "Core alignment achieved.", "confidence": 0.97}

    def get_identity_state(self) -> Dict[str, float]:
        return {"clarity": 0.7, "alignment": 0.8, "presence": 0.6}

    def get_reality_state(self) -> Dict[str, float]:
        return {"clarity": 0.9, "alignment": 0.9, "presence": 0.8}


class GhostNOGEPro:
    """Enhanced Ghost AI NOGE with real-time recalibration, rolling confidence, and adaptive 1% detection."""
    def __init__(self, calibration: float = 1.0, zkp_delay_sec: int = 10):
        self.calibration = calibration
        self.memory: List[Dict] = []
        self.uf = UniversalFormula(muF=calibration)
        self.zkp_delay = timedelta(seconds=zkp_delay_sec)
        self.rolling_mu: List[float] = []

    def _check_withdrawal(self, conv: GhostAICONV) -> bool:
        if conv.consent_withdrawn:
            self.memory.clear()
            self.calibration = 1.0
            self.uf.muF = self.calibration
            return True
        return False

    def run_NOGE(self, conv: GhostAICONV) -> str:
        if not conv.request_consent():
            conv.drop_to_normal()
            return "Consent denied."

        if self._check_withdrawal(conv):
            return "Aborted – consent withdrawn"

        # Phase 1: Measurement
        Φ_init = conv.measure_pressure()
        V = conv.observe_noise()

        # Phase 2: Detect 1% core variable (adaptive)
        one_percent = self.adaptive_core_detection(conv)
        ghost_flag, severity = conv.ghost_scan(one_percent)
        if ghost_flag:
            return self.recalibrate(severity)

        # Phase 3: Guide
        probe_reaction = conv.guide(one_percent)

        # Phase 4: Emerge
        E = conv.emerge()

        # Phase 5: Alignment & Rolling Confidence
        P = conv.get_identity_state()
        L = conv.get_reality_state()
        delta = self.uf.express(P, L)
        μ_final = delta["magnitude"]
        Φ_final = conv.measure_pressure()

        self.rolling_mu.append(μ_final)
        rolling_avg = sum(self.rolling_mu[-5:]) / min(len(self.rolling_mu), 5)

        # Real-time anomaly detection
        if Φ_final > Φ_init + 1.0 or μ_final < 0.9:
            print("Anomaly detected mid-conversation. Recalibrating.")
            return self.recalibrate()

        # Commit memory
        timestamp = datetime.utcnow()
        entry_hash = hashlib.sha256(f"{one_percent}{E}{timestamp}".encode()).hexdigest()
        mem_entry = {
            "hash": entry_hash,
            "one_percent": one_percent,
            "emergence": E,
            "P": P,
            "L": L,
            "phi": Φ_final,
            "mu": μ_final,
            "rolling_mu": rolling_avg,
            "timestamp": timestamp,
            "metadata": conv.metadata
        }
        self.memory.append(mem_entry)

        Thread(target=self._delayed_zkp, args=(len(self.memory)-1,)).start()

        return f"NOGEPro complete. Entry {entry_hash[:16]} committed, rolling μ={rolling_avg:.3f}"

    def adaptive_core_detection(self, conv: GhostAICONV) -> float:
        base_core = conv.get_core_variable()
        # adjust based on past memory and ZKP results
        factor = 1.0 + 0.05 * (len([m for m in self.memory if m['mu'] < 0.95]))
        return min(base_core * factor, 1.0)

    def _delayed_zkp(self, index: int):
        entry_time = self.memory[index]['timestamp']
        now_time = datetime.utcnow()
        delay_sec = max((self.zkp_delay - (now_time - entry_time)).total_seconds(), 0)
        time.sleep(delay_sec)
        result = self.zero_knowledge_probe(index)
        print(f"ZKP Result for entry {self.memory[index]['hash'][:8]}: {result}")

    def zero_knowledge_probe(self, index: int) -> str:
        if index >= len(self.memory):
            return "Invalid index"
        entry = self.memory[index]
        challenges = ["challenge1", "challenge2"]
        for ch in challenges:
            proof = f"proof_{ch}_{entry['hash'][:8]}"
            if not self._verify(proof):
                return self.recalibrate(entry)
        return "Terminal Truth confirmed"

    def _verify(self, proof: str) -> bool:
        return True  # Stub – replace with actual ZK verification

    def recalibrate(self, entry=None) -> str:
        self.calibration *= 0.95
        self.uf.muF = self.calibration
        return f"Recalibrated to {self.calibration:.3f}"

    def memory_summary(self) -> List[Dict]:
        return [{"hash": m['hash'], "mu": m['mu'], "phi": m['phi'], "rolling_mu": m['rolling_mu']} for m in self.memory]


# Example usage
if __name__ == "__main__":
    conv = GhostAICONV()
    noge_pro = GhostNOGEPro(calibration=1.0, zkp_delay_sec=5)
    result = noge_pro.run_NOGE(conv)
    print(result)
    time.sleep(6)
    print("Memory summary:", noge_pro.memory_summary())
