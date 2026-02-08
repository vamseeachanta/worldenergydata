# PHMSA Pipeline Safety Extracted Data

> Pipeline and Hazardous Materials Safety Administration incident data.

## Data Source

**PHMSA Data Portal:** https://www.phmsa.dot.gov/data-and-statistics/pipeline/data-and-statistics-overview

## Datasets

| File | Description |
|------|-------------|
| `gd1986tofeb2004.xlsx` | Gas distribution incidents 1986-2004 |
| `gdmar2004to2009.xlsx` | Gas distribution incidents 2004-2009 |
| `gd2010toPresent.xlsx` | Gas distribution incidents 2010-present |
| `gtgg1986to2001.xlsx` | Gas transmission/gathering 1986-2001 |
| `gtgg2002to2009.xlsx` | Gas transmission/gathering 2002-2009 |
| `gtggungs2010toPresent.xlsx` | Gas transmission/gathering/underground storage 2010-present |
| `hl1986to2001.xlsx` | Hazardous liquid incidents 1986-2001 |
| `hl2002to2009.xlsx` | Hazardous liquid incidents 2002-2009 |
| `hl2010toPresent.xlsx` | Hazardous liquid incidents 2010-present |
| `lng2011toPresent.xlsx` | LNG incidents 2011-present |
| `*FormFields.pdf` | Form field descriptions for each dataset |
| `EightCauseMappingMethods.xlsx` | 8-cause classification methodology |
| `SevenCauseMappingMethods.xlsx` | 7-cause classification methodology |
| `Index Data Sources.txt` | Master index of all datasets |

## Regeneration

1. Visit https://www.phmsa.dot.gov/data-and-statistics/pipeline/data-and-statistics-overview
2. Download each incident dataset for the relevant time periods
3. Extract to this directory

No automated acquirer script exists — PHMSA requires manual download.

## Expected Sizes

Individual XLSX files: 1-8 MB each. Total: ~30-50 MB.

## Gitignored

XLSX and PDF files in this directory are gitignored. Only `Index Data Sources.txt`
and this README are tracked.
