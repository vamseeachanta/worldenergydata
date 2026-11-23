# Plan: Issue #143 — BSEE field economics case study (calibrated cost data)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/143
**Status:** plan-review
**Tier:** T3 (case study report using cost disclosure + FDAS)
**Depends on:** #334–#338 (disclosure dataset), #367 (API12 NPV migration)

## Context
Issue asks to rebuild a BSEE field economics case study using WRK-019 (calibrated cost data)
and WRK-171 (disclosure dataset). Both are now available via the annual disclosure pipeline.

## Plan

### Task 1 — Select case study field
Recommend: `Thunder Horse` or `Atlantis` — both have complete production history and
are covered by the FDAS portfolio analysis.

### Task 2 — Load calibrated cost data
```python
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset
df = load_public_dataset()
thunder_horse = df[df["field"].str.contains("Thunder Horse", case=False)]
print(thunder_horse[["year", "capex_mm", "opex_mm", "operator"]].to_string())
```

### Task 3 — Run FDAS analysis with calibrated costs
```python
from worldenergydata.fdas.api import EconomicsQuery
q = EconomicsQuery()
result = q.analyze(field="Thunder Horse", capex=thunder_horse["capex_mm"].sum(), ...)
```

### Task 4 — Generate case study HTML report
`scripts/gtm/generate_field_case_study.py`:
- Input: field name + cost data
- Output: `reports/gtm/YYYY-MM-DD-{field}-case-study.html`
- Include: production profile, cost breakdown, NPV sensitivity, operator benchmarking

## Acceptance Criteria
- Case study HTML report generated for at least 1 field
- Uses calibrated cost data from annual disclosure dataset
- NPV/IRR computed via FDAS forward layer (not legacy path)
