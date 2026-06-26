# ABOUTME: Cross-references BSEE Well Activity Reports (WAR) against intervention-vessel/rig supply by MODU water-depth band (worldenergydata #597).
# ABOUTME: Joins the recorded-activity supply (rigs/vessels in WAR) to the #583 water-depth demand bands; all band-resolved counts are FLOORS because WAR WATER_DEPTH is ~94% NULL.

"""WAR -> intervention-vessel cross-reference by water-depth band.

Epic #591 wants the *supply* side of the subsea-intervention picture: which
rigs and vessels actually showed up on well-activity records, bucketed into the
MODU/vessel-servicing water-depth bands that the #583 inventory uses for
*demand*. Joining the two gives a band-by-band "who serviced what" view.

**The load-bearing caveat — band-resolved counts are FLOORS.**
``WATER_DEPTH`` is populated on only ~6% of WAR rows (~94% NULL). Every
band-resolved figure here (records, distinct wells, distinct rigs, asset-class
mix) therefore counts *only the depth-stamped subset* and is a hard lower
bound, not a total. The depth-null rows are reported explicitly so the size of
the unresolved remainder is visible. The module never silently drops them into
a band.

**Honest framing — activity history, not a demand trend.**
Recorded deepwater workovers are flat-to-declining (epic #582 / digitalmodel
#890). The yearly activity series is presented as *what was recorded*, an
operational history, NOT a forward demand signal.

Aggregation functions are pure (operate on already-loaded DataFrames, fully
unit-testable on synthetic frames). I/O is confined to ``load_war`` and
``build_crossref``.
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


def _load_rig_classifier():
    """Resolve rig_fleet.classify_rig_type / RigType.

    Prefer the normal package import. The ``worldenergydata.bsee.data`` package
    ``__init__`` chain has heavy optional deps (e.g. ``assetutilities``); if
    that import fails we load the dependency-free ``constants.py`` module
    directly by file path so asset-class classification still works.
    """
    try:
        from worldenergydata.bsee.data.loaders.rig_fleet.constants import (  # noqa: E501
            RigType as _RigType,
            classify_rig_type as _classify,
        )

        return _classify, _RigType
    except Exception:  # pragma: no cover - exercised only when deps missing
        try:
            import importlib.util

            constants_path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "loaders"
                / "rig_fleet"
                / "constants.py"
            )
            spec = importlib.util.spec_from_file_location(
                "_rig_fleet_constants_standalone", constants_path
            )
            if spec is None or spec.loader is None:
                return None, None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.classify_rig_type, module.RigType
        except Exception:  # pragma: no cover - defensive
            return None, None


classify_rig_type, RigType = _load_rig_classifier()

try:  # data-root resolution is best-effort; callers may pass an explicit path
    from worldenergydata.common.data_resolver import get_module_data_safe
except Exception:  # pragma: no cover - core package may be absent in isolation
    get_module_data_safe = None  # type: ignore[assignment]

DEPTH_COL = "WATER_DEPTH"
WELL_COL = "API_WELL_NUMBER"
RIG_COL = "RIG_NAME"
OPERATOR_COL = "BUS_ASC_NAME"
DATE_COL = "WAR_START_DT"

# Placeholder rig labels that are not real assets (BSEE uses these for
# operations not tied to a named rig/vessel). Excluded from distinct-asset and
# asset-class counts so the "active assets" figure stays meaningful.
_NON_ASSET_RIG_TOKENS: tuple[str, ...] = (
    "NON RIG UNIT OPERATION",
    "NON-RIG UNIT OPERATION",
    "NO RIG",
    "UNKNOWN",
)

_WAR_REL = Path("bin") / "war" / "mv_war_main.bin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_real_asset(name: object) -> bool:
    """True when ``name`` is a usable rig/vessel name (not null/placeholder)."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    text = str(name).strip()
    if not text:
        return False
    upper = text.upper().lstrip("* ").strip()
    return not any(tok in upper for tok in _NON_ASSET_RIG_TOKENS)


