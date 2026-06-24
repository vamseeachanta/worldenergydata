"""Per-field netback / break-even *sensitivity* (deterministic, pure-derived).

This is the Rank-3 economics deliverable.  It is explicitly a **sensitivity**,
not a point NPV: per the scoping memo, a true NPV cannot generalize across the
basin because there are no hand-curated per-field development costs.  What we
*can* state honestly combines:

* **Real revenue** — ``GROSS_OIL_REVENUE_MM_USD`` (monthly oil x real WTI),
  already on the atlas result.
* **A real, labeled royalty assumption** — the deepwater GoM statutory default
  (:data:`ROYALTY_RATE_DEFAULT`).  This is an *applied assumption*, not a
  per-lease royalty lookup; it is overridable.
* **A transparent opex band** — a *range* (:data:`OPEX_BAND_LOW_USD_BBL` to
  :data:`OPEX_BAND_HIGH_USD_BBL`), never a single fabricated opex number.

Everything here is pure-derived from columns already on the result DataFrame —
**no new data file is loaded** and there is no I/O.  Divisions are guarded:
fields missing ``GROSS_OIL_REVENUE_MM_USD`` or with non-positive
``CUM_OIL_MMBBL`` get an honest ``NaN`` in the derived columns, never a
fabricated zero.

Honesty notes
-------------
* **Sensitivity, not a forecast or NPV.**  The netback band is a what-if range
  over the opex assumption; it excludes capex and is oil-only.  Decommissioning
  liability is reported separately (it is not netted in here).
* **Royalty is an assumption.**  18.75% is the deepwater statutory default
  applied uniformly, not a per-lease royalty.  Override via ``royalty=``.
* **Opex is a band.**  We never emit a single point opex; ``$5/bbl`` and
  ``$25/bbl`` bracket a transparent sensitivity range.  Override via
  ``opex_low=`` / ``opex_high=``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --- Labeled, overridable assumptions -------------------------------------
# Deepwater GoM statutory royalty default. This is an APPLIED ASSUMPTION used
# uniformly across fields, NOT a per-lease royalty lookup. Override via the
# ``royalty`` argument.
ROYALTY_RATE_DEFAULT = 0.1875

# Transparent opex sensitivity BAND ($/bbl). We never emit a single fabricated
# opex number; these two bracket a what-if range. Override via the
# ``opex_low`` / ``opex_high`` arguments.
OPEX_BAND_LOW_USD_BBL = 5.0
OPEX_BAND_HIGH_USD_BBL = 25.0

# Source columns consumed off the result DataFrame.
_REVENUE_COL = "GROSS_OIL_REVENUE_MM_USD"
_OIL_COL = "CUM_OIL_MMBBL"

# Derived columns this module adds (in output order).
_DERIVED_COLUMNS = [
    "REALIZED_OIL_PRICE_USD_BBL",
    "NET_REVENUE_AFTER_ROYALTY_MM_USD",
    "OPEX_LOW_MM_USD",
    "OPEX_HIGH_MM_USD",
    "NETBACK_HIGH_MM_USD",
    "NETBACK_LOW_MM_USD",
    "BREAKEVEN_OPEX_USD_BBL",
]


def compute_field_netback(
    result_df: pd.DataFrame,
    royalty: float = ROYALTY_RATE_DEFAULT,
    opex_low: float = OPEX_BAND_LOW_USD_BBL,
    opex_high: float = OPEX_BAND_HIGH_USD_BBL,
) -> pd.DataFrame:
    """Add per-field netback / break-even sensitivity columns (pure-derived).

    Returns a **copy** of ``result_df`` with the derived columns appended;
    ``result_df`` is never mutated.  No data file is loaded.

    Derived columns (all in $MM except the two $/bbl columns)::

        REALIZED_OIL_PRICE_USD_BBL       = gross_rev / cum_oil   (both $MM/MMBBL)
        NET_REVENUE_AFTER_ROYALTY_MM_USD = gross_rev x (1 - royalty)
        OPEX_LOW_MM_USD                  = opex_low  x cum_oil
        OPEX_HIGH_MM_USD                 = opex_high x cum_oil
        NETBACK_HIGH_MM_USD              = net_rev - OPEX_LOW   (low opex -> high)
        NETBACK_LOW_MM_USD               = net_rev - OPEX_HIGH
        BREAKEVEN_OPEX_USD_BBL           = realized_price x (1 - royalty)

    Honest nulls: rows missing :data:`_REVENUE_COL` or with non-positive
    :data:`_OIL_COL` get ``NaN`` in the revenue-derived columns (never a
    fabricated ``0``).  The opex columns depend only on oil, so for a field
    with zero oil they are a legitimate ``0`` (no oil to operate), not a guess.

    Parameters
    ----------
    result_df:
        AllFieldsRunner+revenue result with ``GROSS_OIL_REVENUE_MM_USD`` and
        ``CUM_OIL_MMBBL`` columns.  Missing columns are tolerated (the
        corresponding outputs are all-``NaN``).
    royalty:
        Royalty fraction in ``[0, 1)`` applied uniformly (assumption).
    opex_low, opex_high:
        Opex band endpoints in ``$/bbl`` (sensitivity range).

    Returns
    -------
    pd.DataFrame
        Copy of ``result_df`` with :data:`_DERIVED_COLUMNS` appended.
    """
    out = result_df.copy()

    # Empty frame: still declare the derived columns (correctly typed) so
    # downstream callers can rely on them existing.
    if out.empty:
        for col in _DERIVED_COLUMNS:
            out[col] = pd.Series(dtype="float64")
        return out

    n = len(out)
    nan_series = pd.Series(np.nan, index=out.index, dtype="float64")

    # Real revenue (honest NaN where the source column is absent or null).
    if _REVENUE_COL in out.columns:
        gross_rev = pd.to_numeric(out[_REVENUE_COL], errors="coerce")
    else:
        gross_rev = nan_series.copy()

    # Cumulative oil; non-positive oil is treated as "missing" for any ratio
    # (can't realize a price on zero/negative oil) -> guarded to NaN.
    if _OIL_COL in out.columns:
        cum_oil = pd.to_numeric(out[_OIL_COL], errors="coerce")
    else:
        cum_oil = nan_series.copy()
    oil_positive = cum_oil > 0
    oil_for_ratio = cum_oil.where(oil_positive)  # NaN where not positive

    # Realized price: revenue / oil (both in millions -> $/bbl). Guarded.
    realized = gross_rev / oil_for_ratio

    # Net revenue after royalty (royalty is a labeled assumption).
    net_rev = gross_rev * (1.0 - royalty)

    # Opex band ($MM = $/bbl x MMBBL). Depends only on oil; for zero oil this
    # is a legitimate 0 (nothing to operate), not a fabricated figure. Negative
    # oil is nonsensical -> guard to NaN.
    oil_for_opex = cum_oil.where(cum_oil >= 0)
    opex_low_mm = opex_low * oil_for_opex
    opex_high_mm = opex_high * oil_for_opex

    # Netback band: low opex -> high netback, and vice versa.
    netback_high = net_rev - opex_low_mm
    netback_low = net_rev - opex_high_mm

    # Break-even opex ($/bbl) at which netback == 0.
    breakeven = realized * (1.0 - royalty)

    out["REALIZED_OIL_PRICE_USD_BBL"] = realized
    out["NET_REVENUE_AFTER_ROYALTY_MM_USD"] = net_rev
    out["OPEX_LOW_MM_USD"] = opex_low_mm
    out["OPEX_HIGH_MM_USD"] = opex_high_mm
    out["NETBACK_HIGH_MM_USD"] = netback_high
    out["NETBACK_LOW_MM_USD"] = netback_low
    out["BREAKEVEN_OPEX_USD_BBL"] = breakeven

    assert len(out) == n  # pure-derived: no rows added or dropped
    return out
