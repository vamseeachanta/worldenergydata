# ABOUTME: Forward-looking UDW intervention ACCESS-GAP synthesis by water-depth band (worldenergydata #638, capstone of #626).
# ABOUTME: Joins #583 wells x #629 band-cost x #598 fleet x #630 empirical-rate into demand vs supply rig-days/yr + $ exposure; access-RISK framing, never a measured crossover.

"""Intervention access-gap synthesis — demand vs supply rig-days by band (#638).

The capstone of the deep-analytics epic (#626). For each water-depth band it
joins four committed, reviewable inputs into a single FORWARD-LOOKING access-risk
view -- NOT a measured crossover:

* **Installed subsea wells** (#583, ``well_inventory_by_band.yml``) -- the demand
  base: subsea wells on record per band.
* **Band-aware economics** (#629, ``intervention_economics.yml``) -- the
  band-effective heavy_dead_well campaign duration (now depth-scaled via the
  mobilization fix) and the per-band $/intervention used for the $ exposure.
* **Intervention fleet** (#598, ``intervention_fleet_catalog.yml``) -- the
  eligible heavy-deepwater fleet able to serve each band (global roster) AND the
  small GoM-RESIDENT dedicated population (the binding constraint, ~3 per #628).
* **Empirical demand** (#630, ``intervention_demand.yml``) -- the depth-stamped
  ``interventions_per_well`` carried as a CROSS-CHECK against the parameterized
  planning rate (it is a lifetime upper proxy, not an annual lambda).

Arithmetic (deliberately simple and honest), per band::

    DEMAND rig-days/yr = subsea_wells x frequency x heavy duration (#629)
    SUPPLY rig-days/yr = eligible_fleet x utilization x 365
    GAP                = DEMAND - SUPPLY      (rig-days/yr)
    utilization_ratio  = DEMAND / SUPPLY      (>1 => demand outstrips supply)
    $ EXPOSURE/yr      = (subsea_wells x frequency) x band $/intervention (#629)

Both a GLOBAL-eligible-fleet view and a GoM-RESIDENT-only view are produced; the
GoM-resident view is the binding constraint. Every figure is range-valued
(parameter low/central/high) and confidence-labelled; the two planning
parameters (frequency, utilization) are CITED and overridable.

Framing rule (carried into the brief): forward-looking access RISK, not a
measured shortfall. Caveats travel with the numbers -- the WAR depth FLOOR (~6%
coverage, #627/#630), the 44.5% service-type unknown (#627), and the #628
GEOGRAPHY qualifier (GoM has ~0 resident dedicated LIGHT-intervention fleet
because of geography + 6% coverage, NOT because deepwater light intervention is
avoided).
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Optional

# Reuse the band scheme (#583) -- DO NOT redefine here.
from worldenergydata.bsee.analysis.intervention.well_inventory_by_band import (
    BAND_LABELS,
    MODU_SERVICING_BANDS,
)

FEET_PER_METRE = 3.280839895

_HERE = Path(__file__).resolve().parent
DEFAULT_INVENTORY_PATH = _HERE / "data" / "well_inventory_by_band.yml"
DEFAULT_ECONOMICS_PATH = _HERE / "data" / "intervention_economics.yml"
DEFAULT_DEMAND_PATH = _HERE / "data" / "intervention_demand.yml"
DEFAULT_OUTPUT_PATH = _HERE / "data" / "access_gap.yml"

# Lower depth edge of each band, in feet (used for fleet depth-eligibility).
BAND_LOWER_EDGE_FT: "OrderedDict[str, float]" = OrderedDict(
    [
        ("shelf_lt_500", 0.0),
        ("band_500_3000", 500.0),
        ("band_3000_5000", 3000.0),
        ("band_5000_10000", 5000.0),
        ("band_gt_10000", 10000.0),
    ]
)

# Heavy deepwater asset classes that can serve a heavy_dead_well campaign. The
# light RLWI monohull is deliberately EXCLUDED from heavy supply (it does light
# riserless work only). Jack-ups serve the shelf and are a separate, abundant
# market (the shelf band is not the access-constrained one).
HEAVY_DEEPWATER_CLASSES: tuple[str, ...] = (
    "modu_drillship",
    "modu_semisub",
    "heavy_intervention_semi",
)

# ---------------------------------------------------------------------------
# Parameters (CITED engineering assumptions, overridable)
# ---------------------------------------------------------------------------
# Planning intervention frequency per subsea well per year: roughly one
# intervention every 5-10 years (lambda ~= 0.1-0.2 / well / yr). GoM deepwater
# subsea wells are intervened INFREQUENTLY; this is a planning-grade range from
# standard subsea reliability / operator planning norms, NOT a measured rate.
DEFAULT_INTERVENTION_FREQUENCY: dict[str, float] = {
    "low": 0.1,
    "central": 0.15,
    "high": 0.2,
}

INTERVENTION_FREQUENCY_SOURCE = (
    "[engineering-assumption] Planning intervention frequency ~0.1-0.2 per subsea "
    "well per year (one intervention every 5-10 years). GoM deepwater subsea "
    "wells are intervened infrequently; planning-grade range from subsea "
    "reliability / operator planning norms, NOT a measured BSEE rate. The #630 "
    "empirical interventions_per_well is carried separately as a cross-check (it "
    "is a lifetime upper proxy on the ~6% depth-stamped WAR subset, not an annual "
    "lambda). Overridable via the frequency arg."
)

# Practical sustained fleet utilization: 60-80% once weather, transit, contract
# gaps and maintenance are netted off nominal availability.
DEFAULT_UTILIZATION: dict[str, float] = {"low": 0.6, "central": 0.7, "high": 0.8}

UTILIZATION_SOURCE = (
    "[engineering-assumption] Practical sustained fleet utilization 60-80% "
    "(nominal availability net of weather, transit, contracting gaps and "
    "maintenance). Planning-grade; overridable via the utilization arg."
)

DAYS_PER_YEAR = 365

# Confidence label for every access-gap figure.
CONF_FORWARD_RISK = "forward_looking_risk"


# ---------------------------------------------------------------------------
# Loaders (thin I/O; pure core below accepts injected dicts for testing)
# ---------------------------------------------------------------------------
def _load_yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_inventory(path: Optional[Path] = None) -> dict:
    """Load installed subsea wells by band (#583)."""
    return _load_yaml(path if path is not None else DEFAULT_INVENTORY_PATH)


def load_economics(path: Optional[Path] = None) -> dict:
    """Load the band-aware intervention economics (#629)."""
    return _load_yaml(path if path is not None else DEFAULT_ECONOMICS_PATH)


def load_demand(path: Optional[Path] = None) -> dict:
    """Load the empirical intervention demand / rate by band (#630)."""
    return _load_yaml(path if path is not None else DEFAULT_DEMAND_PATH)


def load_fleet_catalog(path: Optional[Path] = None) -> dict:
    """Load the unified intervention-fleet catalog (#598)."""
    if path is not None:
        return _load_yaml(path)
    from importlib import resources

    p = resources.files("worldenergydata.vessel_fleet") / "data"
    return _load_yaml(Path(str(p / "intervention_fleet_catalog.yml")))


# ---------------------------------------------------------------------------
# Pure core
# ---------------------------------------------------------------------------
def _scaled(value: float, factors: dict[str, float]) -> dict[str, float]:
    return {k: value * factors[k] for k in ("low", "central", "high")}


def demand_rig_days(
    subsea_wells: int,
    frequency: dict[str, float],
    eff_duration: dict[str, float],
) -> dict:
    """DEMAND rig-days/yr = wells x frequency x band-effective heavy duration.

    Returns interventions/yr and rig-days/yr, each as low/central/high. The
    low/central/high of rig-days pairs frequency low/central/high with duration
    low/median/high respectively, so the range spans both uncertainties.
    """
    interventions = _scaled(float(subsea_wells), frequency)
    rig_days = {
        "low": round(interventions["low"] * float(eff_duration["low"]), 1),
        "central": round(interventions["central"] * float(eff_duration["median"]), 1),
        "high": round(interventions["high"] * float(eff_duration["high"]), 1),
    }
    return {
        "interventions_per_yr": {k: round(v, 2) for k, v in interventions.items()},
        "rig_days_per_yr": rig_days,
    }


def supply_rig_days(fleet_count: int, utilization: dict[str, float]) -> dict:
    """SUPPLY rig-days/yr = eligible fleet x utilization x 365 (low/central/high)."""
    return {
        k: round(float(fleet_count) * utilization[k] * DAYS_PER_YEAR, 1)
        for k in ("low", "central", "high")
    }


def _ratio(num: float, den: float) -> Optional[float]:
    if den is None or den == 0:
        return None
    return round(num / den, 3)


def gap_metrics(demand_rig: dict, supply_rig: dict) -> dict:
    """GAP rig-days/yr (= demand - supply) + utilization ratios (= demand/supply).

    central = central-vs-central; conservative = high-demand vs low-supply (worst
    case); optimistic = low-demand vs high-supply (best case).
    """
    gap = {
        "central": round(demand_rig["central"] - supply_rig["central"], 1),
        "conservative": round(demand_rig["high"] - supply_rig["low"], 1),
        "optimistic": round(demand_rig["low"] - supply_rig["high"], 1),
    }
    ratio = {
        "central": _ratio(demand_rig["central"], supply_rig["central"]),
        "conservative": _ratio(demand_rig["high"], supply_rig["low"]),
        "optimistic": _ratio(demand_rig["low"], supply_rig["high"]),
    }
    return {"gap_rig_days_per_yr": gap, "utilization_ratio": ratio}


def exposure_usd(
    interventions_per_yr: dict, cost_usd: Optional[dict]
) -> Optional[dict]:
    """$ exposure/yr = interventions/yr x band $/intervention (#629).

    ``None`` when the band cost is not priced (e.g. shelf jackup-serviced N/A).
    """
    if not cost_usd or cost_usd.get("median") is None:
        return None
    return {
        "low": round(interventions_per_yr["low"] * cost_usd["low"]),
        "central": round(interventions_per_yr["central"] * cost_usd["median"]),
        "high": round(interventions_per_yr["high"] * cost_usd["high"]),
    }


def eligible_global_fleet(
    by_asset_class: dict,
    band_lower_edge_ft: float,
    classes: tuple[str, ...] = HEAVY_DEEPWATER_CLASSES,
) -> dict:
    """Count global heavy-deepwater hulls whose depth capability reaches the band.

    A class is eligible when its ``water_depth_capability_ft.max`` >= the band
    lower edge. Returns the summed count plus the per-class breakdown.
    """
    breakdown: "OrderedDict[str, int]" = OrderedDict()
    total = 0
    for klass in classes:
        info = by_asset_class.get(klass) or {}
        cap = (info.get("water_depth_capability_ft") or {}).get("max")
        count = int(info.get("count") or 0)
        if cap is not None and float(cap) >= band_lower_edge_ft and count > 0:
            breakdown[klass] = count
            total += count
    return {"count": total, "by_class": dict(breakdown)}


def eligible_gom_resident(units: list[dict], band_lower_edge_ft: float) -> dict:
    """Count GoM-resident HEAVY units whose depth rating reaches the band.

    Heavy = ``intervention_class == 'heavy'`` or asset_class in the heavy
    deepwater classes; the light RLWI monohull is excluded from heavy supply.
    Depth rating (m) is converted to ft for the band comparison.
    """
    names: list[str] = []
    for unit in units or []:
        is_heavy = (unit.get("intervention_class") == "heavy") or (
            unit.get("asset_class") in HEAVY_DEEPWATER_CLASSES
        )
        if not is_heavy:
            continue
        rating_m = unit.get("water_depth_rating_m")
        rating_ft = float(rating_m) * FEET_PER_METRE if rating_m is not None else None
        if rating_ft is not None and rating_ft >= band_lower_edge_ft:
            names.append(unit.get("name", "?"))
    return {"count": len(names), "units": names}


def build_band_gap(
    band: str,
    subsea_wells: int,
    eff_duration: dict[str, float],
    cost_usd: Optional[dict],
    global_fleet: dict,
    gom_resident: dict,
    empirical_interventions_per_well: Optional[float],
    frequency: dict[str, float],
    utilization: dict[str, float],
) -> dict:
    """Assemble the full demand/supply/gap/exposure record for one band."""
    demand = demand_rig_days(subsea_wells, frequency, eff_duration)
    supply_global = supply_rig_days(global_fleet["count"], utilization)
    supply_gom = supply_rig_days(gom_resident["count"], utilization)

    rig = demand["rig_days_per_yr"]
    return {
        "band": band,
        "label": BAND_LABELS.get(band, band),
        "modu_servicing": band in MODU_SERVICING_BANDS,
        "subsea_wells": int(subsea_wells),
        "demand": {
            "heavy_duration_days": dict(eff_duration),
            "interventions_per_yr": demand["interventions_per_yr"],
            "rig_days_per_yr": rig,
            "empirical_interventions_per_well_xcheck": empirical_interventions_per_well,
        },
        "supply": {
            "eligible_classes": global_fleet["by_class"],
            "global_eligible_fleet_count": global_fleet["count"],
            "gom_resident_eligible_count": gom_resident["count"],
            "gom_resident_eligible_units": gom_resident["units"],
            "rig_days_per_yr_global": supply_global,
            "rig_days_per_yr_gom_resident": supply_gom,
        },
        "gap_vs_global": gap_metrics(rig, supply_global),
        "gap_vs_gom_resident": gap_metrics(rig, supply_gom),
        "exposure_usd_per_yr": exposure_usd(demand["interventions_per_yr"], cost_usd),
        "confidence": CONF_FORWARD_RISK,
    }


# ---------------------------------------------------------------------------
# Assembly helpers
# ---------------------------------------------------------------------------
def _band_eff_duration(economics: dict, band: str) -> dict[str, float]:
    """Band-effective heavy_dead_well duration (days) from the economics YAML."""
    cell = economics.get("economics", {}).get(band, {}).get("heavy_dead_well", {}) or {}
    dur = cell.get("duration_days")
    if dur:
        return {k: dur.get(k) for k in ("low", "median", "high")}
    # Fall back to the base campaign duration if the cell omitted it.
    base = economics.get("campaign_duration_days", {}).get("heavy_dead_well", {})
    return {k: base.get(k) for k in ("low", "median", "high")}


def _band_heavy_cost(economics: dict, band: str) -> Optional[dict]:
    cell = economics.get("economics", {}).get(band, {}).get("heavy_dead_well", {}) or {}
    return cell.get("cost_usd")


def _headline(bands: "OrderedDict[str, dict]") -> str:
    """Headline: the GoM-resident utilization ratio in the deepest populated band."""
    cell = bands.get("band_5000_10000", {})
    ratio = (
        cell.get("gap_vs_gom_resident", {}).get("utilization_ratio", {}).get("central")
    )
    wells = cell.get("subsea_wells")
    gom = cell.get("supply", {}).get("gom_resident_eligible_count")
    if ratio is None:
        return (
            "5,000-10,000 ft: no GoM-resident heavy units eligible -- demand has "
            "no resident supply to draw on (forward-looking access risk)."
        )
    return (
        f"5,000-10,000 ft holds {wells} subsea wells but only {gom} GoM-resident "
        f"heavy-intervention unit(s): forward demand would need ~{ratio:.1f}x the "
        "rig-days that resident supply can provide (access-RISK indicator, NOT a "
        "measured crossover)."
    )


def build_access_gap(
    inventory_path: Optional[Path] = None,
    economics_path: Optional[Path] = None,
    demand_path: Optional[Path] = None,
    fleet_path: Optional[Path] = None,
    out_path: Optional[Path] = None,
    frequency: Optional[dict[str, float]] = None,
    utilization: Optional[dict[str, float]] = None,
    inventory: Optional[dict] = None,
    economics: Optional[dict] = None,
    demand: Optional[dict] = None,
    fleet: Optional[dict] = None,
) -> dict:
    """Assemble the access-gap synthesis; optionally write YAML.

    Inputs may be injected (for tests) or loaded from the committed YAMLs. The
    two planning parameters are overridable via ``frequency`` / ``utilization``.
    """
    inv = inventory if inventory is not None else load_inventory(inventory_path)
    econ = economics if economics is not None else load_economics(economics_path)
    dem = demand if demand is not None else load_demand(demand_path)
    flt = fleet if fleet is not None else load_fleet_catalog(fleet_path)

    freq = frequency if frequency is not None else DEFAULT_INTERVENTION_FREQUENCY
    util = utilization if utilization is not None else DEFAULT_UTILIZATION

    inv_bands = inv.get("bands", {})
    dem_bands = dem.get("bands", {})
    by_class = flt.get("by_asset_class", {})
    gom_units = (flt.get("gom_resident_dedicated_intervention", {}) or {}).get(
        "units", []
    )
    gom_total = (flt.get("gom_resident_dedicated_intervention", {}) or {}).get("count")

    bands: "OrderedDict[str, dict]" = OrderedDict()
    for band in BAND_LABELS:
        wells = int(inv_bands.get(band, {}).get("subsea_wells_on_record", 0) or 0)
        edge = BAND_LOWER_EDGE_FT[band]
        rec = build_band_gap(
            band=band,
            subsea_wells=wells,
            eff_duration=_band_eff_duration(econ, band),
            cost_usd=_band_heavy_cost(econ, band),
            global_fleet=eligible_global_fleet(by_class, edge),
            gom_resident=eligible_gom_resident(gom_units, edge),
            empirical_interventions_per_well=dem_bands.get(band, {}).get(
                "interventions_per_well"
            ),
            frequency=freq,
            utilization=util,
        )
        bands[band] = rec

    result = {
        "headline": _headline(bands),
        "framing": (
            "FORWARD-LOOKING ACCESS RISK, not a measured crossover. Per band: "
            "intervention demand rig-days/yr (subsea wells x parameterized "
            "frequency x band-effective heavy-intervention duration) vs available "
            "fleet rig-days/yr (eligible fleet x utilization x 365). A "
            "utilization_ratio > 1 means forward demand would outstrip that "
            "supply pool; it is an access-risk indicator, not an observed "
            "shortfall."
        ),
        "bands": {k: v for k, v in bands.items()},
        "parameters": {
            "intervention_frequency_per_well_per_yr": dict(freq),
            "intervention_frequency_source": INTERVENTION_FREQUENCY_SOURCE,
            "fleet_utilization": dict(util),
            "fleet_utilization_source": UTILIZATION_SOURCE,
            "days_per_year": DAYS_PER_YEAR,
            "heavy_deepwater_classes": list(HEAVY_DEEPWATER_CLASSES),
            "gom_resident_dedicated_total": gom_total,
        },
        "method": (
            "DEMAND rig-days/yr = subsea_wells x frequency x band-effective "
            "heavy_dead_well duration (#629, depth-scaled). SUPPLY rig-days/yr = "
            "eligible_fleet x utilization x 365, computed for BOTH the global "
            "heavy-deepwater roster and the binding GoM-resident-only fleet. GAP "
            "= DEMAND - SUPPLY; utilization_ratio = DEMAND / SUPPLY. $ exposure/yr "
            "= (subsea_wells x frequency) x band heavy $/intervention (#629)."
        ),
        "confidence": (
            "All figures are [forward_looking_risk] planning-grade indicators, "
            "range-valued over the parameter low/central/high. They are NOT "
            "measured shortfalls. The supply uses the heavy-deepwater fleet "
            "(MODUs + heavy-intervention semis); the light RLWI monohull is "
            "excluded from heavy supply."
        ),
        "caveats": [
            "FORWARD-LOOKING: this is access RISK, not a measured demand/supply "
            "crossover; both parameters (frequency, utilization) are cited "
            "planning assumptions, overridable.",
            "FLOOR: the #630 empirical interventions_per_well cross-check is a "
            "lifetime upper proxy on the ~6% depth-stamped WAR subset (WATER_DEPTH "
            "populated on only ~6% of WAR rows, #627/#630), not an annual lambda.",
            "GEOGRAPHY (#628): GoM has ~0 RESIDENT dedicated LIGHT-intervention "
            "vessels -- this is geography (the global RLWI fleet is elsewhere) + "
            "the 6% WAR coverage, NOT evidence that deepwater light intervention "
            "is avoided. ~3 GoM-resident dedicated units total (#598/#628).",
            "UNKNOWN 44.5% (#627): a large share of WAR service-type is "
            "unclassified, so the empirical work mix is incomplete.",
            "Demand uses the HEAVY heavy_dead_well duration for all interventions "
            "(an upper bound on rig-days); real campaigns mix lighter scopes.",
            "Global-roster supply is a worldwide pool a GoM operator competes for; "
            "the GoM-resident view is the binding constraint.",
            "Subsea well counts are [on record] and likely undercount older "
            "completions (#583/#589).",
        ],
        "provenance": {
            "well_inventory": "worldenergydata#583 (well_inventory_by_band)",
            "economics": "worldenergydata#629 (intervention_economics, band-aware)",
            "fleet_catalog": "worldenergydata#598 (intervention_fleet_catalog)",
            "empirical_demand": "worldenergydata#630 (intervention_demand)",
            "service_type_unknown": "worldenergydata#627",
            "rlwi_coverage_geography": "worldenergydata#628",
            "issue": "worldenergydata#638 (capstone of epic #626)",
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
    res = build_access_gap(out_path=DEFAULT_OUTPUT_PATH)
    print(res["headline"])
    print(f"wrote {DEFAULT_OUTPUT_PATH}")
