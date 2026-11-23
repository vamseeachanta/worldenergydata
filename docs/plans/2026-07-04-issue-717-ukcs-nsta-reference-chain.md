# Plan — worldenergydata #717: UK NSTA Reference-Chain Slice

- **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/717
- **Date:** 2026-07-04
- **Status:** plan-approved
- **Client:** N/A
- **Project:** N/A
- **Lane:** lane:codex
- **Complexity:** T2
- **Dependencies:** #714, #715, #716

## Resource Intelligence Summary

The implementation will mirror the approved Norway reference-chain slice from
#716 while using the UK NSTA production loaders already present in the repo.
`UkcsAdapter` currently returns synthetic benchmark data from
`packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py`.
The real UK production path already exists through `NSTAClient` and
`UKCSFieldProductionLoader`, which produce normalized rows with `field`, `year`,
`month`, `oil_bbl`, `gas_mcf`, and `water_bbl`.

The approved v2 plan notes three correctness constraints:

- The loader uppercases fields, so the adapter bridge will restore titlecase
  `field_name` values to preserve the existing adapter surface.
- `condensate_bbl` will be `NaN`, not `0.0`, because this loader does not
  extract a separate condensate stream.
- Existing UKCS adapter/router/registration tests will stay green while a
  raw-NSTA fixture proves the loader-backed path offline.

Runtime reproduction is N/A because this is an approved feature slice rather
than a reported failing behavior. Baseline tests will be run before and after
implementation.

## Artifact Map

- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py`
  will gain a loader-backed NSTA path while retaining the existing compatibility
  fixture behavior when no loader is supplied.
- `packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py`
  will provide a sparse UK `FieldMetaMapping` consumer for F2.
- `packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py`
  will run the one-field UK chain through production normalization, concept
  screening, and pre-tax cashflow plumbing.
- Unit tests will pin the UKCS bridge, sparse FieldConcept mapping,
  recommendation output, and finite labeled chain metrics.

## Deliverable

This slice will prove one fixture UK field through:

1. `UkcsAdapter.fetch` using a fixture-backed NSTA production loader path.
2. `to_fdas_production` producing the FDAS monthly-production schema.
3. Sparse UK `FieldMetaMapping` producing a valid `FieldConcept`.
4. `recommend()` returning a deterministic ranked list.
5. `CashflowEngine` returning finite pre-tax metrics labeled
   `chain_plumbing_pre_tax`.

The implementation will not publish a UK investment NPV headline. UK after-tax
EPL/RFCT wiring and reconciliation with `UKFiscalRegime` remain deferred to
#736.

## TDD Test List

- UKCS loader-to-`STANDARD_COLUMNS` bridge:
  field titlecasing, `region="ukcs"`, `source="nsta"`, real `water_bbl`,
  and `condensate_bbl` as `NaN`.
- `UkcsAdapter.fetch` fixture path converts to FDAS production.
- Existing UKCS adapter/router/registration compatibility tests remain green.
- UK sparse field metadata maps to `FieldConcept` with `region="uk"`.
- Sparse UK FieldConcept produces a deterministic ranked concept list.
- One-field UK reference chain returns finite pre-tax metrics and the explicit
  `chain_plumbing_pre_tax` label.

## Acceptance Criteria

- Loader-backed `UkcsAdapter.fetch` emits exactly the unified
  `STANDARD_COLUMNS` contract for supplied NSTA loader data.
- Existing UKCS compatibility tests stay green.
- UK FieldConcept mapping ships with the approved sparse metadata boundary.
- Reference-chain metrics are finite and explicitly labeled as pre-tax chain
  plumbing.
- No UK after-tax or investor-value headline is claimed.
- Legal/security scan and focused local tests pass; PR CI passes before merge.

## Review Evidence

The live GitHub issue carries `status:plan-approved`. Its v2 plan comment records
an adversarial review with blocking findings folded: titlecase bridge, condensate
`NaN`, compatibility fixture coverage, UK `region` footgun, and fiscal follow-on
scope. This local artifact materializes that approved issue plan for traceability.
