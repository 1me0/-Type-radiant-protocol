"""
Weighted Meta‑CIS & Composite Intelligence Score

Computes aggregate communication quality (Meta‑CIS) and a final intelligence metric
that includes real‑world outcome and presence.

Mathematical models covered by the Radiant Protocol Master Formula License (RPML) v1.0.

Author: Radiant Protocol
License: MIT (software) / RPML v1.0 (mathematical models)
Version: 1.3.0
"""

from typing import List, Optional, Union, Callable, Sequence, Tuple
import math

__all__ = [
    "normalize_cis",
    "weighted_meta_cis",
    "MetaCISAccumulator",
    "intelligence_score",
]


def normalize_cis(score: float, source_scale: str = "auto") -> float:
    """
    Convert a CIS score to a normalized [0,1] scale.

    Args:
        score: Input CIS score.
        source_scale: "0-10", "0-1", or "auto". Auto detects if score > 1 → 0‑10 scale.

    Returns:
        float: Score clamped to [0,1].

    Raises:
        ValueError: If source_scale is not one of "auto", "0-10", or "0-1".
    """
    if source_scale == "auto":
        source_scale = "0-10" if score > 1.0 else "0-1"
    elif source_scale not in ("0-10", "0-1"):
        raise ValueError("source_scale must be 'auto', '0-10', or '0-1'")

    if source_scale == "0-10":
        return max(0.0, min(1.0, score / 10.0))
    else:  # "0-1"
        return max(0.0, min(1.0, score))


def weighted_meta_cis(
    cis_values: Sequence[float],
    weights: Optional[Sequence[float]] = None,
    weight_strategy: Union[str, Callable[[int], float]] = "uniform",
    normalize: bool = True,
    exponential_decay_rate: float = 0.5,
) -> float:
    """
    Compute a weighted Meta‑CIS from a list of CIS scores.

    The Meta‑CIS is defined as the weighted arithmetic mean:

        Meta‑CIS = (Σ w_i * s_i) / Σ w_i

    where s_i are normalized CIS scores (0‑1) and w_i are non‑negative weights.

    Args:
        cis_values: List of CIS scores (0‑10 or 0‑1 scale).
        weights: Optional explicit weights (same length). If provided, overrides strategy.
        weight_strategy:
            - "uniform": w_i = 1.
            - "linear": w_i = i + 1 (later interactions get higher weight).
            - "exponential": w_i = exp(decay_rate * i) (later interactions get exponentially more weight).
            - "inverse": w_i = 1/(i + 1) (earlier interactions get more weight).
            - Callable: function mapping index (0‑based) → weight.
        normalize: If True, input scores are normalized to [0,1] before averaging.
        exponential_decay_rate: Decay rate for exponential strategy (must be > 0). Default 0.5.

    Returns:
        float: Weighted Meta‑CIS in [0,1]. Returns 0.0 if no scores.

    Raises:
        ValueError: If weights length does not match cis_values length,
                    or if exponential_decay_rate is not positive,
                    or if any weight is negative,
                    or if weight_strategy is unknown.
    """
    n = len(cis_values)
    if n == 0:
        return 0.0

    if weights is not None:
        if len(weights) != n:
            raise ValueError("weights length must match cis_values length")
        weight_list = list(weights)
        if any(w < 0 for w in weight_list):
            raise ValueError("weights must be non-negative")
    else:
        if weight_strategy == "uniform":
            weight_list = [1.0] * n
        elif weight_strategy == "linear":
            weight_list = [float(i + 1) for i in range(n)]
        elif weight_strategy == "exponential":
            if exponential_decay_rate <= 0:
                raise ValueError("exponential_decay_rate must be > 0")
            weight_list = [math.exp(exponential_decay_rate * i) for i in range(n)]
        elif weight_strategy == "inverse":
            weight_list = [1.0 / (i + 1) for i in range(n)]
        elif callable(weight_strategy):
            weight_list = [weight_strategy(i) for i in range(n)]
        else:
            raise ValueError(f"Unknown weight_strategy: {weight_strategy}")

    if normalize:
        scores_norm = [normalize_cis(c) for c in cis_values]
    else:
        scores_norm = list(cis_values)

    total_weight = sum(weight_list)
    if total_weight == 0.0:
        return 0.0
    weighted_sum = sum(s * w for s, w in zip(scores_norm, weight_list))
    return weighted_sum / total_weight


