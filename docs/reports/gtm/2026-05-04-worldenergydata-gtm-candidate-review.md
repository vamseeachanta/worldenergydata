# worldenergydata — GTM Candidate Review
**Date:** 2026-05-04  
**Author:** ACE Engineer / Claude Code  
**Scope:** Go-to-market readiness assessment for the `worldenergydata` Python library

---

## 1. Module Status

| Module | Package Path | Status | Demo Today? | Notes |
|--------|-------------|--------|-------------|-------|
| **FDAS (Field Dev Economics)** | `worldenergydata.fdas.api` | Ready | Yes | `EconomicsQuery` API clean, all metrics working |
| **Production Forecast / Arps** | `worldenergydata.production.forecast.decline` | Ready | Yes | `ArpsDeclineCurve` full fit/forecast/plot cycle |
| **Lower Tertiary Portfolio** | `worldenergydata.lower_tertiary` | Ready | Yes | Portfolio analytics, NPV, production classifier |
| **Marine Safety / IMO GISIS** | `worldenergydata.marine_safety` | Ready | Yes | 13,160 casualties, 125 years of data |
| **BSEE Field Analysis** | `worldenergydata.bsee` | Blocked | No | Module-level instantiation hangs at import (see §4) |
| **Pipeline Safety (PHMSA)** | `worldenergydata.pipeline_safety` | Data Only | Partial | DB models + importer present; requires live PHMSA data load |

---

## 2. Existing Report Inventory

All reports are under `worldenergydata/reports/`.

### Root-level HTML reports

| File | Size | Content |
|------|------|---------|
| `IMO_GISIS_Executive_Report.html` | 133 KB | Full IMO GISIS executive dashboard — 13,160 casualties, 8 interactive Plotly charts, temporal analysis, severity breakdown, ship types, flag states |
| `marine_safety_cause_analysis_demo.html` | 83 KB | Marine safety cause/event-type analysis with interactive breakdowns |
| `lower_tertiary_field_summary.html` | 25 KB | Lower Tertiary field-level NPV/production summary, interactive Plotly |
| `field_analysis_report.html` | 29 KB | BSEE field analysis report (static) |
| `anchor_field_demo_report.html` | 12 KB | Anchor field demonstration report |
| `lower_tertiary_field_summary.md` | 4.5 KB | Markdown version of LT field summary |
| `REPORT_SUMMARY.md` | 7.5 KB | IMO GISIS report metadata, methodology, and usage guide |

### Subdirectory reports

| Path | Files | Content |
|------|-------|---------|
| `reports/marine_safety/` | 5 files (9–10 KB each) | Executive summary, fatality analysis, foundering analysis, hatch analysis |
| `reports/lower_tertiary/` | 2 markdown files (3.7–5.9 KB) | v30 repeatability and WRK-010 latest data reports |
| `reports/bsee/` | 1 HTML + subdirs | Buckskin well analysis (5.9 KB); intervention and lower_tertiary subdirs present (empty) |
| `reports/gtm/` | 1 HTML (63 KB) | **NEW 2026-05-04**: FDAS Field Development Economics interactive report |

---

## 3. GTM Readiness Matrix

| Module | Demo Script Available | Interactive HTML | Client-Grade Output | Production Data | Blockers |
|--------|----------------------|-----------------|---------------------|-----------------|----------|
| FDAS Economics | Yes (`scripts/gtm/generate_fdas_gtm_report.py`) | Yes | Yes | No (scenarios) | None |
| Production / Arps | Yes (embedded in FDAS GTM) | Yes | Yes | No (synthetic) | None |
| Lower Tertiary Portfolio | Partial (`scripts/lower_tertiary_analysis.py`) | Yes (existing HTML) | Yes | Yes (BSEE seeded) | Minor: needs refresh script |
| Marine Safety / IMO GISIS | Yes (`reports/imo_gisis_analysis_report.py`) | Yes (existing 133 KB HTML) | Yes | Yes (13,160 records) | None |
| BSEE Field Analysis | Yes (various `scripts/bsee/`) | Yes (`field_analysis_report.html`) | Partial | Yes (300 MB binary, not in git) | Import hang blocks module-level load |
| Pipeline Safety | No standalone demo | No | No | Requires manual PHMSA download | Data requires `make data` step |

### Summary: Demo-ready today

- FDAS Economics + Arps Decline: **fully demo-able**, self-contained, no external data
- Marine Safety / IMO GISIS: **fully demo-able**, data already loaded, 133 KB HTML ready
- Lower Tertiary Portfolio: **demo-able** with existing HTML; live re-run needs BSEE data

---

## 4. Blockers

### BSEE Module — Import Hang (Critical)

**File:** `src/worldenergydata/bsee/data/bsee_data.py` (lines 3–10)

**Root cause:** Module-level object instantiation at import time triggers network or filesystem I/O before any user code runs:

```python
# bsee_data.py (lines 6-10)
production = ProductionRouter()   # ← hangs 30+ seconds (network/DB probe)
block      = BlockRouter()
lease      = LeaseRouter()
well       = WellData()
data_refresh = DataRefresh()
```

`ProductionRouter.__init__` (or one of its transitive dependencies) attempts to locate or open the ~300 MB BSEE binary dataset (`data/` directory, not tracked in git). On machines where the binary is absent, the router stalls waiting for a path that does not resolve.

