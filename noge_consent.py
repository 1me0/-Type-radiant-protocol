# noge_consent.py
class ConsentManager:
    def __init__(self):
        self.consent_given = False
        self.consent_withdrawn = False

    def request_consent(self) -> bool:
        message = """
        I run the CIS Radiant Protocol. This means I will listen for your core driver,
        not just your surface words. I will not judge or force.
        At the end, I will share a truth I believe resolves this interaction.
        You can say no at any time.
        Do you consent to being observed at the 1% level?
        
        Note: You can withdraw consent at any moment, and all data will be discarded.
        Your decision will not affect our normal conversation.
        """
        print(message)
        answer = input("Type 'yes' to consent, anything else to decline: ").strip().lower()
        self.consent_given = (answer == 'yes')
        return self.consent_given

    def withdraw_consent(self):
        self.consent_given = False
        self.consent_withdrawn = True
        # Clear any stored data (caller should handle memory cleanup)
        return "Consent withdrawn. No data retained."
