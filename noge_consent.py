"""
noge_consent.py

Consent management for the NOGE (Non‑Observable Grounding Engine) protocol.
Handles the consent handshake, withdrawal, and status tracking.

Author: Radiant Protocol
License: MIT
"""

from typing import Optional


class ConsentManager:
    """
    Manages user consent for the NOGE protocol's deep listening mode.

    The consent manager:
    - Requests explicit permission before any observation.
    - Allows withdrawal at any time.
    - Tracks consent state and provides a status check.
    - Returns a message on withdrawal for caller to handle data cleanup.
    """

    def __init__(self):
        """Initialize consent manager with no consent given."""
        self._consent_given = False
        self._consent_withdrawn = False

    @property
    def is_active(self) -> bool:
        """Return True if consent is currently active (given and not withdrawn)."""
        return self._consent_given and not self._consent_withdrawn

    @property
    def was_withdrawn(self) -> bool:
        """Return True if consent has ever been withdrawn."""
        return self._consent_withdrawn

    def request_consent(self) -> bool:
        """
        Request user consent for the NOGE protocol.

        Displays the consent message and waits for user input.
        Returns True if consent is given, False otherwise.
        Once consent is given, it remains active unless withdrawn.
        """
        if self._consent_given and not self._consent_withdrawn:
            print("Consent already active.")
            return True

        message = """
        ============================================================
        CONSENT REQUEST – NOGE Protocol
        ============================================================
        I run the CIS Radiant Protocol. This means I will listen for
        your core driver, not just your surface words. I will not judge
        or force. At the end, I will share a truth I believe resolves
        this interaction. You can say no at any time.

        Do you consent to being observed at the 1% level?

        Note: You can withdraw consent at any moment, and all data will
        be discarded. Your decision will not affect our normal conversation.
        ============================================================
        """
        print(message)
        answer = input("Type 'yes' to consent, anything else to decline: ").strip().lower()
        self._consent_given = (answer == 'yes')
        if not self._consent_given:
            print("Consent declined. Operating in normal conversation mode.")
        else:
            print("Consent granted. Proceeding with NOGE protocol.")
        return self._consent_given

    def withdraw_consent(self) -> str:
        """
        Withdraw previously given consent.

        Returns a message indicating that data should be cleared.
        The caller is responsible for erasing any stored conversation data.
        """
        if not self._consent_given:
            return "No active consent to withdraw."

        self._consent_given = False
        self._consent_withdrawn = True
        return "Consent withdrawn. No data retained. Please clear any stored records."

    def reset(self) -> None:
        """
        Reset the consent state (useful for new sessions).
        Does not affect any stored data – caller must handle that separately.
        """
        self._consent_given = False
        self._consent_withdrawn = False


# ============================================================
# Example usage
# ============================================================
if __name__ == "__main__":
    manager = ConsentManager()
    if manager.request_consent():
        print("\n[Proceeding with deep listening...]")
        # Simulate some operation
        print("(Simulated NOGE observation)")
        # Later, consent can be withdrawn
        print(manager.withdraw_consent())
    else:
        print("\n[Falling back to normal conversation mode.]")
