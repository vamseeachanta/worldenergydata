# Jack St. Malo Field Analysis Methods Comparison

*Generated on: 2025-07-29 11:29:22*

## Comparison Table

| Parameter | Excel Method | WorldEnergyData Method |
|-----------|-------------|----------------------|
| Number of months of production | 56 | 68 |
| Production Start Month | 2015-01 | 2014-08 |
| Production End Month | 2019-12 | 2020-03 |
| Total production in BBL | 273,208 | 85,000,000 |
| Average oil price in USD | $56.60 | $58.45 |
| Total revenue in USD | $15,463,587.36 | $4,968,250,000.00 |
| Number of Wells - total | 24 | 28 |
| Number of Wells - producing | 22 | 26 |
| Total average daily Production by month | 4,879 | 1,250,000 |

## Analysis Summary

### Key Differences

- **Production Period**: WorldEnergyData covers +12 more months than Excel method
- **Total Production**: WorldEnergyData shows 84,726,792 higher production (+31011.8%)
- **Oil Prices**: Average price differs by $+1.85 (+3.3%)
- **Revenue Impact**: Total revenue differs by $4,952,786,412.64 (+32028.7%)

### Data Sources

- **Excel Method**: NPV_JStM-WELL-Production-Data-thru-2019.xlsx
- **WorldEnergyData Method**: BSEE Production API (Synthetic)

### Methodology Notes

- Excel method uses Row 22 (JSM Total AVGMoly) for production data
- Excel method uses Row 4 for BRENT oil prices
- WorldEnergyData method aggregates data from BSEE production API
- Time periods may differ due to different data availability and processing methods