# Drilling Completion Days Analysis - Output Documentation

## Test Execution Summary

**Date:** 2025-08-02  
**Time:** 11:08:30  
**Status:** ✅ Successfully Completed

## Output File Details

- **File Name:** drilling_and_completion_days_by_api_validation.xlsx
- **File Path:** C:\Users\Sk Samdan\Desktop\github\worldenergydata\tests\modules\bsee\analysis\2025-08-02-drilling-completion-output-validation\results\
- **File Size:** 14,358 bytes (14.0 KB)
- **Creation Time:** 2025-08-02 11:08:31

## Data Summary

- **Total Rows:** 122 wells
- **Total Columns:** 12

### Column Information

1. **LEASE_NAME** - Name of the lease
2. **SURF_LEASE_NUM** - Surface lease number
3. **WATER_DEPTH** - Water depth at location
4. **API_WELL_NUMBER** - API well identification number
5. **WELL_NAME** - Name of the well
6. **WELL_SPUD_DATE** - Date when drilling began
7. **TOTAL_DEPTH_DATE** - Date when total depth was reached
8. **DRILLING_DAYS** - Number of days spent drilling
9. **COMPLETION_DAYS** - Number of days spent on completion
10. **MAX_BH_TOTAL_MD** - Maximum borehole total measured depth
11. **MAX_WELL_BORE_TVD** - Maximum well bore true vertical depth
12. **MAX_DRILL_FLUID_WGT** - Maximum drilling fluid weight

## Processing Statistics

- **Input WAR Records:** 358,820 total records
- **Filtered WAR Records:** 2,497 records (matching lease criteria)
- **Borehole Records:** 54,608 total records
- **Property Records:** 356,392 total records
- **Final Output:** 122 wells with complete drilling and completion data

## Lease Coverage

The analysis covered 16 leases from the input lease file, with successful data extraction for wells across multiple fields including:
- Anchor
- North Platte
- And other fields as specified in the lease input file

## Next Steps

This output file is ready for comparison with the original reference output to validate the accuracy of the worldenergydata implementation.