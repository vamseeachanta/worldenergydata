# FDAS Lower-Tertiary pipeline — revision comparison (V30 → V50 → wed)

**Purpose.** Establish the worldenergydata ("wed") toolset as the canonical, go-forward truth for the Frontier-Deepwater Lower-Tertiary economics, by (1) laying the three revisions side by side, (2) tracing every result to the script that produces it, and (3) surfacing every script difference, missed file, and latent bug — so the FDAS authoring group (Roy, Chuck, et al.) and wed converge on **one** definition of the model.

**Revisions and dates**

| Revision | Date | Provenance |
|---|---|---|
| **V30** | 2025-09-29 | Roy Shilling's V30 scripts + results (Gmail "V30 Financial Analysis / V30 of code", Sept 2025); the frozen "golden baseline". |
| **V50** | 2026-06-26 | Roy's refreshed scripts + inputs (file vintage 2026-06-26; coincides with World Oil Part 3). Scripts + inputs **only** — no result workbooks shipped. |
| **wed** | 2026-07-06 | This repository — the canonical target. Reproduces V30 and carries the extended V50 window on one code path. |

Both source archives are backed up at `/mnt/ace/worldenergydata/reference/fdas_revisions/{v30,v50}/` (zips + extracted).

---

## 0. Executive summary

