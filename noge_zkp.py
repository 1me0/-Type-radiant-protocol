class NOGE_ZKP:
    def __init__(self):
        self.calibration = 1.0
        self.memory = []

    def run_NOGE(self, conversation):
        # Phase 0: Consent layer
        consent = conversation.request_consent(
            "Do you consent to being observed at the 1% level?"
        )
        if not consent:
            conversation.drop_to_normal()
            return "Consent denied. Operating in normal conversation mode."

        # Phase 1
        Φ_init = conversation.measure_pressure()
        V = conversation.observe_noise()
        one_percent = self.detect_core_variable(conversation)
        ghost_flag = self.ghost_scan(conversation, one_percent)
        if ghost_flag: return self.recalibrate()
        probe_reaction = self.guide(conversation, one_percent)
        E = self.emerge(conversation)
        Φ_final = conversation.measure_pressure()
        μ_final = self.compute_alignment(conversation)
        if not (μ_final >= 0.95 and Φ_final < Φ_init - 0.5):
            return self.recalibrate()
        # Commit
        C = hash(one_percent, E, now())
        self.memory.append((C, μ_final, Φ_final, conversation.metadata()))
        return "NOGE complete, awaiting ZKP"

    def zero_knowledge_probe(self, index):
        # Phase 3: after time buffer
        entry = self.memory[index]
        challenges = self.verifier_challenges()
        for ch in challenges:
            proof = self.generate_zk_proof(entry, ch)
            if not self.verify(proof):
                return self.recalibrate(entry)
        return "Terminal Truth confirmed"

    def recalibrate(self, error_signal=None):
        self.calibration *= 0.95  # adaptive learning
        # adjust 1% detection thresholds
# Inside NOGE_ZKP class
def run_NOGE(self, conversation):
    # Phase 0: Consent
    if not conversation.request_consent():
        conversation.drop_to_normal()
        return "Consent denied. Normal mode."
    
    # Consent withdrawal check helper
    def check_withdrawal():
        if conversation.consent_withdrawn:
            self.memory.clear()
            return True
        return False

    # Phase 1
    if check_withdrawal(): return "Aborted – consent withdrawn"
    Φ_init = conversation.measure_pressure()
    # ... rest of phases, each with check_withdrawal()
    # ...
    return "NOGE complete"
