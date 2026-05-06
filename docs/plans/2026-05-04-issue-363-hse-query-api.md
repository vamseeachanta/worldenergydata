# Plan: Issue #363 — Public Python query API for HSE module

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/363
**Status:** plan-review
**Tier:** T3 (new public API surface mirroring marine_safety)

## Context
`marine_safety` has `wed.marine_safety_api.incidents.query(source, year, incident_type)`.
`hse` module has importers + DB models but no equivalent query surface.

## Plan

### Task 1 — Audit current HSE module structure
```bash
find src/worldenergydata -path "*/hse*" -name "*.py" | head -20
```
Understand existing importers, models, and any partial query code.

### Task 2 — Design query API
Mirror marine_safety interface:
```python
# src/worldenergydata/hse/api.py
class HSEIncidentsQuery:
    def query(
        self,
        source: str = "bsee_inc",  # bsee_inc | osha | pipeline
        year: int | None = None,
        operator: str | None = None,
        incident_type: str | None = None,
        limit: int = 100,
    ) -> pd.DataFrame: ...
```

### Task 3 — Implement query against existing DB
Wire `HSEIncidentsQuery.query()` to the SQLAlchemy session from `hse.database`.
Support all filter combinations with SQLAlchemy dynamic filters.

### Task 4 — Export from hse package __init__.py
```python
from worldenergydata.hse.api import HSEIncidentsQuery
```

### Task 5 — CLI sub-app (if not already present)
In `src/worldenergydata/cli/commands/hse.py`, add a `query` command that calls the API.

### Task 6 — Tests
```python
def test_query_returns_dataframe():
    q = HSEIncidentsQuery()
    result = q.query(source="bsee_inc", limit=10)
    assert isinstance(result, pd.DataFrame)
    assert len(result) <= 10
```

## Acceptance Criteria
- `HSEIncidentsQuery().query(source="bsee_inc", year=2022)` returns a DataFrame
- API symmetry with marine_safety: same kwargs, same return type
- Unit tests with DB fixture pass
