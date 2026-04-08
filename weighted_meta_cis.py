"""
Weighted Meta‑CIS (Communication Intelligence Score)

Computes an aggregate communication quality score from multiple CIS‑rated interactions,
where each interaction can be assigned a different weight (e.g., by importance, recency, or duration).

Author: Radiant Protocol
License: MIT
"""

from typing import List, Optional, Union, Callable
import math

def normalize_cis(score: float, source_scale: str = "auto") -> float:
    """
    Convert CIS score to a normalized 0–1 scale.
    
    Args:
        score: Input CIS score.
        source_scale: "0-10", "0-1", or "auto". Auto detects if score > 1 → assumes 0‑10 scale.
    
    Returns:
        float: Score normalized to [0, 1].
    """
    if source_scale == "auto":
        if score > 1.0:
            source_scale = "0-10"
        else:
            source_scale = "0-1"
    
    if source_scale == "0-10":
        return max(0.0, min(1.0, score / 10.0))
    else:
        return max(0.0, min(1.0, score))


def weighted_meta_cis(
    cis_values: List[float],
    weights: Optional[List[float]] = None,
    weight_strategy: Union[str, Callable[[int], float]] = "uniform",
    normalize: bool = True
) -> float:
    """
    Compute weighted Meta‑CIS from a list of CIS scores.
    
    Args:
        cis_values: List of CIS scores (can be 0‑10 or 0‑1 scale).
        weights: Optional list of explicit weights (same length). If None, weight_strategy is used.
        weight_strategy: 
            - "uniform": all weights = 1.
            - "linear": weights = index + 1 (later interactions get higher weight).
            - "exponential": weights = exp(decay * index) (later interactions get exponentially more weight).
            - "inverse": weights = 1/(index+1) (earlier interactions get more weight).
            - Callable: function that receives index (0‑based) and returns weight.
        normalize: If True, normalizes input scores to 0‑1 scale before averaging.
    
    Returns:
        float: Weighted average CIS (0‑1). Returns 0.0 if no scores.
    """
    if not cis_values:
        return 0.0
    
    n = len(cis_values)
    
    # Prepare weights
    if weights is not None:
        if len(weights) != n:
            raise ValueError("weights length must match cis_values length")
        weight_list = weights
    else:
        if weight_strategy == "uniform":
            weight_list = [1.0] * n
        elif weight_strategy == "linear":
            weight_list = [float(i + 1) for i in range(n)]
        elif weight_strategy == "exponential":
            decay = 0.5  # can be parameterized
            weight_list = [math.exp(decay * i) for i in range(n)]
        elif weight_strategy == "inverse":
            weight_list = [1.0 / (i + 1) for i in range(n)]
        elif callable(weight_strategy):
            weight_list = [weight_strategy(i) for i in range(n)]
        else:
            raise ValueError(f"Unknown weight_strategy: {weight_strategy}")
    
    # Normalize scores if requested
    if normalize:
        scores_norm = [normalize_cis(c) for c in cis_values]
    else:
        scores_norm = cis_values
    
    # Compute weighted average
    total_weight = sum(weight_list)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(s * w for s, w in zip(scores_norm, weight_list))
    return weighted_sum / total_weight


class MetaCISAccumulator:
    """
    Stateful accumulator for incremental weighted Meta‑CIS.
    Useful for streaming conversations or real‑time updates.
    """
    
    def __init__(self, decay_factor: float = 0.9, max_history: Optional[int] = None):
        """
        Args:
            decay_factor: Exponential decay weight for older scores (0 < decay_factor <= 1).
                          Lower value gives more weight to recent interactions.
            max_history: Maximum number of scores to retain (optional, for memory bounding).
        """
        self.decay_factor = decay_factor
        self.max_history = max_history
        self.scores = []      # list of (cis_score, timestamp)
        self._weighted_sum = 0.0
        self._total_weight = 0.0
    
    def add(self, cis_score: float, timestamp: Optional[float] = None) -> None:
        """
        Add a new CIS score to the accumulator.
        
        Args:
            cis_score: CIS value (0‑10 or 0‑1 scale). Will be normalized.
            timestamp: Optional timestamp (Unix seconds). If not provided, uses current time.
        """
        norm = normalize_cis(cis_score)
        self.scores.append((norm, timestamp))
        
        # Apply exponential decay based on recency if timestamps are provided
        # For simplicity, we use a global decay factor on the cumulative weight.
        # This implementation recalculates on demand for accuracy.
        # To avoid O(n) each time, we can store cumulative values, but for simplicity:
        self._recompute()
        
        if self.max_history and len(self.scores) > self.max_history:
            self.scores = self.scores[-self.max_history:]
            self._recompute()
    
    def _recompute(self) -> None:
        """Recalculate weighted sum and total weight using exponential decay over index order."""
        n = len(self.scores)
        if n == 0:
            self._weighted_sum = 0.0
            self._total_weight = 0.0
            return
        
        # Weight by position: most recent (last) gets weight 1, older get decay_factor^(distance)
        weights = []
        for i in range(n):
            age = n - 1 - i  # 0 for newest
            w = self.decay_factor ** age
            weights.append(w)
        total_weight = sum(weights)
        if total_weight == 0:
            self._weighted_sum = 0.0
            self._total_weight = 0.0
            return
        weighted_sum = sum(score * w for score, w in zip([s[0] for s in self.scores], weights))
        self._weighted_sum = weighted_sum
        self._total_weight = total_weight
    
    def value(self) -> float:
        """Return current weighted Meta‑CIS (0‑1)."""
        if self._total_weight == 0:
            return 0.0
        return self._weighted_sum / self._total_weight
    
    def reset(self) -> None:
        """Clear all history."""
        self.scores.clear()
        self._weighted_sum = 0.0
        self._total_weight = 0.0


# Example usage
if __name__ == "__main__":
    # Example 1: weighted average with custom weights
    cis_vals = [0.9, 0.7, 0.8]   # normalized already
    weights = [3, 1, 2]
    result = weighted_meta_cis(cis_vals, weights=weights, normalize=False)
    print(f"Weighted Meta‑CIS: {result:.3f}")  # 0.825
    
    # Example 2: exponential decay (more weight to recent)
    cis_vals = [0.5, 0.6, 0.7, 0.9]  # later scores higher
    result_exp = weighted_meta_cis(cis_vals, weight_strategy="exponential")
    print(f"Exponential decay: {result_exp:.3f}")  # should be > simple average
    
    # Example 3: stateful accumulator
    acc = MetaCISAccumulator(decay_factor=0.8)
    acc.add(0.7)
    acc.add(0.8)
    acc.add(0.9)
    print(f"Incremental Meta‑CIS: {acc.value():.3f}")
