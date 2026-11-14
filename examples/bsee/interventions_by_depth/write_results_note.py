"""Regenerate the README and optional PR body from the derived tables."""

import argparse
import json
import math
import re
from pathlib import Path

import pandas as pd
from report_text import (
    abandonment_split,
    check_selection,
    coding_sentence,
    family_totals,
    long_date,
    reconciliation,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
BANDS = [
    "under 100 m",
    "100 to 500 m",
    "500 to 1500 m",
    "1500 m and deeper",
    "no depth",
]
BASIS = {
    "spread scenario": "spread x days + mobilisation; source allowances not included",
    "published total": "published total; includes source allowances",
    "not priced": "not priced",
}
TEST_COMMAND = 'uv run --no-sync python -m pytest --noconftest -o addopts="" tests/unit/bsee/test_interventions_by_depth.py tests/unit/bsee/test_well_life_cycle.py tests/unit/bsee/data/utils/test_api_well_normalizer.py -q'


def table(frame):
    frame = frame.replace(
        {"500 to 1500 m": "500 to 1,500 m", "1500 m and deeper": "1,500 m and deeper"}
    )
    for column in frame.select_dtypes(include="integer"):
        frame[column] = frame[column].map(lambda value: f"{value:,}")
    return frame.to_markdown(index=False, disable_numparse=True)


def rate(value):
    return f"{value:.1f}" if pd.notna(value) else "not established"


def million(value):
    if pd.isna(value):
        return "not priced"
    v = value / 1e6
    decimals = max(0, 1 - int(math.floor(math.log10(abs(v))))) if v else 0
    return f"{v:.{decimals}f}" if v else "0"


def well_life_section(out, summary):
    """README section on the per-well life cycle, read from the life-cycle tables."""
    life = json.loads((out / "life_cycle_summary.json").read_text(encoding="utf-8"))
    if life["file_date"] != summary["file_date"]:
        raise ValueError("life-cycle tables come from a different snapshot")
    years = pd.read_csv(out / "life_cycle_life_years.csv").set_index(
        ["group", "status"]
    )
    reach = pd.read_csv(out / "life_cycle_stage_reach.csv")
    checks = pd.read_csv(out / "life_cycle_reconciliation.csv")
    first, last = summary["first_full_year"], summary["last_full_year"]
    life_rows = years.reset_index()
    life_rows = life_rows[
        life_rows.group.isin(
            ["development wells", "exploration wells"] + list(reach.group.unique())
        )
    ]
    life_rows = life_rows[
        ["group", "status", "wells", "q25_years", "median_years", "q75_years"]
    ]
    for c in ["q25_years", "median_years", "q75_years"]:
        life_rows[c] = life_rows[c].map(lambda v: f"{v:.1f}")
    stage = reach.pivot(index="stage", columns="group", values="share_percent").reindex(
        reach.stage.unique()
    )
    per_well = reach.pivot(
        index="stage", columns="group", values="events_per_well"
    ).reindex(reach.stage.unique())
    groups = list(reach.group.unique())
    stage_rows = pd.DataFrame(
        {"stage": stage.index}
        | {
            f"{g}: share of wells (%) / events per well": [
                f"{stage.loc[i, g]:.1f} / {per_well.loc[i, g]:.2f}" for i in stage.index
            ]
            for g in groups
        }
    )
    return f"""## Well life cycle

Each well (API10) is followed from its first non-cancelled spud to permanent abandonment (the stock rule in Method: every non-superseded bore PA, at the latest PA date) or to the file date while it stands. Drilling counts bores with a spud date (original hole, sidetracks and bypasses). Interventions, temporary and permanent abandonments are the approved permits of this example, from {first} to the file date. Interventions are **light** when the permit names a wireline unit (WL), coiled tubing (CT), intervention vessel (WI), liftboat (LB) or recorded non-rig operation (NR), and **heavy** for a hydraulic workover or snubbing unit (HW, SB), platform rig (PF), jack-up (JU), drillship or semisubmersible (DS, SS, SD); otherwise light or heavy is not established. These keep the unit categories below, except that "liftboat / jack-up" is divided by its two source codes ([mapping](output/intervention_weight_mapping.csv)). Development and exploration follow `WELL_TYPE_CODE` (D, E) of the canonical original hole.

Of {life["dated_wells"]:,} dated wells, {life["permanently_abandoned"]:,} are permanently abandoned and {life["standing"]:,} stand; {life["wells_without_first_spud"]:,} lack a first spud and {life["life_not_established"]:,} have an abandonment date before spud (life not established). Life in years:

{table(life_rows)}

Per-well stages for wells first drilled {first}-{last}, whose whole life lies inside the permit record:

{stage_rows.to_markdown(index=False, disable_numparse=True)}

Reconciliation with the permit counts over {life["window"]} ([CSV](output/life_cycle_reconciliation.csv)): the life-cycle events equal the published groups, and permits on wells with no dated life are counted separately.

{table(checks)}

[Event ages](output/life_cycle_event_ages.csv) give the age of the well at every sidetrack spud and approval in the window, for all wells; older wells contribute only their later events. [Light and heavy by year](output/intervention_weight_by_year.csv) partition the well-work approvals of each year.
""".rstrip("\n")


def main(pr_body=None, test_result="not run", out=OUT, readme=ROOT / "README.md"):
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    rates = pd.read_csv(out / "rates.csv")
    ratio_frame = pd.read_csv(out / "approvals_per_distinct_well.csv")
    durations = pd.read_csv(out / "permit_duration_estimates.csv")
    shares = pd.read_csv(out / "unit_type_shares.csv")
    subsea = pd.read_csv(out / "subsea_completion_shares.csv")
    # Every year-tagged table must be built for the summary's selection;
    # otherwise the note would mix years. Nothing is written on failure.
    last = check_selection(
        s,
        {
            "approvals_per_distinct_well.csv": ratio_frame.year,
            "permit_duration_estimates.csv": durations.year,
            "unit_type_shares.csv": shares.period,
            "subsea_completion_shares.csv": subsea.period,
        },
    )
    first, partial = int(s["first_full_year"]), int(s["partial_year"])
    if sorted(rates.year.unique()) != list(range(first, partial + 1)):
        raise ValueError("rates.csv years do not match summary.json")
    pooled = next(p for p in shares.period.astype(str).unique() if "-" in p)
    counts = pd.read_csv(out / "counts_by_year_band_group.csv")
    totals = family_totals(rates, last)
    split = abandonment_split(counts, last)
    permanent = split["permanent abandonment"]
    snapshot_date = long_date(s["snapshot"])
    coverage = pd.read_csv(out / "coverage_by_month.csv")
    feed_start = pd.Timestamp(coverage.month.min() + "-01").strftime("%B %Y")
    file_through = long_date(s["file_date"], year=False)
    latest = rates[rates.year.eq(last)].set_index(["band", "family"])
    ratios = ratio_frame.set_index(["band", "family"])
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
    cost_frame = pd.read_csv(out / "cost_table.csv")
    cost_rows = []
    for r in cost_frame.itertuples():
        cost_rows.append(
            {
                "Well / access type": r.access_type,
                "Event": r.event,
                "Basis": BASIS[r.pricing_method],
                "Applicability": re.sub(
                    r"\b\d{4}\b", lambda match: f"{int(match[0]):,}", r.applicability
                ),
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
    codes = pd.read_csv(out / "code_mapping.csv")
    primary = pd.read_csv(out / "primary_code_by_year.csv")
    coding_note = (
        coding_sentence(primary, first, last)
        + " Part of the apparent well-work decline reflects a coding change. "
        f"The {last} count should not be compared with the long-run mean without this qualification; electronic coverage also changes in the early years."
    )
    reconcile = reconciliation(s, codes, totals)
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
                "Valid estimates, work / permanent abandonment": f'{int(f.loc["well work","estimates"]):,} / {int(f.loc["permanent abandonment","estimates"]):,}',
            }
        )
    medians = {
        event: " / ".join(
            (f"{v:.0f}" if pd.notna(v) else "not established")
            for v in durations[durations.event.eq(event)]
            .set_index("band")
            .reindex(BANDS[:-1])
            .median_est_operation_days
        )
        for event in ["well work", "permanent abandonment"]
    }
    war = pd.read_csv(out / "war_duration_crosscheck.csv")
    deepest_wo = war.loc[
        war.band.eq(BANDS[3]) & war.raw_war_code.eq("WO"), "median_days"
    ]
    deepest_wo_text = (
        f"including the deepest WO-token median of {deepest_wo.iloc[0]:.0f} days"
        if len(deepest_wo)
        else "including each depth band's WO-token median"
    )
    for col in ["q25_days", "median_days", "q75_days"]:
        war[col] = war[col].map(lambda v: f"{v:,.0f}")
    war = war[war.raw_war_code.eq("selected tokens combined")].drop(
        columns="raw_war_code"
    )
    shares = shares[shares.period.astype(str).eq(str(last))]
    categories = [
        "wireline unit",
        "coiled tubing",
        "hydraulic workover / snubbing",
        "platform rig",
        "liftboat / jack-up",
        "intervention vessel",
        "drillship / semisubmersible",
        "non-rig operation (recorded)",
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
        "Non-rig operation (recorded)",
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
            f"{event.capitalize()} — share of approvals, {last}:\n\n"
            + table(frame.reset_index())
        )
    subsea_rows = []
    for band in BANDS:
        f = subsea[
            subsea.period.astype(str).eq(str(last)) & subsea.band.eq(band)
        ].set_index("event")
        subsea_rows.append(
            {
                "Depth band": band,
                "Flag YES, work / permanent abandonment (%)": f'{rate(f.loc["well work","subsea_share_percent"])} / {rate(f.loc["permanent abandonment","subsea_share_percent"])}',
                "Unknown, work / permanent abandonment": f'{int(f.loc["well work","subsea_flag_unknown"])} / {int(f.loc["permanent abandonment","subsea_flag_unknown"])}',
            }
        )

    def unit_count(band, event, category):
        f = shares[
            shares.band.eq(band)
            & shares.event.eq(event)
            & shares.unit_category.eq(category)
        ]
        return int(f.approvals.sum()), int(f.total_approvals.sum())

    nr, shallow_pa = unit_count(
        BANDS[0], "permanent abandonment", "non-rig operation (recorded)"
    )
    none_named, _ = unit_count(BANDS[0], "permanent abandonment", "none named")
    floater, mid_pa = unit_count(
        BANDS[2], "permanent abandonment", "drillship / semisubmersible"
    )
    mid_flags = subsea[
        subsea.period.astype(str).eq(str(last))
        & subsea.band.eq(BANDS[2])
        & subsea.event.eq("permanent abandonment")
    ].iloc[0]
    no_yes = int(mid_flags.subsea_flag_no + mid_flags.subsea_flag_unknown)
    rules = pd.read_csv(out / "unit_type_mapping.csv")
    inventory = pd.read_csv(out / "standing_wells.csv")
    assumed = inventory[inventory.year.eq(last)]
    assumed_note = (
        f"At 1 January {last}, {int(assumed.assumed_standing.sum()):,} wells are **assumed standing**: "
        f"{int(assumed.no_non_superseded_bore.sum()):,} have no non-superseded bore and "
        f"{int(assumed.missing_terminal_status_date.sum()):,} "
        f"{'has' if assumed.missing_terminal_status_date.sum() == 1 else 'have'} a missing terminal status date (categories can overlap). "
        f'{s["inventory_missing_first_spud"]:,} API10 wells lack any non-cancelled first-spud date and are excluded; their historical stock cannot be dated.'
    )
    life_section = well_life_section(out, s)
    charts = f"""- [05 — How long Gulf of Mexico wells last](output/05_well_life.png) · [SVG](output/05_well_life.svg)
- [06 — The life of a well, stage by stage](output/06_well_life_stages.png) · [SVG](output/06_well_life_stages.svg)
- [01 — Approved permits to modify by depth](output/01_approved_interventions.png) · [SVG](output/01_approved_interventions.svg)
- [02 — Approved permits to modify per 100 standing wells](output/02_rates_per_standing_well.png) · [SVG](output/02_rates_per_standing_well.svg)
- [03 — Cost scenarios by well and access type](output/03_cost_per_event.png) · [SVG](output/03_cost_per_event.svg)
- [04 — Unit types named on {last} approvals by depth](output/04_unit_types_by_depth.png) · [SVG](output/04_unit_types_by_depth.svg)"""
    note = f"""# Gulf of Mexico well interventions by water depth

## What this adds

Approved permits to modify existing wells are counted separately from new-well drilling permits. One submission is one event, not one well or evidence of completed work. In {last}, **{totals["well work"]:,} well-work approvals + {totals["abandonment"]:,} abandonment approvals = {totals["all"]:,} events**. Permanent-abandonment costs apply only to the **{permanent:,} permanent approvals**, not the {split["temporary abandonment"]:,} temporary or {split["abandonment unspecified"]:,} unspecified abandonment approvals. No expenditure is inferred from counts.

## Data

The collection owner is worldenergydata; the catalog source ID is `bsee-data-center`. The four BSEE raw archives were downloaded on {snapshot_date} (snapshot folder `{s["snapshot"]}`). Their size and SHA-256 are verified against the manifest before use. Raw archives are ignored and are not backed up by this PR. Only small derived aggregates and charts are committed.

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
- Rates use **wells standing on 1 January**, not year-end stock: approvals during the year can concern wells removed before year end. The numerator includes approvals during the year, including wells first spudded later in that year, so this is approval intensity against opening stock, not a matched-cohort probability. [Standing wells](output/standing_wells.csv) includes stock dates and assumed counts; [year-end stock](output/standing_wells_year_end.csv) is retained separately (partial {partial} capped at the file date). Zero stock yields a missing rate, not zero.
- Full years run {first}–{last}, from the first January in the feed to the year before the file date; [full-year averages](output/full_year_averages.csv) exclude partial {partial} through {file_through}. The {partial} denominator remains 1 January stock and its rates are not annualised. EOR W/A/C counts use one `SN_EOR` and the borehole-status date; these are not a matched APM completion cohort. [EOR counts](output/eor_by_year_band.csv) and [same-year ratios](output/eor_permit_ratios.csv) remain descriptive.

{assumed_note}

{coding_note} The feed begins in {feed_start}; [monthly coverage](output/coverage_by_month.csv) retains the early ramp. Current bore statuses and dates provide a retrospective proxy, not a complete state-transition history; earlier abandonments followed by reopening cannot be reconstructed.

{life_section}

## Headline results

{last} approvals and distinct API10 wells are shown separately. A well can appear in both event families; the two distinct-well columns must not be added as disjoint populations. The cost cases below apply to permanent abandonment only ({permanent:,} of {totals["abandonment"]:,} abandonment approvals).

{headline}

Approval-to-well ratios, from [the CSV](output/approvals_per_distinct_well.csv): approvals are not wells.

{table(pd.DataFrame(ratio_rows))}

{reconcile}

## Unit and access evidence

The permit's `RIG_ID_NUM` joins the archive's `mv_apm_rig_view` fields `RIG_TYPE_CODE` and `RIG_NAME` with a validated many-to-one join. The type code selects the category; names are retained in [the lookup](output/unit_type_lookup.csv) but are not used to guess equipment. The mapping below is also retained in [CSV](output/unit_type_mapping.csv). NR enters **non-rig operation (recorded)**; only blank unit information enters **none named**. Of the {shallow_pa:,} under-100-m permanent-abandonment approvals in {last}, {nr:,} carry the regulator's unit type "non rig PA operation" and {none_named:,} name no unit. An unmatched nonblank ID or unmapped type enters other. SU is a submersible and is not classified as a semisubmersible. A permit's named unit need not be the unit ultimately deployed.

{table(rules)}

{chr(10).join(unit_tables)}

[Unit shares](output/unit_type_shares.csv) also retain pooled {pooled.replace("-", "–")} counts and all zero/no-depth rows. Chart 04 uses {last} to align with the headline counts. In 500–1,500 m, only **{floater:,} of {mid_pa:,}** permanent-abandonment approvals name a drillship or semisubmersible, and **{no_yes:,} of {mid_pa:,}** have no YES subsea-completion flag. Water depth cannot select an access method.

The share with an EOR `SUBSEA_COMPLETION_FLAG=YES` follows. This is an **ever-YES flag at API10 in the retained snapshot**, not a contemporaneous access classification: any YES wins across the well's EOR bores; absent YES with a recorded NO is no, and no usable flag is unknown. Unknown records remain in the approval denominator. The complement of YES is not proof of a dry tree. [The CSV](output/subsea_completion_shares.csv) retains YES, NO and unknown counts, plus pooled {pooled.replace("-", "–")}.

{table(pd.DataFrame(subsea_rows))}

## Duration checks

The permit's own `EST_OPERATION_DAYS` medians are the **operator's estimate on the permit, not observed job length**. Only finite positive estimates enter a median; missing and nonpositive values remain counted in [the CSV](output/permit_duration_estimates.csv). In band order, well-work medians are **{medians["well work"]} days**, and permanent-abandonment medians are **{medians["permanent abandonment"]} days**.

{table(pd.DataFrame(duration_rows))}

Beside those estimates, the weekly-report check unions overlapping or adjacent inclusive intervals of 1–90 days for the same API12, named unit and raw code in {first}–{last}. A gap or changed code/unit starts a new proxy episode. Missing/placeholder units are excluded. WO, REC, TA and PA are an interpreted non-drilling token subset; several meanings lack a published BSEE definition. Full-year filtering precedes union and can censor endpoints. The {s["proxy_episodes"]:,} episodes are neither permits nor proven complete heavy-rig jobs. [The weekly-report CSV](output/war_duration_crosscheck.csv) preserves each raw-code stratum, {deepest_wo_text}.

{table(war)}

## Cost basis

**Access method selects the cost, with depth as source applicability only.** Values are scenario costs per well/event in **unescalated 2015 USD millions, two significant figures**. Permanent-abandonment costs apply only to the {permanent:,} permanent approvals out of {totals["abandonment"]:,} abandonment approvals in {last}; they do not price temporary or unspecified abandonment. No count is multiplied by a cost to claim expenditure.

{cost_table}

- Spread scenarios are rate x days + mobilisation and **leave out the source's allowances**: TAP-738 multiplies wet-tree operations time by weather, work-provision and engineering/project-management allowances (p. 8-18) and applies similar allowances to dry-tree work (Table 8-2). The deep-platform row is a published total that includes them. The Basis column marks each row, so the step between the two platform rows is not a depth effect.
- [BSEE TAP-738](https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf), 2015: Table 8-2, printed p. 8-12 (PDF p. 143), prices rigless dry-tree wells for 50–400 ft. Its USD 225,856 P&A work charge over 84 hours implies USD 64,530/day rounded. Standalone mob and demob are USD 37,743 each. Setup, rig-down and study contingencies are outside the simple dayrate-times-duration arithmetic.
- TAP-738 Table 8-3, p. 8-14 (PDF p. 145), gives USD 68,424/day for the casing-jack spread. The study uses casing jacks above 400 ft and describes dry-tree TLP wells at about 1,500 to over 4,600 ft. The platform work durations and the shallow rigless transport charges are transferred explicitly to the shelf casing-jack scenarios.
- **Deepwater dry-tree platform permanent abandonment** uses the **published** Table 8-4, p. 8-15 (PDF p. 146), final-column totals: USD 734,356 / 987,262 / 1,374,570 per well at 1,700 / 3,000 / 5,000 ft, respectively (USD **0.73 / 0.99 / 1.4 million** at two significant figures). These are 60-well campaign totals normalised per well and include work provision, engineering, weather and shared mobilisation. They are depth anchors, not statistical low/base/high outcomes. A cited deepwater dry-tree well-work basis is not established, so that row is **not priced**. Dry-tree conductor removal is separate.
- TAP-738 section 8.3.2.3, p. 8-18 (PDF p. 149), gives the drillship/semisubmersible total spread as USD 674,600/day. **Rig mobilisation is excluded**, rather than assumed free. Subsea permanent-abandonment durations follow approximate graphic readings of Figure 8-9, p. 8-19. The 3,000-ft row uses 17 days (MODU leaving the wellhead) and 19 days (MODU) at 3,000 ft for low and base, and 23 days, the MODU reading at **6,000 ft**, for high. The deeper row uses 21 and 23 days at 6,000 ft and 27 days at 9,000 ft. These cases do not classify every approval at those depths. Beyond the 9,000-ft anchor, cost applicability is not established.
- The well-work duration labels are **median 7 days / midpoint 10.5 days / two weeks 14 days**. The [BOEM Gulf EIS 2016-018](https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf), section 3.1.3.5, p. 3-37 (PDF p. 163), reports a Gulf median of 7 days with a range from 1 day to several months. [BOEM MAG-PLAN Alaska update](https://espis.boem.gov/final%20reports/5179.pdf), 2012, section 3.5.5.4, p. 108 (PDF p. 117), provides one to two weeks; 10.5 days is its arithmetic midpoint. These are transferred duration scenarios, **not a spread of observed outcomes**. The midpoint retains its half day to avoid changing the arithmetic; other reported duration summaries use integer days.
- [BSEE Pacific cost update, vol. 2](https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf), 2015, Appendix 2, p. A-2 (PDF p. 5), provides 3, 4, 5 and 8 trouble-free rigless days per well. The 3 / 4 / 8-day selections are scenario inputs; transfer to casing jacks is an assumption. Operator permit estimates and the weekly-report proxy above do not validate these duration scenarios.

Every numeric input and its citation are retained in [cost_basis.yml](cost_basis.yml), generated by [build_cost_basis.py](build_cost_basis.py). [Full-precision costs](output/cost_table.csv) and [published comparisons](output/published_pa_comparators.csv) retain the arithmetic. The subsea comparator for 500–1,500 m is Figure 8-10's **3,000-ft (914-m) point**, about **USD 13 million** at two significant figures; the 1,000-ft point is outside that band and is not used. The 6,000/9,000-ft comparator is about USD 16 / 19 million. The rigless published total is USD 0.34–0.42 million per well. Published totals include their stated allowances and campaign assumptions and are not equal to the simpler spread scenarios. [Citation receipts](output/cost_source_manifest.json) retain source URLs and PDF digests; a 2015 study rehosted later remains a 2015 dollar basis.

## Limits

An approval does not establish execution. Repeated IDs, administrative scopes, incomplete initial/recompletion and abandonment subcodes, daily snapshot revisions, narrow narrative screening and incomplete electronic coverage limit interpretation. The current bore-status snapshot is not a complete well-life history. Unknown flags do not establish dry-tree access, and named units do not establish deployment. Rates describe approvals against opening stock, not the proportion of wells intervened on. The coding transition limits comparisons with full-period averages.

Cost cases are neither bids nor confidence intervals. Additional materials, logistics, standby, weather and engineering are excluded unless already included in a source spread or published total. Dry-tree conductor removal, full site clearance and remediation are separate; subsea rig mobilisation remains unpriced. Dollar escalation is not applied. A light intervention vessel is not interchangeable with a heavy workover rig. Total Gulf expenditure is not established.

## Tests and reproduction

From the repository root, use the retained archives in `data/modules/bsee/zip/{s["snapshot"]}/` with the manifest digests. A new BSEE download (`download_data.py --snapshot <YYYY-MM-DD>`) is a different snapshot; the year selection and all report figures follow it. The example requires the packages in [requirements.txt](requirements.txt).

```sh
uv run --no-sync python examples/bsee/interventions_by_depth/count_interventions.py --data-dir data/modules/bsee/zip/{s["snapshot"]} --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/build_cost_basis.py
uv run --no-sync python examples/bsee/interventions_by_depth/estimate_costs.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/plot_charts.py --out examples/bsee/interventions_by_depth/output
uv run --no-sync python examples/bsee/interventions_by_depth/well_life_cycle.py --data-dir data/modules/bsee/zip/{s["snapshot"]}
uv run --no-sync python examples/bsee/interventions_by_depth/plot_life_cycle.py
uv run --no-sync python examples/bsee/interventions_by_depth/write_results_note.py --test-result '{test_result}'
uv run --no-sync python examples/bsee/interventions_by_depth/verify_outputs.py
uv run --no-sync python examples/bsee/interventions_by_depth/build_article.py --build-commit <commit holding the outputs>
```

The article page is [article/gom-well-interventions-r3.html](article/gom-well-interventions-r3.html); its text is generated from the same tables.

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
    readme.write_text(note, encoding="utf-8", newline="\n")
    if pr_body:
        body = f"""## What this adds

A reproducible Gulf of Mexico existing-well activity example: approval counts, distinct wells, rates against opening standing stock, cost cases by well/access method, and four PNG/SVG charts. Related: [activity characterisation issue](https://github.com/vamseeachanta/worldenergydata/issues/1220); this PR does not close it. [README](https://github.com/vamseeachanta/worldenergydata/blob/analysis/gom-interventions-by-depth/examples/bsee/interventions_by_depth/README.md).

## Data

The four BSEE Borehole, approved-permit, end-of-operations and weekly-report archives were downloaded on {snapshot_date}; their SHA-256 manifest is verified before use. Raw files are not committed. Only derived aggregates are published. **ASSUMED - to be confirmed:** every APM main row represents an approved permit; the feed has no separate approval-status field.

## Method

Count one submission ID per approval; exclude initial completions without ZONE and new-hole preparation; retain unknown abandonment subtype. Join depth by API12 with a unique API10 fallback. Rebuild stock per API10 over all non-cancelled bores, from first spud until every non-superseded bore (not ST/BP) is PA by its status date. Missing terminal dates or no terminal bore retain the well as assumed standing. Use **stock on 1 January** for annual rates; year-end stock is retained separately. {assumed_note}

Unit type follows the permit rig ID and the supplied rig-type lookup; EOR ever-YES subsea flags remain descriptive. Approvals are not wells, job completions or expenditure. {coding_note}

## Headline results

{last}: **{totals["well work"]:,} well-work + {totals["abandonment"]:,} abandonment approvals = {totals["all"]:,}**. Cost applies to **permanent abandonment only: {permanent:,} of {totals["abandonment"]:,} abandonment approvals** (the remainder is {split["temporary abandonment"]:,} temporary and {split["abandonment unspecified"]:,} unspecified).

{headline}

{reconcile}

Costs follow **well and access method**, with depth only as source applicability. Low/base/high are **scenario columns, USD million (2015), two significant figures**. Permanent-abandonment costs apply only to permanent approvals ({permanent:,} of {totals["abandonment"]:,} in {last}). Spread scenarios leave out the source's allowances; the deep-platform row is a published total that includes them.

{cost_table}

Sources: [BSEE TAP-738, 2015](https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf), Tables 8-2/8-3/8-4, pp. 8-12/8-14/8-15, and subsea section 8.3.2.3; [BOEM EIS 2016-018](https://www.boem.gov/sites/default/files/environmental-stewardship/Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf), p. 3-37; [BOEM MAG-PLAN Alaska update, 2012](https://espis.boem.gov/final%20reports/5179.pdf), p. 108; [BSEE Pacific update vol. 2, 2015](https://www.bsee.gov/sites/bsee.gov/files/technology-assessment-program-tap/735ab.pdf), p. A-2. Rigless spread: USD 64,530/day derived from Table 8-2; casing jacks: USD 68,424/day; subsea total spread: USD 674,600/day. Deepwater dry-tree P&A uses the published 60-well Table 8-4 totals at 1,700/3,000/5,000 ft, not a subsea rate; its work row is not priced. The 500–1,500-m subsea comparison uses 3,000 ft, not 1,000 ft.

Well-work duration cases are **median 7 days / midpoint 10.5 days / two weeks 14 days**, not an outcome range: the Gulf source spans 1 day to several months. The permit's own operator-estimated medians by band are **{medians["well work"]} days** for well work and **{medians["permanent abandonment"]} days** for permanent abandonment, not observed job lengths. The README places these beside the weekly-report check and includes all approval/well ratios, unit categories and EOR flag shares. In 500–1,500 m, only {floater:,}/{mid_pa:,} permanent approvals name a drillship or semi and {no_yes:,}/{mid_pa:,} lack a YES subsea flag, illustrating why depth alone does not price access.

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
- `04_unit_types_by_depth.png` / `.svg`: {last} well-work and permanent-abandonment approval shares, 100% stacked by unit type and depth.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""
        Path(pr_body).write_text(body, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-body", type=Path)
    parser.add_argument("--test-result", default="not run")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    args = parser.parse_args()
    main(args.pr_body, args.test_result, args.out, args.readme)
