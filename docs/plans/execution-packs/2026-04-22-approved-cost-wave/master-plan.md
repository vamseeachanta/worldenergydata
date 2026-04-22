# Approved Cost Wave — Parallel Execution Pack

Date: 2026-04-22
Repo: worldenergydata
Mode: parallel implementation wave with zero git contention
Approved issues in scope:
- #335 — disclosure-to-CostDataPoint linkage model
- #337 — citation quality and automated ingestion contracts for annual disclosures
- #338 — annual disclosure analytics views and integration surface for cost/fdas/lower_tertiary
Excluded:
- #336 — not approval-ready / still blocked

## Wave structure

Wave 1 (parallel, safe)
- Stream A: #335
- Stream B: #338

Wave 2 (serial after Wave 1)
- Stream C: #337

Reason:
- #335 and #337 both own `src/worldenergydata/cost/data_collection/__init__.py` and therefore cannot run concurrently without git contention.
- #338 writes to `src/worldenergydata/cost/__init__.py`, `src/worldenergydata/fdas/`, and cost analytics tests, so it is file-disjoint from #335 and #337 except for broad repo test surfaces.

## Contention map

Stream A (#335) writes:
- `src/worldenergydata/cost/data_collection/linkage.py`
- `src/worldenergydata/cost/data_collection/__init__.py`
- `tests/unit/cost/test_linkage.py`

Stream B (#338) writes:
- `src/worldenergydata/cost/disclosure_analytics.py`
- `src/worldenergydata/cost/__init__.py`
- `src/worldenergydata/fdas/api.py`
- `src/worldenergydata/fdas/__init__.py`
- `tests/unit/cost/test_disclosure_analytics.py`
- `tests/unit/fdas/test_disclosure_api.py`
- `tests/test_query_api.py`

Stream C (#337) writes:
- `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py`
- `src/worldenergydata/cost/data_collection/__init__.py`
- `tests/unit/cost/test_disclosure_ingest_contract.py`

Zero-overlap rule:
- Stream A and Stream B may run concurrently.
- Stream C must wait until Stream A is fully committed/pushed because both own `src/worldenergydata/cost/data_collection/__init__.py`.

## Global execution rules

- Use TDD: write tests first, confirm failing proof, then implement minimum code.
- Use only approved issue scope. Do not absorb #336 or any parent/sibling scope.
- Post concise GitHub execution-start and closeout comments on the assigned issue.
- Run targeted validation first; expand only as needed.
- If a stream discovers adjacent work, create or propose a follow-up issue instead of expanding scope.
- If a required change falls outside owned paths, stop and return control.

## Morning deliverables

From Stream A (#335)
- linkage contract module
- tests for linked/unlinked/ambiguous behavior and operator-row non-linkability
- issue comment with validation evidence

From Stream B (#338)
- derived analytics view module
- FDAS disclosure namespace/API seam
- tests for raw-vs-derived separation and package-level API exposure
- issue comment with validation evidence

From Stream C (#337)
- disclosure ingest contract module
- tests for citation validity, duplicate/conflict classification, and source-priority conflict reasoning
- issue comment with validation evidence
