"""Regenerate the README and optional PR body from the derived tables."""

import argparse
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
BANDS = [
    "under 100 m",
    "100 to 500 m",
    "500 to 1500 m",
    "1500 m and deeper",
    "no depth",
]
TEST_COMMAND = 'uv run --no-sync python -m pytest --noconftest -o addopts="" tests/unit/bsee/test_interventions_by_depth.py tests/unit/bsee/data/utils/test_api_well_normalizer.py -q'


def table(frame):
    return frame.to_markdown(index=False, disable_numparse=True)


def rate(value):
    return f"{value:.1f}" if pd.notna(value) else "not established"


def million(value):
    if pd.isna(value):
        return "not priced"
    v = value / 1e6
    decimals = max(0, 1 - int(math.floor(math.log10(abs(v))))) if v else 0
    return f"{v:.{decimals}f}" if v else "0"


def main(pr_body=None, test_result="not run"):
    s = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    rates = pd.read_csv(OUT / "rates.csv")
    latest = rates[rates.year.eq(2025)].set_index(["band", "family"])
    ratios = pd.read_csv(OUT / "approvals_per_distinct_well.csv").set_index(
        ["band", "family"]
    )
    rows, ratio_rows = [], []
    for band in BANDS:
        w, a = latest.loc[(band, "well work")], latest.loc[(band, "abandonment")]
        rw, ra = ratios.loc[(band, "well work")], ratios.loc[(band, "abandonment")]
        rows.append(
            {
                "Depth band": band,
                "Work / abandonment approvals": f"{int(w.permits):,} / {int(a.permits):,}",
                "Distinct wells, work / abandonment": f"{int(rw.distinct_wells):,} / {int(ra.distinct_wells):,}",
                "Standing wells, 1 Jan": f"{int(w.standing_wells):,}",
                "Work / abandonment per 100": f"{rate(w.per_100_standing_wells)} / {rate(a.per_100_standing_wells)}",
            }
        )
        ratio_rows.append(
            {
                "Depth band": band,
                "Work approvals / well": rate(rw.approvals_per_well),
                "Abandonment approvals / well": rate(ra.approvals_per_well),
            }
        )
    headline = table(pd.DataFrame(rows))
    cost_frame = pd.read_csv(OUT / "cost_table.csv")
    cost_rows = []
    for r in cost_frame.itertuples():
        cost_rows.append(
            {
                "Well / access type": r.access_type,
                "Event": r.event,
                "Applicability": r.applicability,
                "Low / base / high (USD million, 2015)": (
                    " / ".join(million(v) for v in [r.low_usd, r.base_usd, r.high_usd])
                    if pd.notna(r.low_usd)
                    else "not priced"
                ),
            }
        )
    cost_table = table(pd.DataFrame(cost_rows))
    files = []
    for r in manifest["files"]:
        files.append(
            {
                "File": f'[{r["name"]}]({r["url"]})',
                "Page updated": r["page_last_updated"],
                "Bytes": f'{r["bytes"]:,}',
                "SHA-256": f'`{r["sha256"]}`',
            }
        )
    codes = pd.read_csv(OUT / "code_mapping.csv")
    primary = pd.read_csv(OUT / "primary_code_by_year.csv")
    other = primary[
        primary.APM_OP_CD.eq("OTHER") & primary.year.between(2005, 2020)
    ].approvals
    coding_note = (
        f"Primary OTHER approvals numbered {other.min()}–{other.max()} per year in 2005–2020, then 174 in 2021, 11 in 2022 and zero from 2023, while WORKOVER rose. "
        "Part of the apparent well-work decline reflects a coding change. The 2025 count should not be compared with the long-run mean without this qualification; electronic coverage also changes in the early years."
    )
    durations = pd.read_csv(OUT / "permit_duration_estimates.csv")
    duration_rows = []
    for band in BANDS:
        f = durations[durations.band.eq(band)].set_index("event")
        duration_rows.append(
            {
                "Depth band": band,
                "Well work, median days": (
                    f'{f.loc["well work","median_est_operation_days"]:.0f}'
                    if pd.notna(f.loc["well work", "median_est_operation_days"])
                    else "not established"
                ),
                "Permanent abandonment, median days": (
                    f'{f.loc["permanent abandonment","median_est_operation_days"]:.0f}'
                    if pd.notna(
                        f.loc["permanent abandonment", "median_est_operation_days"]
                    )
                    else "not established"
                ),
                "Valid estimates, work / permanent abandonment": f'{int(f.loc["well work","estimates"])} / {int(f.loc["permanent abandonment","estimates"])}',
            }
        )
    war = pd.read_csv(OUT / "war_duration_crosscheck.csv")
    for col in ["q25_days", "median_days", "q75_days"]:
        war[col] = war[col].map(lambda v: f"{v:.0f}")
    war = war[war.raw_war_code.eq("selected tokens combined")].drop(
        columns="raw_war_code"
    )
    shares = pd.read_csv(OUT / "unit_type_shares.csv")
    shares = shares[shares.period.astype(str).eq("2025")]
    categories = [
        "wireline unit",
        "coiled tubing",
        "hydraulic workover / snubbing",
        "platform rig",
        "liftboat / jack-up",
        "intervention vessel",
        "drillship / semisubmersible",
        "none named",
        "other",
    ]
    short = [
        "Wireline",
        "Coiled tubing",
        "HW / snubbing",
        "Platform rig",
        "Liftboat / jack-up",
        "Intervention vessel",
        "Drillship / semi",
        "None named",
        "Other",
    ]
    unit_tables = []
    for event in ["well work", "permanent abandonment"]:
        frame = (
            shares[shares.event.eq(event)]
            .pivot(index="band", columns="unit_category", values="share_percent")
            .reindex(BANDS)
        )
        frame = frame[categories].map(
            lambda v: rate(v) + "%" if pd.notna(v) else "not established"
        )
        frame.columns = short
        unit_tables.append(
            f"{event.capitalize()} — share of approvals, 2025:\n\n"
            + table(frame.reset_index())
        )
    subsea = pd.read_csv(OUT / "subsea_completion_shares.csv")
    subsea_rows = []
    for band in BANDS:
        f = subsea[
            subsea.period.astype(str).eq("2025") & subsea.band.eq(band)
        ].set_index("event")
        subsea_rows.append(
            {
                "Depth band": band,
                "Flag YES, work / permanent abandonment (%)": f'{rate(f.loc["well work","subsea_share_percent"])} / {rate(f.loc["permanent abandonment","subsea_share_percent"])}',
                "Unknown, work / permanent abandonment": f'{int(f.loc["well work","subsea_flag_unknown"])} / {int(f.loc["permanent abandonment","subsea_flag_unknown"])}',
            }
        )
    rules = pd.read_csv(OUT / "unit_type_mapping.csv")
    inventory = pd.read_csv(OUT / "standing_wells.csv")
    assumed = inventory[inventory.year.eq(2025)]
    assumed_note = (
        f"At 1 January 2025, {int(assumed.assumed_standing.sum()):,} wells are **assumed standing**: "
        f"{int(assumed.no_non_superseded_bore.sum()):,} have no non-superseded bore and "
        f"{int(assumed.missing_terminal_status_date.sum()):,} have a missing terminal status date (categories can overlap). "
        f'{s["inventory_missing_first_spud"]:,} API10 wells lack any non-cancelled first-spud date and are excluded; their historical stock cannot be dated.'
    )
    charts = """- [01 — Approved permits to modify by depth](output/01_approved_interventions.png) · [SVG](output/01_approved_interventions.svg)
- [02 — Approved permits to modify per 100 standing wells](output/02_rates_per_standing_well.png) · [SVG](output/02_rates_per_standing_well.svg)
- [03 — Cost scenarios by well and access type](output/03_cost_per_event.png) · [SVG](output/03_cost_per_event.svg)
- [04 — Unit types named on 2025 approvals by depth](output/04_unit_types_by_depth.png) · [SVG](output/04_unit_types_by_depth.svg)"""
    note = f"""# Gulf of Mexico well interventions by water depth

## What this adds

Approved permits to modify existing wells are counted separately from new-well drilling permits. One submission is one event, not one well or evidence of completed work. In 2025, **765 well-work approvals + 2,610 abandonment approvals = 3,375 events**. Permanent-abandonment costs apply only to the **1,387 permanent approvals**, not the 1,060 temporary or 163 unspecified abandonment approvals. No expenditure is inferred from counts.

## Data

The collection owner is worldenergydata; the catalog source ID is `bsee-data-center`. The four retained BSEE raw archives are dated 12 November 2026. Their size and SHA-256 are verified before use; this revision uses the retained files without downloading again. Raw archives are ignored and are not backed up by this PR. Only small derived aggregates and charts are committed.

{table(pd.DataFrame(files))}

[The manifest](output/manifest.json) retains download-start UTC timestamps and raw-page update times (timezone unspecified by BSEE). Source: [BSEE raw data](https://www.data.bsee.gov/Main/RawData.aspx).

## Method

- **ASSUMED - to be confirmed:** every APM main row represents an approved permit. `ACC_STATUS_DATE` is used as its approval date, consistent with the [query's Approved Date column](https://www.data.bsee.gov/Well/eWellAPM/Default.aspx); a separate approval-status field is absent. Counts require a valid date. Deduplication on `SN_APM` removes {s["duplicate_apm_rows_removed"]} repeated rows; conflicting API/date/primary-code identities fail. Different submission IDs remain separate, including repeated approvals for one well. Resubmittals and suboperations are not extra events.
- Gulf selection uses Borehole `REGION_CODE=G`, at API12 then API10; a G-prefixed lease is a fallback only for unmatched records. Matched non-G regions cannot be overridden. API normalisation uses the existing leaf utility and retains only 10- or 12-digit identifiers.
- Depth in feet is multiplied by exactly 0.3048. Bands are under 100 m, 100 to under 500 m, 500 to under 1,500 m, and 1,500 m and deeper; an edge enters the deeper band. Event depth uses a unique finite nonnegative API12 value then a unique API10 fallback; ambiguity remains **no depth**. Included events have {s["events_with_depth_fraction"]:.1%} depth coverage. No-depth rows are retained in CSVs and omitted from chart legends when event counts are zero.
- WORKOVER and COMP with ZONE form workover/recompletion; ENHANCE forms production enhancement; OTHER, INFORM and UTIL form other well work. ABANDON with PERMABAN is permanent (takes precedence over TEMPABAN), otherwise TEMPABAN is temporary, otherwise unspecified. The three abandonment groups are counted together for rates, but cost applies to permanent abandonment only. Information and utility permits do not establish rig work.
- PLUGBACK (the source's Plugback To Sidetrack/Bypass), primary new-hole codes and narrow explicit new-hole narratives are excluded. Current ST/BP status is never used to exclude historical approvals. COMP without ZONE is excluded. Narrative screening does not establish exhaustive capture of drilling descriptions. [Primary mapping](output/code_mapping.csv), [suboperations](output/suboperation_mapping.csv) and [exclusion audit](output/exclusion_audit.csv) retain the classification evidence.
- **Standing stock is rebuilt per API10 over all bores**, with CNL (cancelled) bores dropped before both first-spud and status evaluation. A well enters on its first non-cancelled spud date. ST and BP bores are superseded and cannot by themselves keep a well alive. A well leaves when every non-superseded bore is PA with a known status date on or before the stock date; the removal date is the latest of those PA dates. Any live terminal bore retains the well. A well with no non-superseded bore is retained as **assumed standing**, rather than treating the empty terminal set as proof of abandonment. A missing status date on any terminal bore also retains the well and is counted as assumed standing. Spud and status cutoffs are inclusive.
- Inventory depth uses the canonical original-hole depth (ST00BP00; API12 ending 00 preferred, then earliest spud/API12); a unique depth across remaining bores is used where no usable original depth exists. This preserves a stable well-level depth without discarding other bores' statuses. Conflicting fallback depths remain no depth.
- Rates use **wells standing on 1 January**, not year-end stock: approvals during the year can concern wells removed before year end. The numerator includes approvals during the year, including wells first spudded later in that year, so this is approval intensity against opening stock, not a matched-cohort probability. [Standing wells](output/standing_wells.csv) includes stock dates and assumed counts; [year-end stock](output/standing_wells_year_end.csv) is retained separately (partial 2026 capped at the file date). Zero stock yields a missing rate, not zero.
- Full years run 2005–2025; [full-year averages](output/full_year_averages.csv) exclude partial 2026 through 12 November. The 2026 denominator remains 1 January stock and its rates are not annualised. EOR W/A/C counts use one `SN_EOR` and the borehole-status date; these are not a matched APM completion cohort. [EOR counts](output/eor_by_year_band.csv) and [same-year ratios](output/eor_permit_ratios.csv) remain descriptive.

{assumed_note}

{coding_note} The feed begins in April 2004; [monthly coverage](output/coverage_by_month.csv) retains the early ramp. Current bore statuses and dates provide a retrospective proxy, not a complete state-transition history; earlier abandonments followed by reopening cannot be reconstructed.

## Headline results

2025 approvals and distinct API10 wells are shown separately. A well can appear in both event families; the two distinct-well columns must not be added as disjoint populations. The cost cases below apply to permanent abandonment only (1,387 of 2,610 abandonment approvals).

{headline}

Approval-to-well ratios, from [the CSV](output/approvals_per_distinct_well.csv): approvals are not wells.

{table(pd.DataFrame(ratio_rows))}

An earlier snapshot of 31 Oct 2026 (not retained here) supplies the comparison: the 2025 raw rows remain **523 WORKOVER + ENHANCE; 2,734 ABANDON; 3,833 all codes**. Exclusions are 127 new-hole preparations (124 ABANDON, 3 ENHANCE) and 331 COMP without ZONE. Retaining 145 COMP/ZONE and 100 INFORM/UTIL gives 523 − 3 + 145 + 100 = 765 well work, and 2,734 − 124 = 2,610 abandonment. EOR counts are 12 W, 891 A and 75 C: W unchanged, A and C each one higher than that earlier snapshot. The old snapshot cannot be independently re-read from this PR.

## Unit and access evidence

The permit's `RIG_ID_NUM` joins the archive's `mv_apm_rig_view` fields `RIG_TYPE_CODE` and `RIG_NAME` with a validated many-to-one join. The type code selects the category; names are retained in [the lookup](output/unit_type_lookup.csv) but are not used to guess equipment. The mapping below is also retained in [CSV](output/unit_type_mapping.csv). NR denotes a non-rig operation and enters none named; an unmatched nonblank ID or unmapped type enters other. SU is a submersible and is not classified as a semisubmersible. A permit's named unit need not be the unit ultimately deployed.

{table(rules)}

{chr(10).join(unit_tables)}

[Unit shares](output/unit_type_shares.csv) also retain pooled 2021–2025 counts and all zero/no-depth rows. Chart 04 uses 2025 to align with the headline counts. In 500–1,500 m, only **90 of 157** permanent-abandonment approvals name a drillship or semisubmersible, and **79 of 157** have no YES subsea-completion flag. Water depth cannot select an access method.

The share with an EOR `SUBSEA_COMPLETION_FLAG=YES` follows. This is an **ever-YES flag at API10 in the retained snapshot**, not a contemporaneous access classification: any YES wins across the well's EOR bores; absent YES with a recorded NO is no, and no usable flag is unknown. Unknown records remain in the approval denominator. The complement of YES is not proof of a dry tree. [The CSV](output/subsea_completion_shares.csv) retains YES, NO and unknown counts, plus pooled 2021–2025.

{table(pd.DataFrame(subsea_rows))}

## Duration checks

The permit's own `EST_OPERATION_DAYS` medians are the **operator's estimate on the permit, not observed job length**. Only finite positive estimates enter a median; missing and nonpositive values remain counted in [the CSV](output/permit_duration_estimates.csv). In band order, well-work medians are **3 / 6 / 15 / 14 days**, and permanent-abandonment medians are **14 / 10 / 25 / 21 days**.

{table(pd.DataFrame(duration_rows))}

Beside those estimates, the weekly-report check unions overlapping or adjacent inclusive intervals of 1–90 days for the same API12, named unit and raw code in 2005–2025. A gap or changed code/unit starts a new proxy episode. Missing/placeholder units are excluded. WO, REC, TA and PA are an interpreted non-drilling token subset; several meanings lack a published BSEE definition. Full-year filtering precedes union and can censor endpoints. The {s["proxy_episodes"]:,} episodes are neither permits nor proven complete heavy-rig jobs. [The weekly-report CSV](output/war_duration_crosscheck.csv) preserves each raw-code stratum, including the deepest WO-token median of 18 days.

{table(war)}

## Cost basis

**Access method selects the cost, with depth as source applicability only.** Values are scenario costs per well/event in **unescalated 2015 USD millions, two significant figures**. Permanent-abandonment costs apply only to the 1,387 permanent approvals out of 2,610 abandonment approvals in 2025; they do not price temporary or unspecified abandonment. No count is multiplied by a cost to claim expenditure.

{cost_table}

- [BSEE TAP-738](https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf), 2015: Table 8-2, printed p. 8-12 (PDF p. 143), prices rigless dry-tree wells for 50–400 ft. Its USD 225,856 P&A work charge over 84 hours implies USD 64,530/day rounded. Standalone mob and demob are USD 37,743 each. Setup, rig-down and study contingencies are outside the simple dayrate-times-duration arithmetic.
- TAP-738 Table 8-3, p. 8-14 (PDF p. 145), gives USD 68,424/day for the casing-jack spread. The study uses casing jacks above 400 ft and describes dry-tree TLP wells at about 1,500 to over 4,600 ft. The platform work durations and the shallow rigless transport charges are transferred explicitly to the shelf casing-jack scenarios.
- **Deepwater dry-tree platform permanent abandonment** uses the **published** Table 8-4, p. 8-15 (PDF p. 146), final-column totals: USD 734,356 / 987,262 / 1,374,570 per well at 1,700 / 3,000 / 5,000 ft, respectively (USD **0.73 / 0.99 / 1.4 million** at two significant figures). These are 60-well campaign totals normalised per well and include work provision, engineering, weather and shared mobilisation. They are depth anchors, not statistical low/base/high outcomes. A cited deepwater dry-tree well-work basis is not established, so that row is **not priced**. Dry-tree conductor removal is separate.
- TAP-738 section 8.3.2.3, p. 8-18 (PDF p. 149), gives the drillship/semisubmersible total spread as USD 674,600/day. **Rig mobilisation is excluded**, rather than assumed free. Subsea permanent-abandonment durations follow approximate graphic readings of Figure 8-9, p. 8-19: 17 / 19 / 23 days around the 3,000-ft anchor and 21 / 23 / 27 days around 6,000–9,000 ft. These cases do not classify every approval at those depths. Beyond the 9,000-ft anchor, cost applicability is not established.
- The well-work duration labels are **median 7 days / midpoint 10.5 days / two weeks 14 days**. The [BOEM Gulf EIS 2016-018](https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf), section 3.1.3.5, p. 3-37 (PDF p. 163), reports a Gulf median of 7 days with a range from 1 day to several months. [BOEM MAG-PLAN Alaska update](https://espis.boem.gov/final%20reports/5179.pdf), 2012, section 3.5.5.4, p. 108 (PDF p. 117), provides one to two weeks; 10.5 days is its arithmetic midpoint. These are transferred duration scenarios, **not a spread of observed outcomes**. The midpoint retains its half day to avoid changing the arithmetic; other reported duration summaries use integer days.
- [BSEE Pacific cost update, vol. 2](https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf), 2015, Appendix 2, p. A-2 (PDF p. 5), provides 3, 4, 5 and 8 trouble-free rigless days per well. The 3 / 4 / 8-day selections are scenario inputs; transfer to casing jacks is an assumption. Operator permit estimates and the weekly-report proxy above do not validate these duration scenarios.

Every numeric input and its citation are retained in [cost_basis.yml](cost_basis.yml), generated by [build_cost_basis.py](build_cost_basis.py). [Full-precision costs](output/cost_table.csv) and [published comparisons](output/published_pa_comparators.csv) retain the arithmetic. The subsea comparator for 500–1,500 m is Figure 8-10's **3,000-ft (914-m) point**, about **USD 13 million** at two significant figures; the 1,000-ft point is outside that band and is not used. The 6,000/9,000-ft comparator is about USD 16 / 19 million. The rigless published total is USD 0.34–0.42 million per well. Published totals include their stated allowances and campaign assumptions and are not equal to the simpler spread scenarios. [Citation receipts](output/cost_source_manifest.json) retain source URLs and PDF digests; a 2015 study rehosted later remains a 2015 dollar basis.

## Limits

An approval does not establish execution. Repeated IDs, administrative scopes, incomplete initial/recompletion and abandonment subcodes, daily snapshot revisions, narrow narrative screening and incomplete electronic coverage limit interpretation. The current bore-status snapshot is not a complete well-life history. Unknown flags do not establish dry-tree access, and named units do not establish deployment. Rates describe approvals against opening stock, not the proportion of wells intervened on. The coding transition limits comparisons with full-period averages.

Cost cases are neither bids nor confidence intervals. Additional materials, logistics, standby, weather and engineering are excluded unless already included in a source spread or published total. Dry-tree conductor removal, full site clearance and remediation are separate; subsea rig mobilisation remains unpriced. Dollar escalation is not applied. A light intervention vessel is not interchangeable with a heavy workover rig. Total Gulf expenditure is not established.

## Tests and reproduction

From the repository root, use the retained archives in `data/modules/bsee/zip/2026-11-12/` with the manifest digests. A new BSEE download is a different snapshot. The example requires the packages in [requirements.txt](requirements.txt).

```sh
uv run --no-sync python examples/bsee/interventions_by_depth/count_interventions.py --data-dir data/modules/bsee/zip/2026-11-12 --out examples/bsee/interventions_by_depth/output --last-full-year 2025
uv run --no-sync python examples/bsee/interventions_by_depth/build_cost_basis.py
uv run --no-sync python examples/bsee/interventions_by_depth/estimate_costs.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/plot_charts.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/write_results_note.py --test-result '{test_result}'
uv run --no-sync python examples/bsee/interventions_by_depth/verify_outputs.py
```

Focused example plus existing API-normalizer tests, PowerShell:

```powershell
$env:PYTHONPATH='packages/worldenergydata-bsee/src;packages/worldenergydata-core/src;../../assetutilities/src;src'
{TEST_COMMAND}
```

Result: **{test_result}**. Tests cover all-bore stock, date boundaries, cancelled bores, assumed standing, unit categories, three hand-worked cost literals read through YAML and published deepwater dry-tree pricing. Tests use no network or retained raw files. Aggregate reconciliation, input provenance, output digests and software versions are retained in [verification.json](output/verification.json).

## Charts

PNG width is 2,160 pixels; SVG versions are retained. Footers identify the raw files and date on activity figures and the four cost studies on the cost figure.

{charts}
"""
    (ROOT / "README.md").write_text(note, encoding="utf-8", newline="\n")
    if pr_body:
        body = f"""## What this adds

A reproducible Gulf of Mexico existing-well activity example: approval counts, distinct wells, rates against opening standing stock, cost cases by well/access method, and four PNG/SVG charts. Related: [activity characterisation issue](https://github.com/vamseeachanta/worldenergydata/issues/1220); this PR does not close it. [README](https://github.com/vamseeachanta/worldenergydata/blob/analysis/gom-interventions-by-depth/examples/bsee/interventions_by_depth/README.md).

## Data

The four retained BSEE Borehole, approved-permit, end-of-operations and weekly-report archives are dated 12 November 2026; their existing SHA-256 manifest is verified before use. Raw files are not committed or re-downloaded. Only derived aggregates are published. **ASSUMED - to be confirmed:** every APM main row represents an approved permit; the feed has no separate approval-status field.

## Method

Count one submission ID per approval; exclude initial completions without ZONE and new-hole preparation; retain unknown abandonment subtype. Join depth by API12 with a unique API10 fallback. Rebuild stock per API10 over all non-cancelled bores, from first spud until every non-superseded bore (not ST/BP) is PA by its status date. Missing terminal dates or no terminal bore retain the well as assumed standing. Use **stock on 1 January** for annual rates; year-end stock is retained separately. {assumed_note}

Unit type follows the permit rig ID and the supplied rig-type lookup; EOR ever-YES subsea flags remain descriptive. Approvals are not wells, job completions or expenditure. {coding_note}

## Headline results

2025: **765 well-work + 2,610 abandonment approvals = 3,375**. Cost applies to **permanent abandonment only: 1,387 of 2,610 abandonment approvals** (the remainder is 1,060 temporary and 163 unspecified).

{headline}

An earlier snapshot of 31 Oct 2026 (not retained here) gives the prior comparison. Raw 2025 rows remain 523 WORKOVER/ENHANCE, 2,734 ABANDON and 3,833 total. Removing 127 new-hole preparations and 331 initial completions yields the table above; 145 COMP/ZONE and 100 INFORM/UTIL remain in well work. EOR reports are 12 workover, 891 abandonment and 75 completion; the last two are each one above that earlier snapshot.

Costs follow **well and access method**, with depth only as source applicability. Low/base/high are **scenario columns, USD million (2015), two significant figures**. Permanent-abandonment costs apply only to permanent approvals (1,387 of 2,610 in 2025).

{cost_table}

Sources: [BSEE TAP-738, 2015](https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf), Tables 8-2/8-3/8-4, pp. 8-12/8-14/8-15, and subsea section 8.3.2.3; [BOEM EIS 2016-018](https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf), p. 3-37; [BOEM MAG-PLAN Alaska update, 2012](https://espis.boem.gov/final%20reports/5179.pdf), p. 108; [BSEE Pacific update vol. 2, 2015](https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf), p. A-2. Rigless spread: USD 64,530/day derived from Table 8-2; casing jacks: USD 68,424/day; subsea total spread: USD 674,600/day. Deepwater dry-tree P&A uses the published 60-well Table 8-4 totals at 1,700/3,000/5,000 ft, not a subsea rate; its work row is not priced. The 500–1,500-m subsea comparison uses 3,000 ft, not 1,000 ft.

Well-work duration cases are **median 7 days / midpoint 10.5 days / two weeks 14 days**, not an outcome range: the Gulf source spans 1 day to several months. The permit's own operator-estimated medians by band are **3 / 6 / 15 / 14 days** for well work and **14 / 10 / 25 / 21 days** for permanent abandonment, not observed job lengths. The README places these beside the weekly-report check and includes all approval/well ratios, unit categories and EOR flag shares. In 500–1,500 m, only 90/157 permanent approvals name a drillship or semi and 79/157 lack a YES subsea flag, illustrating why depth alone does not price access.

## Limits

Current bore statuses are a retrospective stock proxy, not a complete state-transition history. Missing first-spud dates are excluded; assumed stock is explicit. Approvals during the year can include later spuds, so rates are intensity against opening stock, not matched-cohort probabilities. Electronic coverage and operation coding changes limit long-run comparisons. Permits and EOR reports do not establish completed jobs. Unknown flags do not prove dry-tree access; named units do not prove deployment.

Unescalated source-year cost cases are not bids or outcome distributions. Permanent-abandonment costs exclude temporary/unspecified approvals. Dry-tree conductor removal and site clearance are separate; subsea rig mobilisation is excluded. Additional costs enter only where included in the cited spread or published total. No total expenditure is estimated.

## Tests

```powershell
$env:PYTHONPATH='packages/worldenergydata-bsee/src;packages/worldenergydata-core/src;../../assetutilities/src;src'
{TEST_COMMAND}
```

Result: **{test_result}**. Coverage includes ST original/PA sidetrack, live sidetrack, cancelled bores, inclusive dates, assumed stock, unit mapping and three literal cost sums through YAML. Derived tables are reconciled, provenance is checked, all figures are regenerated and inspected, and output digests are retained.

## Charts

- `01_approved_interventions.png` / `.svg`: approved permits to modify by depth; coding-change note.
- `02_rates_per_standing_well.png` / `.svg`: approved permits to modify per 100 wells standing on 1 January; zero-based axes.
- `03_cost_per_event.png` / `.svg`: cost scenarios by well/access type, with cost-study sources.
- `04_unit_types_by_depth.png` / `.svg`: 2025 well-work and permanent-abandonment approval shares, 100% stacked by unit type and depth.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""
        Path(pr_body).write_text(body, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-body", type=Path)
    parser.add_argument("--test-result", default="not run")
    args = parser.parse_args()
    main(args.pr_body, args.test_result)
