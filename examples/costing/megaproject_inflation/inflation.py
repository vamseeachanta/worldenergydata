"""Cost inflation of offshore mega projects from public price indexes: the calculations.

All functions are pure and take plain dicts, so the tests can check them against hand-worked values.

Definitions used in the article (Appendix A):
- Annual value: the calendar-year mean of the monthly observations; a year counts with 11 or 12 observations
  (the CPI for October 2025 was not published, so the 2025 CPI is the mean of 11 months).
- Rebased index: annual value divided by its value in the base year (2000), times 100.
- Real index: rebased index divided by the rebased CPI, times 100. Above 100 means the cost grew faster than the
  general price level since the base year.
- Capital blend: a fixed-weight average of rebased cost indexes (weights in BLEND_WEIGHTS, an assumption, not a
  measured cost share).
- Window escalation: for a project sanctioned (final investment decision, FID) in year s with its estimate in money of
  year s, spending w_k in year s + k (k = 0 .. N-1), escalation = sum_k w_k * I(s + k) / I(s) - 1.
- Spend profile: w_k proportional to sin(pi * (k + 0.5) / N), a bell-shaped profile that peaks mid-execution.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

BASE_YEAR = 2000
LAST_FULL_YEAR = 2025

# Capital blend for an offshore development, an assumption stated in Appendix A, Table A2.
BLEND_WEIGHTS = {
    "machinery": 0.25,     # wellheads, trees, pumps, compressors, process equipment
    "shipbuilding": 0.15,  # hull and module fabrication in a yard
    "steel_mill": 0.10,    # plate and sections for structures
    "steel_pipe": 0.05,    # line pipe, casing, risers
    "drilling": 0.20,      # development drilling
    "support": 0.10,       # installation, well services and marine support
    "engineering": 0.15,   # engineering, project management, design
}
# The two-index blend used by the repository's escalation module (docs/modules/cost/ESCALATION.md).
TWO_INDEX_WEIGHTS = {"machinery": 0.5, "drilling": 0.5}

CYCLES = [  # label, start year, end year (annual means)
    ("2004-2008 boom", 2003, 2008),
    ("2014-2016 bust", 2014, 2016),
    ("2021-2023 boom", 2020, 2023),
]


def read_fred(path: Path) -> dict[str, float]:
    """Monthly observations {"YYYY-MM": value} from a FRED graph CSV; missing values (".") are skipped."""
    out = {}
    with path.open(encoding="utf-8", newline="") as fh:
        rows = csv.reader(fh)
        next(rows)
        for date, val in rows:
            if val not in ("", "."):
                out[date[:7]] = float(val)
    return out


def annual_means(monthly: dict[str, float], min_months: int = 11) -> dict[int, float]:
    """Calendar-year mean of monthly values; years with fewer than min_months observations are left out."""
    acc: dict[int, list[float]] = {}
    for ym, v in monthly.items():
        acc.setdefault(int(ym[:4]), []).append(v)
    return {y: sum(vs) / len(vs) for y, vs in sorted(acc.items()) if len(vs) >= min_months}


def rebase(series: dict, base) -> dict:
    """Series divided by its value at base, times 100."""
    b = series[base]
    return {k: 100.0 * v / b for k, v in series.items()}


def real(index: dict, cpi: dict) -> dict:
    """Rebased index over rebased CPI, times 100, on the keys both hold."""
    return {k: 100.0 * index[k] / cpi[k] for k in index if k in cpi}


def cagr(series: dict[int, float], y0: int, y1: int) -> float:
    """Compound annual growth rate between two years, as a fraction."""
    return (series[y1] / series[y0]) ** (1.0 / (y1 - y0)) - 1.0


def change(series: dict, a, b) -> float:
    """Fractional change from key a to key b."""
    return series[b] / series[a] - 1.0


def blend(rebased: dict[str, dict], weights: dict[str, float]) -> dict:
    """Fixed-weight blend of rebased indexes, on the keys all members hold. Weights must sum to 1."""
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("blend weights must sum to 1")
    keys = set.intersection(*(set(rebased[k]) for k in weights))
    return {t: sum(w * rebased[k][t] for k, w in weights.items()) for t in sorted(keys)}


def spend_profile(n: int) -> list[float]:
    """Bell-shaped spend fractions over n years, summing to 1."""
    raw = [math.sin(math.pi * (k + 0.5) / n) for k in range(n)]
    s = sum(raw)
    return [r / s for r in raw]


def window_escalation(index: dict[int, float], fid: int, n: int) -> float:
    """Escalation over an n-year execution window for a project sanctioned in year fid (fraction)."""
    w = spend_profile(n)
    return sum(w[k] * index[fid + k] / index[fid] for k in range(n)) - 1.0


def escalation_by_fid(index: dict[int, float], n: int, last_year: int = LAST_FULL_YEAR) -> dict[int, float]:
    """Window escalation for every FID year whose whole window lies inside the index (to last_year)."""
    years = [y for y in index if y <= last_year]
    return {s: window_escalation(index, s, n) for s in years if all((s + k) in index and s + k <= last_year
                                                                     for k in range(n))}


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (the same rule as numpy's default), p in 0..100."""
    xs = sorted(values)
    if not xs:
        raise ValueError("no values")
    pos = (len(xs) - 1) * p / 100.0
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


def yoy(series: dict[int, float]) -> dict[int, float]:
    return {y: series[y] / series[y - 1] - 1.0 for y in series if (y - 1) in series}


def quarter_means(monthly: dict[str, float]) -> dict[str, float]:
    """Mean of each complete calendar quarter, keyed "YYYYQn"."""
    acc: dict[str, list[float]] = {}
    for ym, v in monthly.items():
        q = f"{ym[:4]}Q{(int(ym[5:7]) - 1) // 3 + 1}"
        acc.setdefault(q, []).append(v)
    return {q: sum(v) / len(v) for q, v in sorted(acc.items()) if len(v) == 3}


def read_ucci_quoted(path: Path) -> list[dict]:
    """Quoted Upstream Capital Costs Index values (2000 = 100) with their quarter, citation and quoted words.

    The quarter is read from the row note ("Q3 2008"); a row whose note gives a six-month period ending in a month
    takes the quarter of that month.
    """
    out = []
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["COMPONENT"] != "index_ucci":
                continue
            note = r["NOTES"]
            m = re.search(r"Q([1-4])[ -](\d{4})", note)
            if m:
                q = f"{m.group(2)}Q{m.group(1)}"
            else:
                m2 = re.search(r"ending (\d{1,2}) (\w{3})\w* (\d{4})", note)
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                if not m2:
                    raise ValueError(f"no quarter in note: {note!r}")
                q = f"{m2.group(3)}Q{months.index(m2.group(2)) // 3 + 1}"
            out.append({"quarter": q, "value": float(r["VALUE"]), "source": r["SOURCE_TITLE"],
                        "url": r["SOURCE_URL"], "quoted": r["QUOTED_TEXT"], "accessed": r["ACCESSED_DATE"]})
    return sorted(out, key=lambda d: d["quarter"])