**Impact:** Any `import worldenergydata.bsee` chain hangs the Python process. All BSEE-related scripts must be excluded from GTM demos that run in clean environments.

**Fix (recommended):** Defer instantiation behind `@classmethod` or lazy property. Replace module-level singletons with factory functions:
```python
def get_production() -> ProductionRouter:
    return ProductionRouter()
```

**Workaround (immediate):** Never import `worldenergydata.bsee` in GTM scripts. The FDAS and production modules are fully independent.

### Pipeline Safety — No Demo Data

PHMSA data requires a separate download step (`make data` / `scripts/refresh_*.sh`). The database schema and importer are complete (~21,000 incident records when loaded), but a client-facing demo requires the data to be present and imported.

---

## 5. Next Actions — Prioritized for GTM Impact

### P1 — Immediate (this week)

1. **Publish FDAS GTM report** (`reports/gtm/2026-05-04-fdas-field-development-economics.html`, 63 KB) — send to client contacts with field development economics interest.
2. **Package IMO GISIS HTML** (`IMO_GISIS_Executive_Report.html`, 133 KB) — already client-grade; include in marine operations deck.
3. **Create a one-page "worldenergydata capabilities" landing page** combining the module status table and links to the 3 ready HTML reports.

### P2 — Short-term (2–4 weeks)

4. **Fix BSEE module-level instantiation** — lazy-load `ProductionRouter` / `BlockRouter` / `LeaseRouter` / `WellData` so the module imports without hanging. Unlocks GoM production analytics demo.
5. **Create Arps decline demo with real data** — use any of the BSEE or Lower Tertiary production series to replace synthetic GoM well in the GTM report.
6. **Add Pipeline Safety demo** — bundle 500 representative PHMSA records into `data/modules/pipeline_safety/sample/` so the module can be demoed without the full download.

### P3 — Medium-term (1–2 months)

7. **Lower Tertiary live refresh** — parameterize `lower_tertiary_analysis.py` to re-run in <60 seconds against latest BSEE data; output directly to `reports/gtm/`.
8. **Unified GTM demo runner** — single `scripts/gtm/run_all_demos.py` that generates all 3–4 demo reports in sequence, with error isolation so one blocked module does not fail the rest.
9. **Client-facing README / landing page** — add `docs/reports/gtm/README.md` linking to generated HTML reports with thumbnail screenshots.

---

## 6. Client Value Proposition

### FDAS — Field Development Economics (`EconomicsQuery` + `ArpsDeclineCurve`)
**Audience:** E&P engineers, petroleum economists, project finance teams  
**Value:** Rapid, programmable NPV/IRR/MIRR/payback analysis across multiple project scenarios. Replaces ad-hoc Excel spreadsheets with auditable, version-controlled Python code. The `ArpsDeclineCurve` module enables reserve estimation (EUR) and production forecasting from historical well data, directly feeding into cashflow models.

**Key demo differentiator:** Scenario comparison across shallow/deepwater/FPSO/tieback in seconds; sensitivity to discount rate shown interactively. No black-box spreadsheet.

### Marine Safety / IMO GISIS
**Audience:** Marine operations managers, HSE leads, flag state consultants, P&I clubs  
**Value:** 125 years of global marine casualty data (13,160 events) normalized into a queryable Python dataset. Enables fleet risk benchmarking, casualty trend analysis, and regulatory compliance reporting against IMO GISIS standards. The existing 133 KB interactive HTML report is client-deliverable as-is.

**Key demo differentiator:** Rare combination of historical depth (1900–2025), standardized schema, and live Python API — not a static spreadsheet or closed vendor tool.

### Lower Tertiary Portfolio Analytics
**Audience:** GoM deepwater operators, reservoir engineers, asset managers  
**Value:** Portfolio-level NPV aggregation and production classification for Lower Tertiary wells — the deepest, highest-CAPEX tier of GoM development. Integrates with BSEE production data to provide a data-driven view of the Lower Tertiary's economics vs. conventional GoM assets.

**Key demo differentiator:** Lower Tertiary is an under-served niche in commercial analytics platforms; `worldenergydata` provides a purpose-built module with real BSEE seeded data.

### BSEE Field Analysis (when unblocked)
**Audience:** GoM operators, lease analysts, regulatory compliance teams  
**Value:** Programmatic access to the full BSEE production, well, lease, and block datasets for the US Gulf of Mexico — the world's most comprehensively regulated offshore basin. Enables production decline monitoring, lease-level economics, and regulatory filing cross-checks.

**Key demo differentiator:** Covers ~300 MB of parsed BSEE data that most clients currently access only through slow, clunky BOEM/BSEE web portals.

### Pipeline Safety (PHMSA)
**Audience:** Pipeline operators, integrity engineers, HSE directors  
**Value:** ~21,000 PHMSA incident records (gas distribution, gas transmission, hazardous liquid, LNG) from 1986–present, normalized into a relational schema with Fitness-for-Service (FFS) workflow integration (see `examples/phmsa_ffs_case_study.py`).

**Key demo differentiator:** Bridges regulatory incident data to engineering integrity assessments — a gap that most operators currently manage manually.

---

*Generated by ACE Engineer / worldenergydata GTM automation — 2026-05-04*
