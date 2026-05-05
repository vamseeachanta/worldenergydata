# Plan: Issue #361 — Adopt calc-citation-contract for worldenergydata calc outputs

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/361
**Status:** plan-review
**Tier:** T3 (citation schema adoption across calc modules)
**Rule:** `.claude/rules/calc-citation-contract.md`

## Context
The workspace-hub calc-citation-contract requires all standards-derived constants to emit
`Citation` instances as sidecars. Pilot reference: `digitalmodel/orcaflex/mooring_design.py`.

## Scope
Target calc modules for initial adoption:
1. `fdas/core/financial.py` — NPV/IRR/MIRR (BSEE federal royalty 12.5%, WTI price deck)
2. `lower_tertiary/portfolio_economics.py` — breakeven calculations
3. `bsee/analysis/production_api10.py` — production analysis constants

## Plan

### Task 1 — Import citation schema
`src/worldenergydata/citations/__init__.py` (create if absent):
```python
from worldenergydata.citations.schema import Citation, CitationResolutionError
```
Mirror the digitalmodel pilot: `digitalmodel/src/digitalmodel/citations/schema.py`.

### Task 2 — Identify standards-derived constants in target files
Grep for numeric literals with regulatory origin:
- `0.125` or `12.5` → BSEE federal royalty rate
- `0.10` or `0.12` → discount rate (industry convention, not a standard — skip)
- WTI price deck references

### Task 3 — Wire citations in `fdas/core/financial.py`
For BSEE federal royalty rate constant:
```python
BSEE_FEDERAL_ROYALTY_RATE = 0.125
_citation_royalty = Citation(
    code_id="30-CFR-250-royalty",
    constant_name="federal_royalty_rate",
    value=BSEE_FEDERAL_ROYALTY_RATE,
    publisher="BSEE",
)
```

### Task 4 — Fail-closed validation
Per calc-citation-contract: `CitationResolutionError` on missing wiki page.
If wiki page doesn't exist yet, create stub at `knowledge/wikis/.../30-CFR-250-royalty.md`.

### Task 5 — Sidecar emission pattern
Calc functions return `(result, citations: list[Citation])` tuple.
Callers that don't need citations receive `result` only; citations are opt-in.

## Acceptance Criteria
- BSEE federal royalty rate (12.5%) emits a `Citation` instance in FDAS calc path
- `CitationResolutionError` raised if wiki page absent
- No downstream consumer API change (citations in sidecar only)
