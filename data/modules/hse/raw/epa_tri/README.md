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

## Import Summary (2026-02-10)

**Database**: `data/modules/hse/hse_incidents.db` (20 MB, `toxic_releases` table)

| Year | Records |
|------|---------|
| 2020 | 12,047 |
| 2021 | 11,616 |
| 2022 | 10,345 |
| 2023 | 4,446 |
| 2024 | 13,033 |
| **Total** | **51,487** |

16 cross-year duplicate records were detected and skipped. 0 errors.

**Top chemicals by total release volume (lbs)**:
1. Hydrogen sulfide: 192.6M
2. Nitrate compounds: 133.6M
3. Ammonia: 30.5M
4. Hydrogen cyanide: 19.3M
5. Sulfuric acid aerosols: 18.0M
6. n-Hexane: 17.0M
7. Toluene: 16.4M
8. Methanol: 12.9M
9. Hydrochloric acid aerosols: 12.0M
10. Xylene (mixed isomers): 11.5M

**Top states**: TX (9,605), CA (3,373), LA (3,357), OH (2,552), PA (1,973)

**NAICS codes present**: 424710, 324110, 424690, 324121, 211130, 324199, 324191, 324122, 424720, 213113

## Last Regenerated

2026-02-01 (acquirer script working as of this date)
