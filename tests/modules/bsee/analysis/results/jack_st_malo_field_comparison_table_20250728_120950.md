# Jack St. Malo Field Analysis Methods Comparison

*Generated on: 2025-07-28 12:09:50*

## Comparison Table

| Parameter | Excel Method | WorldEnergyData Method |
|-----------|-------------|----------------------|
| Number of months of production | 56 | 1 |
| Production Start Month | 2015-01 | 2014-08 |
| Production End Month | 2019-12 | 2020-03 |
| Total production in BBL | 273,208 | 15 |
| Average oil price in USD | $56.60 | $56.60 |
| Total revenue in USD | $15,463,587.36 | $435,411,726.73 |

## Analysis Summary

### Key Differences

- **Production Period**: WorldEnergyData covers -55 more months than Excel method
- **Total Production**: WorldEnergyData shows 273,193 lower production (-100.0%)
- **Oil Prices**: Average price differs by $+0.00 (+0.0%)
- **Revenue Impact**: Total revenue differs by $419,948,139.37 (+2715.7%)

### Data Sources

- **Excel Method**: NPV_JStM-WELL-Production-Data-thru-2019.xlsx
- **WorldEnergyData Method**: BSEE Production API

### Methodology Notes

- Excel method uses Row 22 (JSM Total AVGMoly) for production data
- Excel method uses Row 4 for BRENT oil prices
- WorldEnergyData method aggregates data from BSEE production API
- Time periods may differ due to different data availability and processing methods