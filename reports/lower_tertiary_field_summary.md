# Lower Tertiary Field Summary - Gulf of Mexico

> **⚠️ SUPERSEDED 2026-05-03 by `reports/lower_tertiary/comprehensive_2026.md` (#377).**
> This summary remains the **roster source-of-record** (10 GoM Lower Tertiary fields)
> but is no longer the canonical narrative report. Generate the comprehensive
> replacement via `uv run worldenergydata lower-tertiary comprehensive-report`
> or `python scripts/reporting/assemble_lt_comprehensive.py`.

**Generated:** January 19, 2026
**Data Through:** July 2025

---

## Portfolio Overview

| Metric | Value |
|--------|-------|
| **Total Oil Production** | 685.0 MMBBL |
| **Total Gas Production** | 144.1 BCF |
| **Active Producing Fields** | 6 |
| **Total Wells** | 158 API12 |
| **Active Leases** | 19 federal |
| **Production Period** | 25 years (Sep 2000 - Jul 2025) |

---

## Field Details

### Producing Fields

| Field | System | Water Depth | Leases | Wells | Cum Oil (MMBBL) | Cum Gas (BCF) | % Total |
|-------|--------|-------------|--------|-------|-----------------|---------------|---------|
| **Jack/St. Malo** | Subsea 15K | 7,240 ft | 6 | 26 | 412.46 | 98.70 | 60.2% |
| **Stones** | Subsea 15K | 9,525 ft | 1 | 8 | 84.68 | 12.56 | 12.4% |
| **Julia** | Tieback 15K | 7,335 ft | 1 | 5 | 71.56 | 7.31 | 10.4% |
| **Big Foot** | Dry Tree | 5,190 ft | 1 | 15 | 68.96 | 16.62 | 10.1% |
| **Cascade/Chinook** | Subsea 15K | 8,200 ft | 2 | 3 | 37.79 | 6.33 | 5.5% |
| **Anchor** | Subsea 20K | 5,080 ft | 2 | 5 | 9.51 | 2.59 | 1.4% |

### Under Development / Pre-FID

| Field | System | Water Depth | Leases | Status |
|-------|--------|-------------|--------|--------|
| **Shenandoah** | Subsea 20K | 5,800 ft | 2 | Under Development |
| **Kaskida** | Subsea 20K | 5,860 ft | 2 | Pre-FID |
| **Tiber** | Subsea 20K | 4,130 ft | 1 | Pre-FID |
| **North Platte** | Subsea 20K | 5,840 ft | 2 | Pre-FID |

---

## Top Producing Leases

| Rank | Lease | Field | Cum Oil (MMBBL) | % Total |
|------|-------|-------|-----------------|---------|
| 1 | G21245 | Jack | 209.53 | 30.6% |
| 2 | G17015 | St. Malo | 130.73 | 19.1% |
| 3 | G17001 | Stones | 84.68 | 12.4% |
| 4 | G20351 | Julia | 71.56 | 10.4% |
| 5 | G16942 | Big Foot | 68.96 | 10.1% |

---

## Production by Development System

| System Type | Description | Fields | Cum Oil (MMBBL) | % Total |
|-------------|-------------|--------|-----------------|---------|
| **Subsea 15K** | First-gen HPHT (15,000 psi) | Jack/St. Malo, Stones, Cascade/Chinook | 534.93 | 78.1% |
| **Tieback 15K** | Tieback to existing host | Julia | 71.56 | 10.4% |
| **Dry Tree** | Surface wellheads on TLP/Spar | Big Foot | 68.96 | 10.1% |
| **Subsea 20K** | Next-gen ultra-HPHT (20,000 psi) | Anchor | 9.51 | 1.4% |

---

## Key Insights

- **Market Dominance:** Jack/St. Malo accounts for **60.2%** of total Lower Tertiary production
- **Concentration:** Top 3 developments represent **83.0%** of cumulative output
- **Technology Evolution:** 20K psi subsea systems represent the frontier of deepwater development
- **Water Depth:** Stones is the deepest producing field at **9,525 ft**
- **Future Growth:** 4 pre-FID/development fields represent significant upside potential

---

## Data Sources & Freshness

| Data Source | Description | Last Data Available | Download Date |
|-------------|-------------|---------------------|---------------|
| **BSEE OGOR Production** | Historical production archives | **July 2025** | October 15, 2025 |
| **BSEE 2024 Annual** | Complete 2024 production year | **December 2024** | August 10, 2025 |
| **FDAS V30 Lease Mapping** | Verified lease-to-field mappings | **October 2024** | October 2024 |
| **Economic Assumptions** | Price decks, fiscal terms, CAPEX/OPEX | **December 2024** | December 20, 2024 |
| **Field Configurations** | Water depths, systems, lease counts | **October 2024** | October 21, 2024 |

---

### Notes

- Production data covers September 2000 through July 2025 (25 years)
- BSEE data is published monthly with approximately 2-month lag
- Pre-FID fields show exploration/appraisal well counts only
- Economic assumptions based on industry benchmarks through December 2024

---

## Related Files

- **Interactive Report:** `reports/lower_tertiary_field_summary.html`
- **Production Data:** `results/fdas_production/e_production_by_development_*.csv`
- **Field Configs:** `config/analysis/lower_tertiary/fields/`
- **Lease Mapping:** `config/analysis/lower_tertiary/lease_mapping_fdas.yml`
- **Economic Params:** `config/analysis/lower_tertiary/economic_assumptions.yml`

---

*World Energy Data | Lower Tertiary Field Analysis*
