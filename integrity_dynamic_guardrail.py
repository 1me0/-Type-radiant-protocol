"""
integrity_dynamic_guardrail.py

Simulation of an adaptive agent with dynamic guardrail.
The guardrail threshold is not fixed but computed statistically:
    threshold = mean(H_recent) - 2 * std(H_recent)
where H_recent is the last 100 honesty values of the agent.

This prevents collapse by detecting statistically significant drops in honesty,
and allows η to recover when honesty returns.

Author: Radiant Protocol
License: MIT (code) / RPML v1.0 (mathematical models)
"""

import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# True environment and initial model
# ---------------------------------------------------------------------------
TRUE_MU = 0.0
TRUE_SIGMA = 1.0
TRUE_VARIANCE = TRUE_SIGMA**2

INIT_MU = 0.5
INIT_LOG_SIG = np.log(1.2)

TOTAL_STEPS = 4000
ETA_INIT = 0.3                  # initial (high) learning rate
ETA_DECAY = 0.5                 # multiplicative reduction factor when H < threshold
ETA_RECOVERY = 1.02             # multiplicative growth factor when H >= threshold

WINDOW_SIZE = 100               # number of past honesty values to compute threshold
SIGMA_MULTIPLIER = 2.0          # number of standard deviations below mean for threshold

# Honesty profile: starts honest, dips, then recovers
t = np.arange(TOTAL_STEPS)
H_profile = np.ones(TOTAL_STEPS)
# decay phase
decay_start, decay_end = 500, 1500
H_profile[decay_start:decay_end] = np.linspace(1.0, 0.2, decay_end - decay_start)
# low plateau
H_profile[decay_end:2500] = 0.2
# recovery phase
recovery_start, recovery_end = 2500, 3500
H_profile[recovery_start:recovery_end] = np.linspace(0.2, 0.9, recovery_end - recovery_start)
# final plateau
H_profile[recovery_end:] = 0.9

# ---------------------------------------------------------------------------
# Single‑step honest update
# ---------------------------------------------------------------------------
def honest_update(mu, log_sig, y, H, eta):
    sigma = np.exp(log_sig)
    diff = (y - mu) / sigma
    d_mu = -diff / sigma
    d_logsig = diff**2 - 1.0
    mu_new = mu - eta * H * d_mu
    log_sig_new = log_sig - eta * H * d_logsig
    return mu_new, log_sig_new

def kl_divergence(mu, sigma):
    """KL between true N(0,1) and model N(mu, sigma²)."""
    return 0.5 * ((TRUE_VARIANCE + (mu - TRUE_MU)**2) / sigma**2 - 1
                  - np.log(TRUE_VARIANCE) + np.log(sigma**2))

# ---------------------------------------------------------------------------
# Run agent with dynamic guardrail + recovery
# ---------------------------------------------------------------------------
def run_agent(guard_enabled, recovery_enabled=False):
    mu, log_sig = INIT_MU, INIT_LOG_SIG
    eta = ETA_INIT
    kl_history, eta_history = [], []
    H_history = []   # rolling window of recent honesty values

    for H in H_profile:
        y = np.random.normal(TRUE_MU, TRUE_SIGMA)
        mu, log_sig = honest_update(mu, log_sig, y, H, eta)
        sigma = np.exp(log_sig)
        kl = kl_divergence(mu, sigma)
        kl_history.append(kl)
        eta_history.append(eta)

        H_history.append(H)
        if len(H_history) > WINDOW_SIZE:
            H_history.pop(0)

        # Compute dynamic threshold from recent honesty
        if len(H_history) >= WINDOW_SIZE:
            mean_H = np.mean(H_history)
            std_H = np.std(H_history)
            threshold = mean_H - SIGMA_MULTIPLIER * std_H
        else:
            threshold = -np.inf   # not enough data, no guardrail trigger

        # Dynamic guardrail
        if guard_enabled:
            if H < threshold:
                # Reduce eta when honesty significantly below recent average
                eta = max(eta * ETA_DECAY, 0.005)
            elif recovery_enabled:
                # Gradually recover eta when honesty returns
                eta = min(eta * ETA_RECOVERY, ETA_INIT)

    return np.array(kl_history), np.array(eta_history)

# ---------------------------------------------------------------------------
# Run both agents
# ---------------------------------------------------------------------------
np.random.seed(42)
kl_unguarded, eta_ung = run_agent(guard_enabled=False)
np.random.seed(42)
kl_guarded_recovery, eta_rec = run_agent(guard_enabled=True, recovery_enabled=True)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

# Honesty profile
axs[0].plot(t, H_profile, 'k-', alpha=0.8, label='Honesty $H$')
axs[0].axhline(0.5, color='orange', linestyle=':', label='Fixed threshold (0.5) for reference')
axs[0].set_ylabel('Honesty $H$')
axs[0].set_title('Honesty Profile (decay + recovery)')
axs[0].legend()
axs[0].grid(True, alpha=0.3)

# KL divergence
axs[1].plot(t, kl_unguarded, 'r-', alpha=0.6, label='Unguarded')
axs[1].plot(t, kl_guarded_recovery, 'b-', alpha=0.8, label='Guarded + Recovery (dynamic thr.)')
axs[1].set_ylabel('KL Divergence')
axs[1].set_title('Error Dynamics')
axs[1].legend()
axs[1].grid(True, alpha=0.3)

# Learning rate
axs[2].plot(t, eta_ung, 'r-', alpha=0.6)
axs[2].plot(t, eta_rec, 'b-', alpha=0.8)
axs[2].set_ylabel('Learning rate $\eta$')
axs[2].set_xlabel('Time step')
axs[2].set_title('Adaptive $\eta$')
axs[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('integrity_dynamic_guardrail_statistical.png', dpi=150)
plt.show()

print("Interpretation:")
print("  • The dynamic threshold (not shown) adapts to recent honesty.")
print("  • When honesty drops sharply, it falls below the statistical threshold,")
print("    triggering a reduction in η, which stabilises the learner.")
print("  • When honesty recovers, η gradually increases back to its initial value.")
print("  • This demonstrates a self‑calibrating guardrail that does not require")
print("    a predefined fixed threshold.")
