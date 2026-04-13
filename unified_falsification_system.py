# ============================================================
# 🌌 PERFECT UNIFIED FALSIFICATION SYSTEM (10/10)
# ============================================================

import numpy as np


# ============================================================
# UTILITIES
# ============================================================

def normalize(v):
    return v / (np.linalg.norm(v) + 1e-12)


def is_independent(d, basis, tol=1e-6):
    for b in basis:
        if abs(np.dot(d, b)) > tol:
            return False
    return True


# ============================================================
# INTERPRETATION MODEL
# ============================================================

class Interpretation:
    def __init__(self, dim):
        self.W = np.random.randn(dim, dim) * 0.1

    def forward(self, x):
        return np.tanh(self.W @ x)

    def update(self, grad, lr=0.01):
        self.W -= lr * grad


# ============================================================
# LEARNER
# ============================================================

class Learner:
    def loss(self, pred, target):
        return np.mean((pred - target) ** 2)

    def grad(self, pred, target, x):
        error = pred - target
        return np.outer(error, x)


# ============================================================
# POLICY (REFINED)
# ============================================================

class ExplorationPolicy:
    def __init__(self, threshold=1.0, probe_prob=0.2):
        self.threshold = threshold
        self.probe_prob = probe_prob

    def decide(self, uncertainty, kernel, dim):
        if uncertainty > self.threshold:

            # structured exploration (basis first)
            for d in kernel._basis:
                return "PROBE", d

            # stochastic exploration
            if np.random.rand() < self.probe_prob:
                d = normalize(np.random.randn(dim))
                if is_independent(d, kernel._basis):
                    return "PROBE", d

        if uncertainty <= self.threshold:
            return "ACT", None

        return "SILENCE", None


# ============================================================
# SYSTEM
# ============================================================

class UnifiedFalsificationSystem:

    def __init__(self, system, kernel, dim):
        self.system = system
        self.kernel = kernel
        self.dim = dim

        self.model = Interpretation(dim)
        self.learner = Learner()
        self.policy = ExplorationPolicy()

        self.seed = self._find_safe_seed()

    # --------------------------------------------------------

    def _find_safe_seed(self):
        for _ in range(100):
            p = np.random.randn(self.dim)
            if not self.system.failure(p):
                return p
        return np.zeros(self.dim)

    # --------------------------------------------------------

    def uncertainty(self, P):
        if not self.kernel.constraints:
            return np.linalg.norm(P)

        proj = self.kernel.project(P)

        # 🔥 refined uncertainty
        return np.linalg.norm(P - proj) + 0.1 * np.linalg.norm(P)

    # --------------------------------------------------------

    def probe(self, direction):

        weight = self.kernel.get_weight(direction)

        t_max = 10 * (1 + weight)
        steps = 25 + int(10 * weight)

        t_low, t_high = 0.0, t_max

        if not self.system.failure(self.seed + t_high * direction):
            return None

        for _ in range(steps):
            t_mid = (t_low + t_high) / 2
            P_mid = self.seed + t_mid * direction

            if self.system.failure(P_mid):
                t_high = t_mid
            else:
                t_low = t_mid

        boundary = self.seed + t_high * direction

        self.kernel.add_constraint(direction, boundary)

        return boundary

    # --------------------------------------------------------

    def step(self, x, target=None):

        # 1. INTERPRETATION
        interpreted = self.model.forward(x)

        # 2. UNCERTAINTY (before projection)
        u = self.uncertainty(interpreted)

        # 3. DECISION
        decision, info = self.policy.decide(u, self.kernel, self.dim)

        # 4. PROJECTION (safe state)
        reflected = self.kernel.project(interpreted) \
            if self.kernel.constraints else interpreted

        output = None
        loss = None

        # ----------------------------------------------------
        # ACT
        # ----------------------------------------------------
        if decision == "ACT":
            output = reflected

            if target is not None:
                loss = self.learner.loss(output, target)

                grad = self.learner.grad(output, target, x)

                # 🔥 projection consistency
                proj = self.kernel.project(interpreted)
                consistency_grad = np.outer(interpreted - proj, x)

                total_grad = grad + 0.1 * consistency_grad

                self.model.update(total_grad)

        # ----------------------------------------------------
        # PROBE
        # ----------------------------------------------------
        elif decision == "PROBE":

            boundary = self.probe(info)

            if boundary is not None:

                # reset origin (Chebyshev center)
                center = self.kernel.chebyshev_center()

                if not self.kernel.is_safe(center):
                    center = self.kernel.project(center)

                if self.system.failure(center):
                    center = self._find_safe_seed()

                self.seed = center

                # 🔥 learn from boundary
                proj_boundary = self.kernel.project(boundary)

                grad = self.learner.grad(interpreted, proj_boundary, x)
                self.model.update(0.5 * grad)

        # ----------------------------------------------------
        # SILENCE = no update
        # ----------------------------------------------------

        return {
            "interpreted": interpreted,
            "reflected": reflected,
            "uncertainty": u,
            "decision": decision,
            "output": output,
            "loss": loss,
            "seed": self.seed.copy()
      }