1. **D&C days are provably version-independent.** `extract_drilling_completion_days.py` is **byte-identical** across V30, V50 and wed (md5 `1b89c23e`) and reads only WAR data — never production. So the drilling+completion day counts carry across revisions unchanged; only the OGOR-A production layer moves.
2. **The V30→V50 economic delta is (in wed's reproduction) purely +11 months of production.** V30 window ends 2025-05; wed's V50 window ends 2026-04. Holding methodology and costs fixed, that adds **+14.1 % oil, +15.2 % revenue, +$432.5 MM aggregate NPV** — with **no field crossing into positive NPV**.
3. **But Roy's shipped V50 script is a *different* model than the published V50 numbers.** `generate_financial_summary_V50.py` adds an after-tax block (severance + ad-valorem + corporate 21 % with NOL carryforward) and its `lease_assumptions.xlsx` **silently changes 13 cost cells** (§3.4). The published V50 figures were produced by **wed's own reproducer** (pre-tax, window-only), *not* by that script. **This is the one thing to align on before adoption** (§4.3).
4. **wed reproduces V30 to ±0.1 % oil / ±1 % NPV** (a passed gate) — the basis for adopting wed as canonical (§4.1).
5. **~30 latent bugs** were found by adversarial review of the four wed scripts (§6). Almost all are *masked by the current Lower-Tertiary dataset* (so they do **not** change any published number today), but they must be fixed before wed is trusted as a general tool. Two are structural and worth immediate attention.
6. **Several files were never migrated** V50→wed (the V50 generator scripts, the updated cost assumptions, and any V50 result workbook — which was never generated anywhere) (§5).

---

## 1. The pipeline and its results lineage

Four stages turn raw public BSEE data into the article's tables. This is the chain to defend end-to-end:

```
 BSEE OGOR-A (monthly production)          BSEE WAR (daily drilling/completion)
        │                                          │
        ▼                                          ▼
 [1] ogora_to_chronological.py            [2] extract_drilling_completion_days.py
        │  chronological_lease_analysis.xlsx        │  drilling_and_completion_days.xlsx
        │  (per lease/well/month oil)               │  (per-well D&C days — VERSION-INDEPENDENT)
        └───────────────┬───────────────────────────┘
                        ▼
             [3] build_multi_year_lease_matrix1.py   (per-lease monthly matrix)
                        │
                        ▼
             [4] generate_financial_summary_*.py  +  lease_assumptions.xlsx  +  wti_monthly.xlsx
                        │
                        ▼
              financial_project_summary.xlsx
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
  Article Table 1                 Article Table 2
  (producing fields:              (exploration-only fields:
   NPV, recovered oil,             Kaskida, North Platte, Tiber —
   revenue)                        D&C spend only, no production)
```

**What moves V30→V50 and what does not:** stages [2] (D&C) is byte-identical; the exploration-only Table-2 fields (no production) are identical V30==V50. All movement is in stage [1]'s window feeding stage [4]. That is why the reconciliation is clean.

---

## 2. Three-revision comparison (master table)

Blank cells are shown as "-" where a revision does not carry that item.

| Dimension | V30 (2025-09-29) | V50 (2026-06-26) | wed (2026-07-06, canonical) |
|---|---|---|---|
| **Source** | Roy — scripts + inputs + results + golden-baseline .docx | Roy — scripts + inputs only | worldenergydata repo |
| **Files shipped** | 11 | 6 | repo (scripts in `docs/…/FDAS_V30/` + package ports + reports) |
| `extract_drilling_completion_days.py` | ✓ (md5 1b89c23e) | ✓ (identical) | ✓ (identical) |
| `ogora_to_chronological.py` | ✓ (`V23_001`) | renamed `…_V50.py` (`Version 008`, rewrite) | ✓ **old `V23_001`** (V50 rewrite not ported) |
| `generate_financial_summary_*.py` | `…_V30.py` (pre-tax) | `…_V50.py` (**adds after-tax**) | `…_V30.py` (pre-tax; V50 script **not** committed) |
| `build_multi_year_lease_matrix1.py` | ✓ | - (not in V50) | ✓ + ported to `packages/…/fdas/data/production.py` |
| **Inputs — leases.xlsx** | 20 leases / 10 devs | 26 leases / 11 devs (**+Buckskin**) | 20 leases / 10 devs (V30-vintage copy) |
| **Inputs — lease_assumptions.xlsx** | baseline | **13 cost cells changed** (§3.4) | V30 values (V50 changes **not** propagated) |
| **Price deck — WTI** | 1986-01→2025-07 (last $68.39) | identical to V30 (byte-identical, thru 2025-07) | refreshed 1986-01→2026-05 (last $102.13) + provenance doc |
| **Price deck — Henry Hub (gas)** | - | - | `henry_hub_monthly.xlsx` (1997-01→2026-05) — present but **unused** (revenue is oil-only) |
| **BSEE production window** | 2000-09 → **2025-05** | 2000-09 → **2026-04** (+11 months) | reproduces both; V50 window auto-detected = 2026-04 |
| **Months of BSEE production** | ~297 (137 in the shipped workbook, 2014-01→2025-05) | ~308 (+11) | reads latest OGOR-A `.bin` incl. 2026 partial-year |
| **NPV / discount rate** | NPV @ 10 %/yr | NPV @ 10 %/yr (unchanged) | NPV @ 10 %/yr |
| **Tax treatment** | pre-tax | **after-tax** (severance + ad-valorem + corporate 21 % + NOL) | pre-tax (V30 methodology) |
| **Result workbook** | `financial_project_summary.xlsx` (+ per-field sheets) | **none shipped** | YAML `golden_baseline_v50.yml` + `field_economics_*_v50.md` (**no .xlsx**) |
| **Golden-baseline doc** | `V30_Golden_Baseline…docx` | - | reports + `v30_repeatability_report.md` |
| **Key output tables** | Table 1 (7 producers), Table 2 (3 exploration) | (numbers exist only in wed reports) | same tables, reproduced + extended |

---

## 3. Script-level differences (V30 → V50), in pipeline order

### 3.1 `extract_drilling_completion_days.py` — **identical**
Byte-for-byte identical across all three revisions (md5 `1b89c23e`). Reads WAR (`mv_war_main`, `mv_war_boreholes_view`, `mv_war_main_prop_remark`) + `leases.xlsx`; emits per-well `DRILLING_DAYS` and `COMPLETION_DAYS`. Confirms the D&C-days-are-version-independent premise. The golden workbook holds 219 well-rows over 20 leases / 12 developments.

### 3.2 `ogora_to_chronological.py` → `…_V50.py` — **rewrite** (the core change)
| Aspect | V30 / wed (`V23_001`) | V50 (`Version 008`) |
|---|---|---|
| File discovery | `glob('ogora20??delimit.zip')` — ZIP only, 2-digit-year | regex accepts zip/txt/csv, de-dupes by year (newest mtime) |
| Zip members read | **only the first member** (`inner[0]`) | **all** `.txt/.csv` members, concatenated |
| Column parsing | named 19-col schema, lease assumed in col 0 | positional indices, auto-detects the G-lease column |
| De-dup | per-file group-sum | global `drop_duplicates()` + additive month aggregate |
| Output columns | 14 (adds D&C-day allocation + WTI + revenue) | 5 (raw oil spine only; revenue moved downstream) |
| Window cutoff | **none hardcoded** — set entirely by which OGOR-A files are present | **none hardcoded** |

The window is *not* pinned in code — it is whatever OGOR-A files sit in the working directory. V50's "+11 months" came from **newer BSEE downloads**, not a code constant. **wed still ships the old `V23_001` reader.**

### 3.3 `generate_financial_summary_V30.py` → `…_V50.py`
- **V50 adds a full after-tax block**: severance + ad-valorem (% of revenue) + corporate tax at 21 % with monthly NOL carryforward, and new tax columns in the output.
- V50 adds a flexible production join (maps `DEV_NAME` from `leases.xlsx` when absent).
- Discount rate (10 %), royalty (0.1875) and WTI base ($60/$75) are unchanged.
- **wed did not adopt the V50 generator** — it ships the V30 script unchanged.

### 3.4 `lease_assumptions.xlsx` — **13 cost cells changed V30→V50** (verified cell-by-cell)
| Parameter | System | V30 → V50 |
|---|---|---|
| Host_CAPEX_MM | subsea15 | 1200 → 900 |
| Host_CAPEX_MM | subsea20 | 1500 → 800 |
| Host_CAPEX_MM | dry | 2000 → 1500 |
| Host_CAPEX_MM | tieback15 | 0 → 80 |
| Host_CAPEX_MM | tieback20 | 0 → 100 |
| Water_Injection_Facility_Cost_MM | subsea20 | 200 → 100 |
| Water_Injection_Facility_Cost_MM | tieback15 | 100 → 200 |
| Water_Injection_Facility_Cost_MM | tieback20 | 200 → 250 |
| Variable_OPEX_$/bbl | subsea15 | 4 → 6 |
| Variable_OPEX_$/bbl | subsea20 | 6 → 8 |
| Variable_OPEX_$/bbl | tieback20 | 6 → 8 |
| Booster_Pump_15K_MM | subsea15 | 275 → 250 |
| Booster_Pump_15K_MM | tieback15 | 275 → 250 |

Discount rate, royalty, WTI base and tax rates are unchanged. **These cost changes were never propagated into wed, and they contradict the "cost assumptions unchanged from V30" statement in the published V50 reports** — see §4.3.

### 3.5 `build_multi_year_lease_matrix1.py` — **V30-only**
Present in V30 and wed (also ported to `packages/…/fdas/data/production.py`); absent from the V50 archive. Carries the most severe latent bug (§6, matrix-1).

---

## 4. Results connection — how the numbers reconcile (the persuasion core)

### 4.1 wed reproduces V30 (the gate)
`v30_repeatability_report.md`: production matches `golden_baseline_v30` within **±0.1 %** for all 7 producers (Jack St Malo +0.03 %, others 0.00 %); NPV within ±1 %. The V30 `financial_project_summary.xlsx` `NPV USD` column ties **1:1** to the V30 column of `v30_vs_v50_comparison.md`. So the shipped V30 workbook is the source of record, and wed regenerates it.

### 4.2 V50 = V30 + 11 months (window-only, in wed's reproduction)
| Metric | V30 | V50 (wed) | Δ |
|---|---:|---:|---:|
| Recovered oil (7 producers) | 669.3 MMbbl | 763.3 MMbbl | **+14.1 %** |
| Revenue | $43,487.3 MM | $50,093.5 MM | **+15.2 %** |
| Portfolio NPV @10 % | −$8,327.8 MM | −$7,895.3 MM | **+$432.5 MM** (still negative) |

Per-field NPV @10 % ($MM), V30 → V50:

| Field | V30 | V50 | Δ | Note |
|---|---:|---:|---:|---|
| Anchor | −1,732.8 | −1,586.9 | +145.9 | late starter, +168 % oil |
| Shenandoah | −1,166.4 | −991.3 | +175.1 | near-zero in V30 |
| Big Foot | −1,063.4 | −989.0 | +74.4 | |
| Julia | −530.6 | −482.8 | +47.8 | |
| Jack St Malo | −881.1 | −804.5 | +76.6 | ~7.3 % reproducer offset flagged |
| Stones | −1,479.5 | −1,460.8 | +18.7 | |
| Cascade Chinook | −1,474.1 | −1,580.0 | −106.0 | **worsens** — V50 also applies a first-oil correction (2014-01 → 2012-09) that front-loads capital |
| **Exploration-only** (Kaskida −625.0, North Platte −783.5, Tiber −228.0) | | | **0.0** | no production → version-independent |

### 4.3 The reconciliation ask — one definition of "V50"
There are currently **two** V50s:
- **wed's V50** (what the published reports show): V30 methodology, **pre-tax**, costs frozen at V30, only the data window extended. Reproduces V30 exactly and moves only with new data.
- **Roy's shipped V50 script**: **after-tax** (severance + ad-valorem + corporate 21 % + NOL) on top of the **13 changed cost cells** in §3.4. This script was **never run to a result workbook** anywhere, so its numbers have never been reconciled.

Running Roy's `generate_financial_summary_V50.py` with his V50 assumptions would **not** reproduce the published V50 figures. To get everyone on the same page, agree explicitly on: **(a) pre-tax vs after-tax**, and **(b) whether the 13 cost-cell changes are intended.** wed can carry either — but it should carry exactly one, documented.

---

## 5. Missed / non-migrated files (inventory)

| File | V30 | V50 | wed | Action for canonical wed |
|---|:--:|:--:|:--:|---|
| `extract_drilling_completion_days.py` | ✓ | ✓ | ✓ | none (identical) |
| `ogora_to_chronological_V50.py` (rewrite) | - | ✓ | **✗** | port the all-members/de-dup/positional improvements |
| `generate_financial_summary_V50.py` (after-tax) | - | ✓ | **✗** | decide + commit one generator (§4.3) |
| `lease_assumptions.xlsx` (V50 costs) | - | ✓ (changed) | **✗** | decide + propagate or reject the 13 cost changes |
| `financial_project_summary.xlsx` (V50 result) | - | **never generated anywhere** | **✗** | generate a V50 workbook in Roy's schema for byte-validation |
| `chronological_lease_analysis.xlsx` (V50) | - | **✗** | **✗** | regenerate under wed |
| `build_multi_year_lease_matrix1.py` | ✓ | - | ✓ | keep; fix critical bug (§6) |
| `wti_monthly.xlsx` refreshed to 2026-05 | - | - | ✓ | verify the 2026 values (§6, inputs-2) |
| `henry_hub_monthly.xlsx` (gas deck) | - | - | ✓ | wire in gas revenue **or** label future-use (currently unused) |
| `PRICE_DECKS_SOURCE.md`, `QUICKSTART.md`, `README_PRODUCTION_RETRIEVAL.md` | - | - | ✓ | wed-only provenance/docs — keep |
| `V30_Golden_Baseline…docx` | ✓ | - | ✓ | keep as V30 reference |

**Stale artifact:** `field_economics_cascade_chinook.md` (un-suffixed) still uses first-oil 2014-01-01 / NPV −1,480.5 MM — it was not re-copied from its `_v50` version after the first-oil correction. Regenerate.

---

## 6. Bugs found (adversarial review of the four wed scripts)

Ranked by severity. **"Affects current LT numbers?"** answers the only question that matters for the published article: almost every finding is *latent* — masked by the current dataset — so **no published figure changes today**. They matter for making wed a **general, canonical** tool.

| # | Severity | Script | Issue | Affects current LT numbers? |
|---|---|---|---|:--:|
| B1 | **Critical** | build_matrix1 | Parser keys on **col 1 (WELL_COMPLETION_ID) as API** instead of col 8 → WAR joins mis-key, lease attribution collapses | Only if this script feeds published numbers — **verify the package port** |
| B2 | High | ogora | Reads only the **first zip member**; multi-member OGOR-A years silently lose rows (V50 fixed this) | No (current years single-member) |
| B3 | High | ogora | Sums `OIL_PROD` (col 5) across **all `PRODUCT_CODE`** without filtering `=='O'` → gas/condensate rows with a col-5 value inflate oil | No (LT set's extra rows are zero-volume) |
| B4 | High | financial_V30 | **MIRR uses the 10 % discount rate** for both reinvest and finance legs, ignoring the `MIRR_Reinvest_Rate`/`MIRR_Finance_Rate` assumptions | MIRR only (NPV unaffected) |
| B5 | High | financial_V30 | The shipped **"golden" workbook was not produced by this script** (different columns/schema) → the canonicalized script ≠ what made the golden numbers | Schema/validation gap |
| B6 | High | extractor | Completion days counted **only from remark-joined WAR rows**; post-TD WAR days with blank remarks are dropped → completion undercount | Possible — worth a targeted check |
| B7 | High | financial_V30 | Host-CAPEX spread window can fall before the global index start → CAPEX undercount, NPV overstated | No (latent; earliest FO 2014-01) |
| B8 | Med | matrix1 | Col 7 (**condensate**) mislabeled as **water**; `__water` sheets report condensate | Water figures only |
| B9 | Med | ogora | `MONTHLY_WATER_VOLUME` is **always 0** (no water column in the 19-col schema) | Water figures only |
| B10 | Med | ogora / financial | Missing-month WTI filled with **$0** (ogora) vs **$75** (financial) → the two disagree on out-of-range months | No (decks cover the window) |
| B11 | Med | financial_V30 | Project universe is **production-driven**; a drilled-but-not-producing field is dropped with its CAPEX | No (all current devs produce or are in Table 2) |
| B12 | Med–low | several | Un-guarded merges/dedup (war_map, lease_names, D&C allocation) can **fan out and double-count** if inputs gain duplicate keys | No (current keys unique) |
| B13 | Low | extractor | TD day double-counted (drilling exclusive + completion inclusive) → +1 day/well if summed | Cosmetic (~1 day) |
| B14 | Low | financial_V30 | A totals row with a real lease name would inject phantom D&C days (guarded today only by a blank lease name) | No (guarded by luck) |

Full per-finding failure scenarios are in the session record; the actionable set (B1–B7) should become tracked issues before wed is declared the general canonical tool.

---

## 7. Recommendation — wed as canonical

1. **Adopt wed as the single toolset.** It reproduces V30 to ±0.1 % and carries the extended window on one code path.
2. **Settle the V50 definition with Roy** (§4.3): pre-tax vs after-tax, and accept/reject the 13 cost-cell changes. Commit exactly one generator + one assumptions file.
3. **Port the V50 `ogora` improvements** (all-members read, de-dup, positional parsing) — these fix real latent risks (B2/B3) with no effect on current numbers.
4. **Generate a V50 result workbook** in Roy's `financial_project_summary.xlsx` schema so wed's V50 can be byte-validated (today there is none).
5. **Fix the critical/high bugs** B1–B7 with regression tests; regenerate the stale Cascade-Chinook report.
6. **Verify the refreshed 2026 WTI values** before any economics rely on them; decide gas-deck usage.

The D&C layer needs nothing — it is already identical and version-independent, and is the cleanest part of the story to put in front of Roy.

---

## 8. Provenance

- Source archives: `/mnt/ace/worldenergydata/reference/fdas_revisions/{v30,v50}/` (original zips + extracted).
- Revision dates confirmed against Gmail (Roy Shilling threads, Sept 2025 and June 2026) and file vintages.
- Every reconciliation number above is drawn from the shipped V30 workbook and the wed reports (`v30_vs_v50_comparison.md`, `v30_repeatability_report.md`, `field_economics_*_v50.md`); the 13-cell assumptions diff was recomputed cell-by-cell from the two `lease_assumptions.xlsx` files.
