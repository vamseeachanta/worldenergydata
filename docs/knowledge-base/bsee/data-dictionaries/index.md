# BSEE Data Dictionaries

> **Purpose**: Field definitions for all BSEE datasets
> **Format**: Reference tables (Field | Type | Description | Example)
> **Last Updated**: 2026-01-18

---

## Quick Reference

| Category | Primary Dataset | Fields | Status |
|----------|-----------------|--------|--------|
| [Wells](wells/) | Borehole | 27 | Complete |
| [Production](production/) | Production Data | 11 | Complete |
| [Platforms](platforms/) | Platform Structures | 28 | Complete |
| [Pipelines](pipelines/) | Pipeline Location | 13 | Complete |
| [Leasing](leasing/) | Lease Area Block | 15 | Complete |
| [Company](company/) | Company Detail | 10 | Complete |
| [Common](common/) | Shared Codes | - | Complete |

---

## Wells

| Document | Description | Fields |
|----------|-------------|--------|
| [borehole-fields.md](wells/borehole-fields.md) | Borehole/well master data | 27 |
| [apd-fields.md](wells/apd-fields.md) | Application for Permit to Drill | 20+ |
| [api-lookup-fields.md](wells/api-lookup-fields.md) | API number lookup | 15 |
| [directional-survey.md](wells/directional-survey.md) | Survey data structure | 12 |
| [bhps-fields.md](wells/bhps-fields.md) | Bottomhole pressure surveys | 18 |
| [status-codes.md](wells/status-codes.md) | Well status codes | 11 |
| [type-codes.md](wells/type-codes.md) | Well type codes | 7 |
| [ewell-fields.md](wells/ewell-fields.md) | eWell submission data | Varies |

---

## Production

| Document | Description | Fields |
|----------|-------------|--------|
| [production-fields.md](production/production-fields.md) | Monthly production data | 11 |
| [ogor-reports.md](production/ogor-reports.md) | OGOR-A, B, C reports | 15+ |
| [fmp-fields.md](production/fmp-fields.md) | Facility Measurement Points | 12 |
| [planning-area.md](production/planning-area.md) | Production by planning area | 8 |
| [by-platform.md](production/by-platform.md) | Production by platform | 10 |

---

## Platforms

| Document | Description | Fields |
|----------|-------------|--------|
| [structure-fields.md](platforms/structure-fields.md) | Platform structure data | 28 |
| [deepwater-structures.md](platforms/deepwater-structures.md) | Deepwater (>1000ft) | 20 |
| [authority-codes.md](platforms/authority-codes.md) | Authority type codes | 10+ |
| [structure-types.md](platforms/structure-types.md) | Platform type codes | 15+ |
| [offshore-stats.md](platforms/offshore-stats.md) | Stats by water depth | 8 |

---

## Pipelines

| Document | Description | Fields |
|----------|-------------|--------|
| [location-fields.md](pipelines/location-fields.md) | Pipeline location data | 13 |
| [permit-fields.md](pipelines/permit-fields.md) | Pipeline permits | 18 |
| [row-descriptions.md](pipelines/row-descriptions.md) | Right-of-Way data | 10 |
| [product-codes.md](pipelines/product-codes.md) | Product type codes | 8 |

---

## Leasing

| Document | Description | Fields |
|----------|-------------|--------|
| [lease-fields.md](leasing/lease-fields.md) | Lease area/block data | 15 |
| [owner-fields.md](leasing/owner-fields.md) | Lease ownership | 12 |
| [assignment-fields.md](leasing/assignment-fields.md) | Ownership assignments | 10 |
| [decom-cost-fields.md](leasing/decom-cost-fields.md) | Decommissioning costs | 8 |
| [area-codes.md](leasing/area-codes.md) | Area/protraction codes | 50+ |

---

## Company

| Document | Description | Fields |
|----------|-------------|--------|
| [company-detail.md](company/company-detail.md) | Company information | 10 |
| [inc-fields.md](company/inc-fields.md) | Incidents of Non-Compliance | 15 |

---

## Common/Shared

| Document | Description |
|----------|-------------|
| [api-number-format.md](common/api-number-format.md) | API 10/12 digit explanation |
| [region-codes.md](common/region-codes.md) | GOA, Pacific, Alaska, Atlantic |
| [nad-projections.md](common/nad-projections.md) | NAD27, NAD83 coordinate systems |
| [district-codes.md](common/district-codes.md) | District identifiers |
| [company-codes.md](common/company-codes.md) | Operator identifiers |

---

## Reference Table Format

All data dictionary files use this standard format:

```markdown
## [Dataset Name] Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| field_name | VARCHAR(50) | Brief description | "G00123" |
| numeric_field | INT | What this measures | 5280 |
| date_field | DATE | When this occurred | 2025-01-15 |

### Code Lookups

| Code | Description |
|------|-------------|
| APD | Application for Permit to Drill |
| COM | Borehole Completed |
```

---

## Data Type Reference

| Type | Description | Example |
|------|-------------|---------|
| VARCHAR(n) | Variable-length string, max n chars | "WELL-001" |
| CHAR(n) | Fixed-length string, exactly n chars | "G " |
| INT | Integer number | 12345 |
| DECIMAL(p,s) | Decimal with p precision, s scale | 1234.56 |
| DATE | Date value | 2025-01-15 |
| DATETIME | Date and time | 2025-01-15 14:30:00 |
| BIT | Boolean (0/1) | 1 |

---

## Units Reference

| Measurement | Unit | Abbreviation |
|-------------|------|--------------|
| Oil volume | Barrels | BBL |
| Gas volume | Thousand cubic feet | MCF |
| Water depth | Feet or Meters | ft / m |
| Measured depth | Feet | ft |
| True vertical depth | Feet | ft |
| Coordinates (GOA) | NAD27 | Degrees |
| Coordinates (Other) | NAD83 | Degrees |
