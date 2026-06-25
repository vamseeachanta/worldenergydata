# ABOUTME: Subsea-well inventory bucketed into the MODU/vessel-servicing water-depth bands (worldenergydata #583).
# ABOUTME: Counts existing GoM subsea wells per band from the BSEE subsea-borehole registry and reconciles against the full well population (sbwd).

"""Well inventory by water-depth band — the MODU-servicing demand axis.

Builds the structured inventory the subsea-intervention/maintenance database
(epic #582) needs: existing Gulf-of-Mexico subsea wells bucketed into the
water-depth bands that decide *what asset can service them*, per Chuck White's
"well maintenance" request:

    < 500 ft        shelf (jack-up / platform serviceable — not MODU-required)
    500 – 3,000 ft  shelf -> deepwater transition
    3,000 – 5,000 ft  deepwater
    5,000 – 10,000 ft ultra-deepwater (BOEM >= 5,000 ft)
    > 10,000 ft     beyond the current band of interest

Two BSEE sources are combined:

* **Subsea-borehole registry** (``permstruc/mv_subsea_boreholes.bin``) — the
  authoritative *subsea-only* well list (each row carries ``WATER_DEPTH`` in
  feet). This is the clean "on record" count.
* **Offshore-statistics wells** (``offshorestats/mv_sbwd_wells.bin``) — the
  full well population (~29k distinct wells with depth), used to report the
  subsea *share* of wells in each band and to surface a likely registry
  undercount.

The registry has no ``API_WELL_NUMBER``, so it cannot be row-joined to the
API-keyed tables; the reconciliation is therefore a *population* comparison
(subsea registry count vs. all wells in the band), not a row-level merge. That
limitation, the registry undercount, and the sparse subsea flag in
``ST_BP_and_tree_height.csv`` are tracked in #589 (data-quality guardrail).

Numbers are externalised to a reviewable YAML so downstream consumers
(#510 calibration, digitalmodel #891 demand model, the #588 brief) read data,
not hard-coded constants.
"""

from __future__ import annotations

import pickle
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

try:  # data-root resolution is best-effort; callers may pass an explicit dir
    from worldenergydata.common.data_resolver import get_module_data_safe
except Exception:  # pragma: no cover - core package may be absent in isolation
    get_module_data_safe = None  # type: ignore[assignment]

FEET_PER_METRE = 3.280839895

# Ordered (upper_edge_ft, band_key). A depth belongs to the first band whose
# upper edge it does not exceed; anything above the last edge is the open top
# band. Edges match Chuck's email exactly.
_BAND_EDGES: tuple[tuple[float, str], ...] = (
    (500.0, "shelf_lt_500"),
    (3000.0, "band_500_3000"),
    (5000.0, "band_3000_5000"),
    (10000.0, "band_5000_10000"),
)
_TOP_BAND = "band_gt_10000"

# Human-facing labels, in display order.
BAND_LABELS: "OrderedDict[str, str]" = OrderedDict(
    [
        ("shelf_lt_500", "< 500 ft (shelf)"),
        ("band_500_3000", "500-3,000 ft"),
        ("band_3000_5000", "3,000-5,000 ft"),
        ("band_5000_10000", "5,000-10,000 ft"),
        ("band_gt_10000", "> 10,000 ft"),
    ]
)

# Bands that require a MODU or a specialised vessel to service (i.e. not the
# shelf band). Used by the serviceability matrix (#586).
MODU_SERVICING_BANDS: tuple[str, ...] = (
    "band_500_3000",
    "band_3000_5000",
    "band_5000_10000",
    "band_gt_10000",
)

_REGISTRY_REL = Path("bin") / "permstruc" / "mv_subsea_boreholes.bin"
_SBWD_REL = Path("bin") / "offshorestats" / "mv_sbwd_wells.bin"


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify_modu_band(depth_ft: Optional[float]) -> Optional[str]:
    """Return the MODU-servicing band key for a water depth in feet.

    Returns ``None`` for missing/non-numeric depths so callers can count
    ``unknown`` explicitly rather than silently mis-bucketing.
    """
    if depth_ft is None or pd.isna(depth_ft):
        return None
    try:
        d = float(depth_ft)
    except (TypeError, ValueError):
        return None
    if d < 0:
        return None
    for upper, key in _BAND_EDGES:
        if d < upper:
            return key
    return _TOP_BAND


def _zeroed_bands() -> "OrderedDict[str, int]":
    return OrderedDict((k, 0) for k in BAND_LABELS)


def band_counts(depths_ft: Iterable[float]) -> "OrderedDict[str, int]":
    """Count depths into the ordered band scheme (plus an ``unknown`` bucket)."""
    counts = _zeroed_bands()
    counts["unknown"] = 0
    for d in depths_ft:
        key = classify_modu_band(d)
        counts["unknown" if key is None else key] += 1
    return counts


# ---------------------------------------------------------------------------
# Aggregation (pure — operate on already-loaded frames, fully unit-testable)
# ---------------------------------------------------------------------------
def _depth_stats(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"count": 0, "min_ft": None, "max_ft": None, "median_ft": None}
    return {
        "count": int(s.size),
        "min_ft": round(float(s.min()), 1),
        "max_ft": round(float(s.max()), 1),
        "median_ft": round(float(s.median()), 1),
    }