class MetaCISAccumulator:
    """
    Stateful accumulator for incremental weighted Meta‑CIS.

    Uses exponential decay based on insertion order (most recent gets highest weight).
    Suitable for streaming conversations or real‑time updates.

    Mathematical formulation:

        Let the sequence of normalized scores be s₀, s₁, …, s_t at time t.
        With decay factor δ ∈ (0,1], the weight of s_i is w_i = δ^{t-i}.
        Then Meta‑CIS = (Σ_{i=0}^t w_i s_i) / (Σ_{i=0}^t w_i).

    Incremental update correctness:

        At time t-1, we have W_{t-1} = Σ_{i=0}^{t-1} δ^{t-1-i} and
        S_{t-1} = Σ_{i=0}^{t-1} δ^{t-1-i} s_i.
        At time t, after appending s_t:
        W_t = Σ_{i=0}^{t-1} δ·δ^{t-1-i} + 1·s_t = δ·W_{t-1} + 1,
        S_t = δ·S_{t-1} + s_t.
        Thus the O(1) update is correct.
    """

    def __init__(self, decay_factor: float = 0.9, max_history: Optional[int] = None):
        if not (0 < decay_factor <= 1):
            raise ValueError("decay_factor must be in (0,1]")
        if max_history is not None and max_history <= 0:
            raise ValueError("max_history must be a positive integer")
        self.decay_factor = decay_factor
        self.max_history = max_history
        self._scores: List[float] = []
        self._weighted_sum: float = 0.0
        self._total_weight: float = 0.0

    def add(self, cis_score: float) -> None:
        norm = normalize_cis(cis_score)
        self._weighted_sum = self._weighted_sum * self.decay_factor + norm
        self._total_weight = self._total_weight * self.decay_factor + 1.0
        self._scores.append(norm)
        if self.max_history and len(self._scores) > self.max_history:
            self._scores.pop(0)
            self._recompute()

    def add_many(self, scores: List[float]) -> None:
        if not scores:
            return
        for sc in scores:
            norm = normalize_cis(sc)
            self._weighted_sum = self._weighted_sum * self.decay_factor + norm
            self._total_weight = self._total_weight * self.decay_factor + 1.0
            self._scores.append(norm)
        if self.max_history and len(self._scores) > self.max_history:
            excess = len(self._scores) - self.max_history
            self._scores = self._scores[excess:]
            self._recompute()

    def _recompute(self) -> None:
        n = len(self._scores)
        if n == 0:
            self._weighted_sum = 0.0
            self._total_weight = 0.0
            return
        total = 0.0
        weighted = 0.0
        for i, s in enumerate(self._scores):
            w = self.decay_factor ** (n - 1 - i)
            total += w
            weighted += w * s
        self._weighted_sum = weighted
        self._total_weight = total

    def value(self) -> float:
        if self._total_weight == 0.0:
            return 0.0
        return self._weighted_sum / self._total_weight

    def reset(self) -> None:
        self._scores.clear()
        self._weighted_sum = 0.0
        self._total_weight = 0.0

    def __len__(self) -> int:
        return len(self._scores)

    def __repr__(self) -> str:
        return f"MetaCISAccumulator(decay={self.decay_factor:.3f}, n={len(self._scores)}, value={self.value():.4f})"


def intelligence_score(
    meta_cis: float,
    outcome_score: float,
    presence_score: float,
    weights: Tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> float:
    """
    Composite intelligence score combining communication quality, task success, and presence.

    The formula is:

        Intelligence = λ₁ * meta_cis + λ₂ * outcome_score + λ₃ * presence_score

    where:
        - meta_cis ∈ [0,1] captures clarity, coherence, and alignment of communication.
        - outcome_score ∈ [0,1] measures success on real tasks (e.g., accuracy, goal completion).
        - presence_score ∈ [0,1] measures active, meaningful engagement (stability + responsiveness + relevance).

    These weights can be adjusted to emphasize different aspects of intelligence.

    Args:
        meta_cis: Normalized Meta‑CIS score (0‑1) from weighted_meta_cis().
        outcome_score: Normalized outcome score (0‑1) from external evaluation.
        presence_score: Normalized presence score (0‑1) from the Radiant Core Engine.
        weights: Tuple of (λ1, λ2, λ3); sum should typically equal 1.0.

    Returns:
        float: Composite intelligence score in [0,1].

    Raises:
        ValueError: If any input is outside [0,1] or weights are negative.
    """
    for name, val in [("meta_cis", meta_cis), ("outcome_score", outcome_score), ("presence_score", presence_score)]:
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"{name} must be in [0,1], got {val}")
    if any(w < 0 for w in weights):
        raise ValueError("Weights must be non-negative")

    return weights[0] * meta_cis + weights[1] * outcome_score + weights[2] * presence_score


# ============================================================
# Example usage
# ============================================================
if __name__ == "__main__":
    # Meta-CIS computation
    cis_vals = [0.9, 0.7, 0.8]
    result = weighted_meta_cis(cis_vals, weights=[3, 1, 2], normalize=False)
    print(f"Meta-CIS: {result:.3f}")

    # Accumulator
    acc = MetaCISAccumulator(decay_factor=0.8)
    acc.add_many([0.7, 0.8, 0.9])
    print(f"Stream Meta-CIS: {acc.value():.3f}")

    # Composite intelligence
    meta = acc.value()                          # e.g., 0.822
    outcome = 0.85                              # task success rate
    presence = 0.9                              # engagement level
    iq = intelligence_score(meta, outcome, presence, weights=(0.5, 0.3, 0.2))
    print(f"Intelligence Score: {iq:.3f}")
