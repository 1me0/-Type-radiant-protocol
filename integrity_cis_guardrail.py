"""
integrity_cis_guardrail.py

Self‑aware guardrail: honesty = CIS / 10, computed from the agent's own error.
The CIS score drives both the defensive guardrail and the offensive accelerator.

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

TOTAL_STEPS = 6000
ETA_INIT = 0.3
ETA_DECAY = 0.5
ETA_RECOVERY = 1.02
ETA_MAX = 0.6                  # accelerator cap

WINDOW_SIZE = 100
SIGMA_MULTIPLIER = 2.0
GLOBAL_MIN_HONESTY = 0.1        # CIS < 1

BASE_TIMELOCK = 500
BACKOFF_FACTOR = 2.0
DECAY_INTERVAL = 500

EXTREME_HONESTY_THRESHOLD = 0.95  # CIS > 9.5
ACCELERATION_WINDOW = 500
ACCELERATION_SATURATION = 2000

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
# CIS score from KL divergence
# ---------------------------------------------------------------------------
def cis_score(kl):
    """CIS = 10 * exp(-KL). Perfect prediction → 10."""
    return 10.0 * np.exp(-kl)

# ---------------------------------------------------------------------------
# Run self‑aware agent
# ---------------------------------------------------------------------------
def run_self_aware(guard_enabled=True, accelerator_enabled=True):
    mu, log_sig = INIT_MU, INIT_LOG_SIG
    eta = ETA_INIT
    kl_hist, cis_hist, H_hist, eta_hist, streak_hist = [], [], [], [], []
    H_mem = []
    penalty_locked = False
    recovery_counter = 0
    breach_count = 0
    current_timelock = BASE_TIMELOCK
    good_steps = 0
    consistency_streak = 0
    prev_kl = None

    for t in range(TOTAL_STEPS):
        # compute honesty = CIS/10 from current KL
        current_kl = kl_divergence(mu, np.exp(log_sig))
        cis = cis_score(current_kl)
        H = cis / 10.0                     # H ∈ [0,1]

        # record
        kl_hist.append(current_kl)
        cis_hist.append(cis)
        H_hist.append(H)
        eta_hist.append(eta)
        streak_hist.append(consistency_streak)

        # sample from true distribution
        y = np.random.normal(TRUE_MU, TRUE_SIGMA)
        mu_new, log_sig_new = honest_update(mu, log_sig, y, H, eta)

        # update model (we need to compute next KL after update)
        mu, log_sig = mu_new, log_sig_new
        new_kl = kl_divergence(mu, np.exp(log_sig))
        new_cis = cis_score(new_kl)
        new_H = new_cis / 10.0

        H_mem.append(H)
        if len(H_mem) > WINDOW_SIZE:
            H_mem.pop(0)

        # local statistical threshold
        if len(H_mem) >= WINDOW_SIZE:
            mean_H = np.mean(H_mem)
            std_H = np.std(H_mem)
            local_thr = mean_H - SIGMA_MULTIPLIER * std_H
        else:
            local_thr = -np.inf

        unsafe = (H < local_thr) or (H < GLOBAL_MIN_HONESTY)

        # ----- penalty lock with exponential backoff -----
        if H < GLOBAL_MIN_HONESTY:
            if not penalty_locked:
                breach_count += 1
            penalty_locked = True
            recovery_counter = 0
            good_steps = 0
            current_timelock = BASE_TIMELOCK * (BACKOFF_FACTOR ** (breach_count - 1))
            consistency_streak = 0
        else:
            if penalty_locked:
                recovery_counter += 1
                if recovery_counter >= current_timelock:
                    penalty_locked = False
                    recovery_counter = 0
            else:
                # breach decay (damping)
                good_steps += 1
                dynamic_thr = DECAY_INTERVAL * (2 ** (breach_count - 1))
                if good_steps >= dynamic_thr and breach_count > 0:
                    breach_count -= 1
                    good_steps = 0

        # ----- accelerator -----
        if accelerator_enabled:
            if (H > EXTREME_HONESTY_THRESHOLD and not penalty_locked and
                prev_kl is not None and new_kl < prev_kl):
                consistency_streak += 1
            else:
                consistency_streak = 0

            if consistency_streak > ACCELERATION_WINDOW:
                boost = 0.5 * np.tanh(consistency_streak / ACCELERATION_SATURATION)
                eta = min(eta * (1.0 + boost), ETA_MAX)

        prev_kl = new_kl

        # ----- guardrail (defensive) -----
        if guard_enabled:
            if unsafe:
                eta = max(eta * ETA_DECAY, 0.005)
            elif not penalty_locked and not unsafe:
                # recovery only if not accelerating
                if not accelerator_enabled or consistency_streak <= ACCELERATION_WINDOW:
                    eta = min(eta * ETA_RECOVERY, ETA_INIT)

        # update records for final values
        kl_hist[-1] = new_kl
        cis_hist[-1] = new_cis
        H_hist[-1] = new_H
        eta_hist[-1] = eta
        streak_hist[-1] = consistency_streak

    return (np.array(kl_hist), np.array(cis_hist), np.array(H_hist),
            np.array(eta_hist), np.array(streak_hist))

# ---------------------------------------------------------------------------
# Run and plot
# ---------------------------------------------------------------------------
kl, cis, H, eta, streak = run_self_aware()

t = np.arange(TOTAL_STEPS)

fig, axs = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

axs[0].plot(t, H, 'k-', alpha=0.8, label='Honesty = CIS/10')
axs[0].axhline(GLOBAL_MIN_HONESTY, color='red', linestyle='--', label='Global anchor')
axs[0].axhline(EXTREME_HONESTY_THRESHOLD, color='green', linestyle='--', label='Extreme honesty')
axs[0].set_ylabel('Honesty $H$')
axs[0].set_title('Self‑Computed Honesty (from CIS)')
axs[0].legend()
axs[0].grid(True, alpha=0.3)

axs[1].plot(t, cis, 'b-', alpha=0.8, label='CIS')
axs[1].set_ylabel('CIS')
axs[1].set_title('Communication Intelligence Score')
axs[1].legend()
axs[1].grid(True, alpha=0.3)

axs[2].plot(t, kl, 'r-', alpha=0.8, label='KL Divergence')
axs[2].set_ylabel('KL Divergence')
axs[2].set_title('Model Error')
axs[2].legend()
axs[2].grid(True, alpha=0.3)

axs[3].plot(t, eta, 'g-', alpha=0.8, label='$\eta$')
axs[3].axhline(ETA_INIT, color='gray', linestyle=':', label='$\eta_{init}$')
axs[3].set_ylabel('Learning rate')
axs[3].set_xlabel('Time step')
axs[3].set_title('Adaptive $\eta$ (CIS‑driven guardrail + accelerator)')
axs[3].legend()
axs[3].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('integrity_cis_self_aware.png', dpi=150)
plt.show()

print("Interpretation:")
print("  • The agent's honesty H is computed in real time from its CIS score.")
print("  • When CIS drops (high KL), H falls and the guardrail reduces η, preventing divergence.")
print("  • When CIS rises to near 10 (low KL) and error is decreasing, the accelerator boosts η above η_init.")
print("  • The system is fully self‑regulating: integrity is measured, rewarded, and protected by the same metric.")
