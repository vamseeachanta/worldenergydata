# Lease Data Fields

> **Dataset**: Lease/Block Administration
> **Source**: https://www.data.bsee.gov/Leasing/LeaseOwner/Default.aspx
> **Scope**: Federal OCS lease identification and administration

---

## Lease Number Format

| Region | Format | Pattern | Example |
|--------|--------|---------|---------|
| Gulf of America | G + 5 digits | G###### | G05123 |
| Alaska | Y + 5 digits | Y###### | Y01234 |
| Pacific | P + 5 digits | P###### | P00456 |
| Atlantic | A + 5 digits | A###### | A00789 |

**Note**: Leading zeros are significant. G05123 ≠ G5123.

---

## Core Lease Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Lease Number | CHAR(6) | Unique lease identifier | G05123 |
| Area Code | CHAR(2) | Protraction area code | GC |
| Block Number | VARCHAR(6) | Block within area | 640 |
| Region | VARCHAR(20) | Geographic region | Gulf of America |
| Lease Status | CHAR(3) | Current lease status | PRD |
| Effective Date | DATE | Lease start date | 01/01/2015 |
| Expiration Date | DATE | Primary term end | 01/01/2025 |
| Lease Type | CHAR(1) | Lease category | O (Oil/Gas) |

---

## Lease Status Codes

| Code | Status | Description |
|------|--------|-------------|
| PRD | Producing | Active production; lease held by production |
| SOP | Suspended Operations | Operations temporarily suspended |
| SOO | Suspension of Operations | Formal suspension granted |
| SOP/SOO | Combined | Both suspensions in effect |
| DSO | Drilling Suspended | Drilling operations paused |
| EXPD | Expired | Primary term ended without production |
| PROD | Production | Alternate code for producing |
| UNIT | Unitized | Lease in unit agreement |
| REL | Relinquished | Voluntarily relinquished |
| TERM | Terminated | Lease terminated for cause |
| PEND | Pending | Lease award pending |

---

## Acreage Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Lease Acres | DECIMAL(10,2) | Total leased acreage | 5760.00 |
| Water Acres | DECIMAL(10,2) | Submerged acreage | 5760.00 |
| Unit Acres | DECIMAL(10,2) | Acres in unit (if unitized) | 23040.00 |
| Whole Block | CHAR(1) | Full block leased (Y/N) | Y |
| Aliquot Parts | VARCHAR(100) | Partial block description | NW/4, SE/4 |

**Standard Block Sizes**:
- Full block: 5,760 acres (3 mi × 3 mi)
- Half block: 2,880 acres
- Quarter block: 1,440 acres

---

## Term Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Primary Term (years) | INT | Initial lease term | 5, 8, or 10 |
| Secondary Term | VARCHAR(20) | Extended by production | Held by Production |
| Effective Date | DATE | Lease commencement | 01/01/2015 |
| Expiration Date | DATE | Primary term end | 01/01/2025 |
| Extension Date | DATE | Extended expiration | NULL (if producing) |
| Rental Due Date | DATE | Annual rental deadline | 01/01/2026 |

**Primary Terms by Water Depth**:
| Water Depth | Primary Term |
|-------------|--------------|
| < 400m | 5 years |
| 400-800m | 8 years |
| > 800m | 10 years |

---

## Royalty Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Royalty Rate | DECIMAL(5,4) | Base royalty percentage | 0.1875 (18.75%) |
| Royalty Suspension Vol | DECIMAL(12,2) | Volume exempt from royalty | 17,500,000 |
| Royalty Suspension Unit | VARCHAR(10) | Volume unit | BOE |
| Minimum Royalty | DECIMAL(10,2) | Annual minimum (if any) | 0.00 |

**Standard Royalty Rates**:
| Water Depth | Rate |
|-------------|------|
| < 200m | 18.75% |
| 200-400m | 16.67% |
| > 400m | 12.5% - 18.75% |

---

## Ownership Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Operator Name | VARCHAR(100) | Current operator | Shell Offshore Inc |
| Operator Number | VARCHAR(10) | BOEM company number | 00276 |
| Working Interest | DECIMAL(7,4) | Operator WI percentage | 0.7500 |
| Record Title Owner | VARCHAR(100) | Title holder | Shell Gulf of America Inc |
| Record Title Interest | DECIMAL(7,4) | Title interest percent | 1.0000 |

---

## Lease Type Codes

| Code | Type | Description |
|------|------|-------------|
| O | Oil and Gas | Standard hydrocarbon lease |
| S | Sulphur | Sulphur mining lease |
| G | Geothermal | Geothermal resources (rare OCS) |
| R | Renewable | Wind/renewable energy |
| M | Minerals | Other minerals |

---

## Sale Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Sale Number | VARCHAR(10) | Lease sale identifier | 261 |
| Sale Date | DATE | Date of sale | 08/21/2024 |
| High Bid | DECIMAL(15,2) | Winning bid amount | 15,234,567.00 |
| Bid Per Acre | DECIMAL(10,2) | Bid normalized by acreage | 2,644.89 |
| Second Bid | DECIMAL(15,2) | Second highest bid | 12,000,000.00 |

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| Region | Dropdown | Geographic region | Gulf of America |
| Area | Dropdown | Protraction area | GC (Green Canyon) |
| Block Number | Text | Block identifier | 640 |
| Lease Number | Text | Direct lease lookup | G05123 |
| Lease Status | Dropdown | Filter by status | PRD |
| Operator Name | Dropdown | Filter by company | Shell Offshore |
| Sale Number | Text | Filter by sale | 261 |

---

## Related Documents

- [Area Codes](area-codes.md) - Complete area/protraction reference
- [Block Numbering](block-numbering.md) - Block system explained
- [Region Codes](../common/region-codes.md) - Region definitions
- [Company Identifiers](../company/company-fields.md) - Operator codes
