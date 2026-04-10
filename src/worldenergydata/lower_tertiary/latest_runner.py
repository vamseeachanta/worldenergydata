# ABOUTME: Orchestrates extended lower tertiary analysis for WRK-010
# ABOUTME: Runs production through Oct 2025 and compares against V30 baseline
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from worldenergydata.lower_tertiary.production_classifier import (
    classify_production,
    summarize_classification,
)
from worldenergydata.lower_tertiary.v30_reproducer import (
    load_golden_baseline,
    reproduce_v30_production,
)
from worldenergydata.lower_tertiary.wti_prices import (
    get_wti_source_summary,
    load_extended_wti_prices,
)

logger = logging.getLogger(__name__)

# Corrected first_oil dates applied on top of golden baseline.
# Golden baseline is NEVER modified — these override in code only.
FIRST_OIL_CORRECTIONS: dict[str, str] = {
    "Cascade Chinook": "2012-09-01",
}


def _compute_development_revenue(
    monthly_production: pd.DataFrame,
    wti_df: pd.DataFrame,
) -> float:
    """Compute total revenue by merging monthly production with WTI prices.

    Parameters
    ----------
    monthly_production : pd.DataFrame
        Columns: date, oil_bbl
    wti_df : pd.DataFrame
        Columns: Month, WTI_USD

    Returns
    -------
    float
        Total revenue in USD (oil_bbl * WTI_USD summed across all months).
    """
    merged = monthly_production.merge(
        wti_df[["Month", "WTI_USD"]],
        left_on="date",
        right_on="Month",
        how="left",
    )
    merged["revenue_usd"] = merged["oil_bbl"] * merged["WTI_USD"]
    total_revenue: float = float(merged["revenue_usd"].sum())
    return total_revenue


def run_latest_analysis(end_date: str = "2025-10-31") -> dict[str, Any]:
    """Run extended lower tertiary production analysis through ``end_date``.

    Reproduces V30 production with an extended date window, loads WTI prices
    covering the full period, and computes per-development revenue.

    Returns
    -------
    dict
        Keys: ``metadata`` (run parameters), ``developments`` (per-dev results).
    """
    logger.info("Running latest analysis through %s", end_date)

    production = reproduce_v30_production(
        end_date=end_date,
        first_oil_overrides=FIRST_OIL_CORRECTIONS,
    )
    wti_df = load_extended_wti_prices(through_date=end_date)
    wti_summary = get_wti_source_summary(wti_df)

    developments: dict[str, Any] = {}
    for dev_name, dev_data in production.items():
        monthly_prod: pd.DataFrame = dev_data["monthly_production"]
        total_revenue = _compute_development_revenue(monthly_prod, wti_df)

        developments[dev_name] = {
            "total_oil_bbl": dev_data["total_oil_bbl"],
            "months": dev_data["months"],
            "first_date": str(dev_data["first_date"].date()),
            "last_date": str(dev_data["last_date"].date()),
            "total_revenue_usd": total_revenue,
            "monthly_production": monthly_prod,
        }
        logger.info(
            "%s: %,.0f bbl, $%,.2f revenue",
            dev_name,
            dev_data["total_oil_bbl"],
            total_revenue,
        )

    metadata: dict[str, Any] = {
        "end_date": end_date,
        "time_period": f"Sep 2000 through {pd.Timestamp(end_date).strftime('%b %Y')}",
        "data_vintage": (
            f"OGOR through {pd.Timestamp(end_date).strftime('%b %Y')}, "
            f"WTI through {pd.Timestamp(end_date).strftime('%b %Y')}"
        ),
        "wti_source_summary": wti_summary,
    }

    logger.info(
        "Analysis complete: %d developments, WTI sources: %s",
        len(developments),
        wti_summary,
    )

    return {
        "metadata": metadata,
        "developments": developments,
    }


def compare_against_v30(latest_results: dict[str, Any]) -> dict[str, Any]:
    """Compare latest analysis results against the V30 golden baseline.

    Parameters
    ----------
    latest_results : dict
        Output from :func:`run_latest_analysis`.

    Returns
    -------
    dict
        Keys: ``developments`` (per-dev comparison), ``deviations`` (significant
        changes only), ``exploration_unchanged`` (zero-production projects).
    """
    baseline = load_golden_baseline()
    latest_devs = latest_results["developments"]

    comparisons: dict[str, dict[str, Any]] = {}
    deviations: list[dict[str, Any]] = []
    exploration_unchanged: list[str] = []

    for _proj_id, proj_data in baseline["projects"].items():
        display_name: str = proj_data["display_name"]
        v30_oil: int = proj_data.get("total_oil_bbl", 0)
        v30_revenue: float = float(proj_data.get("revenue_usd", 0))

        # Exploration projects with no production
        if v30_oil == 0 and display_name not in latest_devs:
            exploration_unchanged.append(display_name)
            continue

        latest_oil = (
            latest_devs[display_name]["total_oil_bbl"]
            if display_name in latest_devs
            else 0
        )
        latest_revenue = (
            latest_devs[display_name]["total_revenue_usd"]
            if display_name in latest_devs
            else 0.0
        )

        delta_oil = latest_oil - v30_oil
        delta_oil_pct = round((delta_oil / v30_oil) * 100, 2) if v30_oil else 0.0

        delta_revenue = latest_revenue - v30_revenue
        delta_revenue_pct = (
            round((delta_revenue / v30_revenue) * 100, 2) if v30_revenue else 0.0
        )

        is_significant = abs(delta_oil_pct) > 5
        explanation = _generate_explanation(delta_oil_pct, is_significant)

        comparisons[display_name] = {
            "v30_oil_bbl": v30_oil,
            "latest_oil_bbl": latest_oil,
            "delta_oil_bbl": delta_oil,
            "delta_oil_pct": delta_oil_pct,
            "v30_revenue_usd": v30_revenue,
            "latest_revenue_usd": latest_revenue,
            "delta_revenue_usd": delta_revenue,
            "delta_revenue_pct": delta_revenue_pct,
            "is_significant": is_significant,
            "explanation": explanation,
        }

        if is_significant:
            deviations.append(
                {
                    "development": display_name,
                    "delta_oil_pct": delta_oil_pct,
                    "explanation": explanation,
                }
            )

    logger.info(
        "V30 comparison: %d developments, %d significant deviations, "
        "%d exploration unchanged",
        len(comparisons),
        len(deviations),
        len(exploration_unchanged),
    )

    return {
        "developments": comparisons,
        "deviations": deviations,
        "exploration_unchanged": exploration_unchanged,
    }


