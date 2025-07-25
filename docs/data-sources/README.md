# Data Sources

Documentation for all energy data sources integrated into WorldEnergyData

**Target Users:** Energy Professional, Data Analyst

## Contents

### BSEE Data

**_Legacy:**
- [Data For Analysis Legacy](bsee\_legacy\data_for_analysis_legacy.md)

**Analysis:**
- [Intro](bsee\analysis\economics\intro.md)
- [Jstm Production](bsee\analysis\economics\JStM_production.md)
- [Lng](bsee\analysis\economics\lng.md)
- [NPV Calculation Methodology Comparison](bsee\analysis\economics\NPV\Methodology_Comparison.md)
- [Npv](bsee\analysis\economics\NPV\npv.md)
- [NPV Analysis Refactoring Summary](bsee\analysis\economics\NPV\NPV_REFACTORING_SUMMARY.md)
- [Power Markets](bsee\analysis\economics\power_markets.md)
- [Revenues](bsee\analysis\economics\revenues.md)
- [Field Layout](bsee\analysis\field\field_layout.md)
- [Julia Api12 Resolution](bsee\analysis\julia_api12_resolution.md)
- [Cummulative Production](bsee\analysis\production\cummulative_production.md)
- [Normalization For Laterals](bsee\analysis\production\normalization_for_laterals.md)
- [Rig Days By Milestone](bsee\analysis\rig_days\rig_days_by_milestone.md)
- [Rig Days By War](bsee\analysis\rig_days\rig_days_by_WAR.md)
- [Rig Days Summary](bsee\analysis\rig_days\rig_days_summary.md)
- [Survey](bsee\analysis\survey\survey.md)

**Data:**
- [BoreHole COdes](bsee\data\analysis_data.md)
- [Apm Data Rev1](bsee\data\apm_data_rev1.md)
- [Summary](bsee\data\clean_up\data_explaination.md)
- [Data For Analysis](bsee\data\clean_up\data_for_analysis.md)
- [Data Rev1](bsee\data\data_rev1.md)
- [Drilling Data Rev1](bsee\data\drilling_data_rev1.md)
- [ANCHOR Field Data Filtering Solution](bsee\data\field_anchor\ANCHOR_Field_Data_Filtering.md)
- [No Of Wells](bsee\data\field_jsm\no_of_wells.md)
- [Notes](bsee\data\production\notes.md)
- [Horizontal Reach](bsee\data\survey\horizontal_reach.md)
- [Well Count](bsee\data\well\well_count.md)
- [Well Activity Cd Description](bsee\data\WELL_ACTIVITY_CD\well_activity_cd_description.md)
- [Well Api Number](bsee\data\well_api_number.md)

### SODIR Data

- [Sodir](sodir\sodir.md)

### EQUIPMENT Data

**Anchor:**
- [Calculation](equipment\anchor\calculation.md)

**X_Tree:**
- [X Tree](equipment\x_tree\x_tree.md)

### ONSHORE Data

**Wyoming:**
- [Data](onshore\wyoming\data.md)

### General Documentation

- [Data Sources](index.md)

## Quick Start

For energy professionals getting started with data analysis:

1. **Choose your data source** - Start with [BSEE](bsee/) for US offshore data or [SODIR](sodir/) for Norwegian data
2. **Review the data structure** - Check the analysis guides for each source
3. **See examples** - Look at the analysis examples in each section
4. **Access the data** - Follow the data access instructions

For developers integrating data sources:
- Check the [development documentation](../development/) for API details
- Review data schemas and formats in each source directory

## Related Documentation

- [Analysis Guides](../analysis-guides/) - Learn analysis methodologies
- [Examples](../examples/) - See practical examples
- [Development](../development/) - Technical integration details
---

*Last updated: 2025-07-24*
*Generated automatically by WorldEnergyData documentation system*