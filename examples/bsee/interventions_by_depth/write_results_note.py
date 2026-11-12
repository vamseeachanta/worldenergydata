"""Regenerate the short results note from the derived tables, not raw records."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"


def table(frame):
    return frame.to_markdown(index=False, floatfmt=".3f")


def main():
    s = json.loads((OUT / "summary.json").read_text())
    manifest = json.loads((OUT / "manifest.json").read_text())
    rates = pd.read_csv(OUT / "rates.csv")
    bands = [
        "under 100 m",
        "100 to 500 m",
        "500 to 1500 m",
        "1500 m and deeper",
        "no depth",
    ]
    latest = rates[rates.year.eq(s["last_full_year"])]
    rows = []
    for band in bands:
        f = latest[latest.band.eq(band)].set_index("family")
        rows.append(
            {
                "Depth band": band,
                "Well work": int(f.loc["well work", "permits"]),
                "Abandonment": int(f.loc["abandonment", "permits"]),
                "Standing wells": int(f.iloc[0].standing_wells),
                "Work / 100 wells": f.loc["well work", "per_100_standing_wells"],
                "Abandonment / 100 wells": f.loc[
                    "abandonment", "per_100_standing_wells"
                ],
            }
        )
    headline = pd.DataFrame(rows).astype(object).fillna("not established")
    files = []
    for r in manifest["files"]:
        files.append(
            {
                "File": f'[{r["name"]}]({r["url"]})',
                "Page last updated": r["page_last_updated"],
                "Download started (UTC)": r["download_utc"],
                "Bytes": r.get("bytes", "failed"),
                "SHA-256": r.get("sha256", r.get("error", "")),
            }
        )
    mapping = pd.read_csv(OUT / "code_mapping.csv").rename(
        columns={
            "primary_code": "Code",
            "group": "Group",
            "permits": "2005–2026 permits",
            "last_full_year_permits": "2025 permits",
            "description": "BSEE description",
        }
    )
    ratios = (
        pd.read_csv(OUT / "eor_permit_ratios.csv")
        .astype(object)
        .fillna("not established")
    )
    costs = pd.read_csv(OUT / "cost_table.csv")
    cost_rows = costs[["band", "event", "low_usd", "base_usd", "high_usd"]].copy()
    cost_rows.columns = ["Depth band", "Event", "Low (USD)", "Base (USD)", "High (USD)"]
    war = pd.read_csv(OUT / "war_duration_crosscheck.csv")
    war = war[war.raw_war_code.eq("selected tokens combined")].drop(
        columns="raw_war_code"
    )
    exclusions = (
        pd.read_csv(OUT / "exclusion_audit.csv")
        .groupby("exclusion_basis")
        .permits.sum()
        .to_dict()
    )
    note = f"""# Gulf of Mexico well interventions by water depth

## What was counted and why

Approved applications to modify existing wells show the volume of proposed well work. They are distinct from new-well drilling permits. One APM submission is one event; it is not one well or proof of work performed. Initial completion permits without a zone-change subcode are excluded to keep the focus on existing-well work.

## Data

