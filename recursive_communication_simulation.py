import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# PARAMETERS
# ============================================================

alpha = 0.2    # understanding rate (toward reality)
beta = 0.3     # communication rate (other learns you)
gamma = 0.1    # feedback rate (you adapt to others)

steps = 100
dim = 5

# Noise levels
expr_noise_std = 0.05      # language imperfection
reality_noise_std = 0.01   # dynamic reality

# ============================================================
# INITIAL STATES
# ============================================================

R = np.random.randn(dim)   # Reality
S = np.random.randn(dim)   # Self (your understanding)
O = np.random.randn(dim)   # Other (listener)

# ============================================================
# TRACKING
# ============================================================

self_errors = []
other_errors = []
total_errors = []

# ============================================================
# RECURSIVE SYSTEM (ORDER-INVARIANT UPDATE)
# ============================================================

for t in range(steps):

    # --------------------------------------------------------
    # 1. DYNAMIC REALITY
    # --------------------------------------------------------
    R = R + np.random.normal(0, reality_noise_std, dim)

    # --------------------------------------------------------
    # 2. NOISY EXPRESSION (based on current S)
    # --------------------------------------------------------
    noise = np.random.normal(0, expr_noise_std, dim)
    E = S + noise

    # --------------------------------------------------------
    # 3. OTHER UPDATES (listening to expression)
    # --------------------------------------------------------
    O = O + beta * (E - O)

    # --------------------------------------------------------
    # 4. SELF UPDATE (COMBINED: truth + feedback)
    # --------------------------------------------------------
    S = S + alpha * (R - S) + gamma * (O - S)

    # --------------------------------------------------------
    # ERRORS
    # --------------------------------------------------------
    e_self = np.linalg.norm(R - S)
    e_other = np.linalg.norm(S - O)
    e_total = e_self + e_other

    self_errors.append(e_self)
    other_errors.append(e_other)
    total_errors.append(e_total)

# ============================================================
# RESULTS
# ============================================================

print("Final Self Error (Understanding):", self_errors[-1])
print("Final Other Error (Being Understood):", other_errors[-1])
print("Final Total Error:", total_errors[-1])

# ============================================================
# VISUALIZATION
# ============================================================

plt.figure()
plt.plot(self_errors, label="Self Error (R - S)")
plt.plot(other_errors, label="Other Error (S - O)")
plt.plot(total_errors, label="Total Error")
plt.legend()
plt.title("Unified Update: Truth + Feedback (Order-Invariant)")
plt.xlabel("Time")
plt.ylabel("Error")
plt.grid()
plt.show()
