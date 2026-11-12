"""Materialise source-year cost scenarios by well access method (no network)."""

from pathlib import Path

import yaml

RETRIEVED = "2026-11-12"
SOURCES = {
    "bsee738": dict(
        title="Decommissioning Methodology and Cost Evaluation, TAP-738",
        publisher="BSEE / ICF International",
        date="2015-07-31",
        url="https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf",
        retrieval_date=RETRIEVED,
        note="2015 study market; later rehosting does not change the dollar year.",
    ),
    "bsee735": dict(
        title="Decommissioning Cost Update for Pacific OCS Region Facilities, Volume 2",
        publisher="BSEE / TSB Offshore",
        date="2015-02",
        url="https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf",
        retrieval_date=RETRIEVED,
    ),
    "boem2016": dict(
        title="Gulf of Mexico OCS Oil and Gas Lease Sales 2017-2022, Final EIS, Volume I, BOEM 2016-018",
        publisher="BOEM",
        date="2016",
        url="https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf",
        retrieval_date=RETRIEVED,
    ),
    "boem2012": dict(
        title="MAG-PLAN Alaska Update, BOEM 2011-059",
        publisher="BOEM / Northern Economics",
        date="2012-05-31",
        url="https://espis.boem.gov/final%20reports/5179.pdf",
        retrieval_date=RETRIEVED,
    ),
}


def fact(value, unit, asset, applicability, source, location, interpretation):
    return dict(
        value=value,
        unit=unit,
        asset=asset,
        applicability=applicability,
        citation={**SOURCES[source], "location": location},
        interpretation=interpretation,
    )


