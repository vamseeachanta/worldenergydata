# FDAS Canonicalization Notes from Roy Shilling

Source: Roy Shilling email text provided by Vamsee in the 2026-07-08 BSEE/FDAS
analysis session.

## Confirmed Direction

- `worldenergydata` (`wed`) should become the canonical go-forward codebase for
  Frontier-Deepwater Lower-Tertiary economics.
- The current wed V30 reproduction quality is a valid reproduction gate: about
  +/-0.1% oil and +/-1% NPV versus the frozen V30 baseline.
- That validates the codebase and reproduction harness. It does not mean every
  current wed assumption is final.
- Roy's shipped V50 economic model is broader than wed's current window-only
  "V50" run because it includes after-tax logic, NOL carryforward, changed cost
  assumptions, and the expanded lease set.
- Keep a pre-tax comparison case, but do not retreat to a pre-tax-only V30 model
  as the sole go-forward model.

## Required Follow-Ups

1. Write a one-page V50 assumptions change log before accepting the V50 cost and
   model changes as canonical: [#899](https://github.com/vamseeachanta/worldenergydata/issues/899).
2. Settle the NPV reference-date convention. Roy recommends discounting from
   first material project expenditure as the primary thesis case because long
   pre-first-oil capital exposure is part of the Lower-Tertiary economics story:
   [#900](https://github.com/vamseeachanta/worldenergydata/issues/900).
3. Keep the D&C reconciliation closed. V50, V30, and wed D&C extraction match to
   the day on the reconciled path; no well-level drill-down is needed when the
   field-level delta is zero.
4. Fix the actionable bug queue without blocking canonicalization on low-priority
   latent issues: [#875](https://github.com/vamseeachanta/worldenergydata/issues/875).
5. After the assumptions and NPV convention are settled, generate and freeze one
   official `financial_project_summary_V50_canonical.xlsx` validation workbook:
   [#901](https://github.com/vamseeachanta/worldenergydata/issues/901).

## Bug Priority from Roy's Note

Prioritize:

- OGOR-A reader improvements: all file members, deduping, better parsing.
- Product-code filtering so oil volumes are explicitly oil.
- Targeted completion-day WAR remark check.
- CAPEX timeline guard so project spend cannot fall outside the model window.
- MIRR assumption fix after NPV-critical work.

Do not let low-priority water-column labeling issues hold up the canonical
economic model.

## Current Commit Boundary

This commit fixes stale frozen V30 reference values in per-field V50 reports by
rendering the official V30 reference values from
`config/analysis/lower_tertiary/golden_baseline_v30.yml`.

It does not adopt Roy's full after-tax V50 model, settle the NPV discount
reference convention, or generate the canonical V50 workbook. Those are tracked
in [#899](https://github.com/vamseeachanta/worldenergydata/issues/899),
[#900](https://github.com/vamseeachanta/worldenergydata/issues/900), and
[#901](https://github.com/vamseeachanta/worldenergydata/issues/901).
