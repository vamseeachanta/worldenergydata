# EPA Toxics Release Inventory (TRI) Data

> WRK-067: EPA TRI data for oil & gas operations.

## Data Source

**EPA Envirofacts REST API**
- Base URL: `https://data.epa.gov/efservice/MV_TRI_BASIC_DOWNLOAD`
- Documentation: https://www.epa.gov/enviro/envirofacts-data-service-api

## Regeneration

```bash
uv run python -m worldenergydata.hse.acquirers.epa_tri_acquirer \
    --output-dir data/modules/hse/raw/epa_tri \
    --years 2020-2024 \
    --filter-industry \
    --force
```

### Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `--output-dir` | required | Output directory |
| `--years` | 2020-2024 | Year range (`"2020"`, `"2020-2024"`, `"2020,2022,2024"`) |
| `--filter-industry` | True | Filter for oil & gas SIC/NAICS codes |
| `--force` | False | Overwrite existing files |

## Expected Output

| File | Description | Size (approx) |
|------|-------------|---------------|
| `tri_basic_{year}_oil_gas.csv` | Annual TRI oil & gas records | 1-5 MB each |
| `tri_basic_{start}-{end}_oil_gas_combined.csv` | Combined multi-year | 10-25 MB |

## Oil & Gas Industry Codes

**SIC:** 1311, 1381, 1382, 1389, 2911, 4612, 4613, 4922-4925, 5171
**NAICS prefixes:** 211, 213, 324, 424, 486

## Dependencies

- pandas, requests

## Last Regenerated

2026-02-01 (acquirer script working as of this date)
