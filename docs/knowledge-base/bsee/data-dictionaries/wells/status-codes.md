# Well Status Codes

> **Usage**: Indicates current regulatory/operational status of a well
> **Source**: BSEE Well/Borehole data
> **Total Codes**: 11 primary status codes

---

## Status Code Reference

| Code | Full Name | Description | Active? |
|------|-----------|-------------|---------|
| APD | Application for Permit to Drill | Permit submitted, awaiting approval | No |
| AST | Approved Sidetrack | Sidetrack operation approved | Active |
| CNL | Cancelled | Permit or well cancelled | Inactive |
| COM | Borehole Completed | Well completed, may be producing or shut-in | Active |
| CT | Core Test | Core test well for formation evaluation | Active |
| DRL | Drilling | Currently drilling | Active |
| DSI | Drilling Suspended - Rig on Location | Drilling paused, rig still on site | Active |
| PA | Permanently Abandoned | Well plugged and abandoned, no future use | Inactive |
| ST | Sidetrack | Sidetrack operation in progress | Active |
| TA | Temporarily Abandoned | Temporarily plugged, may be re-entered | Inactive |
| VCW | Verified Completion of Work | Work verified complete by BSEE | Active |

---

## Status Lifecycle

```
   APD ──────► DRL ──────► COM
   (Permit)   (Drilling)  (Completed)
     │           │           │
     ▼           ▼           ▼
   CNL         DSI          PA
 (Cancel)   (Suspend)   (Permanent)
                           │
                           ▼
                          TA
                    (Temporary)
```

### Typical Progression

1. **APD** → Permit application submitted
2. **DRL** → Drilling commenced
3. **DSI** → (Optional) Drilling suspended
4. **COM** → Well completed
5. **TA** → (Optional) Temporarily abandoned
6. **PA** → Permanently abandoned

---

## Detailed Descriptions

### APD - Application for Permit to Drill
- Permit application submitted to BSEE
- Well not yet spudded
- May be approved, denied, or cancelled

### AST - Approved Sidetrack
- Sidetrack from existing wellbore approved
- Original wellbore remains (may be plugged back)

### CNL - Cancelled
- Permit or well cancelled
- No drilling activity occurred (if cancelled before spud)
- May occur at any stage

### COM - Borehole Completed
- Drilling complete, well finished
- May be:
  - Producing oil/gas
  - Shut-in (not currently producing)
  - Injection well
  - Monitoring well

### CT - Core Test
- Well drilled primarily for core samples
- Formation evaluation purpose
- May be converted to production

### DRL - Drilling
- Currently drilling
- Rig on location, operations ongoing

### DSI - Drilling Suspended - Rig on Location
- Drilling temporarily halted
- Rig remains on location
- Expect operations to resume

### PA - Permanently Abandoned
- Well plugged with cement
- Casing cut below mudline (offshore)
- No future use possible
- Site cleared (or pending clearance)

### ST - Sidetrack
- Sidetrack drilling in progress
- Drilling new hole from existing wellbore

### TA - Temporarily Abandoned
- Well temporarily plugged
- May be re-entered later
- Surface equipment may remain
- Periodic inspection required

### VCW - Verified Completion of Work
- BSEE verified work complete
- Applied after certain operations
- Regulatory milestone

---

## Status Counts (Approximate)

Based on typical OCS inventory:

| Status | Approximate Count | Percentage |
|--------|-------------------|------------|
| PA | 35,000+ | ~60% |
| COM | 15,000+ | ~26% |
| TA | 4,000+ | ~7% |
| DRL | 100+ | <1% |
| APD | 500+ | ~1% |
| Other | 2,000+ | ~3% |

---

## Query Filters

### Active Wells Only
```sql
WHERE status_code NOT IN ('PA', 'CNL', 'TA')
```

### Producing Wells
```sql
WHERE status_code = 'COM'
  AND EXISTS (SELECT 1 FROM production WHERE ...)
```

### Abandoned Wells
```sql
WHERE status_code IN ('PA', 'TA')
```

### Currently Drilling
```sql
WHERE status_code IN ('DRL', 'DSI', 'ST')
```

---

## Status Date

The `Status Date` field indicates when the current status was assigned:
- For **PA**: Date of permanent abandonment
- For **COM**: Date of completion
- For **DRL**: Date drilling commenced (spud date may differ)

---

## Related Documents

- [Borehole Fields](borehole-fields.md) - Complete borehole data dictionary
- [Type Codes](type-codes.md) - Well type classification
- [APD Fields](apd-fields.md) - Permit application data
