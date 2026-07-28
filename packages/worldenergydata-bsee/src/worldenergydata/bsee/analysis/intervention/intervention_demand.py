# ABOUTME: Intervention DEMAND metrics by MODU water-depth band from BSEE WAR (worldenergydata #630).
# ABOUTME: Per band — intervention rig-days/year (summed WAR durations) and interventions-per-well rate; all band-resolved figures are FLOORS (WAR WATER_DEPTH ~6% filled, durations partial).

"""Intervention demand metrics by water-depth band — rig-days + rate.

Epic #591 / #582 wants the *demand* intensity of subsea well intervention,
expressed in the MODU/vessel-servicing water-depth bands the #583 inventory
defines. Where ``war_vessel_crossref`` (#597) answered *who serviced what*
(supply: rigs/vessels per band), this module answers *how much servicing
effort* each band carries:

* **intervention rig-days/year** — sum of WAR activity durations
  (``WAR_END_DT - WAR_START_DT``, inclusive day count) per calendar year per
  band. Records with a missing/unparseable end date contribute a FLOOR of one
  rig-day each (we know the activity happened, but not its span). Reported as
  recorded operational HISTORY, not a forward trend.
* **interventions-per-well** — distinct intervention records divided by
  distinct wells in the band: a per-well intervention-rate proxy.

**The load-bearing caveat — every band-resolved figure is a FLOOR (twice over).**
``WATER_DEPTH`` is populated on only ~6% of WAR rows (~94% NULL), so each band
only counts the depth-stamped subset. On top of that the rig-day total is a
floor because missing/zero-span durations are counted as a single day. The
unresolved remainder (depth-null rows, end-null rows) is reported explicitly so
the size of what is *not* captured stays visible; the module never silently
buckets a depth-null row or fabricates a duration.

The rig-day count reuses the ``(end - start).days + 1`` inclusive-day
convention from :func:`worldenergydata.bsee.analysis.war_rig_days.union_days`.
The full module does not fit here — it resolves days per API12 against an
activity code, and needs the WAR-property table joined in to do so — whereas
this module aggregates raw WAR durations across the whole table by band,
regardless of activity. Only the day-count convention is shared.

Aggregation functions are pure (operate on already-loaded DataFrames, fully
unit-testable on synthetic frames). I/O is confined to ``load_war`` and
``build_demand``.
"""

from __future__ import annotations

import pickle
import re
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import pandas as pd

# Reuse the demand-axis band scheme (#583) verbatim — never redefine bands here.
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    MODU_SERVICING_BANDS,
    classify_modu_band,
)

try:  # data-root resolution is best-effort; callers may pass an explicit path
    from worldenergydata.common.data_resolver import get_module_data_safe
except Exception:  # pragma: no cover - core package may be absent in isolation
    get_module_data_safe = None  # type: ignore[assignment]

DEPTH_COL = "WATER_DEPTH"
WELL_COL = "API_WELL_NUMBER"
START_COL = "WAR_START_DT"
END_COL = "WAR_END_DT"

_WAR_REL = Path("bin") / "war" / "mv_war_main.bin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _band_series(war: pd.DataFrame, depth_col: str = DEPTH_COL) -> pd.Series:
    """Map each WAR row to its band key (``None`` where depth is missing)."""
    depths = pd.to_numeric(war.get(depth_col), errors="coerce")
    return depths.map(classify_modu_band)


