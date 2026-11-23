# DOE/PHMSA Offshore Pipeline Data

**Downloaded:** 2025-10-06
**Source:** NOAA Marine Cadastre / PHMSA

## Files

### PipelineArea.gpkg (30 MB)
- **Format:** GeoPackage (spatial database)
- **Source:** https://marinecadastre.gov/downloads/data/mc/PipelineArea.zip
- **Coverage:** U.S. offshore pipeline infrastructure areas
- **Updated:** August 29, 2022
- **Description:** Geographic boundaries of offshore pipeline areas in U.S. waters
- **Use:** Spatial analysis of offshore pipeline locations

### bsee_accident_database_page.html (28 KB)
- **Source:** https://www.data.bsee.gov/Main/Accident.aspx
- **Purpose:** Reference page for BSEE accident database portal
- **Note:** Requires web portal access for full incident data

## Data Quality Notes

- ✅ **PipelineArea.gpkg:** Complete spatial dataset, ready for GIS analysis
- ⚠️ **PHMSA Direct Downloads:** Not accessible (404 errors on direct file URLs)
- ℹ️ **Alternative:** PHMSA data requires portal access at www.phmsa.dot.gov

## Next Steps

1. Import PipelineArea.gpkg into QGIS/PostGIS for spatial analysis
2. Cross-reference with BSEE offshore incident data
3. Access PHMSA incident database via web portal for detailed incident records
4. Filter offshore-specific incidents from broader pipeline database

## Related Datasets

- See `/bsee_offshore/` for offshore installation incident data
- See `/noaa_spills/` for marine pollution incidents
- Marine pipeline corridors data available at Marine Cadastre
