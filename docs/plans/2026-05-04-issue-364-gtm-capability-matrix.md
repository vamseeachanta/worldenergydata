# Plan: Issue #364 — Publish GTM capability matrix

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/364
**Status:** plan-review
**Tier:** T2 (docs generation script from manifest)
**Depends on:** #354 (manifest schema) — DONE

## Context
#354 added `catalog_status`, `public_cli`, and `capability_source` to all 27 modules in
`module-manifest.yaml`. This plan generates the buyer-facing GTM capability matrix from
that authoritative source.

## Plan

### Task 1 — Write generation script
`scripts/gtm/generate_capability_matrix.py`:
```python
# Reads module-manifest.yaml
# Classifies each module into Tier A / B / C based on catalog_status:
#   Tier A: catalog_status in {"full", "reference_data"} → production-ready
#   Tier B: catalog_status in {"sample", "runtime_fetched"} → staging
#   Tier C: catalog_status in {"empty", "not_applicable", "unknown"} → roadmap
# Emits:
#   docs/gtm/capability-matrix.md (human-readable table)
#   data/capability-matrix.json (machine-readable for #350 freshness scorecard)
```

### Task 2 — Generate `docs/gtm/capability-matrix.md`
Three-tier table per issue spec:
- **Tier A** — production-ready: module, region, records, last refresh, API/CLI, coverage
- **Tier B** — staging: module, records, blocker, ETA
- **Tier C** — roadmap: module, status, notes

Populate from `module-manifest.yaml` + `data/catalog.yaml` record counts.

### Task 3 — Generate `data/capability-matrix.json`
Machine-readable sidecar (for freshness scorecard #350):
```json
{"generated_at": "...", "modules": [{"id": "bsee", "tier": "A", ...}]}
```

### Task 4 — Link from README.md
Add one line to README under "Modules" section:
```markdown
See [Capability Matrix](docs/gtm/capability-matrix.md) for production-ready vs staging vs roadmap status.
```

### Task 5 — Smoke test
```bash
python3 scripts/gtm/generate_capability_matrix.py
# Assert docs/gtm/capability-matrix.md exists and has Tier A/B/C sections
# Assert data/capability-matrix.json is valid JSON
python3 -c "import json; json.load(open('data/capability-matrix.json'))"
```

## Acceptance Criteria
- `docs/gtm/capability-matrix.md` exists with three-tier format
- `data/capability-matrix.json` is valid JSON with per-module tier assignments
- Script is idempotent (re-running overwrites cleanly)
