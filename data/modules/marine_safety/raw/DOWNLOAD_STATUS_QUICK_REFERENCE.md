# Industrial Maritime Datasets - Quick Reference

**Last Updated:** 2025-10-06

## ✅ Ready for Analysis (Downloaded)

| Dataset | File(s) | Size | Records | Coverage |
|---------|---------|------|---------|----------|
| **NOAA Pipeline Areas** | PipelineArea.gpkg | 30 MB | GIS features | U.S. offshore pipelines |
| **EMSA Reports** | 4 PDFs (2020-2023) | 5.8 MB | ~12,000/yr | European casualties |
| **Oregon OSHA** | oregon_osha_inspections.csv | 2 KB | 37 years | State inspections |
| **ILO Report** | ILO_Seafarers_Report_2021.pdf | 37 KB | Report | Global seafarers |
| **Paris MOU** | Paris_MOU_Annual_Report_2024.pdf | 54 KB | ~18,000/yr | EU inspections |

**Total Downloaded:** ~36 MB usable data

## ⚠️ Requires Manual Download/Portal Access

| Dataset | Access Method | Expected Records |
|---------|---------------|------------------|
| **OSHA Federal Fatalities** | BLS SOII portal or state portals | 1,000+ fatalities |
| **PHMSA Pipeline Incidents** | PHMSA web portal query | 900+ offshore |
| **PHMSA Hazmat Water** | PHMSA portal, filter by mode | 1,000-3,000 |
| **IMCA DP Incidents** | IMCA membership or free summaries | 100-200/year |

## ℹ️ Requires Free Registration

| Dataset | Registration URL | Data Available |
|---------|-----------------|----------------|
| **IMO GISIS** | https://gisis.imo.org/ | Global casualties |
| **ILOStat** | https://ilostat.ilo.org/ | Seafarer deaths |
| **Paris MOU DB** | https://www.parismou.org/ | Vessel inspections |

## 📂 All Data Locations

Base: `/mnt/github/workspace-hub/worldenergydata/data/modules/marine_safety/raw/`

- `doe_pipelines/` - Offshore pipeline infrastructure
- `emsa_reports/` - European marine casualties
- `osha_maritime/` - Maritime worker safety
- `ilo_seafarer_deaths/` - Global seafarer safety
- `paris_mou/` - Port state control
- `imca_dp/` - DP vessel incidents
- `phmsa_hazmat/` - Hazmat transport incidents
- `imo_gisis/` - Global casualty database
- `lloyds_historical/` - Historical data

## 🎯 Next Actions Priority List

1. **Extract EMSA statistics** from PDFs → Create time series
2. **Register for IMO GISIS** → Download global casualty data
3. **Query PHMSA portal** → Get offshore pipeline incidents
4. **Register for ILOStat** → Get seafarer death statistics
5. **Import PipelineArea.gpkg** → GIS analysis
6. **Access Paris MOU database** → Vessel inspection records