def _band_series(war: pd.DataFrame, depth_col: str = DEPTH_COL) -> pd.Series:
    """Map each WAR row to its band key (``None`` where depth is missing)."""
    depths = pd.to_numeric(war.get(depth_col), errors="coerce")
    return depths.map(classify_modu_band)


def _empty_band_map() -> "OrderedDict[str, int]":
    return OrderedDict((k, 0) for k in BAND_LABELS)


def _classify_asset(name: str) -> str:
    """Return a rig-type value string for ``name`` (``unknown`` if unavailable)."""
    if classify_rig_type is None:
        return "unknown"
    try:
        return classify_rig_type(name).value
    except Exception:  # pragma: no cover - defensive
        return "unknown"


# ---------------------------------------------------------------------------
# Aggregation (pure — operate on already-loaded frames)
# ---------------------------------------------------------------------------
def depth_coverage(war: pd.DataFrame, depth_col: str = DEPTH_COL) -> dict:
    """Report how much of the WAR frame is depth-resolvable.

    Establishes the FLOOR: ``records_total`` vs the depth-stamped subset.
    """
    total = int(len(war))
    depths = pd.to_numeric(war.get(depth_col), errors="coerce")
    present = int(depths.notna().sum())
    null = total - present
    return {
        "records_total": total,
        "records_with_water_depth": present,
        "records_missing_water_depth": null,
        "depth_coverage_fraction": round(present / total, 4) if total else None,
        "is_floor": True,
    }


def crossref_by_band(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    well_col: str = WELL_COL,
    rig_col: str = RIG_COL,
) -> "OrderedDict[str, dict]":
    """Bucket depth-stamped WAR rows into bands: records + distinct wells + rigs.

    Only rows carrying a numeric ``WATER_DEPTH`` are bucketed; null-depth rows
    are excluded (see :func:`depth_coverage`). Every count returned is a FLOOR.
    """
    bands = _band_series(war, depth_col)
    work = war.copy()
    work["_band"] = bands

    records = _empty_band_map()
    wells_acc: "OrderedDict[str, set]" = OrderedDict((k, set()) for k in BAND_LABELS)
    rigs_acc: "OrderedDict[str, set]" = OrderedDict((k, set()) for k in BAND_LABELS)

    resolved = work[work["_band"].notna()]
    for band_key, group in resolved.groupby("_band", sort=False):
        if band_key not in records:
            continue
        records[band_key] = int(len(group))
        if well_col in group.columns:
            wells_acc[band_key] = {
                str(w).strip() for w in group[well_col].dropna() if str(w).strip()
            }
        if rig_col in group.columns:
            rigs_acc[band_key] = {
                str(r).strip() for r in group[rig_col] if _is_real_asset(r)
            }

    out: "OrderedDict[str, dict]" = OrderedDict()
    for key, label in BAND_LABELS.items():
        out[key] = {
            "label": label,
            "war_records": int(records[key]),
            "distinct_wells": int(len(wells_acc[key])),
            "distinct_assets": int(len(rigs_acc[key])),
            "modu_servicing": key in MODU_SERVICING_BANDS,
            "is_floor": True,
        }
    return out


