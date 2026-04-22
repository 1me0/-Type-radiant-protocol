"""
Weighted Meta‑CIS (Communication Intelligence Score)

Computes an aggregate communication quality score from multiple CIS‑rated interactions,
where each interaction can be assigned a different weight (e.g., by importance, recency, or duration).

Author: Radiant Protocol
License: MIT
Version: 1.1.0
"""

from typing import List, Optional, Union, Callable, Sequence, Any
import math

__all__ = [
    "normalize_cis",
    "weighted_meta_cis",
    "MetaCISAccumulator",
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

    Examples:
        >>> normalize_cis(8.5, "0-10")
        0.85
        >>> normalize_cis(0.85, "0-1")
        0.85
        >>> normalize_cis(8.5)  # auto detects 0-10
        0.85
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
        TypeError: If weight_strategy is not callable when expected.

    Examples:
        >>> weighted_meta_cis([0.9, 0.7, 0.8], weights=[3,1,2], normalize=False)
        0.83333...
        >>> weighted_meta_cis([0.5, 0.6, 0.7, 0.9], weight_strategy="exponential")
        # Returns a value > simple average 0.675 due to recency weighting.
    """
    n = len(cis_values)
    if n == 0:
        return 0.0

    # ---- weights ----
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

    # ---- normalize scores ----
    if normalize:
        scores_norm = [normalize_cis(c) for c in cis_values]
    else:
        scores_norm = list(cis_values)

    # ---- weighted average ----
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

    Mathematical formulation: Let the sequence of normalized scores be s₀, s₁, …, s_{t}.
    With decay factor δ ∈ (0,1], the weight of s_i is w_i = δ^{t-i}.
    Then Meta‑CIS = (Σ w_i s_i) / Σ w_i.

    This implementation uses an O(1) incremental update to avoid recomputing from scratch,
    except when the optional history limit is exceeded (then a lightweight recomputation occurs).

    Attributes:
        decay_factor (float): Exponential decay factor (0 < decay_factor ≤ 1).
        max_history (Optional[int]): Maximum number of stored scores (None = unlimited).
    """

    def __init__(self, decay_factor: float = 0.9, max_history: Optional[int] = None):
        """
        Args:
            decay_factor: Weight multiplier for each step back in history (0 < decay_factor ≤ 1).
                          Smaller values give more weight to recent scores.
            max_history: Optional memory bound. When exceeded, oldest scores are dropped.

        Raises:
            ValueError: If decay_factor is not in (0,1] or if max_history is not a positive integer.
        """
        if not (0 < decay_factor <= 1):
            raise ValueError("decay_factor must be in (0,1]")
        if max_history is not None and max_history <= 0:
            raise ValueError("max_history must be a positive integer")
        self.decay_factor = decay_factor
        self.max_history = max_history

        self._scores: List[float] = []       # normalized scores in chronological order
        self._weighted_sum: float = 0.0
        self._total_weight: float = 0.0

    def add(self, cis_score: float) -> None:
        """
        Add a new CIS score (0‑10 or 0‑1 scale). The score is normalized automatically.

        Args:
            cis_score: Raw CIS value.
        """
        norm = normalize_cis(cis_score)

        # Incremental update: multiply existing sums by decay_factor,
        # then add the new score with weight 1.
        self._weighted_sum = self._weighted_sum * self.decay_factor + norm
        self._total_weight = self._total_weight * self.decay_factor + 1.0

        self._scores.append(norm)

        # Enforce history limit by dropping oldest score and adjusting sums.
        if self.max_history and len(self._scores) > self.max_history:
            self._scores.pop(0)
            # Recompute to maintain exact precision after truncation.
            self._recompute()

    def _recompute(self) -> None:
        """Recompute cumulative weighted sum and total weight from stored scores."""
        n = len(self._scores)
        if n == 0:
            self._weighted_sum = 0.0
            self._total_weight = 0.0
            return

        total = 0.0
        weighted = 0.0
        # Weight for score at index i: decay_factor ** (n - 1 - i)
        for i, s in enumerate(self._scores):
            w = self.decay_factor ** (n - 1 - i)
            total += w
            weighted += w * s
        self._weighted_sum = weighted
        self._total_weight = total

    def value(self) -> float:
        """Return current weighted Meta‑CIS in [0,1]."""
        if self._total_weight == 0.0:
            return 0.0
        return self._weighted_sum / self._total_weight

    def reset(self) -> None:
        """Clear all history and reset accumulator."""
        self._scores.clear()
        self._weighted_sum = 0.0
        self._total_weight = 0.0

    def __len__(self) -> int:
        """Return number of stored scores."""
        return len(self._scores)

    def __repr__(self) -> str:
        return f"MetaCISAccumulator(decay={self.decay_factor:.3f}, n={len(self._scores)}, value={self.value():.4f})"


# ============================================================
# Example usage (only executed when run directly)
# ============================================================
if __name__ == "__main__":
    # Example 1: explicit weights
    cis_vals = [0.9, 0.7, 0.8]   # already normalized
    weights = [3, 1, 2]
    result = weighted_meta_cis(cis_vals, weights=weights, normalize=False)
    print(f"Weighted Meta‑CIS (explicit): {result:.3f}")

    # Example 2: exponential decay (more weight to recent)
    cis_vals = [0.5, 0.6, 0.7, 0.9]   # increasing quality
    result_exp = weighted_meta_cis(cis_vals, weight_strategy="exponential", exponential_decay_rate=0.5)
    print(f"Exponential decay: {result_exp:.3f}")

    # Example 3: stateful accumulator
    acc = MetaCISAccumulator(decay_factor=0.8)
    acc.add(0.7)
    acc.add(0.8)
    acc.add(0.9)
    print(f"Incremental Meta‑CIS: {acc.value():.3f}")
    print(acc)
