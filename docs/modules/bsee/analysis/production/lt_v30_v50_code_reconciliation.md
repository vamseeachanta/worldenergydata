# Lower Tertiary V30 → V50: Code Reconciliation & Canonical-Path Decision

**Date:** 2026-06-26
**Scope:** `worldenergydata` BSEE module — Lower Tertiary financial baselines
**Trigger:** Roy Shilling's "leases rerun with the latest ogora files and mv_war …
do some qa/qc compared to before" → establish a new gold standard (**V50**) from
the latest BSEE OGOR-A, reproduce V30 first, and reconcile the analysis code.

---

## 1. The two code paths that existed

Before this work there were **two** Lower Tertiary analysis lanes that did not
agree, because they were written for different purposes at different times:

| | Path A — `latest_runner` (WRK-010) | Path B — `reproduce_v30_financials` (WRK-009) |
|---|---|---|
| Module | `lower_tertiary/latest_runner.py` | `lower_tertiary/v30_financial_reproducer.py` |
| Writes | `config/.../latest_baseline.yml` | `golden_baseline_v30.yml` (validation target) |
| Computes | **production + revenue only** | **full financials** (D&C, facilities, royalty, opex, NPV, MIRR) |
| First-oil dates | applies `FIRST_OIL_CORRECTIONS` (Cascade Chinook → 2012-09-01) | uses golden-baseline dates as-is (Cascade → 2014-01-01) |
| WTI | extended EIA/FRED cascade | frozen V30 xlsx (None) / extended cascade (end_date) |
| Window | latest OGOR month | frozen 2025-05 (None) / any end_date |

### Qualitative differences

1. **First-oil correction (the real disagreement).**
   Path A corrects Cascade Chinook's first production from **2014-01-01 → 2012-09-01**;
   Path B does not. Raw BSEE OGOR shows Cascade well **608124004602** online
   **2012-09-01**, and `reports/lower_tertiary/wrk010_latest_data_report.md`
   records the fix ("corrects Cascade Chinook's first_oil … adding ~3.26M [bbl]").
   → The golden V30 date is a **carried-over error**; the correction is **verified**.

2. **Financial coverage.** Path A never computed NPV/MIRR/costs — it was a
   production+revenue extension only. Any "latest" economics had to fall back to
   the frozen V30 NPV. Path B is the only engine that produces full economics.

3. **Jack St Malo D&C timing (a tolerance, not a bug).** Path B allocates D&C
   spend **monthly from raw OGOR**, whereas Roy's V30 Excel used pre-processed
   D&C timing. This yields a **known ~7.3% NPV deviation** for JSM
   (`test_jsm_npv_within_known_deviation`, `rel=0.08`). All other producing
   fields reproduce within ±1% NPV and ±0.1% production.

---

## 2. Which code is right — decision

| Question | Decision | Rationale |
|---|---|---|
| Cascade first-oil for the **new standard**? | **2012-09-01 (corrected)** | Verified against raw OGOR + WRK-010 report; 2014-01 is an error. |
| Cascade first-oil for **frozen V30**? | **2014-01-01 (unchanged)** | V30 must keep matching Roy's sanctioned Excel so the reproduction gate stays valid. |
| Canonical economics engine? | **`reproduce_v30_financials`** | Only path with full financials; now the single engine for both vintages. |
| JSM D&C timing? | **raw-OGOR monthly allocation** | Fully reproducible from public source; Roy's Excel pre-processing is not. 7.3% offset documented, not "fixed". |
| Two lanes? | **Unify** | `reproduce_v30_financials` now accepts `first_oil_overrides`; V50 passes `latest_runner.FIRST_OIL_CORRECTIONS`, so V50 == `latest_baseline` on oil/revenue **and** adds NPV/MIRR. |

**Net:** there is now **one** financial engine. V30 = engine with no overrides
(frozen, matches Roy). V50 = same engine, latest window, **plus the verified
first-oil corrections**. Every V30→V50 delta is therefore attributable to (a)
new production data, (b) the longer window, and (c) the one verified Cascade fix —
never to an unexplained methodology change.

---

## 3. Repo code changes made

- `v30_financial_reproducer.reproduce_v30_financials(end_date=None,
  first_oil_overrides=None)`:
  - `end_date` parametrises the window (None ⇒ exact frozen V30).
  - `first_oil_overrides` corrects first-oil for **both** the production window
    and the D&C/facilities cashflow timing.
  - now also returns `total_oil_bbl` per development.
- `FIRST_OIL_CORRECTIONS` remains defined once in `latest_runner.py` and is
  imported by the V50 generator (single source of truth).
- New `scripts/lower_tertiary/regenerate_golden_baseline_v50.py` →
  `config/analysis/lower_tertiary/golden_baseline_v50.yml`.
- New `scripts/lower_tertiary/build_v30_vs_v50_comparison.py` →
  `reports/lower_tertiary/v30_vs_v50_comparison.md`.

## 4. Reproduction gate (run before any update)

`reproduce_v30_financials()` (no overrides) was diffed against the frozen
`golden_baseline_v30.yml`: production within ±0.1% and NPV within ±1% for all
matched projects; JSM NPV within its documented ~7.3% band. Gate **passed**, so
the V50 deltas are trustworthy. See `tests/unit/lower_tertiary/test_v50_baseline.py`
and `reports/lower_tertiary/v30_repeatability_report.md`.
