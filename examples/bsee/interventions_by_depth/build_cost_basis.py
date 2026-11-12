"""Materialise the cited scenario inputs in cost_basis.yml (no network)."""

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
        note="Project completed in 2015; attachment rehosted in 2023. Cost basis is the study's 2015 market, not the rehosting year.",
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


def fact(value, unit, asset, band, source, location, interpretation):
    return dict(
        value=value,
        unit=unit,
        asset=asset,
        band=band,
        citation={**SOURCES[source], "location": location},
        interpretation=interpretation,
    )


def build():
    scenarios = []
    bands = ["under 100 m", "100 to 500 m", "500 to 1500 m", "1500 m and deeper"]
    for i, band in enumerate(bands):
        asset = (
            "platform casing-jack heavy unit (proxy)"
            if i < 2
            else "semisubmersible or drillship MODU spread"
        )
        spread = 68424 if i < 2 else 674600
        for event in ["well work", "permanent abandonment"]:
            scenario = dict(band=band, event=event, asset=asset, dollar_year=2015)
            durations = (
                [7, 10.5, 14]
                if event == "well work"
                else ([3, 4, 8] if i < 2 else [17, 19, 23] if i == 2 else [21, 23, 27])
            )
            for case, duration in zip(["low", "base", "high"], durations):
                rate = fact(
                    spread,
                    "USD/day",
                    asset,
                    band,
                    "bsee738",
                    (
                        "Table 8-3, p.8-14 (PDF p.145)"
                        if i < 2
                        else "Section 8.3.2.3, p.8-18 (PDF p.149)"
                    ),
                    "Published total spread. Transfer to workover is a scenario assumption; casing-jack package is a heavy-unit proxy, not a quoted workover rig rate.",
                )
                if event == "well work":
                    source = "boem2016" if case == "low" else "boem2012"
                    location = (
                        "Section 3.1.3.5, p.3-37 (PDF p.163): median 7 days"
                        if case == "low"
                        else "Section 3.5.5.4, p.108 (PDF p.117): one to two weeks"
                    )
                    interpretation = "Scenario 7 / 10.5 / 14 days: published Gulf median, midpoint and upper end of published Alaska 7-14-day range. Alaska duration is transferred explicitly; not a Gulf depth-specific estimate."
                elif i < 2:
                    source, location = (
                        "bsee735",
                        "Appendix 2, p.A-2 (PDF p.5), Days/Well 3, 4, 5, 8",
                    )
                    interpretation = "Low, medium-low and high trouble-free rigless P&A durations transferred to the heavier casing-jack unit. Pacific duration proxy; materials and contingencies excluded from arithmetic."
                else:
                    source, location = "bsee738", "Figure 8-9, p.8-19 (PDF p.150)"
                    interpretation = (
                        "Approximate rounded graphic readings: MODU leaving wellhead at 3000 ft (~17); MODU at 3000 ft (~19) and 6000 ft (~23). Scenario anchors span adjacent depths; not band quantiles."
                        if i == 2
                        else "Approximate rounded graphic readings: MODU leaving wellhead at 6000 ft (~21); MODU at 6000 ft (~23) and 9000 ft (~27). No estimate above the chart's 9000-ft anchor is established."
                    )
                days = fact(
                    duration, "day/event", asset, band, source, location, interpretation
                )
                mob = fact(
                    75486 if i < 2 else 0,
                    "USD/event",
                    asset,
                    band,
                    "bsee738",
                    (
                        "Table 8-2, p.8-12 (PDF p.143): mob and demob each USD 37743"
                        if i < 2
                        else "Section 8.3.2.3, p.8-18: mobilisation costs not included"
                    ),
                    (
                        "Two published standalone transport charges, no campaign sharing; transferred to casing-jack scenario."
                        if i < 2
                        else "EXCLUDED cost, not a finding of zero expense. Scenario assumes an already mobilised unit; no cited floating-unit mobilisation amount is available."
                    ),
                )
                scenario[case] = dict(
                    spread_dayrate=rate, duration=days, mobilisation=mob
                )
            scenarios.append(scenario)
    comparators = [
        dict(
            band=bands[0],
            scope="dry-tree rigless T&A barrier work; conductor removal separate",
            low_usd=344405,
            high_usd=421853,
            dollar_year=2015,
            source="bsee738",
            location="Table 8-2, p.8-12: 20-well versus standalone campaign",
        ),
        dict(
            band=bands[1],
            scope="dry-tree T&A with casing jacks; 60-well campaign",
            low_usd=479820,
            high_usd=713836,
            dollar_year=2015,
            source="bsee738",
            location="Table 8-4, p.8-15: 400 and 1600 ft; conductor removal separate",
        ),
        dict(
            band=bands[2],
            scope="wet-tree MODU P&A; approximate graphic readings; no mob/demob",
            low_usd=11200000,
            high_usd=13400000,
            dollar_year=2015,
            source="bsee738",
            location="Figure 8-10, p.8-20: 1000 and 3000 ft anchors, not band bounds",
        ),
        dict(
            band=bands[3],
            scope="wet-tree MODU P&A; approximate graphic readings; no mob/demob",
            low_usd=16400000,
            high_usd=18700000,
            dollar_year=2015,
            source="bsee738",
            location="Figure 8-10, p.8-20: 6000 and 9000 ft anchors",
        ),
    ]
    for row in comparators:
        row.update(
            unit="USD/well",
            asset="published study scenario",
            citation=SOURCES[row["source"]],
        )
    return dict(
        schema_version=1,
        retrieval_date=RETRIEVED,
        currency="Unescalated 2015 study USD; later and earlier duration sources change time only, not currency.",
        method="cost = total spread dayrate x duration + mobilisation. Scenario ranges, not confidence intervals, bids or observed averages.",
        assumptions=[
            "Dry-tree casing-jack spread used for both platform bands. A jackup/liftboat quote for the requested heavy-work scope is not established.",
            "MODU heavy scope used for both deeper bands. A riserless vessel serves lighter work and is not priced here.",
            "Quoted total spreads include the study's services. No extra materials, logistics, standby, weather or engineering markups are added.",
            "No total Gulf expenditure is estimated: administrative, light, temporary and repeated approvals cannot be priced as one heavy event each.",
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
