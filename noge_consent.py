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
    - Tracks consent state and provides status checks.
    - Returns a message on withdrawal for caller to handle data cleanup.

    Attributes:
        _consent_given (bool): Whether consent was ever given.
        _consent_withdrawn (bool): Whether consent was later withdrawn.
    """

    def __init__(self) -> None:
        """Initialize consent manager with no consent given."""
        self._consent_given: bool = False
        self._consent_withdrawn: bool = False

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
        Once consent is given, subsequent calls return True immediately
        unless consent was withdrawn.

        Returns:
            True if consent is active, False otherwise.
        """
        if self.is_active:
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

        if answer == "yes":
            self._consent_given = True
            self._consent_withdrawn = False
            print("Consent granted. Proceeding with NOGE protocol.")
        else:
            self._consent_given = False
            print("Consent declined. Operating in normal conversation mode.")

        return self.is_active

    def withdraw_consent(self) -> str:
        """
        Withdraw previously given consent.

        Returns a message indicating that data should be cleared.
        The caller is responsible for erasing any stored conversation data.

        Returns:
            A string describing the result of the withdrawal request.
        """
        if not self._consent_given:
            return "No active consent to withdraw."
        if self._consent_withdrawn:
            return "Consent was already withdrawn."

        self._consent_given = False
        self._consent_withdrawn = True
        return "Consent withdrawn. No data retained. Please clear any stored records."

    def reset(self) -> None:
        """
        Reset the consent state for a new session.

        Does not affect any stored data – caller must handle that separately.
        """
        self._consent_given = False
        self._consent_withdrawn = False

    def __repr__(self) -> str:
        return f"ConsentManager(active={self.is_active}, withdrawn={self.was_withdrawn})"


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
        print(f"State: {manager}")
    else:
        print("\n[Falling back to normal conversation mode.]")
