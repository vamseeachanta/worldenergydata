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
4. **Five article errors were found** and are documented with our evidence for QA hand-back (§4).
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
| 4 | STOIIP / recovery | ✅ recovered volumes match 7/9 (see errors E1, E5) | STOIIP wholly external — see §5 |

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

## 4. Errors found in the article (QA hand-back)

Surfaced by our BSEE-grounded check; these are the article's errors, not ours.

| # | Error | Our evidence |
|---|---|---|
| E1 | **Table 4 "recovered = 1" for Anchor and Shenandoah** — stale placeholder | Our OGOR-A: Anchor 9.5–18.6 MMbbl, Shenandoah 21.2 MMbbl. Contradicts the article's own Table 2. |
| E2 | **Stones NPV/NCF row duplicates the Tiber row** | Real Stones NPV ≈ −$1,461M (V50 rerun; recorded 2026-07-06 validation), not −$228M. |
| E3 | **Cascade Chinook NCF +$3,656M alongside NPV −$1,122M — impossible** | Our canonical workbook: Cascade Chinook lifetime NCF **−$3,820M** (V30, thru 2025-05). A field with 34 MMbbl produced and ~$1.8B lifetime OPEX cannot post +$3.7B NCF. |
| E4 | **Julia and Stones OPEX = 0** for fields producing since 2016 | V30 workbook lifetime OPEX: Julia $1,119M; Stones $1,610M. |
| E5 | **Jack St Malo recovery factor prints 10%** | Their own figures: 420/5,000 = 8.4%. |

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
| 2026-07-06 | All four article tables validated against `financial_project_summary.xlsx` (§1–2); five article errors documented (§4); STOIIP confirmed to have no government source (§5). |
| 2026-07-06 | KC deepwater ingest landed (PR #851): canonical extractor reads raw WAR `.bin`; Buckskin becomes a matched row (§3); Anchor fidelity pinned exactly by test. Benchmark renamed to "World Oil April 2026 article" everywhere (PR #852). This report committed (PR #853). |
| 2026-07-06 | BOEM reserves + discovery ingest landed (#847 / PR #861, plan #854 with two adversarial review rounds): annual Table 4 workbook + Deepwater Qualified Fields on refresh cadence; curated per-development table with citation columns; **Stones reserves discrepancy surfaced** (§5.1). Follow-on source family filed as #855. |