def subsea_inventory_by_band(
    registry: pd.DataFrame, depth_col: str = "WATER_DEPTH"
) -> dict:
    """Bucket the subsea-borehole registry into bands; return counts + stats."""
    depths = pd.to_numeric(registry[depth_col], errors="coerce")
    counts = band_counts(depths)
    return {"counts": dict(counts), "stats": _depth_stats(depths)}


def well_population_by_band(
    wells: pd.DataFrame, depth_col: str = "WATER_DEPTH"
) -> "OrderedDict[str, int]":
    """Bucket the full well population (one depth per well) into bands."""
    return band_counts(pd.to_numeric(wells[depth_col], errors="coerce"))


def reconcile(subsea_inv: dict, population: "OrderedDict[str, int]") -> "OrderedDict[str, dict]":
    """Per band: subsea registry count, total wells, and subsea share."""
    out: "OrderedDict[str, dict]" = OrderedDict()
    subsea_counts = subsea_inv["counts"]
    for key, label in BAND_LABELS.items():
        subsea = int(subsea_counts.get(key, 0))
        total = int(population.get(key, 0))
        share = round(subsea / total, 4) if total else None
        out[key] = {
            "label": label,
            "subsea_wells_on_record": subsea,
            "total_wells_in_band": total,
            "subsea_share": share,
            "modu_servicing": key in MODU_SERVICING_BANDS,
        }
    return out


# ---------------------------------------------------------------------------
# Loaders (I/O — resolve BSEE data, kept thin so aggregation stays testable)
# ---------------------------------------------------------------------------
def _resolve_data_dir(data_dir: Optional[Path]) -> Path:
    if data_dir is not None:
        return Path(data_dir)
    if get_module_data_safe is not None:
        return Path(get_module_data_safe("bsee"))
    raise RuntimeError(
        "No data_dir given and worldenergydata.common.data_resolver is unavailable."
    )


def _read_pickle_df(path: Path) -> pd.DataFrame:
    with open(path, "rb") as fh:
        obj = pickle.load(fh)
    return obj if isinstance(obj, pd.DataFrame) else pd.DataFrame(obj)


def load_subsea_well_registry(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load the authoritative subsea-borehole registry (one row per subsea well)."""
    path = _resolve_data_dir(data_dir) / _REGISTRY_REL
    df = _read_pickle_df(path)
    if "WATER_DEPTH" not in df.columns:
        raise KeyError(f"WATER_DEPTH not in {path} (cols={list(df.columns)})")
    return df


def load_well_water_depths(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load the full well population with one water depth per API well.

    The sbwd table is depth-per-well-per-month; water depth is effectively
    static per well, so we take the median per ``API_WELL_NUMBER`` for a
    deterministic, date-independent value.
    """
    path = _resolve_data_dir(data_dir) / _SBWD_REL
    df = _read_pickle_df(path)
    df = df[["API_WELL_NUMBER", "WATER_DEPTH"]].copy()
    df["WATER_DEPTH"] = pd.to_numeric(df["WATER_DEPTH"], errors="coerce")
    df = df.dropna(subset=["WATER_DEPTH"])
    per_well = (
        df.groupby("API_WELL_NUMBER", as_index=False)["WATER_DEPTH"].median()
    )
    return per_well


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_inventory(
    data_dir: Optional[Path] = None,
    out_path: Optional[Path] = None,
    include_population: bool = True,
) -> dict:
    """Assemble the well-inventory-by-band result; optionally write YAML.

    Returns a dict with ``bands`` (reconciliation per band), ``subsea_total``,
    ``subsea_depth_stats``, ``provenance`` and ``caveats``.
    """
    registry = load_subsea_well_registry(data_dir)
    subsea_inv = subsea_inventory_by_band(registry)

    population: "OrderedDict[str, int]" = _zeroed_bands()
    population["unknown"] = 0
    well_count = None
    if include_population:
        wells = load_well_water_depths(data_dir)
        population = well_population_by_band(wells)
        well_count = int(len(wells))

    bands = reconcile(subsea_inv, population)
    result = {
        "bands": {k: v for k, v in bands.items()},
        "subsea_total": int(sum(subsea_inv["counts"][k] for k in BAND_LABELS)),
        "subsea_depth_stats": subsea_inv["stats"],
        "well_population_total": well_count,
        "provenance": {
            "subsea_source": "BSEE permstruc/mv_subsea_boreholes.bin (subsea-borehole registry)",
            "population_source": (
                "BSEE offshorestats/mv_sbwd_wells.bin (median WATER_DEPTH per API_WELL_NUMBER)"
                if include_population
                else None
            ),
            "band_scheme_ft": dict(BAND_LABELS),
            "issue": "worldenergydata#583 (epic #582)",
        },
        "caveats": [
            "Registry is authoritative subsea-only but likely undercounts older completions.",
            "Registry has no API_WELL_NUMBER; reconciliation is a population comparison, not a row join.",
            "Subsea flag in ST_BP_and_tree_height.csv is a ~100-row sample, not comprehensive (#589).",
            "Confidence: subsea band counts are [on record]; subsea_share depends on full-population coverage.",
        ],
    }

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result
