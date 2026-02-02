"""
HSE Risk Index Normalizer

Percentile-rank normalization for mapping raw metric values
to a standardized 1-10 risk scale.
"""

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NormalizationResult:
    """Immutable container for normalization outputs.

    Attributes:
        original: The original input series.
        percentile_ranks: Percentile ranks (0-1) for each value.
        scaled: Values mapped to the target integer scale.
        metadata: Additional information about the normalization.
    """

    original: pd.Series
    percentile_ranks: pd.Series
    scaled: pd.Series
    metadata: Dict[str, Any]


def percentile_rank(values: pd.Series) -> pd.Series:
    """Compute percentile ranks for a series of values.

    Returns a Series of percentile ranks in [0, 1] where ties
    receive the same rank (average method). NaN values are preserved.

    Args:
        values: Input numeric series.

    Returns:
        Series of percentile ranks with the same index as the input.
    """
    if len(values) == 0:
        return pd.Series([], dtype=float)

    # Identify non-NaN positions
    mask = values.notna()
    result = pd.Series(np.nan, index=values.index, dtype=float)

    valid = values[mask]
    if len(valid) == 0:
        return result

    # Rank using average method for ties, then convert to 0-1 scale
    ranks = valid.rank(method="average")
    percentiles = ranks / len(valid)

    result[mask] = percentiles.values
    return result


def normalize_to_scale(values: pd.Series, low: int = 1, high: int = 10) -> pd.Series:
    """Map percentile ranks to an integer scale.

    Computes percentile ranks, then maps them to integer buckets
    in the range [low, high]. NaN values are preserved.

    Args:
        values: Input numeric series.
        low: Minimum value of the output scale (inclusive).
        high: Maximum value of the output scale (inclusive).

    Returns:
        Series of integer-valued scores with the same index as the input.
    """
    if len(values) == 0:
        return pd.Series([], dtype=float)

    pct = percentile_rank(values)
    result = pd.Series(np.nan, index=values.index, dtype=float)

    mask = pct.notna()
    if not mask.any():
        return result

    # Map percentile (0, 1] to [low, high] using ceiling of scaled value
    # percentile 0.2 on 1-10 scale: 0.2 * (10-1) + 1 = 2.8 -> ceil -> 3
    # But we want [10,20,30,40,50] -> [2,4,6,8,10]
    # percentile_rank gives [0.2, 0.4, 0.6, 0.8, 1.0]
    # Linear map: pct * (high - low) + low
    # 0.2*9+1=2.8 -> round -> 3 ... not quite [2,4,6,8,10]
    # Use: ceil(pct * high_range) where high_range = high - low + 1, then clamp
    # Actually: map pct directly to scale using even buckets
    # For 5 items with pct [0.2, 0.4, 0.6, 0.8, 1.0] on scale 1-10:
    # Use: round(pct * (high - low) + low - 0.5) but clamped
    # 0.2*9+0.5 = 2.3 -> round -> 2 YES
    # 0.4*9+0.5 = 4.1 -> round -> 4 YES
    # 0.6*9+0.5 = 5.9 -> round -> 6 YES
    # 0.8*9+0.5 = 7.7 -> round -> 8 YES
    # 1.0*9+0.5 = 9.5 -> round -> 10 YES (with proper rounding)
    # Actually let's use: low + round(pct * (high - low + 1) - 0.5)
    # 0.2*(10) - 0.5 + 1 = 2.5 -> nope
    # Simplest correct approach: map (0,1] to [low,high] evenly
    # Scale = pct * (high - low) + low - 0.5, then round, then clamp
    scale_range = high - low
    raw_scaled = pct[mask] * scale_range + (low - 0.5)
    clamped = np.clip(np.round(raw_scaled), low, high).astype(int)

    result[mask] = clamped.values
    return result
