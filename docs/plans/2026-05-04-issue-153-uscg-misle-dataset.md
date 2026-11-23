# Plan: Issue #153 — Acquire USCG MISLE bulk dataset

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/153
**Status:** plan-review
**Tier:** T2 (data acquisition + ingest)
**Related:** marine_safety module

## Context
USCG MISLE (Marine Information for Safety and Law Enforcement) is the comprehensive US
marine incident database. The marine_safety module currently scrapes individual reports.
Bulk MISLE data would unlock broader trend analysis.

## Plan

### Task 1 — Identify current acquisition method
```bash
find src/ -name "*.py" | xargs grep -l "MISLE\|misle" | head -10
```
Check if any existing scraper handles MISLE bulk exports.

### Task 2 — Research bulk acquisition path
USCG MISLE bulk data may be available via FOIA or public data portal.
Options:
1. USCG public MISLE query portal: `https://cgmix.uscg.mil/MISLE/`
2. FOIA request (separate process, out of scope here)
3. Existing scrapers in `marine_safety/scrapers/`

### Task 3 — Implement bounded acquisition
If portal available:
- Add `src/worldenergydata/modules/marine_safety/scrapers/misle_bulk.py`
- Fetch past 2 years of data as initial acquisition
- Store to `data/modules/marine_safety/misle/`

### Task 4 — Register in data/catalog.yaml and scheduler
If acquisition works, add to `config/scheduler/scheduler_config.yml` with quarterly cadence.

## Acceptance Criteria
- At least 1 year of MISLE incidents acquired and stored locally
- Records accessible via `marine_safety_api.incidents.query(source='misle')`
