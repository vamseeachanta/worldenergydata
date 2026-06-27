# ABOUTME: Indicative intervention COST by depth-band x scope (worldenergydata #629).
# ABOUTME: representative dayrate (median of eligible class) x typical campaign duration; not_public assets flagged, never invented.

"""Intervention economics — indicative $/intervention by band x scope (#629).

Joins three reviewable inputs into a planning-grade cost view: the serviceability
matrix (#586, eligible asset class(es) + riser rule per band x scope; index 0 =
representative asset), the public day-rate snapshot (#596,
``summary_by_asset_class``), and a PARAMETERIZED campaign-duration table
(:data:`DEFAULT_CAMPAIGN_DURATION_DAYS`, overridable).

Arithmetic (deliberately simple and honest)::

    effective_duration = scope base duration + per-band mobilization adder
    cost_{low,median,high} = dayrate_{low,median,high} x effective_{low,med,high}

Two band-inertness fixes (#629): a per-band mobilization / riser-running adder
(:data:`BAND_MOBILIZATION_DAYS`) so cost VARIES by depth, and shelf heavy / CT
priced as jackup-serviced N/A (no public jack-up rate) rather than on the
deepwater-MODU rate.

Key honesty rule: where the representative asset's day-rate is not public
(Helix Q-class semis, RLWI monohulls) the cost is NOT invented — it is priced off
the next eligible public asset (MODU/MPSV proxy) or left ``null``/``unknown``.
Bands/scopes are reused from #583/#586 — this module DOES NOT redefine them.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Optional

from worldenergydata.bsee.analysis.intervention.serviceability_matrix import (
    SCOPE_LABELS,
    SCOPES,
)

# Reuse the band scheme (#583) and scope legend (#586) — DO NOT redefine here.
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
)

_HERE = Path(__file__).resolve().parent
DEFAULT_SERVICEABILITY_PATH = _HERE / "data" / "serviceability_matrix.yml"
DEFAULT_OUTPUT_PATH = _HERE / "data" / "intervention_economics.yml"


# ---------------------------------------------------------------------------
# Campaign-duration table (PARAMETERIZED ENGINEERING ASSUMPTION, overridable)
# ---------------------------------------------------------------------------
# Representative on-station campaign durations by scope, in days, as low /
# median / high. These are planning-grade ranges from standard Gulf-of-Mexico
# deepwater intervention practice, NOT a measured BSEE dataset.
DEFAULT_CAMPAIGN_DURATION_DAYS: "OrderedDict[str, dict[str, int]]" = OrderedDict(
    [
        ("light_live_well", {"low": 5, "median": 10, "high": 15}),
        ("through_tubing_ct", {"low": 15, "median": 20, "high": 30}),
        ("heavy_dead_well", {"low": 30, "median": 45, "high": 60}),
    ]
)

DURATION_SOURCE_NOTE = (
    "[engineering-assumption] Representative subsea well-intervention campaign "
    "durations (typical on-station days incl. routine contingency), by scope: "
    "riserless light wireline jobs run a few days to ~2 weeks (5-15 d); "
    "riser-based through-tubing coiled-tubing programs ~2-4 weeks (15-30 d); "
    "full workover-riser + subsea-BOP jobs (tubing pull / recompletion / ESP "
    "change-out / P&A) ~1-2 months (30-60 d). Planning-grade ranges from "
    "standard GoM deepwater intervention practice / operator AFE norms (e.g. "
    "SPE intervention literature), NOT a measured BSEE dataset. These are the "
    "ON-STATION SCOPE BASE durations; the per-band mobilization / riser-running "
    "adder (BAND_MOBILIZATION_DAYS) is applied ON TOP so effective duration and "
    "cost vary by depth band. Overridable via the duration_table argument."
)


# ---------------------------------------------------------------------------
# Per-band mobilization / riser-running adder (#629 band-inertness fix)
# ---------------------------------------------------------------------------
# Effective duration = scope BASE on-station days + a per-band mobilization /
# riser-running adder. Deeper water = more transit to/from the resident-asset
# base + markedly longer riser & subsea-BOP running through the water column, so
# deeper bands carry a larger adder. Without it every band priced to the SAME
# cost (the band-inertness defect). Median follows the issue spec; low/high scale
# around it. Days, low/median/high. Overridable via mobilization_table.
BAND_MOBILIZATION_DAYS: "OrderedDict[str, dict[str, int]]" = OrderedDict(
    [
        ("shelf_lt_500", {"low": 0, "median": 0, "high": 0}),
        ("band_500_3000", {"low": 2, "median": 3, "high": 5}),
        ("band_3000_5000", {"low": 4, "median": 6, "high": 9}),
        ("band_5000_10000", {"low": 7, "median": 10, "high": 14}),
        ("band_gt_10000", {"low": 10, "median": 14, "high": 20}),
    ]
)

MOBILIZATION_SOURCE_NOTE = (
    "[engineering-assumption] Per-band mobilization / riser-running adder (days), "
    "applied on top of the scope BASE on-station duration so effective duration "
    "and cost scale with water depth. Rationale: deeper bands need more transit "
    "to/from the (scarce) resident-asset base and substantially longer riser & "
    "subsea-BOP running/recovery through a deeper water column. Median adder: "
    "shelf +0, 500-3,000 ft +3, 3,000-5,000 ft +6, 5,000-10,000 ft +10, "
    ">10,000 ft +14; low/high scale around the median. Planning-grade GoM "
    "deepwater-intervention practice, NOT a measured BSEE dataset. Overridable "
    "via the mobilization_table argument."
)

# Shelf (<500 ft) heavy / through-tubing work is serviced by a JACK-UP rig, not a
# deepwater MODU (drillship). A jack-up day-rate is FAR lower; pricing shelf
# heavy/CT on the deepwater-MODU rate would massively OVERSTATE the cost. There is
# no public jack-up day-rate in the snapshot (#596), so rather than invent one or
# borrow the drillship rate, these cells are marked "jackup-serviced,
# deepwater-MODU rate N/A" with a null cost (honest under-claim, not overstate).
SHELF_BAND = "shelf_lt_500"
SHELF_JACKUP_SCOPES: tuple[str, ...] = ("through_tubing_ct", "heavy_dead_well")

# Map the serviceability-matrix asset classes (#586) onto the day-rate snapshot
# taxonomy (#596). A "MODU" in US-GoM intervention/workover is represented by a
# drillship (the semisub day-rates in the snapshot are harsh-env Norway/Black
# Sea comparables, not GoM). RLWI monohulls and heavy-intervention semis have no
# public day-rate (handled as proxy/unknown below).
ASSET_DAYRATE_MAP: dict[str, str] = {
    "modu": "modu_drillship",
    "heavy_intervention_semi": "heavy_intervention_semi",
    "rlwi_monohull": "rlwi_monohull",
    "mpsv": "mpsv_osv",
}

# Confidence labels emitted per cell.
CONF_INDICATIVE = "indicative"  # representative asset has a public day-rate
CONF_PROXY_MODU = "proxy_modu"  # representative not public; MODU proxy used
CONF_PROXY_MPSV = "proxy_mpsv"  # representative not public; eligible MPSV proxy
CONF_UNKNOWN = "unknown"  # no eligible asset has a public day-rate
CONF_JACKUP_NA = "jackup_na"  # shelf jackup-serviced; deepwater-MODU rate N/A

CONFIDENCE_LABELS: tuple[str, ...] = (
    CONF_INDICATIVE,
    CONF_PROXY_MODU,
    CONF_PROXY_MPSV,
    CONF_UNKNOWN,
    CONF_JACKUP_NA,
)

# Confidence labels whose cost is intentionally null (not priced).
NULL_COST_CONFIDENCE: tuple[str, ...] = (CONF_UNKNOWN, CONF_JACKUP_NA)


# ---------------------------------------------------------------------------
# Input loaders (best-effort; pure functions accept injected inputs)
# ---------------------------------------------------------------------------
def load_serviceability_matrix(path: Optional[Path] = None) -> dict:
    """Load the base (vertical-tree) ``matrix`` from the serviceability YAML."""
    import yaml

    src = Path(path) if path is not None else DEFAULT_SERVICEABILITY_PATH
    doc = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    return doc.get("matrix", {}) or {}


def load_dayrate_bands(snapshot: Optional[dict] = None) -> dict[str, dict]:
    """Return the per-asset-class day-rate summary keyed by snapshot taxonomy.

    Delegates to vessel_fleet's :func:`summary_by_asset_class`. Best-effort
    import so this module stays usable even when vessel_fleet is absent (callers
    can inject ``dayrate_bands`` directly into the pure functions).
    """
    from worldenergydata.vessel_fleet.dayrate_snapshot import (  # type: ignore
        summary_by_asset_class,
    )

    return summary_by_asset_class(snapshot)


# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------
def _public_band_for(
    asset: str,
    dayrate_bands: dict[str, dict],
    asset_map: dict[str, str],
) -> tuple[str, Optional[dict]]:
    """Resolve a serviceability asset to its day-rate taxonomy key + band.

    Returns ``(dayrate_class_key, band_or_None)`` where ``band`` is the summary
    entry only if a public median rate exists, else ``None``.
    """
    dr_key = asset_map.get(asset, asset)
    entry = dayrate_bands.get(dr_key)
    if (
        entry
        and entry.get("rate_disclosed")
        and entry.get("median_usd_per_day") is not None
    ):
        return dr_key, entry
    return dr_key, None


def _proxy_confidence(basis_dayrate_key: str) -> str:
    """Confidence label for a proxy-priced cell, from the basis asset class."""
    if basis_dayrate_key.startswith("modu"):
        return CONF_PROXY_MODU
    if basis_dayrate_key.startswith("mpsv"):
        return CONF_PROXY_MPSV
    return CONF_PROXY_MPSV  # any other public eligible alt is light-vessel class


def _effective_duration(
    base: dict[str, int], mob: dict[str, int]
) -> "OrderedDict[str, int]":
    """Scope BASE on-station days + per-band mobilization adder, per low/med/high."""
    return OrderedDict(
        (k, int(base[k]) + int(mob.get(k, 0))) for k in ("low", "median", "high")
    )


def intervention_cost(
    eligible_asset_classes: list[str],
    scope: str,
    dayrate_bands: dict[str, dict],
    duration_table: Optional[dict[str, dict[str, int]]] = None,
    asset_map: Optional[dict[str, str]] = None,
    band: Optional[str] = None,
    mobilization_table: Optional[dict[str, dict[str, int]]] = None,
) -> dict:
    """Compute the indicative cost record for one (eligible-assets, scope) cell.

    ``eligible_asset_classes`` is ordered (index 0 = representative asset);
    ``dayrate_bands`` is the snapshot summary (:func:`load_dayrate_bands`).
    ``duration_table`` / ``asset_map`` / ``mobilization_table`` are optional
    overrides. When ``band`` is given, the per-band mobilization / riser-running
    adder is added to the scope base duration so cost VARIES by band (#629 fix),
    and shelf heavy / through-tubing is flagged jackup-serviced (null cost,
    deepwater-MODU rate N/A) rather than overstated. Returns the cost record with
    base + mobilization + effective durations, low/median/high cost (or nulls), a
    confidence label and an honesty flag.
    """
    durations = duration_table or DEFAULT_CAMPAIGN_DURATION_DAYS
    amap = asset_map or ASSET_DAYRATE_MAP
    mob_table = (
        mobilization_table if mobilization_table is not None else BAND_MOBILIZATION_DAYS
    )
    if scope not in durations:
        raise KeyError(f"no duration for scope {scope!r}; have {list(durations)}")
    if not eligible_asset_classes:
        raise ValueError("eligible_asset_classes must be non-empty")

    base = durations[scope]
    mob = mob_table.get(band, {}) if band else {}
    eff = _effective_duration(base, mob)

    # Shelf heavy / through-tubing is jack-up work, not deepwater-MODU work.
    # No public jack-up rate -> do NOT price on the drillship rate (overstate);
    # mark jackup-serviced, deepwater-MODU rate N/A with a null cost.
    if band == SHELF_BAND and scope in SHELF_JACKUP_SCOPES:
        return {
            "scope": scope,
            "eligible_asset_classes": list(eligible_asset_classes),
            "representative_asset": "jackup",
            "representative_dayrate_public": False,
            "dayrate_basis_asset": None,
            "dayrate_band": None,
            "base_duration_days": dict(base),
            "mobilization_days": {
                k: int(mob.get(k, 0)) for k in ("low", "median", "high")
            },
            "duration_days": dict(eff),
            "cost_usd": {"low": None, "median": None, "high": None},
            "confidence": CONF_JACKUP_NA,
            "flag": (
                "shelf heavy/through-tubing is jackup-serviced; deepwater-MODU "
                "rate N/A (no public jack-up day-rate) — cost left null to avoid "
                "overstating shelf work on a deepwater-MODU rate"
            ),
        }

    rep = eligible_asset_classes[0]
    rep_key, rep_band = _public_band_for(rep, dayrate_bands, amap)

    basis_asset: Optional[str] = None
    basis_key: Optional[str] = None
    dr_band: Optional[dict] = None
    flag = ""

    if rep_band is not None:
        basis_asset, basis_key, dr_band = rep, rep_key, rep_band
        confidence = CONF_INDICATIVE
    else:
        # Representative asset's day-rate is not public — DO NOT invent it.
        # Fall to the next eligible asset class that has a public rate.
        for alt in eligible_asset_classes[1:]:
            alt_key, alt_band = _public_band_for(alt, dayrate_bands, amap)
            if alt_band is not None:
                basis_asset, basis_key, dr_band = alt, alt_key, alt_band
                break
        if dr_band is None:
            confidence = CONF_UNKNOWN
            flag = "dayrate not public — use MODU proxy or mark unknown"
        else:
            confidence = _proxy_confidence(basis_key or "")
            flag = (
                f"representative asset '{rep}' day-rate not public — priced via "
                f"eligible proxy '{basis_asset}' ({basis_key}); indicative only, "
                "not the representative asset's true rate"
            )

    if dr_band is not None:
        cost = {
            "low": round(dr_band["band_low_usd_per_day"] * eff["low"]),
            "median": round(dr_band["median_usd_per_day"] * eff["median"]),
            "high": round(dr_band["band_high_usd_per_day"] * eff["high"]),
        }
        dayrate_band = {
            "asset_class": basis_key,
            "low_usd_per_day": dr_band["band_low_usd_per_day"],
            "median_usd_per_day": dr_band["median_usd_per_day"],
            "high_usd_per_day": dr_band["band_high_usd_per_day"],
            "source_confidence": dr_band.get("confidence_labels"),
        }
    else:
        cost = {"low": None, "median": None, "high": None}
        dayrate_band = None

    return {
        "scope": scope,
        "eligible_asset_classes": list(eligible_asset_classes),
        "representative_asset": rep,
        "representative_dayrate_public": rep_band is not None,
        "dayrate_basis_asset": basis_asset,
        "dayrate_band": dayrate_band,
        "base_duration_days": dict(base),
        "mobilization_days": {k: int(mob.get(k, 0)) for k in ("low", "median", "high")},
        "duration_days": dict(eff),
        "cost_usd": cost,
        "confidence": confidence,
        "flag": flag,
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def build_economics_matrix(
    serviceability_matrix: dict,
    dayrate_bands: dict[str, dict],
    duration_table: Optional[dict[str, dict[str, int]]] = None,
    asset_map: Optional[dict[str, str]] = None,
    mobilization_table: Optional[dict[str, dict[str, int]]] = None,
) -> "OrderedDict[str, OrderedDict[str, dict]]":
    """Build the full band x scope economics matrix (nested OrderedDict).

    Each cell is band-aware: the per-band mobilization adder makes cost vary by
    depth (#629 band-inertness fix).
    """
    out: "OrderedDict[str, OrderedDict[str, dict]]" = OrderedDict()
    for band in BAND_LABELS:
        band_row = serviceability_matrix.get(band, {})
        row: "OrderedDict[str, dict]" = OrderedDict()
        for scope in SCOPES:
            cell = band_row.get(scope, {})
            eligible = cell.get("eligible_asset_classes") or []
            rec = intervention_cost(
                eligible,
                scope,
                dayrate_bands,
                duration_table=duration_table,
                asset_map=asset_map,
                band=band,
                mobilization_table=mobilization_table,
            )
            rec["band"] = band
            rec["band_label"] = BAND_LABELS[band]
            rec["scope_label"] = SCOPE_LABELS[scope]
            rec["riser_required"] = bool(cell.get("riser_required"))
            row[scope] = rec
        out[band] = row
    return out


def _headline(matrix: "OrderedDict[str, OrderedDict[str, dict]]") -> str:
    """Compose the headline string: heavy dead-well in 5,000-10,000 ft."""
    cell = matrix.get("band_5000_10000", {}).get("heavy_dead_well", {})
    cost = cell.get("cost_usd", {}) or {}
    lo, md, hi = cost.get("low"), cost.get("median"), cost.get("high")
    if md is None:
        return "Heavy dead-well in 5,000-10,000 ft: cost unknown (dayrate not public)."

    def _m(v: Optional[float]) -> str:
        return f"${v / 1e6:.1f}M" if v is not None else "n/a"

    rep = cell.get("representative_asset")
    return (
        f"Heavy dead-well (tubing pull / recompletion / P&A) in 5,000-10,000 ft: "
        f"~{_m(md)} per intervention (range {_m(lo)}-{_m(hi)}), priced on a "
        f"{rep} day-rate x {cell.get('duration_days', {}).get('median')} days "
        "(indicative public day-rate snapshot)."
    )


def build_intervention_economics(
    serviceability_path: Optional[Path] = None,
    snapshot: Optional[dict] = None,
    duration_table: Optional[dict[str, dict[str, int]]] = None,
    asset_map: Optional[dict[str, str]] = None,
    out_path: Optional[Path] = None,
    dayrate_bands: Optional[dict[str, dict]] = None,
    mobilization_table: Optional[dict[str, dict[str, int]]] = None,
) -> dict:
    """Assemble the intervention-economics result; optionally write YAML.

    Args:
        serviceability_path: Path to ``serviceability_matrix.yml`` (#586).
        snapshot: Optional pre-loaded day-rate snapshot (#596).
        duration_table: Optional campaign-duration override.
        asset_map: Optional serviceability->snapshot taxonomy override.
        out_path: If given, write the result as YAML there.
        dayrate_bands: Optional injected per-class day-rate summary (skips the
            vessel_fleet import; mainly for tests).

    Returns:
        Result dict with ``economics`` (band x scope), the duration table, asset
        map, ``headline``, ``confidence`` note and ``provenance``.
    """
    svc = load_serviceability_matrix(serviceability_path)
    bands = dayrate_bands if dayrate_bands is not None else load_dayrate_bands(snapshot)
    durations = duration_table or DEFAULT_CAMPAIGN_DURATION_DAYS
    mob = (
        mobilization_table if mobilization_table is not None else BAND_MOBILIZATION_DAYS
    )

    matrix = build_economics_matrix(
        svc,
        bands,
        duration_table=durations,
        asset_map=asset_map,
        mobilization_table=mob,
    )
    economics = {
        band: {scope: dict(cell) for scope, cell in row.items()}
        for band, row in matrix.items()
    }

    result = {
        "headline": _headline(matrix),
        "economics": economics,
        "scopes": dict(SCOPE_LABELS),
        "bands": dict(BAND_LABELS),
        "campaign_duration_days": {k: dict(v) for k, v in durations.items()},
        "duration_source": DURATION_SOURCE_NOTE,
        "band_mobilization_days": {k: dict(v) for k, v in mob.items()},
        "mobilization_source": MOBILIZATION_SOURCE_NOTE,
        "asset_dayrate_map": dict(asset_map or ASSET_DAYRATE_MAP),
        "method": (
            "effective_duration = scope base duration + per-band mobilization "
            "adder (BAND_MOBILIZATION_DAYS). cost_low = dayrate_band_low x "
            "effective_duration_low; cost_median = dayrate_median x "
            "effective_duration_median; cost_high = dayrate_band_high x "
            "effective_duration_high. Representative asset = "
            "eligible_asset_classes[0]; if its day-rate is not public, price off "
            "the next eligible public asset (MODU/MPSV proxy) or mark unknown. "
            "Shelf (<500 ft) heavy / through-tubing is jackup-serviced: priced "
            "N/A (no public jack-up rate) rather than on the deepwater-MODU rate."
        ),
        "confidence": (
            "Indicative planning-grade only. Day-rates are a point-in-time PUBLIC "
            "snapshot (#596), not a live subscription index; intervention-semi "
            "(Helix Q-class) and RLWI-monohull day-rates are NOT public and are "
            "shown via eligible proxies or left unknown, never invented. Campaign "
            "durations are an [engineering-assumption] (see duration_source); the "
            "per-band mobilization/riser-running adder (see mobilization_source) "
            "makes cost VARY BY BAND. Confidence labels per cell: indicative "
            "(public representative rate), proxy_modu / proxy_mpsv (priced off an "
            "eligible public proxy), unknown (no eligible public rate), jackup_na "
            "(shelf jackup-serviced, deepwater-MODU rate N/A)."
        ),
        "provenance": {
            "serviceability_matrix": "worldenergydata#586",
            "dayrate_snapshot": "worldenergydata#596",
            "band_scheme": "worldenergydata#583 (well_inventory_by_band)",
            "issue": "worldenergydata#629 (epic #582)",
        },
    }

    if out_path is not None:
        import yaml

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            yaml.safe_dump(result, fh, sort_keys=False, default_flow_style=False)

    return result


if __name__ == "__main__":  # pragma: no cover
    res = build_intervention_economics(out_path=DEFAULT_OUTPUT_PATH)
    print(res["headline"])
    print(f"wrote {DEFAULT_OUTPUT_PATH}")
