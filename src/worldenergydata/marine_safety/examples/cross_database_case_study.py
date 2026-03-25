# ABOUTME: Cross-database marine safety case study — MAIB, IMO, EMSA, TSB correlation.
# ABOUTME: Runnable script demonstrating unified query, correlation analysis, and findings.

"""
Cross-Database Marine Safety Case Study
========================================

Queries all four major marine safety investigation authorities (MAIB, IMO,
EMSA, TSB), runs correlation analysis, identifies top findings, and prints
a formatted summary report to stdout.

Usage
-----
    python -m worldenergydata.marine_safety.examples.cross_database_case_study

or directly:

    python cross_database_case_study.py
"""

from worldenergydata.marine_safety.cross_database import (
    CrossDatabaseAnalyzer,
    CrossDatabaseQuery,
)


def _section(title: str) -> None:
    width = 64
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _subsection(title: str) -> None:
    print()
    print(f"-- {title} --")


def main() -> None:
    analyzer = CrossDatabaseAnalyzer()

    # ------------------------------------------------------------------ #
    # 1. Full cross-database query                                        #
    # ------------------------------------------------------------------ #
    _section("CROSS-DATABASE MARINE SAFETY CASE STUDY")
    print("Querying all 4 sources: MAIB, IMO, EMSA, TSB (2015-2024)")

    result = analyzer.query(CrossDatabaseQuery())

    print(f"\nTotal incidents retrieved : {result.total_incidents}")
    print("Breakdown by source:")
    for src, count in sorted(result.by_source.items()):
        print(f"  {src.upper():6s} : {count:4d} incidents")

    # ------------------------------------------------------------------ #
    # 2. Correlation analysis                                             #
    # ------------------------------------------------------------------ #
    _section("CORRELATION ANALYSIS")

    corrs = analyzer.correlations(result.data)

    _subsection("Incident type severity ranking (mean score 1=minor … 5=fatal)")
    type_sev = corrs["incident_type_severity"]
    for _, row in type_sev.iterrows():
        print(f"  {row['incident_type']:20s}  {row['mean_severity_score']:.2f}")

    _subsection("Source cross-reporting overlap rate")
    overlap = corrs["source_overlap_rate"]
    print(f"  Incidents in same type/year/region across 2+ sources: {overlap:.1%}")

    _subsection("Year-over-year trend (all sources, last 5 years)")
    trend = corrs["trend_yoy"]
    recent = trend[trend["year"] >= 2020]
    yoy_total = recent.groupby("year")["count"].sum()
    for yr, cnt in yoy_total.items():
        print(f"  {yr}: {cnt:3d} incidents")

    _subsection("Top 5 incident types")
    top = analyzer.top_incident_types(result.data, n=5)
    for _, row in top.iterrows():
        print(f"  {row['incident_type']:20s}  {int(row['count']):3d}")

    # ------------------------------------------------------------------ #
    # 3. Risk hotspots                                                    #
    # ------------------------------------------------------------------ #
    _section("RISK HOTSPOTS — REGION x INCIDENT TYPE")

    hotspots = analyzer.risk_hotspots(result.data)
    print(hotspots.to_string())

    # ------------------------------------------------------------------ #
    # 4. Top 3 findings                                                   #
    # ------------------------------------------------------------------ #
    _section("TOP 3 FINDINGS")

    # Finding 1: Tanker grounding rate in North Sea
    north_sea_tankers = result.data[
        (result.data["region"] == "north_sea")
        & (result.data["vessel_type"] == "tanker")
    ]
    global_tankers = result.data[result.data["vessel_type"] == "tanker"]
    ns_ground_rate = (
        (north_sea_tankers["incident_type"] == "grounding").sum()
        / len(north_sea_tankers)
        if len(north_sea_tankers) > 0
        else 0
    )
    global_ground_rate = (
        (global_tankers["incident_type"] == "grounding").sum()
        / len(global_tankers)
        if len(global_tankers) > 0
        else 0
    )
    ratio = ns_ground_rate / global_ground_rate if global_ground_rate > 0 else float("inf")
    print(
        f"\n[Finding 1] Tankers in North Sea have a {ratio:.1f}x higher grounding"
        f" rate ({ns_ground_rate:.1%}) than the global tanker average"
        f" ({global_ground_rate:.1%})."
    )

    # Finding 2: Fishing vessels — highest fatal severity share
    fatal_by_type = result.data[result.data["severity"] == "fatal"].groupby(
        "vessel_type"
    ).size()
    total_by_type = result.data.groupby("vessel_type").size()
    fatal_rate = (fatal_by_type / total_by_type).sort_values(ascending=False)
    top_fatal_vessel = fatal_rate.index[0]
    top_fatal_pct = fatal_rate.iloc[0]
    print(
        f"\n[Finding 2] '{top_fatal_vessel}' vessels have the highest proportion"
        f" of fatal incidents at {top_fatal_pct:.1%} of their incidents across"
        f" all four databases."
    )

    # Finding 3: MAIB and EMSA report overlapping North Sea tanker groundings
    ns_tanker_groundings = result.data[
        (result.data["region"] == "north_sea")
        & (result.data["vessel_type"] == "tanker")
        & (result.data["incident_type"] == "grounding")
    ]
    sources_reporting = ns_tanker_groundings["source"].unique().tolist()
    print(
        f"\n[Finding 3] North Sea tanker groundings are reported by"
        f" {len(sources_reporting)} of 4 sources"
        f" ({', '.join(sorted(sources_reporting)).upper()}), suggesting"
        f" shared jurisdiction and potential for cross-authority"
        f" data reconciliation studies."
    )

    print()
    print("Case study complete.")


if __name__ == "__main__":
    main()
