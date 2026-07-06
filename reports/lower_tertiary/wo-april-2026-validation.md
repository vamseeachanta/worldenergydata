# World Oil April 2026 article — validation against worldenergydata

**Status:** validated 2026-07-06 · all 4 tables dispositioned
**Benchmark name:** "World Oil April 2026 article" (World Oil Lower-Tertiary series, part 2; BSEE-derived data thru Nov 2025)
**Canonical model artifact:** `docs/modules/bsee/analysis/production/FDAS_V30/financial_project_summary.xlsx` (+ assumptions in `lease_assumptions.xlsx`)
**Live reconciliation page:** [/completion/verification.html](https://vamseeachanta.github.io/worldenergydata/completion/verification.html)

---

## 0. Executive summary

This document is the durable, single-source record of the validation — every number, discrepancy, and open question lives HERE (email carries only brief pointers to it).

1. **The apparent 2× well-days gap is resolved.** Our page had headlined drilling-only days; on a like-for-like drilling-plus-completion basis our BSEE-derived extract reconciles with the article's Table 1 within a few percent, with every per-development difference itemized in §3 and kept current on the [live verification page](https://vamseeachanta.github.io/worldenergydata/completion/verification.html).
2. **Buckskin is recovered.** It was missing from our extract because the pipeline read a shelf-only dataset; the canonical extractor now reads the raw Keathley Canyon WAR data directly and Buckskin lands within one sidetrack and ~2.6% of the article's figures (§3).
3. **All four article tables are dispositioned** (§2): BSEE-derived columns reconcile through our code end-to-end; modeled and operator-announced columns are flagged, never recomputed.
4. **Five discrepancies were found** and are documented with WED evidence and side-by-side comparison tables for QA hand-back (§4).
5. **Free BOEM reserves + discovery dates are now in our refresh pipeline** (§5.1), which surfaced one substantive reserves discrepancy on Stones to resolve with the article team.
6. **Open asks to the article team** (§5): STOIIP basis, cost-deck vintage, and the appraisal-well definition.

## 1. Headline finding

The article's four tables **are this repository's FDAS V30 model output**: `financial_project_summary.xlsx` reproduces Tables 1 and 2 column-for-column (spud dates 9/9, wellbores, D&C days, oil volumes and revenues in band). Validation therefore splits cleanly:

- **BSEE-derived columns** (wells, sidetracks, spud dates, D&C days, produced oil, revenue) — reconciled by re-running our own code against BSEE WAR + OGOR-A raw data. These we can defend end-to-end.
- **Modeled columns** (cost deck, NPV10) — flagged as model output on the V30 assumptions deck (`lease_assumptions.xlsx`); reproduced by our code but only as good as the deck.
- **Announced/external columns** (STOIIP, some recoverable-reserve figures) — operator press figures; **no government source exists for STOIIP**. Cited as theirs, never recomputed.

## 2. Table-by-table disposition

| Table | Content | BSEE-derived verdict | Modeled / announced |
|---|---|---|---|
| 1 | Well metrics (wells, sidetracks, D&C days) | ✅ reconciles — see §3 | costs = V30 deck |
| 2 | Project financials | ✅ spud dates 9/9 exact; oil/revenue in band | NPV10 = V30 deck |
| 3 | BSEE dataset summary | ✅ mean project NPV −$1.19B reproduced | appraisal-well subset definition is theirs |
| 4 | STOIIP / recovery | ✅ recovered volumes match 7/9 (see discrepancies D1, D5) | STOIIP wholly external — see §5 |

## 3. Field-level D&C reconciliation (Table 1)

Our full-raw candidate extraction (canonical extractor reading raw BSEE WAR `.bin`; wed PR [#851](https://github.com/vamseeachanta/worldenergydata/pull/851), issue [#842](https://github.com/vamseeachanta/worldenergydata/issues/842)) vs the article, total D&C days:

| Development | WED bores | WO bores | WED D&C | WO D&C | Δ days | Status |
|---|---:|---:|---:|---:|---:|---|
| Anchor | 17 | 17 | 1,825 | 1,825 | 0 | exact |
| Cascade Chinook | 14 | 14 | 2,467 | 2,467 | 0 | exact |
| Stones | 22 | 22 | 2,625 | 2,625 | 0 | exact |
| Julia | 9 | 9 | 1,687 | 1,687 | 0 | exact |
| Kaskida | 7 | 7 | 841 | 841 | 0 | exact |
| Tiber | 2 | 2 | 250 | 250 | 0 | exact |
| North Platte | 23 | 20 | 971 | 971 | 0 | days exact; +3 zero-day sidetracks |
| Shenandoah | 23 | 23 | 2,370 | 2,346 | +24 | resolved (frozen V30 was −357) |
| **Buckskin** | **25** | **24** | **2,056** | **2,004** | +52 | **recovered** — was missing entirely (shelf-only extract) |
| Jack St Malo | 73 | 73 | 7,047 | 6,928 | +119 | open — suspect over-counted post-TD completion days; deferred bug [#846](https://github.com/vamseeachanta/worldenergydata/issues/846) |
| Big Foot | 38 | — | 3,265 | — | — | WED-only: the article intentionally excluded Big Foot |

Fidelity anchor: the candidate extraction reproduces the frozen V30 workbook **exactly** on Anchor (821 drilling / 1,004 completion days), pinned by `tests/integration/test_kc_ingest_fidelity.py`. Candidate totals: 253 wells / 25,404 D&C days across 26 leases, 11 developments.

The like-for-like frozen-V30 reconciliation (217 wells, 22,478 WED vs 21,944 WO D&C days; matched-9 −2.5%) lives on the [verification page](https://vamseeachanta.github.io/worldenergydata/completion/verification.html) and in `scripts/completion/build_completion_report.py` (`WO_APRIL_2026_ARTICLE` frozen benchmark).

## 4. Discrepancies found in the article (QA hand-back)

Surfaced by the BSEE-grounded cross-check. Each discrepancy gets its own side-by-side comparison table (same treatment as the §3 day-count table) so the exact cell where the two bases diverge is visible at a glance. Every WED figure is computed by repository code from the canonical workbook (`financial_project_summary.xlsx`) or raw BSEE OGOR-A; per-field detail lives on the live economics pages linked in each table.

Summary:

| # | Discrepancy | WED evidence (detail below) |
|---|---|---|
| D1 | Table 4 prints **recovered = "1"** for Anchor and Shenandoah — looks like a placeholder that survived into print; it also disagrees with the article's own Table 2 production values | BSEE OGOR-A cumulative oil for both fields is material and growing month-on-month — §4.1 |
| D2 | The **Stones NPV/NCF entries match the Tiber row to the dollar** — consistent with a row-copy slip during table assembly | WED canonical Tiber NPV equals the printed "Stones" value exactly; the real Stones values are far larger in magnitude — §4.2 |
| D3 | **Cascade Chinook net cash flow prints positive** while its own NPV prints negative — the underlying revenue/OPEX stack cannot produce a positive NCF | Full cash-stack rebuild from the canonical workbook — §4.3 |
| D4 | **Julia and Stones OPEX print as zero** for fields producing since 2016 | Lifetime variable + fixed OPEX from the canonical workbook — §4.4 |
| D5 | **Jack St Malo recovery factor prints 10%** where the article's own recovered/recoverable figures give 8.4% | Arithmetic on the article's own Table 4 cells; WED OGOR-A cumulative confirms the recovered figure — §4.5 |

### 4.1 D1 — Table 4 "recovered" for Anchor and Shenandoah

| Development | WO Table 4 recovered (MMbbl) | WED, frozen V30 window (thru 2025-05) | WED, latest OGOR-A | WED evidence |
|---|---:|---:|---:|---|
| Anchor | 1 | 6.9 | 18.6 | [Anchor economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-anchor.html) · `financial_project_summary.xlsx` Project_Summary · `field_economics_anchor_v50.md` |
| Shenandoah | 1 | 0.004 (first oil 2025-02; window ends 2025-05) | 21.2 | [Shenandoah economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-shenandoah.html) · `field_economics_shenandoah_v50.md` |

Both fields' produced volumes are material in the BSEE record and rising month-on-month, so "1" reads as a stale placeholder rather than a data point — and Table 2 of the article itself carries production for both.

### 4.2 D2 — Stones NPV/NCF entries match the Tiber row exactly

| Metric ($M) | WO prints for "Stones" | WED canonical **Tiber** | WED canonical **Stones** |
|---|---:|---:|---:|
| NPV @10% | −228 | **−228.0** | −1,479.5 (V30; −1,461 on the V50 latest-OGOR rerun) |
| Net cash flow | −275 | **−275.0** | −3,305.5 |

The printed "Stones" values equal WED's Tiber row **to the dollar** (Tiber: two exploration bores, never developed — small numbers by construction). The real Stones values are roughly six to twelve times larger in magnitude. WED evidence: [Stones economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-stones.html) · `financial_project_summary.xlsx` sheets `Stones` / `Tiber`.

### 4.3 D3 — Cascade Chinook net cash flow cannot be positive

| Cash-stack line ($M, lifetime thru 2025-05) | WED canonical |
|---|---:|
| Revenue | 2,326.9 |
| − Royalty | 436.3 |
| − OPEX (variable 137.3 + fixed 1,700.0) | 1,837.3 |
| **= Margin before capital** | **+53.3** |
| − Host CAPEX | 1,200.0 |
| − SURF | 600.0 |
| − Drilling + completion cost | 1,973.6 |
| **= Net cash flow** | **−3,820.3** |
| WO prints | **+3,656** |

With barely break-even lifetime margin before capital, no assignment of the capital stack can produce a positive NCF — and the article's own NPV for the same field prints negative (−1,122), which is internally inconsistent with a positive NCF of that size. WED evidence: [Cascade–Chinook economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-cascade_chinook.html) · `financial_project_summary.xlsx` sheet `Cascade Chinook`.

### 4.4 D4 — Julia and Stones OPEX print as zero

| Development (producing since) | WO OPEX ($M) | WED variable | WED fixed | WED total |
|---|---:|---:|---:|---:|
| Julia (2016) | 0 | 425.6 | 693.8 | **1,119.4** |
| Stones (2016) | 0 | 334.6 | 1,275.0 | **1,609.6** |

Both fields have produced continuously for roughly a decade; zero lifetime OPEX is not plausible on any basis. WED evidence: [Julia economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-julia.html) · [Stones economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-stones.html) · `financial_project_summary.xlsx` sheets `Julia` / `Stones`.

### 4.5 D5 — Jack St Malo recovery factor

| Quantity | Value | Source |
|---|---:|---|
| Recovered (article's own Table 4) | 420 MMbbl | WO Table 4 |
| Recoverable/STOIIP basis (article's own Table 4) | 5,000 MMbbl | WO Table 4 |
| Implied recovery factor | **8.4%** | 420 ÷ 5,000 |
| Printed recovery factor | **10%** | WO Table 4 |
| WED OGOR-A cumulative oil (V30 window) | 406.6 MMbbl | `financial_project_summary.xlsx`; consistent with ~420 at the latest OGOR-A month |

Pure arithmetic on the article's own cells; the recovered figure itself checks out against WED. WED evidence: [Jack / St. Malo economics (live)](https://vamseeachanta.github.io/worldenergydata/economics-jack_st_malo.html).

### 4.6 Project-cost basis (full stack, per development)

The article's Table 1/2 cost columns are the V30 assumptions deck (`lease_assumptions.xlsx`) run through our model — so this table IS the WED side of any cost comparison. If any article cost cell disagrees, the divergent cell locates exactly where the bases differ (and feeds ask §5.2, deck vintage). All values $M, lifetime thru 2025-05, from `financial_project_summary.xlsx` Project_Summary:

| Development | Host CAPEX | SURF | Boost/WI pumps | Dry-well system | Facilities total | Drilling cost | Completion cost | D&C total | Revenue | Royalty | OPEX | NCF | NPV @10% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Anchor | 1,500 | 700 | 0 | 0 | 2,400 | 657 | 1,104 | 1,761 | 476 | 89 | 167 | −3,941 | −1,733 |
| Big Foot | 2,000 | 0 | 0 | 630 | 2,730 | 966 | 822 | 1,787 | 4,738 | 888 | 1,058 | −1,725 | −1,063 |
| Cascade Chinook | 1,200 | 600 | 0 | 0 | 1,900 | 964 | 1,010 | 1,974 | 2,327 | 436 | 1,837 | −3,820 | −1,474 |
| Jack St Malo | 1,200 | 5,200 | 900 | 0 | 7,400 | 2,359 | 3,091 | 5,450 | 25,649 | 4,809 | 3,201 | +4,788 | −881 |
| Julia | 0 | 1,000 | 275 | 0 | 1,375 | 642 | 708 | 1,350 | 4,715 | 884 | 1,119 | −13 | −531 |
| Kaskida | 0 | 0 | 0 | 0 | 0 | 612 | 314 | 925 | 0 | 0 | 0 | −925 | −625 |
| North Platte | 0 | 0 | 0 | 0 | 0 | 743 | 326 | 1,068 | 0 | 0 | 0 | −1,068 | −784 |
| Shenandoah | 1,500 | 350 | 0 | 0 | 2,050 | 990 | 826 | 1,817 | 0.3 | 0.1 | 13 | −3,879 | −1,166 |
| Stones | 1,200 | 2,400 | 450 | 0 | 4,150 | 1,166 | 916 | 2,082 | 5,582 | 1,047 | 1,610 | −3,306 | −1,480 |
| Tiber | 0 | 0 | 0 | 0 | 0 | 235 | 40 | 275 | 0 | 0 | 0 | −275 | −228 |

(Boost/WI pumps = booster + water-injection pump capital combined; OPEX = variable + fixed. Pre-FID fields carry exploration/appraisal D&C only.)

### 4.7 Project financials — full WED model output (the article's Table 2 equivalent)

The complete per-development financial summary from the same canonical workbook, published so the article team can inspect the WED side of every Table 2 cell and gain confidence in the tables we produce. Production and wells are BSEE-derived (OGOR-A / WAR); dollars are the V30 model on the assumptions deck; all money in $M, lifetime thru 2025-05:

| Development | First oil | Oil produced (MMbbl) | Producer / injector wells | Total bores | Revenue | Royalty | OPEX | Net cash flow | NPV @10% | MIRR (annual) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Anchor | 2024-08 | 6.9 | 2 / 0 | 15 | 476 | 89 | 167 | −3,941 | −1,733 | −17.7% |
| Big Foot | 2018-11 | 66.9 | 7 / 1 | 38 | 4,738 | 888 | 1,058 | −1,725 | −1,063 | 3.5% |
| Cascade Chinook | 2014-01 | 34.3 | 3 / 0 | 14 | 2,327 | 436 | 1,837 | −3,820 | −1,474 | −1.8% |
| Jack St Malo | 2014-12 | 406.6 | 22 / 4 | 73 | 25,649 | 4,809 | 3,201 | +4,788 | −881 | 8.5% |
| Julia | 2016-03 | 70.9 | 4 / 0 | 9 | 4,715 | 884 | 1,119 | −13 | −531 | 6.3% |
| Kaskida | pre-FID | 0 | 0 / 0 | 7 | 0 | 0 | 0 | −925 | −625 | — |
| North Platte | pre-FID | 0 | 0 / 0 | 14 | 0 | 0 | 0 | −1,068 | −784 | — |
| Shenandoah | 2025-02 | 0.004 | 1 / 0 | 23 | 0.3 | 0.1 | 13 | −3,879 | −1,166 | — |
| Stones | 2016-09 | 83.7 | 10 / 2 | 22 | 5,582 | 1,047 | 1,610 | −3,306 | −1,480 | 2.7% |
| Tiber | never | 0 | 0 / 0 | 2 | 0 | 0 | 0 | −275 | −228 | — |

Cross-checks a reader can do immediately: the D2 duplicate row is visible here (Tiber's −275 / −228 are the values the article prints for Stones); D3's Cascade Chinook NCF is here in context; D4's OPEX columns are non-zero for Julia and Stones; Table 3's mean project NPV (−$1.19B) is the average of the NPV column. Per-field monthly cash-flow detail: the live economics pages ([Anchor](https://vamseeachanta.github.io/worldenergydata/economics-anchor.html) · [Big Foot](https://vamseeachanta.github.io/worldenergydata/economics-big_foot.html) · [Cascade–Chinook](https://vamseeachanta.github.io/worldenergydata/economics-cascade_chinook.html) · [Jack/St. Malo](https://vamseeachanta.github.io/worldenergydata/economics-jack_st_malo.html) · [Julia](https://vamseeachanta.github.io/worldenergydata/economics-julia.html) · [Shenandoah](https://vamseeachanta.github.io/worldenergydata/economics-shenandoah.html) · [Stones](https://vamseeachanta.github.io/worldenergydata/economics-stones.html)) and the [portfolio summary](https://vamseeachanta.github.io/worldenergydata/portfolio.html). Sanctioned-baseline figures are CI-guarded against `golden_baseline_v30.yml` — see [capabilities § validation](https://vamseeachanta.github.io/worldenergydata/capabilities/#validation).

## 5. Open asks to Roy / Chuck (their inputs, cited as theirs)

1. **STOIIP source for Table 4** *(hard gap)* — no BOEM/BSEE source exists for STOIIP/OOIP; public record is operator FID press only (Buckskin ~5 Bbbl, Julia 6 Bbbl, Stones >2 Bboe, Tiber 4–6 Bbbl; Cascade/Chinook has no clean public figure). Need their basis for a consistent column.
2. **Cost / rate-deck vintage confirmation** — are Table 1/2 costs the V30 `lease_assumptions.xlsx` deck we hold, or a revised deck?
3. **Complete recoverable-reserves (STB) set + appraisal-well definition** — we hold a few in BOE. BOEM's free Reserves Inventory (field-level, 31-Dec-2023 vintage) + Deepwater Qualified Fields (discovery/first-oil dates) are NOW IN the refresh pipeline ([#847](https://github.com/vamseeachanta/worldenergydata/issues/847), landed 2026-07-06 — see §5.1); WO Table 4 recoverable figures for Anchor 440 / JSM 500 / Stones 250 match operator press exactly, but BOEM's booked figure for Stones does not (§5.1) — which basis does the article intend?

### 5.1 BOEM cross-check (added 2026-07-06, #847 implementation)

The free BOEM Reserves Inventory (Table 4, 31-Dec-2023 vintage) is now in the refresh pipeline; curated output `data/modules/offshore_assets/curated/lt_reserves_discovery.csv`. Cross-check against the WO Table 4 / operator-announced recoverable figures (all MMBOE):

| Development | BOEM original (mean) | Operator/WO announced | Verdict |
|---|---:|---:|---|
| Jack St Malo | 550.6 | 500 | consistent (+10%) |
| **Stones** | **128.3** | **250** | **−48.7% — discrepancy flagged** (`lt_reserves_discrepancies.csv`); ask Roy/Chuck which basis WO intends |
| Anchor | not booked in 2023 vintage (FO 2024) | 440 | BOEM cross-check possible from the next vintage |
| Buckskin | 456.6 | — (WO carries no figure) | BOEM fills the gap |
| Big Foot / Cascade Chinook / Julia | 176.9 / 74.0 / 127.6 | — | new BOEM columns |
| Kaskida / North Platte / Tiber / Shenandoah | not booked (pre-FID / FO 2025) | — | rows kept with vintage caveat |

Discovery + first-production dates now sourced from BSEE Deepwater Qualified Fields (weekly cadence), field-level first-prod preferred (per-lease dates can post-date field first oil — Buckskin 2019-06 vs a 2026 lease date).

## 6. Provenance and versioning

- **V30** = frozen baseline (this workbook; production window thru 2025-05). **V50** = rerun on latest OGOR-A (changes production window/economics only). **D&C days are WAR-derived and identical under both** — the Table 1 reconciliation is version-independent (`reports/lower_tertiary/v30_vs_v50_comparison.md`).
- Owner decision (2026-07-06, noted on [#842](https://github.com/vamseeachanta/worldenergydata/issues/842)): the full-raw extraction **supersedes** V30 as canonical D&C once Roy confirms this validation; consumers (`v30_reproducer`, `financial/config_loader`) migrate then.
- Every "WED" number in this report is computed by repository code from BSEE raw data (WAR + OGOR-A). Numbers we could not recompute in-session are tagged with their recorded source.

## 7. Related work

| Ref | What |
|---|---|
| wed [#841](https://github.com/vamseeachanta/worldenergydata/pull/841) (merged) | `/completion/` Total-D&C column + verification page |
| wed [#843](https://github.com/vamseeachanta/worldenergydata/pull/843) (merged) | like-for-like reframe + Buckskin identity surfaced |
| wed [#851](https://github.com/vamseeachanta/worldenergydata/pull/851) (merged) | KC deepwater ingest — raw `.bin` extractor + Buckskin leases + fidelity tests |
| wed [#852](https://github.com/vamseeachanta/worldenergydata/pull/852) (merged) | benchmark renamed "World Oil April 2026 article" on the live pages |
| wed [#861](https://github.com/vamseeachanta/worldenergydata/pull/861) (merged) | #847 implementation: BOEM reserves + discovery in the refresh pipeline; curated `lt_reserves_discovery.csv` |
| wed [#842](https://github.com/vamseeachanta/worldenergydata/issues/842) | KC ingest issue; V30-supersede decision recorded (open pending article-team confirmation) |
| wed [#844](https://github.com/vamseeachanta/worldenergydata/issues/844) | living cost-basis time-series |
| wed [#846](https://github.com/vamseeachanta/worldenergydata/issues/846) | JSM D&C overshoot (+119) |
| wed [#847](https://github.com/vamseeachanta/worldenergydata/issues/847) (closed) | BOEM reserves + discovery-date ingest |
| wed [#855](https://github.com/vamseeachanta/worldenergydata/issues/855) | future BOEM source family (field monthly production, reserve history 1975–2023, older vintages) |
| wshub [#3385](https://github.com/vamseeachanta/workspace-hub/issues/3385) | "Verified against references & baselines" section epic |

## 8. Change log (session notes — the durable record)

| Date | What happened |
|---|---|
| 2026-07-05 | Article-team QA question received (well-days basis). Root cause found the same day: our `/completion/` page headlined drilling-only days; true D&C total reconciles (§3). PR [#841](https://github.com/vamseeachanta/worldenergydata/pull/841): verification page + Total-D&C column shipped. |
| 2026-07-06 | Consistency review found the original headline comparison was not like-for-like (offsetting Big Foot-vs-Buckskin); reframed via PR [#843](https://github.com/vamseeachanta/worldenergydata/pull/843). Buckskin identity recovered (six Keathley Canyon leases; the shelf-only extract had dropped it). |
| 2026-07-06 | All four article tables validated against `financial_project_summary.xlsx` (§1–2); five discrepancies documented with comparison tables (§4); STOIIP confirmed to have no government source (§5). |
| 2026-07-06 | KC deepwater ingest landed (PR #851): canonical extractor reads raw WAR `.bin`; Buckskin becomes a matched row (§3); Anchor fidelity pinned exactly by test. Benchmark renamed to "World Oil April 2026 article" everywhere (PR #852). This report committed (PR #853). |
| 2026-07-06 | BOEM reserves + discovery ingest landed (#847 / PR #861, plan #854 with two adversarial review rounds): annual Table 4 workbook + Deepwater Qualified Fields on refresh cadence; curated per-development table with citation columns; **Stones reserves discrepancy surfaced** (§5.1). Follow-on source family filed as #855. |
