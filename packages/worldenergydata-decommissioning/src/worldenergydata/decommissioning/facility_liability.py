# ABOUTME: Facility-level regional decommissioning liability from curated offshore assets.
# ABOUTME: Maps HOST_TYPE->asset, COUNTRY/GoM->region, prices each with the cost model.

"""Regional decommissioning-liability roll-up for the offshore-assets portfolio.

Two forces set a decommissioning bill and they pull opposite ways: the regional
multiplier (North Sea 25-30% dearer per identical asset) and the asset mix (the
money is in floating production, concentrated in Brazil / West-Africa deepwater).
This module maps each curated production facility onto the parametric
``DecommissioningCostEstimator`` and rolls the priced portfolio up by region and
asset type so both effects can be shown side by side.

Side-effect free: pure functions over a DataFrame; no file IO, no printing.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.decommissioning.cost_model import DecommissioningCostEstimator

# HOST_TYPE (curated production_facilities) -> cost-model asset_type. Types not
# listed here (e.g. "Artificial Island") are excluded: not an offshore structure
# removal the parametric model prices.
_ASSET_MAP: dict[str, str] = {
    "Fixed Platform": "jacket",
    "Compliant Tower": "jacket",
    "MOPU": "jacket",
    "TLP": "tlp",
    "Mini-TLP": "tlp",
    "SPAR": "spar",
    "DDCV": "spar",
    "FPSO": "fpso",
    "FLNG": "fpso",
    "FSO/FSU": "fpso",
    "Semisub": "fpso",
    "FPU/FPS": "fpso",
    "Subsea Tieback": "subsea_tree",
}

# COUNTRY -> region multiplier key. Only the five regions the cost model carries
# a multiplier for are modeled; everything else is unmodeled (excluded).
_UKCS = {"United Kingdom", "UK"}
_US = {"United States", "USA", "US"}
_WEST_AFRICA = {
    "Nigeria", "Angola", "Ghana", "Congo", "Republic of Congo",
    "Equatorial Guinea", "Gabon", "Ivory Coast", "Cameroon",
    "Côte d'Ivoire", "Cote d'Ivoire",
}
_GOM_TRUE = {"Y", "YES", "TRUE", "1"}


def classify_asset_type(host_type: object) -> str | None:
    """Map a facility HOST_TYPE onto a cost-model asset type, or None if unmapped."""
    if host_type is None:
        return None
    return _ASSET_MAP.get(str(host_type).strip())


def region_of(country: object, us_gom_flag: object = None) -> str | None:
    """Map (COUNTRY, US_GOM_FLAG) onto a cost-model region, or None if unmodeled."""
    if str(us_gom_flag).strip().upper() in _GOM_TRUE:
        return "gom"
    c = str(country).strip()
    if c in _US:
        return "gom"  # US non-GoM offshore is tiny; GoM baseline
    if c in _UKCS:
        return "ukcs"
    if c == "Norway":
        return "ncs"
    if c == "Brazil":
        return "brazil"
    if c in _WEST_AFRICA:
        return "west_africa"
    return None


def price_portfolio(df: pd.DataFrame) -> dict:
    """Price every facility and roll up by region and asset type.

    Returns a dict with:
        total_musd                    - sum of modeled liability (MUSD)
        by_region                     - {region: {"sum_musd", "count"}}
        by_asset                      - {asset: {"sum_musd", "count"}}
        mean_per_facility_by_region   - {region: mean MUSD/facility}
        counts                        - {"modeled", "unmodeled_region", "unmapped_asset"}
        rows                          - per-facility priced records (list of dict)
    """
    est = DecommissioningCostEstimator()
    rows: list[dict] = []
    unmodeled_region = 0
    unmapped_asset = 0
    for _, r in df.iterrows():
        reg = region_of(r.get("COUNTRY"), r.get("US_GOM_FLAG"))
        if reg is None:
            unmodeled_region += 1
            continue
        asset = classify_asset_type(r.get("HOST_TYPE"))
        if asset is None:
            unmapped_asset += 1
            continue
        wd = r.get("WATER_DEPTH_M")
        wd = 0.0 if pd.isna(wd) else float(wd)
        e = est.estimate(asset_type=asset, water_depth_m=wd, weight_tonnes=0.0, region=reg)
        rows.append(
            {
                "facility_id": r.get("FACILITY_ID"),
                "facility_name": r.get("FACILITY_NAME"),
                "country": r.get("COUNTRY"),
                "region": reg,
                "asset": asset,
                "host_type": str(r.get("HOST_TYPE")).strip(),
                "water_depth_m": wd,
                "cost_musd": e.estimated_cost_musd,
            }
        )

    res = pd.DataFrame(rows)
    by_region: dict[str, dict] = {}
    by_asset: dict[str, dict] = {}
    mean_per_facility_by_region: dict[str, float] = {}
    total_musd = 0.0
    if not res.empty:
        total_musd = round(float(res["cost_musd"].sum()), 4)
        gr = res.groupby("region")["cost_musd"].agg(["sum", "count", "mean"])
        for reg, row in gr.iterrows():
            by_region[reg] = {"sum_musd": round(float(row["sum"]), 4), "count": int(row["count"])}
            mean_per_facility_by_region[reg] = round(float(row["mean"]), 4)
        ga = res.groupby("asset")["cost_musd"].agg(["sum", "count"])
        for asset, row in ga.iterrows():
            by_asset[asset] = {"sum_musd": round(float(row["sum"]), 4), "count": int(row["count"])}

    return {
        "total_musd": total_musd,
        "by_region": by_region,
        "by_asset": by_asset,
        "mean_per_facility_by_region": mean_per_facility_by_region,
        "counts": {
            "modeled": len(rows),
            "unmodeled_region": unmodeled_region,
            "unmapped_asset": unmapped_asset,
        },
        "rows": rows,
    }