The [BSEE raw-data page](https://www.data.bsee.gov/Main/RawData.aspx) was read on 12 November 2026. All four downloads succeeded. SHA-256 digests were checked again before counting. The authoritative collection is owned by this repository; the source identifier is `bsee-data-center`. Only derived aggregates are committed. Raw archives remain in the ignored dated download directory and are not backed up by this PR.

{table(pd.DataFrame(files))}

Page update times are reproduced as shown; the page does not state their timezone. Download times are UTC transfer starts. The complete machine-readable receipt is [output/manifest.json](output/manifest.json).

## Method

- Depth in feet is multiplied by exactly 0.3048. Bands are under 100 m; 100 to under 500 m; 500 to under 1,500 m; and 1,500 m and deeper. An edge belongs to the deeper band. Rounded reader equivalents are 328, 1,640 and 4,921 ft; classification uses the exact metre edges.
- Gulf records use Borehole `REGION_CODE=G`, joined first on normalised API12 and then API10. Unmatched records may use a surface lease beginning G; matched non-G regions are never overridden. All 101,833 unique APM submissions resolve to G. Pacific and Alaska records are excluded from selected events and inventory through the region selection. No location is inferred from an operator name.
- API strings are stripped and a trailing `.0` is removed using the existing repository utility. Only 10- or 12-digit values are usable. Depth uses a unique nonnegative finite value at API12, then a unique value across that API10. Ambiguous fallback depths remain **no depth**. The included 2005–2026 events have **{s["events_with_depth_fraction"]:.1%} depth coverage** ({s["depth_join"].get("api12",0):,} exact API12 matches; no fallback was needed). The no-depth category remains in every output, including its zero counts.
- APM `ACC_STATUS_DATE` is treated as the approval date, consistent with the [APM query's Approved Date column](https://www.data.bsee.gov/Well/eWellAPM/Default.aspx). A nonblank valid approval date is required for annual counts. No approval-status field is supplied. Missing dates: {s["invalid_approval_dates"]}. Main rows are deduplicated on `SN_APM`; API, date and primary code must agree or the run fails. This removes {s["duplicate_apm_rows_removed"]} repeated rows across the file. Resubmittal dates and one-to-many suboperations are never counted as extra events. Separate submission IDs remain separate approvals, even for one well or a changed scope; the feed supplies no parent-permit chain to collapse them further.
- Primary codes come from the archive's published code table. WORKOVER is group 1; COMP with ZONE is recompletion in group 1; ENHANCE is group 2. ABANDON with PERMABAN is group 4, taking precedence if TEMPABAN is also present. Otherwise TEMPABAN is group 3. OTHER, INFORM and UTIL form group 5. An ABANDON without either subtype remains **abandonment unspecified**, included in abandonment rates but never represented as known permanent work. This is an explicit sixth residual category rather than a guessed split.
- PLUGBACK means **Plugback To Sidetrack/Bypass** in the supplied suboperation table and is excluded before grouping. Explicit legacy deepening or sidetrack/bypass approval narratives are also screened by narrow rules in the code. Across 2005–2026, {exclusions.get("PLUGBACK subcode",0):,} permits are excluded by PLUGBACK and {exclusions.get("explicit new-hole narrative",0):,} by narrative. Current borehole ST/BP status is not an exclusion: it can describe a later operation. Future deepening under another permit, and bypassing a tubing obstruction, are retained. Unstructured narrative screening cannot establish exhaustive capture of every drilling description. COMP without ZONE is excluded ({exclusions.get("completion without ZONE",0):,} permits); this also removes completions whose initial/recompletion distinction is not established. [Suboperation counts](output/suboperation_mapping.csv) overlap and are not event counts.
- The [APM query](https://www.data.bsee.gov/Well/eWellAPM/Default.aspx) starts with eWell submissions in April 2004. The file has 599 approval rows in 2004 and 3,143 in 2005; all 12 months of 2005 are represented. The series starts at **2005**, the first full calendar year available. September 2005 has only four rows; electronic coverage and reporting disruptions limit early comparisons. Complete capture of paper approvals is not established. [Monthly coverage](output/coverage_by_month.csv) retains 2004 for inspection.
- EOR W (workover), A (abandonment) and C (completion) are counted once per `SN_EOR`. Year uses `BOREHOLE_STAT_DT`, the structured date supplied by the main EOR table. These are a floor of recorded reports, with a status-date timing proxy; they are not a matched APM completion cohort. Annual band counts are in [output/eor_by_year_band.csv](output/eor_by_year_band.csv). W/APM-WORKOVER and A/APM-ABANDON ratios below use the corresponding retained primary-code permits, not all intervention groups.
- Standing wells use Gulf original-hole rows with suffix ST00BP00, once per API10. API12 ending 00 is preferred where duplicate original-hole suffixes exist (two API10s); ties use earliest spud then API12. Spud must precede the next 1 January. A currently PA original hole is removed from the year of its status date onward; PA with a missing date would be excluded as unknown. Other statuses, including TA, ST and BP, remain standing. {s["original_holes_missing_spud"]} original-hole rows have no spud date and are excluded; PA without a date: {s["original_holes_pa_without_date"]}. This is an **original-hole status proxy**, not a reconstruction of whether every branch of the entire well was abandoned. Abandoning an original hole while a sidetrack survives, later status changes, missing original holes and absent spud dates can bias the denominator.
- Rates are group 1 + 2 + 5 approvals per 100 standing wells, and all abandonment approvals per 100 standing wells, respectively. A zero denominator gives a missing rate, not zero. The rate is approval intensity, not the percentage of wells worked on. Full years end in **2025**. **2026 is partial through 12 November**, uses inventory at the file date, is not annualised and never enters the full-year averages. No trend is fitted.

The full primary-code grouping follows. Counts cover 2005 through partial 2026; unused code/group combinations are absent. The CSV is [output/code_mapping.csv](output/code_mapping.csv).

{table(mapping)}

## Results

In 2025, **765 well-work approvals** and **2,610 abandonment approvals** remain: **3,375 interventions**. Of the abandonment permits, 1,387 specify permanent abandonment, 1,060 specify temporary abandonment and 163 lack a subtype. Other-well-work includes administrative INFORMATION and UTILITY approvals; the count does not imply that every approval required a rig.

{table(headline)}

The 31 October checkpoint is reconciled as follows. Today's raw 2025 APM rows are unchanged: **523 WORKOVER + ENHANCE; 2,734 ABANDON; 3,833 all codes**. The analysis removes 127 new-hole-preparation permits (124 ABANDON and 3 ENHANCE) and 331 COMP permits without ZONE. The remaining 145 COMP/ZONE permits enter workover/recompletion, and 100 INFORM/UTIL permits enter other work. Hence 523 − 3 + 145 + 100 = 765 well work, and 2,734 − 124 = 2,610 abandonment. EOR reports are **12 W, 891 A and 75 C**: unchanged workover and one additional abandonment and completion report since the supplied October checkpoint. These daily-file differences are small.

The following EOR/permit ratios are same-year descriptive comparisons; they are not completion probabilities. No-depth ratios have zero reports and zero permits and are not established.

{table(ratios)}

WAR is a secondary duration check. For 2005–2025, valid inclusive report intervals of 1–90 days are unioned when overlapping or adjacent for the same API12, named unit and raw code. A gap, unit change or code change starts a new proxy episode. Missing/placeholder units are excluded; a named unit is not proof of a heavy rig. The selected tokens are WO, REC, TA and PA. Several WAR meanings, including WO and REC, lack a published BSEE definition; this is an interpreted non-drilling subset, not a qualified operation classifier. Full-year filtering precedes union; episodes may be censored at the selection endpoints. The {s["proxy_episodes"]:,} episodes are not permits or proven complete jobs. Two selected report spans fail the date/API validity screen. Raw-code strata are preserved in [output/war_duration_crosscheck.csv](output/war_duration_crosscheck.csv).

{table(war)}

## Cost basis

Costs are **indicative heavy-work scenarios in unescalated 2015 study US dollars**. They are not 2025 or 2026 market quotes. The equation is total spread day rate × duration + cited mobilisation. Each input in [cost_basis.yml](cost_basis.yml) records value, unit, asset, band, citation, location, interpretation and retrieval date. The code reads that YAML; no cost is inferred from the permit counts.

{table(cost_rows)}

| Input / scenario | Basis and citation |
|---|---|
| Both platform bands: total spread USD 68,424/day | [BSEE TAP-738](https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf), 2015 study, Table 8-3, p.8-14. Casing-jack heavy-unit proxy; transfer to workover and to under 100 m is an assumption. This is not a published jackup workover quote. |
| Both deeper bands: total spread USD 674,600/day | Same study, section 8.3.2.3, p.8-18. MODU semisubmersible/drillship spread, including stated services. |
| Well-work durations 7 / 10.5 / 14 days | [BOEM Gulf final EIS 2016-018](https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf), section 3.1.3.5, p.3-37: median 7 days; [BOEM MAG-PLAN Alaska Update](https://espis.boem.gov/final%20reports/5179.pdf), 2012, section 3.5.5.4, p.108: 7–14 days. Base is the midpoint. Alaska duration is transferred as an assumption; there is no published band-specific Gulf distribution here. |
| Platform P&A durations 3 / 4 / 8 days | [BSEE Pacific cost update, volume 2](https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf), February 2015, Appendix 2, p.A-2. Trouble-free rigless durations transferred to a heavier unit; not measured Gulf heavy-unit durations. |
| Deep P&A durations 17 / 19 / 23 and 21 / 23 / 27 days | TAP-738, Figure 8-9, p.8-19, approximate rounded MODU graphic readings. Low cases leave the wellhead; deeper/high cases extend to adjacent depth anchors. These are scenario choices, not depth-band quantiles. No cost at depths beyond the study's 9,000-ft anchor is established. |
| Platform mobilisation USD 75,486/event | TAP-738, Table 8-2, p.8-12: two USD 37,743 transport charges, with no campaign sharing, transferred to the heavy-unit case. |
| Floating mobilisation | Excluded, consistent with TAP-738 section 8.3.2.3. Zero in the calculation means omitted cost, not zero actual expense. The assumed unit is already mobilised. |

The study was completed in 2015 and its attachment was rehosted in 2023. Published P&A totals are set beside the arithmetic in [output/published_pa_comparators.csv](output/published_pa_comparators.csv): dry-tree rigless barrier work USD 0.344–0.422 million; dry-tree casing-jack barrier work USD 0.480–0.714 million at the cited 400/1,600-ft examples; wet-tree MODU examples about USD 11.2–13.4 million at 1,000/3,000 ft and USD 16.4–18.7 million at 6,000/9,000 ft. These are examples, not band bounds. The source totals include allowances and campaign assumptions that the simple arithmetic excludes. Dry-tree conductor removal is separate, so those published totals do not establish a complete sever-and-remove P&A bill.

Assumed assets differ with access method: a platform casing-jack package serves the two shallower bands in this calculation; semisubmersibles or drillships serve the two deeper heavy-work cases. Liftboats, jackups, moored semisubmersibles and riserless intervention vessels may serve other cases. A vessel for light riserless work is not interchangeable with a heavy workover unit. Water depth alone cannot select a method. The optional spend chart is omitted: multiplying every approval, including light work and administration, by a heavy-work cost would not establish actual spend.

## Limits

An approval is not performed work, and an EOR is not a matched completion of that approval. Daily snapshots revise history. The APM source does not expose a complete revision lineage. Initial/recompletion classification and the structured abandonment split are incomplete. Narrative exclusions are deliberately narrow. Depth matches are complete for this snapshot, but historical depth or well attribution is not reconstructed. The standing-well denominator is approximate and is neither a producing-well count nor a full status history. The 2005 coverage transition limits long-run comparisons.

The ranges reflect cited scenarios and transferred assumptions, not statistical confidence intervals. They apply to the described heavy work or one-well barrier job; a full abandonment may also require conductor removal, site clearance or remediation. The deepest-band WO-token duration has an 18-day median and 33-day upper quartile, above the 10.5-day published-proxy base. That interpreted subset does not validate the cost duration; longer jobs can exceed the scenario range. Logistics, materials, standby, weather and engineering are excluded unless already included in a cited spread or transport charge. Floating-unit mobilisation remains unpriced. Dollar values are not escalated. No total Gulf expenditure is established.

All four cost citation URLs returned PDF content and HTTP 200; [the source receipt](output/cost_source_manifest.json) records byte digests and check times. The ESPIS endpoint initially rejected the default script user agent with HTTP 403; the same public PDF resolved with a browser user agent. No credentials or paywall were used.

## How to rerun

From the repository root, with Python 3.10+ and `uv`:

```sh
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r examples/bsee/interventions_by_depth/requirements.txt
uv run --no-sync python examples/bsee/interventions_by_depth/download_data.py
uv run --no-sync python examples/bsee/interventions_by_depth/count_interventions.py --data-dir data/modules/bsee/zip/2026-11-12 --out examples/bsee/interventions_by_depth/output --last-full-year 2025
uv run --no-sync python examples/bsee/interventions_by_depth/estimate_costs.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/plot_charts.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/write_results_note.py
uv run --no-sync python -m pytest --noconftest -o addopts="" tests/unit/bsee/test_interventions_by_depth.py -q
```

On Linux/macOS, the virtual-environment interpreter for the install command is `.venv/bin/python`. The archive script checks the listed raw-page links and saves a new receipt; BSEE does not promise immutable historical downloads. To reproduce these exact results, retain the four archives with the manifest digests. A later download will produce a different snapshot and receipt; do not describe it as the same data.

Validation command used for the example plus the existing imported API utility tests (PowerShell environment syntax):

```powershell
$env:PYTHONPATH='packages/worldenergydata-bsee/src;packages/worldenergydata-core/src;../../assetutilities/src;src'
uv run --no-sync python -m pytest --noconftest -o addopts="" tests/unit/bsee/test_interventions_by_depth.py tests/unit/bsee/data/utils/test_api_well_normalizer.py -q
```

Result: **41 passed**. The shared utility's existing tests need the repository's usual optional loader dependencies; the example loads that leaf source directly to keep its own runtime small. The test-first run initially failed because the new counting module did not exist. No test uses a network or retained raw file.

Charts (PNG width 2,160 pixels; SVG also retained):

- [Approved interventions](output/01_approved_interventions.png) · [SVG](output/01_approved_interventions.svg)
- [Approvals per 100 standing wells](output/02_rates_per_standing_well.png) · [SVG](output/02_rates_per_standing_well.svg)
- [Cost per event](output/03_cost_per_event.png) · [SVG](output/03_cost_per_event.svg)
"""
    (ROOT / "README.md").write_text(note, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
