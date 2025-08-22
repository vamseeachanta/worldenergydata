# Go-By Report Patterns Documentation

## Executive Summary

Analysis of go-by Excel reports from Jack, Julia, St. Malo, and Stones fields reveals a consistent reporting structure that will guide the comprehensive report system implementation.

## Common Report Structure

### Universal Pattern
All analyzed reports follow an identical structure:
- **Format**: Single Excel sheet per field
- **Layout**: Row-based categories with well-specific columns
- **Dimensions**: 14 data categories (rows) × Variable wells (columns)

### Field Report Statistics

| Field | Wells | Sheet Name | Operator |
|-------|-------|------------|----------|
| Jack | 11 | Jack_field_data | Chevron U.S.A. Inc. |
| Julia | 7 | Julia_field_data | Exxon Mobil Corporation |
| St. Malo | 16 | St Malo_field_data | Union Oil Company of California |
| Stones | 16 | Stones_field_data | Shell Offshore Inc. |

## Data Categories (Standard 14 Rows)

All reports contain these exact data categories in order:

1. **Company** - Operating company name
2. **Water Depth (ft)** - Field water depth in feet
3. **Well Purpose** - Purpose code (E = Exploration, D = Development)
4. **Rig(s)** - Drilling rig names used
5. **Side Tracks** - Number of sidetracks per well
6. **Spud Date** - Well spud date
7. **Wellbore Status** - Current wellbore status
8. **Last BSEE Date** - Last BSEE activity date
9. **Well Construction Days** - Days to construct well
10. **Well Completion Days** - Days to complete well
11. **Rig Last Date on Well** - Last date rig was on well
12. **Tree Height AML (ft)** - Tree height above mudline
13. **BSEE Field** - BSEE field designation
14. **API10** - 10-digit API well number

## Well Naming Conventions

### Jack Field Wells
- Format: PS### (e.g., PS001, PS002, PS003)
- Also includes numeric identifiers (1, 2) and alphanumeric (001a)

### Julia Field Wells
- Format: JU### or DC### (e.g., JU102, JU103, DC101)
- Numeric identifier: 1

### St. Malo Field Wells
- Format: PN### (e.g., PN001, PN002)
- Also includes numeric (1, 2, 3) and alphanumeric (001a, 001aa, 001aaa)

### Stones Field Wells
- Mixed format: Numeric (1-15) and alphanumeric (001a, 001aa)
- Includes PS### format similar to Jack

## Data Types and Characteristics

### Categorical Data
- Company (text)
- Well Purpose (single character code)
- Rig(s) (text, may contain multiple rig names)
- Wellbore Status (text status codes)
- BSEE Field (text field name)

### Numeric Data
- Water Depth (integer, feet)
- Side Tracks (integer count)
- Well Construction Days (integer)
- Well Completion Days (integer)
- Tree Height AML (numeric, feet)

### Date/Time Data
- Spud Date (date format)
- Last BSEE Date (date format)
- Rig Last Date on Well (date format)

### Identifier Data
- API10 (10-digit numeric string)

## Missing Data Patterns

Common patterns of missing data observed:
- Side tracks often null for wells without sidetracks
- Completion days may be null for uncompleted wells
- Tree height may be null for certain well types
- Some date fields null for wells in progress

## Hierarchical Organization

While the go-by reports show field-level summaries, the underlying hierarchy is:

```
Block
  └── Field
       └── Lease
            └── Well
```

Each Excel report represents a **Field** level aggregation with individual **Well** details.

## Key Insights for Report System

1. **Standardization**: All reports follow identical structure, enabling template-based generation
2. **Well-Centric**: Data organized around individual wells as primary entities
3. **Field Summary**: Each report provides field-level overview with well-specific details
4. **Operator Focus**: Single operator per field (though ownership may vary by well)
5. **Time Series**: Date fields enable temporal analysis and trending
6. **Construction Metrics**: Days to drill/complete are key performance indicators

## Required Data Fields for Comprehensive Reports

### Essential Fields (Must Have)
- Field Name
- Operator/Company
- Water Depth
- Well Name/Identifier
- API Number
- Spud Date
- Well Status
- Construction Days
- Completion Days

### Important Fields (Should Have)
- Well Purpose
- Rig Information
- Side Tracks
- Last Activity Date
- Tree Height
- BSEE Field Designation

### Enhanced Fields (Nice to Have)
- Production Data (not in go-by but available from BSEE)
- Economic Metrics (NPV, ROI)
- Cumulative Production
- Reserve Estimates

## Recommendations for Template Design

1. **Maintain Compatibility**: Keep the 14-row structure for field summary sheets
2. **Extend with Production**: Add production data tabs for comprehensive analysis
3. **Add Aggregation Levels**: Include lease and block level roll-ups
4. **Standardize Well Naming**: Create consistent well identifier format
5. **Include Visualizations**: Add charts for production trends and well performance
6. **Economic Integration**: Incorporate NPV and economic analysis sections

## Next Steps

1. Create Jinja2 templates matching this structure
2. Design data aggregation pipeline for multi-level reporting
3. Implement visualization components for field and well data
4. Build export system maintaining Excel format compatibility
5. Add production and economic data integration

---
*Generated: 2025-08-22*
*Source: Analysis of Jack, Julia, St. Malo, and Stones field Excel reports*