def build():
    scenarios = []
    definitions = [
        (
            "platform_rigless",
            "Platform dry-tree / rigless spread",
            "Shelf; source case 50-400 ft (15-122 m)",
            "rigless platform spread",
            64530,
            "Table 8-2, p.8-12 (PDF p.143): USD 225856 / 84 hr x 24, rounded to USD 64530/day",
        ),
        (
            "platform_casing",
            "Platform dry-tree / casing jacks",
            "Platform-based spread; source casing-jack case above 400 ft; shelf example",
            "platform casing-jack spread",
            68424,
            "Table 8-3, p.8-14 (PDF p.145): total spread/day",
        ),
        (
            "subsea",
            "Subsea wet-tree / drillship or semisubmersible",
            "Subsea access; durations anchored at 3000 ft (914 m); not all wells in a depth band",
            "drillship or semisubmersible total spread",
            674600,
            "Section 8.3.2.3, p.8-18 (PDF p.149): total MODU spread",
        ),
    ]
    for prefix, access, applicability, asset, rate, rate_location in definitions:
        events = ["well work", "permanent abandonment"]
        for event in events:
            options = [
                (
                    "",
                    (
                        [7, 10.5, 14]
                        if event == "well work"
                        else [3, 4, 8] if prefix != "subsea" else [17, 19, 23]
                    ),
                )
            ]
            if prefix == "subsea" and event == "permanent abandonment":
                options.append(("_6000_9000ft", [21, 23, 27]))
            for suffix, durations in options:
                app = (
                    applicability
                    if not suffix
                    else "Subsea access; 6000-9000 ft (1829-2743 m) anchors; extrapolation beyond 9000 ft not established"
                )
                if prefix == "subsea" and event == "well work":
                    app = "Subsea access; duration cases 7 / 10.5 / 14 days, not depth-specific; not all wells in a depth band"
                scenario = dict(
                    scenario_id=prefix
                    + ("_work" if event == "well work" else "_pa")
                    + suffix,
                    access_type=access,
                    applicability=app,
                    event=event,
                    asset=asset,
                    dollar_year=2015,
                    pricing_method="spread scenario",
                )
                for case, duration in zip(["low", "base", "high"], durations):
                    if event == "well work":
                        source = "boem2016" if case == "low" else "boem2012"
                        location = (
                            "Section 3.1.3.5, p.3-37 (PDF p.163): Gulf median 7 days; range 1 day to several months"
                            if case == "low"
                            else "Section 3.5.5.4, p.108 (PDF p.117): one to two weeks"
                        )
                        interpretation = "Median 7 days / midpoint 10.5 days / two weeks 14 days. Duration scenarios, not low/base/high outcome quantiles. Alaska interval transferred to Gulf spread; no access-specific observed distribution established."
                    elif prefix != "subsea":
                        source, location = (
                            "bsee735",
                            "Appendix 2, p.A-2 (PDF p.5), Days/Well 3, 4, 5, 8",
                        )
                        interpretation = "Pacific trouble-free rigless duration choices 3 / 4 / 8 days; transferred to Gulf spread. Casing-jack transfer is a scenario assumption."
                    else:
                        source, location = "bsee738", "Figure 8-9, p.8-19 (PDF p.150)"
                        interpretation = (
                            "Approximate rounded graphic readings; scenario anchors, not depth-band quantiles. "
                            + (
                                "MODU leaving wellhead at 3000 ft (~17 days), MODU at 3000 ft (~19) and 6000 ft (~23)."
                                if not suffix
                                else "MODU leaving wellhead at 6000 ft (~21), MODU at 6000 ft (~23) and 9000 ft (~27)."
                            )
                        )
                    scenario[case] = dict(
                        spread_dayrate=fact(
                            rate,
                            "USD/day",
                            asset,
                            app,
                            "bsee738",
                            rate_location,
                            "Published spread (rigless rate derived from published task cost and hours). Transfer to well work is an explicit scenario, not a quoted workover rate.",
                        ),
                        duration=fact(
                            duration,
                            "day/event",
                            asset,
                            app,
                            source,
                            location,
                            interpretation,
                        ),
                        mobilisation=fact(
                            0 if prefix == "subsea" else 75486,
                            "USD/event",
                            asset,
                            app,
                            "bsee738",
                            (
                                "Section 8.3.2.3, p.8-18: mobilisation excluded"
                                if prefix == "subsea"
                                else "Table 8-2, p.8-12: mob and demob USD 37743 each"
                            ),
                            (
                                "EXCLUDED, not zero actual expense; already mobilised unit."
                                if prefix == "subsea"
                                else "Two standalone transport charges; no campaign sharing. Transferred to casing-jack spread where applicable."
                            ),
                        ),
                    )
                scenarios.append(scenario)
    common = dict(
        access_type="Deepwater platform dry-tree / casing jacks",
        applicability="TLP dry-tree access (source); applied to spars as an assumption; Table 8-4 anchors 1700 / 3000 / 5000 ft (518 / 914 / 1524 m)",
        asset="dry-tree deepwater platform, 60-well casing-jack campaign",
        dollar_year=2015,
    )
    work = dict(
        common,
        scenario_id="deep_platform_work",
        event="well work",
        pricing_method="not priced",
        limitation="A cited well-work basis on this deepwater platform spread is not established; no price transferred from the subsea case.",
    )
    scenarios.append(work)
    pa = dict(
        common,
        scenario_id="deep_platform_pa",
        event="permanent abandonment",
        pricing_method="published total",
    )
    for case, value, depth in zip(
        ["low", "base", "high"], [734356, 987262, 1374570], [1700, 3000, 5000]
    ):
        pa[case] = dict(
            published_cost=fact(
                value,
                "USD/well",
                common["asset"],
                common["applicability"],
                "bsee738",
                f"Table 8-4, p.8-15 (PDF p.146), {depth} ft, final column: normalized cost per well",
                "Published 60-well campaign total divided by 60; includes work provision, engineering, weather and shared mobilisation. Barrier work; conductor removal separate. Cases are depth anchors, not outcome quantiles.",
            )
        )
    scenarios.append(pa)
    comparators = [
        dict(
            access_type="Platform dry-tree / rigless",
            applicability="50-400 ft source case",
            low_usd=344405,
            high_usd=421853,
            location="Table 8-2, p.8-12: 20-well and standalone campaigns",
        ),
        dict(
            access_type="Platform dry-tree / casing jacks",
            applicability="400 and 1600 ft anchors",
            low_usd=479820,
            high_usd=713836,
            location="Table 8-4, p.8-15: 60-well campaign",
        ),
        dict(
            access_type="Deepwater platform dry-tree / casing jacks",
            applicability="1700 and 5000 ft anchors",
            low_usd=734356,
            high_usd=1374570,
            location="Table 8-4, p.8-15: 60-well campaign",
        ),
        dict(
            access_type="Subsea wet-tree / drillship or semisubmersible",
            applicability="3000 ft point (914 m), within 500-1500 m",
            low_usd=13400000,
            high_usd=13400000,
            location="Figure 8-10, p.8-20: approximate MODU reading at 3000 ft; not 1000 ft",
        ),
        dict(
            access_type="Subsea wet-tree / drillship or semisubmersible",
            applicability="6000 and 9000 ft anchors",
            low_usd=16400000,
            high_usd=18700000,
            location="Figure 8-10, p.8-20: approximate MODU readings",
        ),
    ]
    for r in comparators:
        r.update(
            dollar_year=2015,
            unit="USD/well",
            source="bsee738",
            citation=SOURCES["bsee738"],
            scope="Permanent-abandonment barrier work; dry-tree conductor removal separate; subsea mobilisation excluded",
        )
    return dict(
        schema_version=2,
        retrieval_date=RETRIEVED,
        currency="Unescalated 2015 study USD; duration-source dates do not alter the dollar year.",
        method="Spread scenarios: dayrate x duration + mobilisation; deep platform P&A: published Table 8-4 total. Scenarios are not outcome distributions.",
        duration_case_labels={
            "low": "median 7 days",
            "base": "midpoint 10.5 days",
            "high": "two weeks 14 days",
        },
        assumptions=[
            "Access method selects cost; depth only states source applicability.",
            "Deepwater dry-tree well work is not priced without a cited basis.",
            "Permanent-abandonment costs do not apply to temporary or unspecified abandonment approvals.",
            "No expenditure estimate: approvals include repeats, administration and light work.",
            "Additional logistics, materials, standby, weather and engineering are excluded unless present in the cited spread or published total.",
        ],
        sources=SOURCES,
        scenarios=scenarios,
        published_pa_comparators=comparators,
    )


if __name__ == "__main__":
    Path(__file__).with_name("cost_basis.yml").write_text(
        yaml.safe_dump(build(), sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )
