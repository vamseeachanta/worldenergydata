# API Well Number Format

> **Standard**: American Petroleum Institute (API) Well Number
> **Versions**: API10 (10-digit), API12 (12-digit), API14 (14-digit)
> **Usage**: Unique well identification across US oil & gas industry

---

## Quick Reference

| Format | Digits | Components | Example |
|--------|--------|------------|---------|
| API10 | 10 | State + County + Well | 4228325000 |
| API12 | 12 | API10 + Sidetrack | 422832500000 |
| API14 | 14 | API12 + Completion | 42283250000000 |

---

## API10 Format (10 Digits)

```
XX-YYY-ZZZZZ
│  │   └── Well Sequence (5 digits)
│  └────── County Code (3 digits)
└───────── State Code (2 digits)
```

### Components

| Position | Length | Description | Example |
|----------|--------|-------------|---------|
| 1-2 | 2 | State Code | 17 (Louisiana) |
| 3-5 | 3 | County/Parish Code | 709 (Plaquemines Parish) |
| 6-10 | 5 | Well Sequence Number | 34001 |

### OCS State Codes

| Code | Region | Notes |
|------|--------|-------|
| 17 | Gulf of America - Federal | All federal OCS wells |
| 55 | Alaska - Federal | Alaska OCS |
| 66 | Pacific - Federal | Pacific OCS |
| 77 | Atlantic - Federal | Atlantic OCS |

**Note**: OCS wells use pseudo-state codes, not actual state codes.

---

## API12 Format (12 Digits)

```
XX-YYY-ZZZZZ-AA
│  │   │      └── Sidetrack Code (2 digits)
│  │   └────────── Well Sequence (5 digits)
│  └────────────── County Code (3 digits)
└─────────────────── State Code (2 digits)
```

### Sidetrack Code

| Code | Description |
|------|-------------|
| 00 | Original hole |
| 01 | First sidetrack |
| 02 | Second sidetrack |
| ... | ... |
| S1, S2 | Alternative notation |

---

## API14 Format (14 Digits)

```
XX-YYY-ZZZZZ-AA-BB
│  │   │      │  └── Completion Event (2 digits)
│  │   │      └───── Sidetrack Code (2 digits)
│  │   └──────────── Well Sequence (5 digits)
│  └──────────────── County Code (3 digits)
└────────────────────── State Code (2 digits)
```

### Completion Event Code

| Code | Description |
|------|-------------|
| 00 | Original completion |
| 01 | First recompletion |
| 02 | Second recompletion |
| ... | ... |

---

## BSEE-Specific Usage

### Common Patterns in OCS Data

| API Format | Usage | Example |
|------------|-------|---------|
| 1770934001 | API10 (no separators) | Well in GOA |
| 177093400100 | API12 (no separators) | Well + sidetrack |
| 17-709-34001 | API10 (with dashes) | Formatted display |
| 17-709-34001-00 | API12 (with dashes) | Formatted display |

### County Codes for OCS

For federal OCS wells, the "county" code identifies the protraction/area:

| Code | Area | Region |
|------|------|--------|
| 709 | Various GOA areas | Gulf of America |
| ... | ... | ... |

**Note**: OCS "county" codes don't correspond to actual counties.

---

## Parsing Examples

### Python
```python
def parse_api(api_number: str) -> dict:
    """Parse API number into components."""
    # Remove any separators
    api = api_number.replace('-', '').replace(' ', '')

    result = {
        'state': api[0:2],
        'county': api[2:5],
        'well': api[5:10],
    }

    if len(api) >= 12:
        result['sidetrack'] = api[10:12]
    if len(api) >= 14:
        result['completion'] = api[12:14]

    return result

# Example
parse_api('177093400100')
# {'state': '17', 'county': '709', 'well': '34001', 'sidetrack': '00'}
```

### SQL
```sql
-- Extract API10 from API12
SELECT SUBSTR(api_number, 1, 10) as api10
FROM wells;

-- Extract sidetrack
SELECT SUBSTR(api_number, 11, 2) as sidetrack
FROM wells
WHERE LENGTH(api_number) >= 12;
```

---

## Validation Rules

| Rule | Description |
|------|-------------|
| Length | 10, 12, or 14 digits |
| Characters | Numeric only (after removing separators) |
| State Code | Valid state/region code |
| Leading Zeros | Must be preserved |

### Validation Regex
```regex
^(\d{2})-?(\d{3})-?(\d{5})(-?\d{2})?(-?\d{2})?$
```

---

## Common Issues

1. **Leading Zeros Lost**
   - Store as VARCHAR, not INTEGER
   - Example: "0100100001" becomes "100100001" if stored as number

2. **Separator Inconsistency**
   - May appear with or without dashes
   - Normalize before comparison

3. **Length Variations**
   - Some sources provide API10, others API12/14
   - Pad with "00" for missing sidetrack

4. **Regional Differences**
   - State codes vary by region
   - OCS uses pseudo-state codes

---

## Cross-Reference

| BSEE Field | API Component |
|------------|---------------|
| API Well Number | Full API (10, 12, or 14) |
| Well Sequence | Digits 6-10 |
| Sidetrack | Digits 11-12 |
| Completion | Digits 13-14 |

---

## Related Documents

- [Borehole Fields](../wells/borehole-fields.md) - API in borehole data
- [APD Fields](../wells/apd-fields.md) - API in permit data
- [Region Codes](region-codes.md) - Regional identifiers
