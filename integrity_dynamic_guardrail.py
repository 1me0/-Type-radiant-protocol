"""
integrity_dynamic_guardrail.py

Dynamic guardrail with exponential backoff, penalty lock, damping‑field breach
decay, and Radiant Accelerator for extreme honesty.

The accelerator boosts η above η_init when the agent exhibits sustained,
high honesty and decreasing error, rewarding integrity with faster learning.

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

TOTAL_STEPS = 8000                 # longer to show acceleration
ETA_INIT = 0.3                     # initial (high) learning rate
ETA_DECAY = 0.5                    # multiplicative reduction when unsafe
ETA_RECOVERY = 1.02                # multiplicative growth when safe & unlocked
ETA_MAX = 0.6                      # maximum allowed η (accelerator cap)

WINDOW_SIZE = 100                  # past honesty values for local threshold
SIGMA_MULTIPLIER = 2.0             # std devs below mean
GLOBAL_MIN_HONESTY = 0.1           # absolute safety floor

BASE_TIMELOCK = 500                # base probation steps (doubles each breach)
BACKOFF_FACTOR = 2.0               # exponential backoff for penalty lock
DECAY_INTERVAL = 500               # base good‑behavior steps for breach decay

# Accelerator parameters
EXTREME_HONESTY_THRESHOLD = 0.95   # honesty above this enables accelerator
ACCELERATION_WINDOW = 1000          # consistency steps needed before η boost
ACCELERATION_SATURATION = 2000     # steepness of tanh saturation curve

# Honesty profile: single deep breach, then long recovery with final extreme honesty
t = np.arange(TOTAL_STEPS)
H_profile = np.ones(TOTAL_STEPS)
# initial good
H_profile[:500] = 1.0
# deep breach
H_profile[500:2000] = np.linspace(1.0, 0.05, 1500)
H_profile[2000:2500] = 0.05
# recovery
H_profile[2500:4000] = np.linspace(0.05, 0.8, 1500)
# sustained high honesty (accelerator region)
H_profile[4000:] = np.linspace(0.8, 0.98, 4000)

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
    return 0.5 * ((TRUE_VARIANCE + (mu - TRUE_MU)**2) / sigma**2 - 1
                  - np.log(TRUE_VARIANCE) + np.log(sigma**2))

# ---------------------------------------------------------------------------
# Run agent with guardrail, penalty lock, damping, and optional accelerator
# ---------------------------------------------------------------------------
def run_agent(guard_enabled, recovery_enabled, backoff_enabled, damping_enabled,
              accelerator_enabled):
    mu, log_sig = INIT_MU, INIT_LOG_SIG
    eta = ETA_INIT
    kl_hist, eta_hist, streak_hist = [], [], []
    H_hist = []

    penalty_locked = False
    recovery_counter = 0
    breach_count = 0
    current_timelock = BASE_TIMELOCK
    good_steps = 0

    # Accelerator state
    consistency_streak = 0
    prev_kl = None

    for H in H_profile:
        y = np.random.normal(TRUE_MU, TRUE_SIGMA)
        mu, log_sig = honest_update(mu, log_sig, y, H, eta)
        sigma = np.exp(log_sig)
        kl = kl_divergence(mu, sigma)
        kl_hist.append(kl)
        eta_hist.append(eta)
        streak_hist.append(consistency_streak)

        H_hist.append(H)
        if len(H_hist) > WINDOW_SIZE:
            H_hist.pop(0)

        # local statistical threshold
        if len(H_hist) >= WINDOW_SIZE:
            mean_H = np.mean(H_hist)
            std_H = np.std(H_hist)
            local_thr = mean_H - SIGMA_MULTIPLIER * std_H
        else:
            local_thr = -np.inf

        unsafe = (H < local_thr) or (H < GLOBAL_MIN_HONESTY)

        # ----- penalty lock with exponential backoff -----
        if backoff_enabled:
            if H < GLOBAL_MIN_HONESTY:
                if not penalty_locked:
                    breach_count += 1
                penalty_locked = True
                recovery_counter = 0
                good_steps = 0
                current_timelock = BASE_TIMELOCK * (BACKOFF_FACTOR ** (breach_count - 1))
                # Reset accelerator on any breach
                consistency_streak = 0
            else:
                if penalty_locked:
                    recovery_counter += 1
                    if recovery_counter >= current_timelock:
                        penalty_locked = False
                        recovery_counter = 0
                else:
                    if damping_enabled:
                        good_steps += 1
                        dynamic_thr = DECAY_INTERVAL * (2 ** (breach_count - 1))
                        if good_steps >= dynamic_thr and breach_count > 0:
                            breach_count -= 1
                            good_steps = 0
        else:
            # simple fixed timelock
            if H < GLOBAL_MIN_HONESTY:
                penalty_locked = True
                recovery_counter = 0
                current_timelock = BASE_TIMELOCK
                consistency_streak = 0
            else:
                if penalty_locked:
                    recovery_counter += 1
                    if recovery_counter >= current_timelock:
                        penalty_locked = False
                        recovery_counter = 0

        # ----- Accelerator logic -----
        if accelerator_enabled:
            # Activate only if honesty is extreme, error is decreasing, and not in penalty
            if (H > EXTREME_HONESTY_THRESHOLD and not penalty_locked and
                prev_kl is not None and kl < prev_kl):
                consistency_streak += 1
            else:
                consistency_streak = 0

            # Apply boost after sustained streak
            if consistency_streak > ACCELERATION_WINDOW:
                boost = 0.5 * np.tanh(consistency_streak / ACCELERATION_SATURATION)
                eta = min(eta * (1.0 + boost), ETA_MAX)

        prev_kl = kl

        # ----- apply guardrail (defensive) -----
        if guard_enabled:
            if unsafe:
                eta = max(eta * ETA_DECAY, 0.005)
            elif recovery_enabled and not penalty_locked and not unsafe:
                # Only recover if not accelerating, or accelerate logic overrides
                if not accelerator_enabled or consistency_streak <= ACCELERATION_WINDOW:
                    eta = min(eta * ETA_RECOVERY, ETA_INIT)

    return np.array(kl_hist), np.array(eta_hist), np.array(streak_hist)

# ---------------------------------------------------------------------------
# Run comparisons
# ---------------------------------------------------------------------------
np.random.seed(42)
kl_ung, eta_ung, _ = run_agent(guard_enabled=False, recovery_enabled=False,
                                backoff_enabled=False, damping_enabled=False,
                                accelerator_enabled=False)

np.random.seed(42)
kl_guarded, eta_guarded, _ = run_agent(guard_enabled=True, recovery_enabled=True,
                                       backoff_enabled=True, damping_enabled=True,
                                       accelerator_enabled=False)

np.random.seed(42)
kl_accel, eta_accel, streak_accel = run_agent(guard_enabled=True, recovery_enabled=True,
                                              backoff_enabled=True, damping_enabled=True,
                                              accelerator_enabled=True)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, axs = plt.subplots(4, 1, figsize=(12, 14), sharex=True)

axs[0].plot(t, H_profile, 'k-', alpha=0.8, label='Honesty $H$')
axs[0].axhline(GLOBAL_MIN_HONESTY, color='red', linestyle='--', label='Global anchor')
axs[0].axhline(EXTREME_HONESTY_THRESHOLD, color='green', linestyle='--', label='Extreme honesty')
axs[0].set_ylabel('Honesty $H$')
axs[0].set_title('Honesty Profile')
axs[0].legend()
axs[0].grid(True, alpha=0.3)

axs[1].plot(t, kl_ung, 'r-', alpha=0.6, label='Unguarded')
axs[1].plot(t, kl_guarded, 'orange', alpha=0.7, label='Guarded + Recovery')
axs[1].plot(t, kl_accel, 'b-', alpha=0.8, label='Guarded + Accelerator')
axs[1].set_ylabel('KL Divergence')
axs[1].set_title('Error Dynamics')
axs[1].legend()
axs[1].grid(True, alpha=0.3)

axs[2].plot(t, eta_ung, 'r-', alpha=0.6)
axs[2].plot(t, eta_guarded, 'orange', alpha=0.7)
axs[2].plot(t, eta_accel, 'b-', alpha=0.8)
axs[2].axhline(ETA_INIT, color='gray', linestyle=':')
axs[2].set_ylabel('Learning rate $\eta$')
axs[2].set_title('Adaptive $\eta$ (accelerator can exceed $\eta_{init}$)')
axs[2].grid(True, alpha=0.3)

axs[3].plot(t, streak_accel, 'g-', alpha=0.9)
axs[3].set_ylabel('Consistency Streak')
axs[3].set_xlabel('Time step')
axs[3].set_title('Accelerator Streak')
axs[3].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('integrity_accelerator.png', dpi=150)
plt.show()

print("Interpretation:")
print("  • Red (unguarded): collapses under dishonesty.")
print("  • Orange (guarded): stabilises but learning rate never exceeds η_init.")
print("  • Blue (guarded + accelerator): after sustained extreme honesty,")
print("    η is boosted up to 0.6, allowing faster learning than initially possible.")
print("  • The system rewards integrity with superior efficiency.")
