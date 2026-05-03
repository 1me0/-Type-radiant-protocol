"""
Weighted Meta‑CIS & Composite Intelligence Score

Computes aggregate communication quality (Meta‑CIS) and a final intelligence metric
that includes real‑world outcome and presence.

Mathematical models covered by the Radiant Protocol Master Formula License (RPML) v1.0.

Author: Radiant Protocol
License: MIT (software) / RPML v1.0 (mathematical models)
Version: 1.4.0
"""

import warnings
import math
from typing import List, Optional, Union, Callable, Sequence, Tuple

__all__ = [
    "normalize_cis",
    "weighted_meta_cis",
    "MetaCISAccumulator",
    "intelligence_score",
]


def _is_finite_score(val: float) -> bool:
    """Return True if val is finite (not NaN, inf, or -inf)."""
    return math.isfinite(val)


def normalize_cis(score: float, source_scale: str = "auto") -> float:
    """
    Convert a CIS score to the normalized [0,1] interval.

    Args:
        score: Input CIS score (must be finite).
        source_scale: "0‑10", "0‑1", or "auto". When ``"auto"`` is used,
            values > 1.0 are treated as 0‑10 scale, values ≤ 1.0 as 0‑1 scale.
            **Important:** a score of e.g. 0.8 cannot be unambiguously
            auto‑detected — a warning is emitted when the value could belong to
            either scale *and* the caller did not specify a scale explicitly.

    Returns:
        ``score`` clamped to [0,1] after appropriate re‑scaling.

    Raises:
        ValueError: If *source_scale* is invalid or *score* is not finite.
    """
    if not _is_finite_score(score):
        raise ValueError("CIS score must be a finite number")
    if source_scale == "auto":
        source_scale = "0-10" if score > 1.0 else "0-1"
        # Emit a warning when the auto‑detection is ambiguous
        if 0 < score <= 1.0:
            warnings.warn(
                f"CIS score {score} ≤ 1.0 assumed as 0‑1 scale. "
                f"Pass source_scale='0-10' or '0-1' explicitly to suppress this warning."
            )
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
    source_scale: str = "auto",
    exponential_decay_rate: float = 0.5,
) -> float:
    """
    Compute a weighted Meta‑CIS from a list of CIS scores.

    The Meta‑CIS is defined as the weighted arithmetic mean:

        Meta‑CIS = (Σ w_i * s_i) / Σ w_i

    where s_i are normalized CIS scores (0‑1) and w_i are non‑negative weights.

    Args:
        cis_values: CIS scores (0‑10 or 0‑1 scale, all finite).
        weights: Optional explicit weights (same length). If provided, overrides *weight_strategy*.
        weight_strategy: * ``"uniform"`` : w_i = 1
                         * ``"linear"`` : w_i = i+1 (later interactions higher)
                         * ``"exponential"`` : w_i = exp(decay_rate * i)
                         * ``"inverse"`` : w_i = 1/(i+1) (earlier interactions higher)
                         * callable : function(index) -> weight
        normalize: If ``True``, scores are normalised to [0,1] using *source_scale*.
        source_scale: Scale of input scores (see :func:`normalize_cis`).
        exponential_decay_rate: Parameter for the exponential strategy (>0).

    Returns:
        Weighted Meta‑CIS in [0,1]. Returns 0.0 if the score list is empty.

    Raises:
        ValueError: If weights length mismatch, decay_rate≤0, weight_strategy unknown,
                    or any score is not finite.
    """
    n = len(cis_values)
    if n == 0:
        return 0.0

    # ---- normalise scores ----
    if normalize:
        scores_norm = [normalize_cis(c, source_scale) for c in cis_values]
    else:
        scores_norm = list(cis_values)

    # Safety: check finiteness after normalisation
    if not all(_is_finite_score(s) for s in scores_norm):
        raise ValueError("CIS scores must be finite after normalisation")

    # ---- build weights ----
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

    total_weight = sum(weight_list)
    if total_weight == 0.0:
        return 0.0
    return sum(s * w for s, w in zip(scores_norm, weight_list)) / total_weight


