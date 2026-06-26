# ABOUTME: Planned/projected GoM subsea-wells overlay (worldenergydata #587, child of epic #582).
# ABOUTME: Loads an on-record FID register of announced US GoM subsea developments and triangulates a P10/P50/P90 new-wells-per-year projection against analyst tree-installation rates.

"""Planned / projected Gulf-of-Mexico subsea-wells overlay — the forward axis.

Where ``well_inventory_by_band`` (#583) counts the *installed* subsea-well base,
this module supplies the *forward* view epic #582 needs: a structured register
of **announced** US Gulf-of-Mexico developments resolving to new subsea wells by
*year* and by *water-depth band*, with explicit uncertainty.

Two confidence tiers are carried, and never silently mixed:

* **on_record** — itemised, sanctioned-by-FID projects (operator/wells/first-oil
  taken from public announcements). Summed, these form a *floor*: a hard lower
  bound on new wells per year. Later infill phases that are not yet itemised are
  deliberately *not* counted, so the floor under-states reality.
* **projected** — an analyst installation rate (~12-20 subsea trees/wells per
  year for the GoM, ±15%; Westwood Subsea Tree Tracker, Rystad). This brackets
  the on-record floor to give P10/P50/P90 new-wells-per-year.

The projection is a deliberately simple, transparent **triangulation**, not a
stochastic model:

    P50[year] = on-record FID floor for that year (itemised, sanctioned)
    P10[year] = min(P50, analyst_low)    analyst_low  = central * (1 - pct)
    P90[year] = max(P50, analyst_high)   analyst_high = central * (1 + pct)

The min/max clamps guarantee ``P10 <= P50 <= P90`` for every year even when the
itemised floor for a year already exceeds the analyst band (i.e. the analyst
rate is then known to under-state that year).

The water-depth band of each project is placed with the **same** scheme as the
installed-base inventory — ``classify_modu_band`` from
``well_inventory_by_band`` — so the forward and installed views are directly
comparable. Projects whose host water depth could not be sourced are placed in
a ``deepwater_unknown`` bucket rather than guessed.

Trion (Chevron, Mexican waters) is excluded: this overlay is US GoM only.

Numbers live in a reviewable YAML register
(``data/planned_subsea_wells.yml``) so downstream consumers read data, not
hard-coded constants.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Optional

from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    classify_modu_band,
)

# Bucket for projects with no sourced host water depth — kept distinct from the
# real bands so unknowns are never silently folded into a depth class.
UNKNOWN_BAND = "deepwater_unknown"

_REGISTER_REL = Path("data") / "planned_subsea_wells.yml"


# ---------------------------------------------------------------------------
# Loaders (thin I/O; aggregation below operates on plain dicts and is testable)
# ---------------------------------------------------------------------------
def _default_register_path() -> Path:
    return Path(__file__).resolve().parent / _REGISTER_REL


def load_register(path: Optional[Path] = None) -> dict:
    """Load the planned-subsea-wells YAML register.

    Returns the parsed mapping with at least ``on_record_projects`` (list) and
    ``analyst_rate`` (mapping). Raises if the file is missing.
    """
    import yaml

    register_path = Path(path) if path is not None else _default_register_path()
    with open(register_path, "r") as fh:
        data = yaml.safe_load(fh) or {}
    data.setdefault("on_record_projects", [])
    data.setdefault("analyst_rate", {})
    return data


def on_record_projects(register: dict) -> list:
    """Return the list of on-record (FID) project records."""
    return list(register.get("on_record_projects", []))


# ---------------------------------------------------------------------------
# Band placement
# ---------------------------------------------------------------------------
def project_band(project: dict) -> str:
    """Return the water-depth band key for a project.

    Uses the project's explicit ``water_depth_band`` if present and non-null;
    otherwise derives it from ``water_depth_ft`` via the shared
    ``classify_modu_band``. Falls back to :data:`UNKNOWN_BAND` when depth is
    unknown, so unknowns are counted explicitly.
    """
    band = project.get("water_depth_band")
    if band:
        return band
    derived = classify_modu_band(project.get("water_depth_ft"))
    return derived if derived is not None else UNKNOWN_BAND


# ---------------------------------------------------------------------------
# Aggregations over on-record projects
# ---------------------------------------------------------------------------
def wells_by_year(register: dict) -> "OrderedDict[int, int]":
    """Sum on-record new subsea wells by first-oil year (ascending)."""
    totals: dict[int, int] = {}
    for proj in on_record_projects(register):
        year = proj.get("first_oil_year")
        wells = proj.get("wells") or 0
        if year is None:
            continue
        totals[int(year)] = totals.get(int(year), 0) + int(wells)
    return OrderedDict((y, totals[y]) for y in sorted(totals))


def wells_by_band(register: dict) -> "OrderedDict[str, int]":
    """Sum on-record new subsea wells by water-depth band (display order)."""
    counts: "OrderedDict[str, int]" = OrderedDict((k, 0) for k in BAND_LABELS)
    counts[UNKNOWN_BAND] = 0
    for proj in on_record_projects(register):
        band = project_band(proj)
        wells = int(proj.get("wells") or 0)
        counts[band] = counts.get(band, 0) + wells
    return counts


def total_on_record_wells(register: dict) -> int:
    """Total itemised on-record new subsea wells across all projects."""
    return sum(int(p.get("wells") or 0) for p in on_record_projects(register))


# ---------------------------------------------------------------------------
# Projection (triangulation — see module docstring)
# ---------------------------------------------------------------------------
def _analyst_band(register: dict) -> tuple[float, float, float]:
    """Return (low, central, high) analyst wells/yr from the register.

    ``central`` defaults to the midpoint of the low/high tree-per-year range if
    not given explicitly; the band is widened by ``uncertainty_pct`` (±%).
    """
    rate = register.get("analyst_rate", {}) or {}
    low_in = rate.get("trees_per_year_low")
    high_in = rate.get("trees_per_year_high")
    central = rate.get("central")
    if central is None and low_in is not None and high_in is not None:
        central = (float(low_in) + float(high_in)) / 2.0
    if central is None:
        central = 0.0
    pct = float(rate.get("uncertainty_pct", 0)) / 100.0
    low = float(central) * (1.0 - pct)
    high = float(central) * (1.0 + pct)
    return low, float(central), high


def _forecast_years(register: dict, years: Optional[Iterable[int]]) -> list:
    if years is not None:
        return sorted({int(y) for y in years})
    by_year = wells_by_year(register)
    return list(by_year.keys())


def projection_pxx(
    register: dict, years: Optional[Iterable[int]] = None
) -> "OrderedDict[int, dict]":
    """Triangulate P10/P50/P90 new subsea wells per year.

    ``P50`` is the on-record FID floor for the year; ``P10``/``P90`` bracket it
    with the analyst ±% band (clamped so ``P10 <= P50 <= P90`` always holds).
    See the module docstring for the method. All values are integers (wells).

    Pass ``years`` to force a specific forecast horizon; by default the span of
    on-record first-oil years is used.
    """
    analyst_low, _central, analyst_high = _analyst_band(register)
    floor_by_year = wells_by_year(register)
    out: "OrderedDict[int, dict]" = OrderedDict()
    for year in _forecast_years(register, years):
        p50 = int(floor_by_year.get(year, 0))
        p10 = int(round(min(p50, analyst_low)))
        p90 = int(round(max(p50, analyst_high)))
        out[year] = {
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "on_record_floor": p50,
            "confidence": "on_record_floor_with_projected_bracket",
        }
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_overlay(
    out_path: Optional[Path] = None,
    register_path: Optional[Path] = None,
) -> dict:
    """Assemble the overlay summary; optionally write it to YAML.

    Returns a dict with ``by_year``, ``by_band``, ``projection`` (per-year
    P10/P50/P90), totals, the analyst-rate provenance and the standing caveats.
    """
    register = load_register(register_path)
    analyst_low, central, analyst_high = _analyst_band(register)

    by_year = wells_by_year(register)
    by_band = wells_by_band(register)
    projection = projection_pxx(register)

    result = {
        "by_year": {int(y): int(n) for y, n in by_year.items()},
        "by_band": {k: int(v) for k, v in by_band.items()},
        "projection_per_year": {int(y): v for y, v in projection.items()},
        "totals": {
            "on_record_wells": total_on_record_wells(register),
            "on_record_projects": len(on_record_projects(register)),
        },
        "analyst_rate": {
            "wells_per_year_low": round(analyst_low, 1),
            "wells_per_year_central": round(central, 1),
            "wells_per_year_high": round(analyst_high, 1),
            "uncertainty_pct": register.get("analyst_rate", {}).get("uncertainty_pct"),
            "confidence": "projected",
            "sources": register.get("analyst_rate", {}).get("sources", []),
        },
        "band_scheme_ft": dict(BAND_LABELS),
        "method": (
            "Triangulation (not stochastic): P50 = on-record FID floor per year; "
            "P10 = min(P50, analyst_low); P90 = max(P50, analyst_high); "
            "analyst band = central * (1 +/- uncertainty_pct)."
        ),
        "provenance": {
            "register_source": "data/planned_subsea_wells.yml (author-curated, public announcements)",
            "band_module": "worldenergydata.bsee.analysis.intervention.well_inventory_by_band",
            "issue": "worldenergydata#587 (child of epic #582)",
        },
        "caveats": [
            "On-record FID register is a FLOOR: later infill/expansion phases not yet itemised are excluded, so true new-well counts will run higher.",
            "Installed subsea-well base is derived elsewhere (#583); this overlay is forward-looking only.",
            "Trion (Chevron) is excluded — it lies in Mexican waters, not the US GoM.",
            "Host water depths are sourced from public announcements where findable; projects without a sourced depth sit in 'deepwater_unknown', not a guessed band.",
            "Analyst rate (12-20 wells/yr, +/-15%) is [projected]; itemised project counts are [on_record].",
        ],
    }

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result