def _parse_year(value: object) -> Optional[int]:
    """Best-effort year extraction from a WAR_START_DT string/date."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    year = int(match.group(0))
    if 1947 <= year <= 2100:
        return year
    return None


def _record_rig_days(start: object, end: object) -> tuple[int, bool]:
    """Rig-days for one WAR record and whether the value is an end-date FLOOR.

    Inclusive-day convention (``(end - start).days + 1``) shared with
    :mod:`war_rig_days`. When the end date is missing, zero-span,
    negative (data error), or unparseable, the record contributes a FLOOR of one
    rig-day — we know the activity occurred but not its true span. The second
    return value is ``True`` whenever the floor fallback was used.
    """
    start_dt = pd.to_datetime(start, errors="coerce")
    end_dt = pd.to_datetime(end, errors="coerce")
    if pd.isna(start_dt):
        return 0, True
    if pd.isna(end_dt):
        return 1, True
    span = (end_dt - start_dt).days + 1
    if span <= 0:
        return 1, True
    return int(span), False


# ---------------------------------------------------------------------------
# Aggregation (pure — operate on already-loaded frames)
# ---------------------------------------------------------------------------
def duration_coverage(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    start_col: str = START_COL,
    end_col: str = END_COL,
) -> dict:
    """Report depth + end-date coverage over the WAR frame (the FLOOR basis)."""
    total = int(len(war))
    depths = pd.to_numeric(war.get(depth_col), errors="coerce")
    depth_present = int(depths.notna().sum())

    if end_col in war.columns:
        end_present = int(pd.to_datetime(war[end_col], errors="coerce").notna().sum())
    else:
        end_present = 0
    return {
        "records_total": total,
        "records_with_water_depth": depth_present,
        "records_missing_water_depth": total - depth_present,
        "depth_coverage_fraction": (round(depth_present / total, 4) if total else None),
        "records_with_end_date": end_present,
        "records_missing_end_date": total - end_present,
        "is_floor": True,
    }


def rig_days_by_band_year(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    start_col: str = START_COL,
    end_col: str = END_COL,
) -> "OrderedDict[str, OrderedDict[int, int]]":
    """Per band, summed intervention rig-days per calendar year (FLOOR).

    Only depth-stamped rows are bucketed. Each record's rig-days follow
    :func:`_record_rig_days` (end-missing -> 1-day floor). The year is taken
    from ``WAR_START_DT``; records with no parseable start year are skipped.
    """
    bands = _band_series(war, depth_col)
    work = war.copy()
    work["_band"] = bands

    out: "OrderedDict[str, OrderedDict[int, int]]" = OrderedDict(
        (k, OrderedDict()) for k in BAND_LABELS
    )
    resolved = work[work["_band"].notna()]
    starts = resolved.get(start_col)
    ends = (
        resolved.get(end_col)
        if end_col in resolved.columns
        else pd.Series([None] * len(resolved), index=resolved.index)
    )
    for idx, band_key in resolved["_band"].items():
        if band_key not in out:
            continue
        year = _parse_year(starts.loc[idx]) if starts is not None else None
        if year is None:
            continue
        days, _ = _record_rig_days(
            starts.loc[idx] if starts is not None else None, ends.loc[idx]
        )
        if days <= 0:
            continue
        per_year = out[band_key]
        per_year[year] = per_year.get(year, 0) + days

    for key in out:
        out[key] = OrderedDict(sorted(out[key].items()))
    return out


def demand_by_band(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    well_col: str = WELL_COL,
    start_col: str = START_COL,
    end_col: str = END_COL,
) -> "OrderedDict[str, dict]":
    """Per band: rig-days/year, total rig-days, distinct wells, rate (FLOOR).

    ``interventions_per_well`` = depth-stamped intervention records / distinct
    wells in the band — a per-well intervention-rate proxy. Every figure is a
    FLOOR (depth-stamped subset only; rig-days floored on missing durations).
    """
    bands = _band_series(war, depth_col)
    work = war.copy()
    work["_band"] = bands

    by_year = rig_days_by_band_year(war, depth_col, start_col, end_col)

    records = OrderedDict((k, 0) for k in BAND_LABELS)
    wells_acc: "OrderedDict[str, set]" = OrderedDict((k, set()) for k in BAND_LABELS)
    resolved = work[work["_band"].notna()]
    for band_key, group in resolved.groupby("_band", sort=False):
        if band_key not in records:
            continue
        records[band_key] = int(len(group))
        if well_col in group.columns:
            wells_acc[band_key] = {
                str(w).strip() for w in group[well_col].dropna() if str(w).strip()
            }

    out: "OrderedDict[str, dict]" = OrderedDict()
    for key, label in BAND_LABELS.items():
        year_map = {int(y): int(d) for y, d in by_year[key].items()}
        total_days = int(sum(year_map.values()))
        interventions = int(records[key])
        distinct_wells = int(len(wells_acc[key]))
        rate = round(interventions / distinct_wells, 3) if distinct_wells else None
        out[key] = {
            "label": label,
            "intervention_rig_days_by_year": dict(sorted(year_map.items())),
            "total_rig_days_floor": total_days,
            "distinct_wells": distinct_wells,
            "interventions": interventions,
            "interventions_per_well": rate,
            "modu_servicing": key in MODU_SERVICING_BANDS,
            "is_floor": True,
        }
    return out


def summarize(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    well_col: str = WELL_COL,
    start_col: str = START_COL,
    end_col: str = END_COL,
) -> dict:
    """Assemble the full intervention-demand result dict from a WAR frame (pure)."""
    coverage = duration_coverage(war, depth_col, start_col, end_col)
    bands = demand_by_band(war, depth_col, well_col, start_col, end_col)

    modu_rig_days = sum(
        bands[k]["total_rig_days_floor"] for k in MODU_SERVICING_BANDS if k in bands
    )
    modu_wells = sum(
        bands[k]["distinct_wells"] for k in MODU_SERVICING_BANDS if k in bands
    )

    return {
        "depth_coverage": coverage,
        "bands": {k: v for k, v in bands.items()},
        "totals": {
            "modu_band_rig_days_floor": int(modu_rig_days),
            "modu_band_distinct_wells_floor": int(modu_wells),
            "note": "Sums over MODU-servicing bands only; FLOOR (depth-stamped subset).",
        },
        "caveats": [
            "FLOOR: WATER_DEPTH is populated on only ~6% of WAR rows (~94% NULL); "
            "every band-resolved count is a hard lower bound, not a total.",
            "FLOOR: rig-days use (WAR_END_DT - WAR_START_DT).days + 1; records with a "
            "missing/zero/negative span are counted as a single day (a floor), so "
            "total_rig_days_floor understates true effort.",
            "Depth-null rows are excluded from bands and reported under "
            "depth_coverage.records_missing_water_depth — not silently bucketed.",
            "interventions_per_well counts depth-stamped WAR records as intervention "
            "events; multiple WAR reports can belong to one campaign, so the rate is "
            "an upper proxy on the depth-stamped subset.",
            "intervention_rig_days_by_year is recorded operational HISTORY (deepwater "
            "workovers flat-to-declining per epic #582 / digitalmodel #890), NOT a "
            "forward demand trend.",
        ],
        "provenance": {
            "war_source": "BSEE war/mv_war_main.bin (well-activity reports)",
            "rig_day_convention": (
                "(WAR_END_DT - WAR_START_DT).days + 1, inclusive; shared with "
                "war_rig_days.union_days"
            ),
            "band_scheme_ft": dict(BAND_LABELS),
            "issue": "worldenergydata#630 (epic #591)",
        },
    }


# ---------------------------------------------------------------------------
# Loaders / build (I/O)
# ---------------------------------------------------------------------------
def _resolve_war_path(
    data_dir: Optional[Path] = None, war_path: Optional[Path] = None
) -> Path:
    if war_path is not None:
        return Path(war_path)
    if data_dir is not None:
        return Path(data_dir) / _WAR_REL
    if get_module_data_safe is not None:
        return Path(get_module_data_safe("bsee")) / _WAR_REL
    raise RuntimeError(
        "No war_path/data_dir given and worldenergydata.common.data_resolver "
        "is unavailable."
    )


def load_war(
    data_dir: Optional[Path] = None, war_path: Optional[Path] = None
) -> pd.DataFrame:
    """Load the WAR main table (one row per well-activity report)."""
    path = _resolve_war_path(data_dir, war_path)
    with open(path, "rb") as fh:
        obj = pickle.load(fh)
    df = obj if isinstance(obj, pd.DataFrame) else pd.DataFrame(obj)
    if DEPTH_COL not in df.columns:
        raise KeyError(f"{DEPTH_COL} not in {path} (cols={list(df.columns)})")
    return df


def build_demand(
    data_dir: Optional[Path] = None,
    war_path: Optional[Path] = None,
    out_path: Optional[Path] = None,
) -> dict:
    """Load WAR, build the per-band intervention-demand result, optionally write YAML.

    Returns the result dict (see :func:`summarize`). All band-resolved figures
    are FLOOR-labelled in the output.
    """
    war = load_war(data_dir=data_dir, war_path=war_path)
    result = summarize(war)

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result