def asset_class_mix_by_band(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    rig_col: str = RIG_COL,
) -> "OrderedDict[str, dict]":
    """Per band, count distinct assets by inferred rig/vessel type.

    Uses :func:`classify_rig_type` (rig_fleet) on each distinct asset name.
    FLOOR-bound for the same reason as :func:`crossref_by_band`.
    """
    bands = _band_series(war, depth_col)
    work = war.copy()
    work["_band"] = bands

    out: "OrderedDict[str, dict]" = OrderedDict()
    resolved = work[work["_band"].notna()]
    by_band = dict(tuple(resolved.groupby("_band", sort=False)))
    for key, label in BAND_LABELS.items():
        group = by_band.get(key)
        class_counts: "OrderedDict[str, int]" = OrderedDict()
        if group is not None and rig_col in group.columns:
            seen: set = set()
            for name in group[rig_col]:
                if not _is_real_asset(name):
                    continue
                norm = str(name).strip()
                if norm in seen:
                    continue
                seen.add(norm)
                cls = _classify_asset(norm)
                class_counts[cls] = class_counts.get(cls, 0) + 1
        out[key] = {
            "label": label,
            "asset_class_counts": dict(
                sorted(class_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "distinct_assets": int(sum(class_counts.values())),
            "is_floor": True,
        }
    return out


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


def deepwater_activity_by_year(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    date_col: str = DATE_COL,
) -> "OrderedDict[int, int]":
    """Yearly count of depth-stamped WAR records in MODU-servicing bands.

    Activity HISTORY (what was recorded), NOT a demand forecast. FLOOR-bound.
    """
    bands = _band_series(war, depth_col)
    work = war.copy()
    work["_band"] = bands
    resolved = work[work["_band"].isin(MODU_SERVICING_BANDS)]
    counts: dict[int, int] = {}
    if date_col in resolved.columns:
        for value in resolved[date_col]:
            year = _parse_year(value)
            if year is None:
                continue
            counts[year] = counts.get(year, 0) + 1
    return OrderedDict(sorted(counts.items()))


def summarize(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    well_col: str = WELL_COL,
    rig_col: str = RIG_COL,
    date_col: str = DATE_COL,
) -> dict:
    """Assemble the full cross-reference result dict from a WAR frame (pure)."""
    coverage = depth_coverage(war, depth_col)
    bands = crossref_by_band(war, depth_col, well_col, rig_col)
    asset_mix = asset_class_mix_by_band(war, depth_col, rig_col)
    activity = deepwater_activity_by_year(war, depth_col, date_col)

    modu_records = sum(
        bands[k]["war_records"] for k in MODU_SERVICING_BANDS if k in bands
    )
    modu_wells_floor = sum(
        bands[k]["distinct_wells"] for k in MODU_SERVICING_BANDS if k in bands
    )

    return {
        "depth_coverage": coverage,
        "bands": {k: v for k, v in bands.items()},
        "asset_class_mix": {k: v for k, v in asset_mix.items()},
        "deepwater_activity_history_by_year": {
            int(y): int(c) for y, c in activity.items()
        },
        "totals": {
            "modu_band_records_floor": int(modu_records),
            "modu_band_distinct_wells_floor": int(modu_wells_floor),
            "note": "Sums over MODU-servicing bands only; FLOOR (depth-stamped subset).",
        },
        "caveats": [
            "FLOOR: WATER_DEPTH is populated on only ~6% of WAR rows (~94% NULL); "
            "every band-resolved count is a hard lower bound, not a total.",
            "Depth-null records are excluded from bands and reported under "
            "depth_coverage.records_missing_water_depth — not silently bucketed.",
            "Asset-class mix is heuristic (rig-name pattern match via "
            "rig_fleet.classify_rig_type); 'unknown' covers unmatched names.",
            "distinct_assets excludes placeholder labels (e.g. NON RIG UNIT "
            "OPERATION); a single asset may appear across multiple bands.",
            "deepwater_activity_history_by_year is recorded operational HISTORY "
            "(flat-to-declining per epic #582 / digitalmodel #890), NOT a "
            "forward demand trend.",
        ],
        "provenance": {
            "war_source": "BSEE war/mv_war_main.bin (well-activity reports)",
            "band_scheme_ft": dict(BAND_LABELS),
            "rig_classifier": (
                "worldenergydata.bsee.data.loaders.rig_fleet.classify_rig_type"
                if classify_rig_type is not None
                else None
            ),
            "issue": "worldenergydata#597 (epic #591)",
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


def build_crossref(
    data_dir: Optional[Path] = None,
    war_path: Optional[Path] = None,
    out_path: Optional[Path] = None,
) -> dict:
    """Load WAR, build the band cross-reference, optionally write YAML.

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
