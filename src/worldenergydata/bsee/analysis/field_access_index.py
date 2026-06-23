"""Composite access / concentration index (relative, percentile-rank based).

The prior Lower-Tertiary work framed deepwater fields as an *access /
concentration* story: a few hard-to-reach, highly productive wells operated by
one party (deepwater hubs) versus many dispersed, low-per-well wells with many
operators (the shelf).  OGOR-A has **no** subsea/dry-tree/completion-type flag,
so "access" cannot be measured directly.  This module instead builds a
**relative** index from three real, already-computed per-field signals:

* ``WATER_DEPTH_AVG``     — deeper ⇒ harder access
* ``REC_PER_WELL_MMBBL``  — higher ⇒ concentrated, highly productive wells
* ``TOP_OPERATOR_SHARE``  — higher ⇒ concentrated operatorship

Method (deliberately assumption-light):
1. Restrict to *material* fields (``CUM_OIL_MMBBL >= 1`` and
   ``WELL_COUNT >= 3``) that have **all three** components present.
2. Convert each component to its percentile rank within that universe ([0, 1]).
3. Average the ranks (equal weight by default — an explicit, overridable
   choice) and scale to 0–100.

Honesty notes
-------------
* This is a **relative ranking**, not a measured quantity — there are no
  fabricated dollar or physical values, only ranks of real inputs.  A field at
  80 is "more deepwater-concentrated than ~80% of the material peer set", not an
  absolute access cost.
* Equal weighting is a stated assumption (pass ``weights`` to override).
* Fields outside the material/complete universe get an honest ``NaN`` index,
  never a fabricated score.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Components, each oriented so that "higher = more deepwater-concentrated hub".
ACCESS_COMPONENTS = (
    "WATER_DEPTH_AVG",
    "REC_PER_WELL_MMBBL",
    "TOP_OPERATOR_SHARE",
)

# Material-field gate (consistent with the atlas charts' universe).
MIN_CUM_OIL_MMBBL = 1.0
MIN_WELL_COUNT = 3

_INDEX_COL = "ACCESS_CONCENTRATION_INDEX"


def compute_access_index(
    result_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Add the ``ACCESS_CONCENTRATION_INDEX`` (0–100) column.

    Returns a **copy** of ``result_df``; the input is never mutated.  The index
    is the (optionally weighted) average percentile rank of
    :data:`ACCESS_COMPONENTS`, computed over the material fields that have all
    three components, scaled to 0–100.  Fields outside that universe get
    ``NaN``.

    Parameters
    ----------
    result_df:
        Per-field atlas result.  Must contain the component columns plus
        ``CUM_OIL_MMBBL`` and ``WELL_COUNT`` for the material gate; missing
        columns yield an all-``NaN`` index (honest, no crash).
    weights:
        Optional ``{component: weight}``.  Defaults to equal weights.  Only the
        listed components are used; weights are normalized to sum to 1.
    """
    out = result_df.copy()

    required = set(ACCESS_COMPONENTS) | {"CUM_OIL_MMBBL", "WELL_COUNT"}
    if out.empty or not required.issubset(out.columns):
        if not required.issubset(out.columns):
            logger.warning(
                "Access index skipped — missing columns %s",
                sorted(required - set(out.columns)),
            )
        out[_INDEX_COL] = pd.Series(np.nan, index=out.index, dtype="float64")
        return out

    # Resolve and normalize weights.
    if weights:
        w = {c: float(weights.get(c, 0.0)) for c in ACCESS_COMPONENTS}
        total = sum(w.values())
        if total <= 0:
            logger.warning("Access index weights sum to 0 — using equal weights.")
            w = {c: 1.0 / len(ACCESS_COMPONENTS) for c in ACCESS_COMPONENTS}
        else:
            w = {c: v / total for c, v in w.items()}
    else:
        w = {c: 1.0 / len(ACCESS_COMPONENTS) for c in ACCESS_COMPONENTS}

    # Material + complete universe.
    cum_oil = pd.to_numeric(out["CUM_OIL_MMBBL"], errors="coerce")
    wells = pd.to_numeric(out["WELL_COUNT"], errors="coerce")
    comp = {c: pd.to_numeric(out[c], errors="coerce") for c in ACCESS_COMPONENTS}

    universe = (cum_oil >= MIN_CUM_OIL_MMBBL) & (wells >= MIN_WELL_COUNT)
    for series in comp.values():
        universe &= series.notna()

    index = pd.Series(np.nan, index=out.index, dtype="float64")
    n = int(universe.sum())
    if n == 0:
        logger.warning("Access index: no material fields with all components.")
        out[_INDEX_COL] = index
        return out

    # Percentile-rank each component within the universe, then weighted-average.
    score = pd.Series(0.0, index=out.index[universe])
    for c, series in comp.items():
        ranks = series[universe].rank(pct=True)
        score = score + w[c] * ranks
    index.loc[universe] = (score * 100.0).round(1)

    out[_INDEX_COL] = index
    logger.info(
        "Access/concentration index computed for %d material fields "
        "(equal-weight percentile rank of %s).",
        n,
        ", ".join(ACCESS_COMPONENTS),
    )
    return out
