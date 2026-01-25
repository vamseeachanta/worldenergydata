# APD (Application for Permit to Drill) Fields

> **Dataset**: eWell APD
> **Source**: https://www.data.bsee.gov/Well/APD/Default.aspx
> **Raw Data**: https://www.data.bsee.gov/Well/Files/APDRawData.zip
> **Update Frequency**: Daily
> **Purpose**: Drilling permit applications and approvals

---

## APD Number Format

| Component | Length | Description | Example |
|-----------|--------|-------------|---------|
| Region Code | 1 | G=Gulf, P=Pacific, A=Alaska | G |
| Year | 2 | Year submitted (last 2 digits) | 24 |
| Sequence | 5 | Sequential number within year | 00123 |
| **Full Format** | 8 | Combined APD number | G2400123 |

---

## Application Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| APD Number | VARCHAR(8) | Unique permit identifier | G2400123 |
| API Well Number | VARCHAR(12) | Well API number (assigned on approval) | 177093400100 |
| Lease Number | VARCHAR(10) | Associated lease | G00456 |
| Area Code | CHAR(2) | Protraction area code | AC |
| Block Number | VARCHAR(6) | Block within area | 857 |
| Region | VARCHAR(20) | Geographic region | Gulf of America |
| Well Name | VARCHAR(50) | Proposed well name | THUNDER HAWK A-1 |

---

## Application Type Codes

| Code | Description | Notes |
|------|-------------|-------|
| N | New Well | Original wellbore at new surface location |
| S | Sidetrack | Sidetrack from existing wellbore |
| B | Bypass | Bypass existing wellbore obstruction |
| R | Re-drill | Re-drill at existing location |
| D | Deepen | Deepen existing well |
| P | Plugback | Plug back to shallower zone |

---

## APD Status Codes

| Code | Description | Notes |
|------|-------------|-------|
| PND | Pending | Application under review |
| APV | Approved | Permit approved, ready to drill |
| APD | APD Received | Application received |
| DNS | Denied | Application denied |
| CNL | Cancelled | Application cancelled by operator |
| EXP | Expired | Permit expired (not used within timeframe) |
| SUS | Suspended | Review suspended pending information |
| RVW | Under Review | Technical review in progress |

---

## Approval/Denial Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Status Code | CHAR(3) | Current APD status | APV |
| Status Date | DATE | Date status changed | 01/15/2024 |
| Approval Date | DATE | Date permit approved | 01/20/2024 |
| Denial Date | DATE | Date permit denied (if applicable) | NULL |
| Denial Reason | VARCHAR(500) | Reason for denial | Environmental concern |
| Expiration Date | DATE | Permit expiration date | 01/20/2026 |
| Extension Date | DATE | Extended expiration (if granted) | 01/20/2027 |

---

## Proposed Well Data

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Proposed TD | DECIMAL(10,2) | Proposed total depth (ft) | 25000.00 |
| Proposed TVD | DECIMAL(10,2) | Proposed true vertical depth (ft) | 18500.00 |
| Water Depth | DECIMAL(8,2) | Water depth at location (ft) | 4500.00 |
| Surface Latitude | DECIMAL(10,6) | Proposed surface latitude | 27.123456 |
| Surface Longitude | DECIMAL(11,6) | Proposed surface longitude | -89.654321 |
| Bottom Latitude | DECIMAL(10,6) | Proposed bottomhole latitude | 27.125000 |
| Bottom Longitude | DECIMAL(11,6) | Proposed bottomhole longitude | -89.650000 |
| Well Type | CHAR(1) | D=Development, E=Exploratory | D |

---

## Actual vs Proposed Comparison

| Proposed Field | Actual Field | Notes |
|----------------|--------------|-------|
| Proposed TD | BH Total MD | May differ due to drilling conditions |
| Proposed TVD | True Vertical Depth | Typically close to proposed |
| Proposed Location | Surface Location | Minor adjustments allowed |
| Proposed BH Location | Bottom Location | May change due to geological targets |

---

## Date Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Submit Date | DATE | Date application submitted | 01/05/2024 |
| Received Date | DATE | Date received by BSEE | 01/06/2024 |
| Review Start Date | DATE | Technical review began | 01/08/2024 |
| Approval Date | DATE | Permit approved | 01/20/2024 |
| Spud Date | DATE | Actual spud date (after drilling) | 02/15/2024 |
| Expiration Date | DATE | Permit expires (2 years typical) | 01/20/2026 |

---

## Operator Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Company Name | VARCHAR(100) | Operator name | Shell Offshore Inc. |
| Company Number | VARCHAR(10) | BSEE company code | 00689 |
| Contact Name | VARCHAR(100) | Primary contact | John Smith |
| Contact Phone | VARCHAR(20) | Contact phone number | 713-555-0100 |
| Contact Email | VARCHAR(100) | Contact email | jsmith@shell.com |

---

## Rig Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Rig Name | VARCHAR(50) | Drilling rig name | DEEPWATER HORIZON |
| Rig Type | VARCHAR(20) | Rig classification | Semi-submersible |
| Rig Owner | VARCHAR(100) | Rig owning company | Transocean |
| Contractor | VARCHAR(100) | Drilling contractor | Transocean Ltd |

---

## Environmental Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| NEPA Document | VARCHAR(50) | Environmental document type | EA |
| NEPA Status | VARCHAR(20) | Environmental review status | Complete |
| Biological Opinion | BIT | BiOp required (1=Yes) | 1 |
| Archaeological Survey | BIT | Survey completed (1=Yes) | 1 |
| Shallow Hazards | BIT | Shallow hazards survey done | 1 |

---

## Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| APD Number | Text | Specific APD number | G2400123 |
| Region | Dropdown | Geographic region | Gulf of America |
| Area | Dropdown | Protraction area | AC |
| Block | Text | Block number | 857 |
| Status | Dropdown | APD status | APV |
| Submit Date Range | Date Range | Date submitted | 01/01/2024 - 12/31/2024 |
| Company Name | Dropdown | Operator | Shell Offshore |

---

## APD to Borehole Linkage

| APD Field | Borehole Field | Notes |
|-----------|----------------|-------|
| APD Number | - | APD number not in borehole data |
| API Well Number | API Well Number | Assigned on approval |
| Lease Number | Surface Lease Number | Same lease |
| Well Name | Well Name | May have minor variations |
| Status | Status Code | APD status differs from well status |

---

## Sample Query URL

```
https://www.data.bsee.gov/Well/APD/Default.aspx
  ?Region=Gulf%20of%20America
  &StatusCode=APV
  &SubmitDateFrom=01/01/2024
  &SubmitDateTo=12/31/2024
```

---

## Related Documents

- [Borehole Fields](borehole-fields.md) - Well master data
- [Status Codes](status-codes.md) - Well status reference
- [Type Codes](type-codes.md) - Well type classification
- [API Number Format](../common/api-number-format.md) - API numbering system
- [WAR Fields](war-fields.md) - Well Activity Reports