def _generate_explanation(delta_oil_pct: float, is_significant: bool) -> str:
    """Auto-generate an explanation string for significant production deltas."""
    if not is_significant:
        return ""
    if delta_oil_pct > 50:
        return "Ramping field — significant new production in extended window"
    if delta_oil_pct > 5:
        return "Active producing field with material new production"
    # Negative significant deviation (decline beyond 5%)
    return "Production decline exceeds significance threshold"


def run_classified_analysis(
    end_date: str = "2025-10-31",
) -> dict[str, Any]:
    """Run latest analysis with well-test vs commercial classification.

    Extends :func:`run_latest_analysis` by classifying each development's
    raw OGOR records into well_test / commercial / non_producing using
    PRODUCT_CODE, WELL_STAT_CD, and first_oil dates.

    Returns the same structure as *run_latest_analysis* with additional keys
    per development: ``well_test_oil_bbl``, ``classification_summary``.
    """
    from worldenergydata.lower_tertiary.v30_reproducer import (
        _build_first_oil_map,
        load_ogor_production,
        load_v30_leases,
    )

    latest = run_latest_analysis(end_date=end_date)

    # Load raw OGOR at well level for classification
    leases_df = load_v30_leases()
    end_year = max(2025, int(end_date[:4]))
    ogor_df = load_ogor_production(start_year=2000, end_year=end_year)
    ogor_df = ogor_df[(ogor_df["date"] >= "2000-09-01") & (ogor_df["date"] <= end_date)]

    # Map to developments at record level
    lease_to_dev = dict(zip(leases_df["LEASE_NUM"], leases_df["DEV_NAME"]))
    v30_leases = set(lease_to_dev.keys())
    ogor_filtered = ogor_df[ogor_df["LEASE_NUMBER"].isin(v30_leases)].copy()
    ogor_filtered["development"] = ogor_filtered["LEASE_NUMBER"].map(lease_to_dev)
    ogor_filtered = ogor_filtered.rename(columns={"MON_O_PROD_VOL": "oil_bbl"})

    # Build first_oil_map with corrections
    baseline = load_golden_baseline()
    first_oil_map = _build_first_oil_map(baseline)
    if FIRST_OIL_CORRECTIONS:
        for dev_name, date_str in FIRST_OIL_CORRECTIONS.items():
            first_oil_map[dev_name] = pd.Timestamp(date_str)

    classified = classify_production(ogor_filtered, first_oil_map=first_oil_map)
    cls_summary = summarize_classification(classified)

    # Enrich latest results with classification data
    for dev_name, dev_data in latest["developments"].items():
        if dev_name in cls_summary:
            dev_data["well_test_oil_bbl"] = cls_summary[dev_name]["well_test_oil_bbl"]
            dev_data["classification_summary"] = cls_summary[dev_name]
        else:
            dev_data["well_test_oil_bbl"] = 0.0
            dev_data["classification_summary"] = {}

    latest["metadata"]["classification"] = "well_test / commercial / non_producing"
    return latest


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    results = run_latest_analysis()
    comparison = compare_against_v30(results)

    logger.info("=" * 80)
    logger.info("Extended Lower Tertiary Analysis — WRK-010")
    logger.info(f"Period: {results['metadata']['time_period']}")
    logger.info(f"Data: {results['metadata']['data_vintage']}")
    logger.info("=" * 80)

    header = (
        f"{'Development':<25} {'Latest Oil':>15} {'V30 Oil':>15} "
        f"{'Delta %':>10} {'Significant':>12}"
    )
    logger.info(header)
    logger.info("-" * 80)

    for dev_name, comp in comparison["developments"].items():
        logger.info(
            f"{dev_name:<25} {comp['latest_oil_bbl']:>15,.0f} "
            f"{comp['v30_oil_bbl']:>15,.0f} {comp['delta_oil_pct']:>+10.2f}% "
            f"{'YES' if comp['is_significant'] else '':>12}"
        )

    if comparison["deviations"]:
        logger.info(f"\nSignificant deviations ({len(comparison['deviations'])}):")
        for dev in comparison["deviations"]:
            logger.info(
                f"  {dev['development']}: {dev['delta_oil_pct']:+.2f}% "
                f"— {dev['explanation']}"
            )

    if comparison["exploration_unchanged"]:
        logger.info(
            f"\nExploration unchanged: {', '.join(comparison['exploration_unchanged'])}"
        )