class MetaCISAccumulator:
    """
    Stateful accumulator for incremental weighted Meta‑CIS.

    Uses exponential decay based on insertion order — the most recent score has the
    highest weight.  Suitable for streaming conversations or real‑time updates.

    Mathematical formulation
    -------------------------
    Let the sequence of normalized scores be s₀, s₁, …, s_t at time t.
    With decay factor δ ∈ (0,1], the weight of s_i is w_i = δ^{t-i}.
    Then Meta‑CIS = (Σ_{i=0}^t w_i s_i) / (Σ_{i=0}^t w_i).

    The implementation uses an O(1) incremental update.  When the optional
    ``max_history`` is set and exceeded, a lightweight O(k) recomputation occurs
    on the retained window.

    Parameters
    ----------
    decay_factor : float
        Weight multiplier for each step back in history (0 < δ ≤ 1).
        Smaller values give more weight to recent scores.
    max_history : int, optional
        Maximum number of stored scores.  When exceeded the oldest score is silently
        dropped.  ``None`` means unlimited (be careful with memory on unbounded streams).
    source_scale : str
        Default scale for raw CIS values passed to :meth:`add` / :meth:`add_many`.
        Can be ``"auto"``, ``"0-10"``, or ``"0-1"`` (see :func:`normalize_cis`).
    """

    def __init__(self,
                 decay_factor: float = 0.9,
                 max_history: Optional[int] = None,
                 source_scale: str = "auto") -> None:
        if not (0 < decay_factor <= 1):
            raise ValueError("decay_factor must be in (0,1]")
        if max_history is not None and max_history <= 0:
            raise ValueError("max_history must be a positive integer")

        self.decay_factor = decay_factor
        self.max_history = max_history
        self.source_scale = source_scale

        self._scores: List[float] = []          # normalized scores, chronological
        self._weighted_sum: float = 0.0
        self._total_weight: float = 0.0

    def add(self, cis_score: float) -> None:
        """
        Add a single CIS score (0‑10 or 0‑1 scale).

        The score is normalised using the accumulator's *source_scale*.
        """
        norm = normalize_cis(cis_score, self.source_scale)
        self._weighted_sum = self._weighted_sum * self.decay_factor + norm
        self._total_weight = self._total_weight * self.decay_factor + 1.0
        self._scores.append(norm)

        if self.max_history and len(self._scores) > self.max_history:
            self._scores.pop(0)
            self._recompute()

    def add_many(self, scores: List[float]) -> None:
        """
        Add a batch of CIS scores in the given order.

        More efficient than calling :meth:`add` in a loop when ``max_history`` is set
        because only a single recomputation is triggered after the batch.
        """
        if not scores:
            return

        # Normalise all incoming scores
        norm_scores = [normalize_cis(s, self.source_scale) for s in scores]

        if self.max_history is not None and self.max_history > 0:
            # Directly build the final window to avoid temporary memory bloat
            # Determine how many of the old scores to keep
            new_cnt = len(norm_scores)
            old_cnt = len(self._scores)

            # The final window is the last max_history scores
            # We'll take from old list: min(old_cnt, max_history - new_cnt) (if positive)
            # and from new list: min(new_cnt, max_history)
            # Actually, we need to keep the most recent items overall.
            # Create a combined list of the last max_history entries.
            combined = self._scores[-self.max_history:] + norm_scores   # at most 2*max_history
            self._scores = combined[-self.max_history:] if len(combined) > self.max_history else combined
        else:
            # No limit – just append
            self._scores.extend(norm_scores)

        # Recompute sums from the final list
        self._recompute()

    def _recompute(self) -> None:
        """Recalculate weighted sum and total weight from scratch."""
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
        """Current weighted Meta‑CIS in [0,1]."""
        if self._total_weight == 0.0:
            return 0.0
        return self._weighted_sum / self._total_weight

    def reset(self) -> None:
        """Clear all history."""
        self._scores.clear()
        self._weighted_sum = 0.0
        self._total_weight = 0.0

    def __len__(self) -> int:
        return len(self._scores)

    def __repr__(self) -> str:
        return (f"MetaCISAccumulator(decay={self.decay_factor:.3f}, "
                f"n={len(self._scores)}, value={self.value():.4f})")


def intelligence_score(
    meta_cis: float,
    outcome_score: float,
    presence_score: float,
    weights: Tuple[float, float, float] = (0.5, 0.3, 0.2),
) -> float:
    """
    Composite intelligence score combining communication quality, task success,
    and presence/engagement.

    The formula is:

        Intelligence = λ₁·meta_cis + λ₂·outcome_score + λ₃·presence_score

    where:
        - **meta_cis** ∈ [0,1] captures clarity, coherence, and alignment.
        - **outcome_score** ∈ [0,1] measures success on real tasks (accuracy,
          goal completion, etc.).
        - **presence_score** ∈ [0,1] represents the stability, responsiveness,
          and relevance of the entity's presence.  This value should be obtained
          from the **Radiant Core Engine** (``RadiantCoreEngine.presence_score()``)
          or an equivalent active‑engagement metric.

    The weights are automatically normalised so that a convex combination is
    formed, guaranteeing that the output remains within [0,1].

    Args:
        meta_cis: Weighted Meta‑CIS score (0‑1).
        outcome_score: Task success score (0‑1).
        presence_score: Presence/engagement score (0‑1).
        weights: Relative importance of the three dimensions.

    Returns:
        Composite intelligence score ∈ [0,1].

    Raises:
        ValueError: If any input is outside [0,1] or not finite.
    """
    for name, val in [("meta_cis", meta_cis),
                      ("outcome_score", outcome_score),
                      ("presence_score", presence_score)]:
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"{name} must be in [0,1], got {val}")
        if not _is_finite_score(val):
            raise ValueError(f"{name} must be finite")

    sum_w = sum(weights)
    if sum_w <= 0:
        raise ValueError("Sum of weights must be positive")

    # Normalise weights so they sum to 1
    norm_w = tuple(w / sum_w for w in weights)
    return norm_w[0] * meta_cis + norm_w[1] * outcome_score + norm_w[2] * presence_score


# ============================================================
# Example usage
# ============================================================
if __name__ == "__main__":
    # 1. Batch weighted Meta-CIS with explicit 0-10 source scale
    cis_vals_10 = [8.5, 7.2, 9.0]          # 0‑10 scale
    result = weighted_meta_cis(cis_vals_10,
                               weights=[3, 1, 2],
                               normalize=True,
                               source_scale="0-10")
    print(f"[1] Meta-CIS (0-10 inputs): {result:.3f}")   # ~0.86

    # 2. Streaming accumulator with explicit 0-1 scale
    acc = MetaCISAccumulator(decay_factor=0.8, max_history=50, source_scale="0-1")
    acc.add_many([0.7, 0.85, 0.92])
    print(f"[2] Streaming Meta-CIS: {acc.value():.3f}")   # weighted recent-heavy

    # 3. Composite intelligence score
    meta_cis_val = weighted_meta_cis([0.78, 0.82, 0.90],
                                     normalize=False)  # already 0-1
    outcome = 0.85              # e.g., task success rate
    presence = 0.9              # from Radiant Core Engine
    iq = intelligence_score(meta_cis_val, outcome, presence,
                            weights=(0.5, 0.3, 0.2))
    print(f"[3] Composite Intelligence: {iq:.3f}")
