"""ABOUTME: Descriptive, leave-one-out drilling-days versus TVD comparisons.
ABOUTME: Reuses the saved drilling insight CSV; never supplies acceptance limits.

Source: NIST/SEMATECH e-Handbook of Statistical Methods, section 4.4.3.1,
web edition retrieved 2026-10-19,
straight-line least squares estimates of slope and intercept:
https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm

The workbook-derived durations include partial-scope intervals. A fitted ratio
is descriptive, not evidence of learning, efficiency, or engineering acceptance.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

COLUMNS = {"api_well_number", "max_well_bore_tvd_ft", "drilling_days"}
LIMITATION = (
    "Workbook-derived days; partial-scope intervals included; descriptive only, "
    "not an acceptance criterion or a causal learning measure."
)


def load_benchmark_rows(path: Path) -> list[dict]:
    """Read the saved insight without converting API identifiers to floats."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError("Drilling benchmark CSV lacks required columns")
        return list(reader)


def _api(value) -> str | None:
    """Accept integer API keys and the workbook export's decimal-zero suffix."""
    text = str(value).strip()
    text = text.removesuffix(".0")
    return text if text.isascii() and text.isdigit() else None


def _positive(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    # Zero cannot be a divisor or a positive-duration/depth observation.
    return number if math.isfinite(number) and number > 0 else None


def benchmark_well(well: dict, rows: list[dict] | tuple = ()) -> dict:
    """Compare a matching well to other unique API rows within their depth range.

    Two distinct peer depths are the algebraic minimum for slope/intercept,
    not a statistical adequacy threshold. No extrapolation is supplied.
    """
    result = {
        "status": "NOT_EVALUATED",
        "reason": "",
        "peer_count": 0,
        "fitted_days": None,
        "observed_to_fitted": None,
        "limitation": LIMITATION,
    }

    def unavailable(reason):
        return dict(result, reason=reason)

    api = _api(well.get("api"))
    depth = _positive(well.get("max_tvd_ft"))
    days = _positive(well.get("drilling_rig_days"))
    if api is None or depth is None or days is None:
        return unavailable("API, positive TVD and positive drilling days are required")
    keyed = {}
    for row in rows:
        key = _api(row.get("api_well_number"))
        if key is None:
            continue
        if key in keyed:
            return unavailable("Saved benchmark contains duplicate API keys")
        keyed[key] = row
    target = keyed.pop(api, None)
    if target is None:
        return unavailable("No matching API in the saved drilling insight CSV")
    if (
        _positive(target.get("max_well_bore_tvd_ft")) != depth
        or _positive(target.get("drilling_days")) != days
    ):
        return unavailable("Stage facts and saved benchmark TVD or days disagree")
    peers = [
        (x, y)
        for row in keyed.values()
        if (x := _positive(row.get("max_well_bore_tvd_ft"))) is not None
        and (y := _positive(row.get("drilling_days"))) is not None
    ]
    result["peer_count"] = len(peers)
    return _fit_comparison(depth, days, peers, result)


def _fit_comparison(depth, days, peers, result):
    """Evaluate the NIST straight-line formula, retaining explicit failure state."""

    def unavailable(reason):
        return dict(result, reason=reason)

    # A straight line has two parameters: NIST section 4.4.3.1, cited above.
    if len(peers) < 2:
        return unavailable("At least two valid peers with distinct TVDs are required")
    xs, ys = zip(*peers)
    if not min(xs) <= depth <= max(xs):
        return unavailable("Target TVD lies outside the peer depth range")
    try:
        xbar, ybar = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
        # NIST section 4.4.3.1: b=Sxy/Sxx, a=ybar-b*xbar, yhat=a+b*x.
        sxx = math.fsum((x - xbar) ** 2 for x in xs)
        if sxx == 0:
            return unavailable("Peer TVDs are constant; slope cannot be calculated")
        slope = math.fsum((x - xbar) * (y - ybar) for x, y in peers) / sxx
        fitted = ybar + slope * (depth - xbar)
    except (OverflowError, ValueError):
        return unavailable("Peer arithmetic exceeds finite numeric range")
    if not math.isfinite(fitted) or fitted <= 0:
        return unavailable("Fitted drilling days are not finite and positive")
    ratio = days / fitted
    if not math.isfinite(ratio):
        return unavailable("Observed-to-fitted ratio exceeds finite numeric range")
    return dict(
        result,
        status="EVALUATED",
        fitted_days=fitted,
        observed_to_fitted=ratio,
    )
