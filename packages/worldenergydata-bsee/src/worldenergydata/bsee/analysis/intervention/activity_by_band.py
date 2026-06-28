# ABOUTME: Intervention SERVICE-TYPE activity bucketed by MODU/vessel water-depth band (worldenergydata #627).
# ABOUTME: Classifies each WAR asset (rig_fleet.classify_rig_type) into a service type, crosses it with the #583 depth bands; all band-resolved counts are FLOORS (WAR WATER_DEPTH ~6% filled).

"""Service-type x water-depth-band activity matrix from BSEE WAR.

Epic #591 asked *which kind of intervention service* showed up on the
well-activity record, resolved against the MODU/vessel-servicing water-depth
bands the #583 inventory uses for demand. Where #597 cut the WAR by asset
*class mix per band*, this module pivots the other way: a
``service_type x band`` matrix (records + distinct wells per cell), plus a
``light`` vs ``heavy`` rollup per band.

**Service types** are the granular ``rig_fleet`` rig-type values applied to
``RIG_NAME`` via :func:`classify_rig_type` — the same classifier #597 uses. The
intervention services of interest are wireline, coil-tubing, lift-boat,
snubbing, workover, support-vessel and pumping; drilling-rig classes
(drillship / semi / jack-up / etc.) are also bucketed so the heavy rollup is
complete.

**Light vs heavy rollup** (per band):

* ``light``  = wireline + coil_tubing + snubbing + lift_boat + support_vessel
* ``heavy``  = workover + the MODU/semi/drillship drilling classes
* ``other``  = anything else (pumping, land rig, unknown) — kept explicit, never
  folded into light or heavy.

**The load-bearing caveat — band-resolved counts are FLOORS.** ``WATER_DEPTH``
is populated on only ~6% of WAR rows (~94% NULL). Every band-resolved figure
here counts *only the depth-stamped subset* and is a hard lower bound, not a
total. Depth-null rows are reported under ``depth_coverage`` and never silently
bucketed.

Aggregation functions are pure (operate on already-loaded DataFrames, fully
unit-testable on synthetic frames). I/O is confined to :func:`load_war`
(re-exported from #597) and :func:`build_activity_by_band`.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Optional

import pandas as pd

# Reuse the #597 WAR loader, depth-coverage floor reporter, column names, the
# resolved rig classifier and the placeholder-asset guard. Single source of
# truth for WAR I/O and asset classification.
from worldenergydata.bsee.analysis.intervention.war_vessel_crossref import (
    DEPTH_COL,
    RIG_COL,
    WELL_COL,
    RigType,
    _is_real_asset,
    classify_rig_type,
    depth_coverage,
    load_war,
)

# Reuse the demand-axis band scheme (#583) verbatim — never redefine bands here.
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    MODU_SERVICING_BANDS,
    classify_modu_band,
)

# ---------------------------------------------------------------------------
# Service-type scheme (granular rig_fleet rig types) + light/heavy rollup
# ---------------------------------------------------------------------------
# Display order: intervention services first (the services of interest), then
# the drilling-rig classes, then the catch-alls.
SERVICE_TYPE_ORDER: tuple[str, ...] = (
    RigType.WIRELINE_UNIT.value,
    RigType.COIL_TUBING_UNIT.value,
    RigType.SNUBBING_UNIT.value,
    RigType.LIFT_BOAT.value,
    RigType.SUPPORT_VESSEL.value,
    RigType.PUMPING_UNIT.value,
    RigType.WORKOVER_RIG.value,
    RigType.DRILLSHIP.value,
    RigType.SEMI_SUBMERSIBLE.value,
    RigType.JACK_UP.value,
    RigType.PLATFORM_RIG.value,
    RigType.TENDER_ASSISTED.value,
    RigType.INLAND_BARGE.value,
    RigType.SUBMERSIBLE.value,
    RigType.LAND_RIG.value,
    RigType.UNKNOWN.value,
)

# Light intervention services (per #627): wireline + coil_tubing + snubbing +
# lift_boat + support_vessel.
LIGHT_SERVICE_TYPES: frozenset[str] = frozenset(
    {
        RigType.WIRELINE_UNIT.value,
        RigType.COIL_TUBING_UNIT.value,
        RigType.SNUBBING_UNIT.value,
        RigType.LIFT_BOAT.value,
        RigType.SUPPORT_VESSEL.value,
    }
)

# Heavy services (per #627): workover + the MODU/semi/drillship drilling classes.
HEAVY_SERVICE_TYPES: frozenset[str] = frozenset(
    {
        RigType.WORKOVER_RIG.value,
        RigType.DRILLSHIP.value,
        RigType.SEMI_SUBMERSIBLE.value,
        RigType.JACK_UP.value,
        RigType.PLATFORM_RIG.value,
        RigType.TENDER_ASSISTED.value,
        RigType.INLAND_BARGE.value,
        RigType.SUBMERSIBLE.value,
    }
)

ROLLUP_ORDER: tuple[str, ...] = ("light", "heavy", "other")


def classify_service_type(rig_name: object) -> str:
    """Return the granular service-type value for a ``RIG_NAME``.

    Wraps :func:`classify_rig_type` (rig_fleet) so callers get a plain string
    and never raise on null / placeholder names (those resolve to ``unknown``).
    """
    if not _is_real_asset(rig_name):
        return RigType.UNKNOWN.value
    if classify_rig_type is None:  # pragma: no cover - classifier always present here
        return RigType.UNKNOWN.value
    try:
        return classify_rig_type(str(rig_name).strip()).value
    except Exception:  # pragma: no cover - defensive
        return RigType.UNKNOWN.value


def service_rollup(service_type: str) -> str:
    """Map a service type to the ``light`` / ``heavy`` / ``other`` rollup."""
    if service_type in LIGHT_SERVICE_TYPES:
        return "light"
    if service_type in HEAVY_SERVICE_TYPES:
        return "heavy"
    return "other"


# ---------------------------------------------------------------------------
# Aggregation (pure — operate on already-loaded frames)
# ---------------------------------------------------------------------------
def _prepare(
    war: pd.DataFrame,
    depth_col: str,
    rig_col: str,
    well_col: str,
) -> pd.DataFrame:
    """Project WAR to ``[_band, _svc, _well]`` for depth-stamped rows only.

    Rows without a numeric ``WATER_DEPTH`` (no band) are dropped here — they are
    accounted for separately by :func:`depth_coverage`, never bucketed.
    """
    depths = pd.to_numeric(war.get(depth_col), errors="coerce")
    band = depths.map(classify_modu_band)
    rig = war.get(rig_col)
    well = war.get(well_col)

    work = pd.DataFrame(
        {
            "_band": band,
            "_svc": (
                rig.map(classify_service_type)
                if rig is not None
                else RigType.UNKNOWN.value
            ),
            "_well": (
                well.map(lambda w: str(w).strip() if pd.notna(w) else "")
                if well is not None
                else ""
            ),
        }
    )
    return work[work["_band"].notna()].reset_index(drop=True)


def _cell(records: int, wells: int) -> "OrderedDict[str, object]":
    return OrderedDict(
        [
            ("war_records", int(records)),
            ("distinct_wells", int(wells)),
            ("is_floor", True),
        ]
    )


def service_type_by_band(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    rig_col: str = RIG_COL,
    well_col: str = WELL_COL,
) -> "OrderedDict[str, dict]":
    """Build the ``service_type x band`` matrix (records + distinct wells/cell).

    Returns an ordered map keyed by service type (only those with at least one
    depth-stamped record, in :data:`SERVICE_TYPE_ORDER`), each value a map over
    *all* bands plus a per-service ``total``. Every count is a FLOOR.
    """
    work = _prepare(war, depth_col, rig_col, well_col)

    matrix: "OrderedDict[str, dict]" = OrderedDict()
    if work.empty:
        return matrix

    present = [s for s in SERVICE_TYPE_ORDER if s in set(work["_svc"])]
    for svc in present:
        svc_rows = work[work["_svc"] == svc]
        bands: "OrderedDict[str, dict]" = OrderedDict()
        for band_key, label in BAND_LABELS.items():
            cell_rows = svc_rows[svc_rows["_band"] == band_key]
            wells = {w for w in cell_rows["_well"] if w}
            cell = _cell(len(cell_rows), len(wells))
            cell["label"] = label
            cell["modu_servicing"] = band_key in MODU_SERVICING_BANDS
            bands[band_key] = cell
        total_wells = {w for w in svc_rows["_well"] if w}
        matrix[svc] = OrderedDict(
            [
                ("rollup", service_rollup(svc)),
                ("bands", bands),
                ("total", _cell(len(svc_rows), len(total_wells))),
            ]
        )
    return matrix


def light_vs_heavy_by_band(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    rig_col: str = RIG_COL,
    well_col: str = WELL_COL,
) -> "OrderedDict[str, dict]":
    """Per band, roll service types up into ``light`` / ``heavy`` / ``other``.

    Distinct-well counts are the *union* of wells across the service types in
    each rollup (a well serviced by both a light and a heavy asset is counted
    once per rollup). FLOOR-bound, same as the matrix.
    """
    work = _prepare(war, depth_col, rig_col, well_col)
    work = work.copy()
    work["_rollup"] = work["_svc"].map(service_rollup)

    out: "OrderedDict[str, dict]" = OrderedDict()
    for band_key, label in BAND_LABELS.items():
        band_rows = work[work["_band"] == band_key]
        rollups: "OrderedDict[str, dict]" = OrderedDict()
        for name in ROLLUP_ORDER:
            r_rows = band_rows[band_rows["_rollup"] == name]
            wells = {w for w in r_rows["_well"] if w}
            rollups[name] = _cell(len(r_rows), len(wells))
        out[band_key] = OrderedDict(
            [
                ("label", label),
                ("modu_servicing", band_key in MODU_SERVICING_BANDS),
                ("rollups", rollups),
            ]
        )
    return out


def summarize(
    war: pd.DataFrame,
    depth_col: str = DEPTH_COL,
    rig_col: str = RIG_COL,
    well_col: str = WELL_COL,
) -> dict:
    """Assemble the full service-type-by-band result dict (pure)."""
    coverage = depth_coverage(war, depth_col)
    matrix = service_type_by_band(war, depth_col, rig_col, well_col)
    rollup = light_vs_heavy_by_band(war, depth_col, rig_col, well_col)

    # Floor totals over the MODU-servicing bands, by rollup.
    modu_totals: "OrderedDict[str, int]" = OrderedDict(
        (name, 0) for name in ROLLUP_ORDER
    )
    for band_key in MODU_SERVICING_BANDS:
        band = rollup.get(band_key)
        if band is None:
            continue
        for name in ROLLUP_ORDER:
            modu_totals[name] += int(band["rollups"][name]["war_records"])

    return {
        "depth_coverage": coverage,
        "service_type_by_band": {k: v for k, v in matrix.items()},
        "light_vs_heavy_by_band": {k: v for k, v in rollup.items()},
        "totals": {
            "service_types_present": list(matrix.keys()),
            "modu_band_records_floor_by_rollup": {
                name: int(modu_totals[name]) for name in ROLLUP_ORDER
            },
            "note": (
                "Rollup record sums over MODU-servicing bands only; FLOOR "
                "(depth-stamped subset)."
            ),
        },
        "rollup_scheme": {
            "light": sorted(LIGHT_SERVICE_TYPES),
            "heavy": sorted(HEAVY_SERVICE_TYPES),
            "other": (
                "all remaining service types (e.g. pumping_unit, land_rig, " "unknown)"
            ),
        },
        "caveats": [
            "FLOOR: WATER_DEPTH is populated on only ~6% of WAR rows (~94% "
            "NULL); every band-resolved count is a hard lower bound, not a "
            "total.",
            "Depth-null records are excluded from bands and reported under "
            "depth_coverage.records_missing_water_depth — not silently "
            "bucketed.",
            "Service type is heuristic (rig-name pattern match via "
            "rig_fleet.classify_rig_type); 'unknown' covers unmatched / "
            "placeholder names.",
            "distinct_wells per cell counts API_WELL_NUMBER; a well serviced "
            "in more than one band/service is counted once per cell, and "
            "rollup well counts union across the rollup's service types.",
            "Recorded deepwater intervention is flat-to-declining (epic #582 / "
            "digitalmodel #890); this is operational HISTORY, NOT a forward "
            "demand trend.",
        ],
        "provenance": {
            "war_source": "BSEE war/mv_war_main.bin (well-activity reports)",
            "band_scheme_ft": dict(BAND_LABELS),
            "service_classifier": (
                "worldenergydata.bsee.data.loaders.rig_fleet.classify_rig_type"
                if classify_rig_type is not None
                else None
            ),
            "issue": "worldenergydata#627 (epic #591)",
        },
    }


# ---------------------------------------------------------------------------
# Build (I/O)
# ---------------------------------------------------------------------------
def build_activity_by_band(
    data_dir: Optional[Path] = None,
    war_path: Optional[Path] = None,
    out_path: Optional[Path] = None,
) -> dict:
    """Load WAR, build the service-type-by-band matrix, optionally write YAML.

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
            yaml.safe_dump(
                _plain(result), fh, sort_keys=False, default_flow_style=False
            )

    return result


def _plain(obj):
    """Recursively convert OrderedDicts to plain dicts for ``yaml.safe_dump``."""
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj
