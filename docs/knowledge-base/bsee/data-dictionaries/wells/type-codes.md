# Well Type Codes

> **Usage**: Classifies the purpose/type of well
> **Source**: BSEE Well/Borehole data
> **Total Codes**: 7 primary type codes

---

## Type Code Reference

| Code | Full Name | Description | Typical Count |
|------|-----------|-------------|---------------|
| C | Core Test | Well drilled to obtain core samples | ~500 |
| D | Development | Well in proven/developed area | ~35,000 |
| E | Exploratory | Wildcat well in unproven area | ~15,000 |
| N | New Well | New original wellbore | ~40,000 |
| O | Original Completion | Original completion event | ~45,000 |
| R | Recompletion | Recompletion of existing well | ~8,000 |
| S | Sidetrack | Sidetrack from existing wellbore | ~5,000 |

---

## Detailed Descriptions

### C - Core Test
- **Purpose**: Obtain formation core samples
- **Characteristics**:
  - Limited depth drilling
  - Focus on geological evaluation
  - May not produce hydrocarbons
- **Use Case**: Formation evaluation, reservoir characterization

### D - Development
- **Purpose**: Develop proven hydrocarbon reserves
- **Characteristics**:
  - Drilled in established producing area
  - Lower geological risk
  - Designed for production
- **Use Case**: Field development, production optimization

### E - Exploratory
- **Purpose**: Explore unproven geological prospects
- **Characteristics**:
  - Higher geological risk
  - May discover new reserves
  - Also called "wildcat" wells
- **Use Case**: New field discovery, prospect evaluation

### N - New Well
- **Purpose**: Drill new original wellbore
- **Characteristics**:
  - First penetration at surface location
  - Original drilling event
  - May be D or E classification
- **Use Case**: Tracking original drilling activity

### O - Original Completion
- **Purpose**: Initial completion of well
- **Characteristics**:
  - First completion event
  - Original zone perforations
  - Initial production setup
- **Use Case**: Completion tracking, production history

### R - Recompletion
- **Purpose**: Re-complete well in different zone
- **Characteristics**:
  - Change producing interval
  - May involve plug-back or plug-forward
  - Same wellbore, different completion
- **Use Case**: Zone optimization, production enhancement

### S - Sidetrack
- **Purpose**: Drill new wellbore from existing
- **Characteristics**:
  - Kicks off from original wellbore
  - May bypass obstruction or reach new target
  - Gets new API12 suffix
- **Use Case**: Reaching bypassed pay, avoiding problems

---

## Type vs Status

| Type | Status | Relationship |
|------|--------|--------------|
| E | APD | Exploratory permit applied |
| E | DRL | Exploratory well drilling |
| E | COM | Exploratory well completed |
| D | COM | Development well completed |
| S | ST | Sidetrack in progress |
| R | COM | Recompletion complete |

---

## Query Filters

### Exploratory Wells Only
```sql
WHERE type_code = 'E'
```

### Development Wells Only
```sql
WHERE type_code = 'D'
```

### Sidetrack Wells
```sql
WHERE type_code = 'S'
```

### New Original Wells
```sql
WHERE type_code = 'N'
  AND sidetrack_code = '00'  -- API12 suffix
```

---

## Statistics by Type

| Type | Approximate Count | Percentage |
|------|-------------------|------------|
| D | 35,000 | ~60% |
| E | 15,000 | ~26% |
| S | 5,000 | ~9% |
| R | 2,500 | ~4% |
| C | 500 | ~1% |

---

## Type Code Evolution

A well's type code typically does not change, but the wellbore may have multiple events:

```
Original Well (N, D) → Recompletion (R) → Same wellbore
Original Well (N, E) → Sidetrack (S) → New API12 suffix
```

---

## Related Documents

- [Status Codes](status-codes.md) - Well status reference
- [Borehole Fields](borehole-fields.md) - Complete field list
- [API Number Format](../common/api-number-format.md) - Sidetrack numbering
