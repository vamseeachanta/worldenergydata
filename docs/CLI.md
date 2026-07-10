# WorldEnergyData CLI Reference

Complete command-line interface documentation for WorldEnergyData.

## Installation

```bash
# Using UV (recommended)
uv sync
uv run worldenergydata --help

# Using pip
pip install -e .
worldenergydata --help
```

## Global Commands

### `worldenergydata`

Main entry point for all commands.

```bash
worldenergydata --help              # Show help
worldenergydata --verbose           # Enable verbose output
worldenergydata version             # Show version
worldenergydata info                # List available modules
worldenergydata status              # Show system status
```

---

## BSEE Module

BSEE (Bureau of Safety and Environmental Enforcement) data operations.

```bash
worldenergydata bsee --help
```

### `bsee analyze`

Analyze BSEE well and production data.

```bash
# Options
--block, -b TEXT      Block number (e.g., 759)
--field, -f TEXT      Field name (e.g., "Jack", "Thunder Horse")
--lease, -l TEXT      Lease number (e.g., OCS-G-12345)
--api, -a TEXT        API number (10 or 12 digit)
--output, -o PATH     Output directory [default: ./reports]
--verbose, -v         Enable verbose output

# Examples
worldenergydata bsee analyze --block 759
worldenergydata bsee analyze --field "Jack" --verbose
worldenergydata bsee analyze --api 608114001200
worldenergydata bsee analyze --field "Thunder Horse" --output ./analysis
```

### `bsee report`

Generate comprehensive BSEE reports.

```bash
# Options
--type, -t [block|field|lease|well]   Report type [default: field]
--id, -i TEXT                         Entity identifier (required)
--format, -f [excel|json|html|pdf]    Output format [default: excel]
--output, -o PATH                     Output directory [default: ./reports]
--oil-price FLOAT                     Oil price per barrel [default: 75.00]
--gas-price FLOAT                     Gas price per MCF [default: 3.50]
--discount-rate, -r FLOAT             Discount rate [default: 0.10]
--verbose, -v                         Enable verbose output

# Examples
worldenergydata bsee report --type block --id 759 --format excel
worldenergydata bsee report --type field --id "Jack" --oil-price 80
worldenergydata bsee report --type lease --id OCS-G-12345 --format pdf
worldenergydata bsee report --type well --id 608114001200 --discount-rate 0.08
```

### `bsee data`

Retrieve BSEE data for a specific entity.

```bash
# Options
--api, -a TEXT        API number (10 or 12 digit)
--block, -b TEXT      Block number
--lease, -l TEXT      Lease number
--type, -t [well|production|block|lease|all]  Data type [default: well]
--output, -o PATH     Output file path (optional)
--verbose, -v         Enable verbose output

# Examples
worldenergydata bsee data --api 608114001200
worldenergydata bsee data --block 759 --type production
worldenergydata bsee data --lease OCS-G-12345 --output data.json
```

### `bsee refresh`

Refresh BSEE data from source.

```bash
# Options
--type, -t [well|production|block|lease|all]  Data type [default: all]
--force, -f           Force refresh even if data is current
--verbose, -v         Enable verbose output

# Examples
worldenergydata bsee refresh --type well
worldenergydata bsee refresh --type production --force
worldenergydata bsee refresh --type all --verbose
```

### `bsee stats`

Display BSEE data statistics.

```bash
# Options
--verbose, -v         Show detailed statistics

# Examples
worldenergydata bsee stats
worldenergydata bsee stats --verbose
```

---

## Marine Safety Module

Marine safety incident data management.

```bash
worldenergydata marine-safety --help
```

### `marine-safety scrape`

Scrape incident data from various sources.

#### `marine-safety scrape uscg`

Scrape USCG MISLE database.

```bash
# Options
--start-year INTEGER      Starting year
--end-year INTEGER        Ending year
--output, -o PATH         Output file path
--checkpoint-dir PATH     Directory for checkpoint files
--no-resume               Do not resume from checkpoint
--verbose, -v             Enable verbose output

# Examples
worldenergydata marine-safety scrape uscg --start-year 2020 --end-year 2023
worldenergydata marine-safety scrape uscg --output uscg_data.json --verbose
worldenergydata marine-safety scrape uscg --checkpoint-dir ./checkpoints
```

#### `marine-safety scrape ntsb`

Scrape NTSB marine accident database.

```bash
# Options
--start-year INTEGER      Starting year
--end-year INTEGER        Ending year
--output, -o PATH         Output file path
--verbose, -v             Enable verbose output

# Examples
worldenergydata marine-safety scrape ntsb --start-year 2020 --end-year 2023
```

#### `marine-safety scrape maib`

Scrape UK MAIB (Marine Accident Investigation Branch).

```bash
# Options
--start-year INTEGER      Starting year
--end-year INTEGER        Ending year
--output, -o PATH         Output file path
--verbose, -v             Enable verbose output

# Examples
worldenergydata marine-safety scrape maib --start-year 2020
```

### `marine-safety db`

Database management operations.

#### `marine-safety db init`

Initialize database schema.

```bash
# Options
--force, -f               Force recreation of existing database
--db-url TEXT             Database connection URL
--dev-mode                Use SQLite schema for development
--dry-run                 Print SQL without executing
--verbose, -v             Enable verbose output

# Examples
worldenergydata marine-safety db init
worldenergydata marine-safety db init --force
worldenergydata marine-safety db init --db-url postgresql://user:pass@localhost/marine
worldenergydata marine-safety db init --dev-mode --db-url sqlite:///marine_safety.db
```

#### `marine-safety db migrate`

Run database migrations.

```bash
# Options
--target-version INTEGER  Target migration version
--dry-run                 Show migration plan without executing

# Examples
worldenergydata marine-safety db migrate
worldenergydata marine-safety db migrate --target-version 5
worldenergydata marine-safety db migrate --dry-run
```

### `marine-safety stats`

Display incident statistics.

```bash
# Options
--source, -s [all|uscg|ntsb|bsee|maib|tsb]  Data source [default: all]
--verbose, -v             Show detailed statistics

# Examples
worldenergydata marine-safety stats
worldenergydata marine-safety stats --source uscg
worldenergydata marine-safety stats --verbose
```

### `marine-safety export`

Export incident data.

```bash
# Arguments
FORMAT                    Export format (csv, json, excel, parquet)

# Options
--output, -o PATH         Output file path (required)
--source, -s [all|uscg|ntsb|bsee|maib|tsb]  Data source [default: all]
--start-date TEXT         Start date filter (YYYY-MM-DD)
--end-date TEXT           End date filter (YYYY-MM-DD)
--limit INTEGER           Limit number of records
--verbose, -v             Enable verbose output

# Examples
worldenergydata marine-safety export csv --output incidents.csv
worldenergydata marine-safety export json --output incidents.json --source uscg
worldenergydata marine-safety export excel --output report.xlsx --start-date 2020-01-01
worldenergydata marine-safety export parquet --output data.parquet --limit 1000
```

### `marine-safety analyze`

Analyze incident patterns and trends.

```bash
# Options
--type, -t TEXT           Incident type to analyze
--region, -r TEXT         Region to analyze (e.g., "GOM", "Atlantic")
--output, -o PATH         Output directory

# Examples
worldenergydata marine-safety analyze --type collision
worldenergydata marine-safety analyze --region GOM --output ./analysis
```

### `marine-safety info`

Display module information.

```bash
worldenergydata marine-safety info
```

---

## FDAS Module

Field Development Analysis System.

```bash
worldenergydata fdas --help
```

### `fdas calculate-npv`

Calculate Net Present Value.

```bash
# Options
--cashflows, -c TEXT      Cashflows as JSON array (required)
--discount-rate, -r FLOAT Annual discount rate [default: 0.10]
--period, -p [monthly|annual]  Cashflow period [default: monthly]

# Examples
worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300,400,500]"
worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]" --discount-rate 0.08
worldenergydata fdas calculate-npv --cashflows "[-5000,1000,1500,2000]" --period annual
```

### `fdas calculate-mirr`

Calculate Modified Internal Rate of Return.

```bash
# Options
--cashflows, -c TEXT          Cashflows as JSON array (required)
--discount-rate, -r FLOAT     Annual discount rate [default: 0.10]
--reinvestment-rate FLOAT     Annual reinvestment rate

# Examples
worldenergydata fdas calculate-mirr --cashflows "[-1000,100,200,300,400,500]"
worldenergydata fdas calculate-mirr --cashflows "[-5000,1000,1500,2000]" --discount-rate 0.12
```

### `fdas calculate-irr`

Calculate Internal Rate of Return.

```bash
# Options
--cashflows, -c TEXT      Cashflows as JSON array (required)
--period, -p [monthly|annual]  Cashflow period [default: monthly]

# Examples
worldenergydata fdas calculate-irr --cashflows "[-1000,100,200,300,400,500]"
worldenergydata fdas calculate-irr --cashflows "[-5000,2000,2000,2000]" --period annual
```

### `fdas calculate-all`

Calculate all financial metrics.

```bash
# Options
--cashflows, -c TEXT      Cashflows as JSON array (required)
--discount-rate, -r FLOAT Annual discount rate [default: 0.10]
--period, -p [monthly|annual]  Cashflow period [default: monthly]

# Examples
worldenergydata fdas calculate-all --cashflows "[-1000,100,200,300,400,500]"
worldenergydata fdas calculate-all --cashflows "[-5000,1000,1500,2000]" --discount-rate 0.12
```

### `fdas analyze`

Perform comprehensive field development analysis.

```bash
# Options
--field, -f TEXT          Field name (e.g., "Thunder Horse")
--lease, -l TEXT          Lease number
--dev-system, -d TEXT     Development system type [default: subsea15]
--discount-rate, -r FLOAT Annual discount rate [default: 0.10]
--oil-price FLOAT         Oil price per barrel [default: 75.00]
--gas-price FLOAT         Gas price per MCF [default: 3.50]
--royalty-rate FLOAT      Royalty rate [default: 0.188]
--output, -o PATH         Output file path
--verbose, -v             Enable verbose output

# Examples
worldenergydata fdas analyze --field "Thunder Horse" --discount-rate 0.10
worldenergydata fdas analyze --lease OCS-G-12345 --oil-price 80
worldenergydata fdas analyze --field "Jack" --dev-system subsea20 --verbose
```

### `fdas classify`

Classify development system by water depth.

```bash
# Arguments
WATER_DEPTH               Water depth in feet (required)

# Examples
worldenergydata fdas classify 500    # shelf
worldenergydata fdas classify 5000   # deepwater
worldenergydata fdas classify 10000  # ultra_deepwater
```

### `fdas info`

Display module information.

```bash
worldenergydata fdas info
```

---

## Dashboard Module (`worldenergydata dashboard`)

Interactive well/field production dashboards.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata dashboard --help` | `bounded-safe` | Show available commands |
| `worldenergydata dashboard serve` | `server-starting` | Launch local web server |

```bash
# Safety: bounded-safe — no data or network required
worldenergydata dashboard --help

# Safety: server-starting — starts a local HTTP server
worldenergydata dashboard serve --port 8050
```

---

## EIA Module (`worldenergydata eia`)

U.S. Energy Information Administration data feed.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata eia --help` | `bounded-safe` | Show available commands |
| `worldenergydata eia fetch` | `credential-required` | Fetch EIA data (requires API key) |

```bash
# Safety: bounded-safe
worldenergydata eia --help

# Safety: credential-required — requires EIA_API_KEY env var
worldenergydata eia fetch
```

---

## Lower Tertiary Module (`worldenergydata lower-tertiary`)

Gulf of Mexico Lower Tertiary field economics and production forecasting.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata lower-tertiary --help` | `bounded-safe` | Show available commands |
| `worldenergydata lower-tertiary analyze` | `fixture-only` | Run portfolio economics |
| `worldenergydata lower-tertiary report` | `fixture-only` | Generate HTML report |

```bash
# Safety: bounded-safe
worldenergydata lower-tertiary --help

# Safety: fixture-only — uses bundled YAML configs, no live data
worldenergydata lower-tertiary analyze
worldenergydata lower-tertiary report --output reports/lt_portfolio.html
```

---

## Forecast Module (`worldenergydata forecast`)

Production decline curve analysis and forecasting.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata forecast --help` | `bounded-safe` | Show available commands |
| `worldenergydata forecast run` | `data-required` | Run decline forecast |

```bash
# Safety: bounded-safe
worldenergydata forecast --help

# Safety: data-required — requires local BSEE dataset
worldenergydata forecast run --field "Thunder Horse"
```

---

## SODIR Module (`worldenergydata sodir`)

Norwegian Continental Shelf data from the Norwegian Offshore Directorate.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata sodir --help` | `bounded-safe` | Show available commands |
| `worldenergydata sodir fetch` | `network-required` | Download NCS data |

```bash
# Safety: bounded-safe
worldenergydata sodir --help

# Safety: network-required
worldenergydata sodir fetch --dataset wellbore
```

---

## Metocean Module (`worldenergydata metocean`)

Marine environmental and metocean data (NDBC, NOAA CO-OPS, Open-Meteo).

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata metocean --help` | `bounded-safe` | Show available commands |
| `worldenergydata metocean fetch` | `network-required` | Fetch metocean observations |

```bash
# Safety: bounded-safe
worldenergydata metocean --help

# Safety: network-required
worldenergydata metocean fetch --station 42001
```

---

## NDBC Module (`worldenergydata ndbc`)

NOAA National Data Buoy Center buoy data.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata ndbc --help` | `bounded-safe` | Show available commands |
| `worldenergydata ndbc fetch` | `network-required` | Fetch buoy observations |

```bash
# Safety: bounded-safe
worldenergydata ndbc --help

# Safety: network-required
worldenergydata ndbc fetch --buoy 42001
```

---

## Texas RRC Module (`worldenergydata texas-rrc`)

Texas Railroad Commission production and permit data.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata texas-rrc --help` | `bounded-safe` | Show available commands |
| `worldenergydata texas-rrc fetch` | `network-required` | Download RRC data |

```bash
# Safety: bounded-safe
worldenergydata texas-rrc --help

# Safety: network-required
worldenergydata texas-rrc fetch
```

---

## Canada Module (`worldenergydata canada`)

Alberta, BC, and Saskatchewan well and production data.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata canada --help` | `bounded-safe` | Show available commands |
| `worldenergydata canada fetch` | `network-required` | Download provincial data |

```bash
# Safety: bounded-safe
worldenergydata canada --help

# Safety: network-required
worldenergydata canada fetch --province alberta
```

---

## Mexico CNH Module (`worldenergydata mexico-cnh`)

Mexico National Hydrocarbons Commission data.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata mexico-cnh --help` | `bounded-safe` | Show available commands |
| `worldenergydata mexico-cnh fetch` | `network-required` | Download CNH data |

```bash
# Safety: bounded-safe
worldenergydata mexico-cnh --help

# Safety: network-required
worldenergydata mexico-cnh fetch
```

---

## Landman Module (`python -m worldenergydata.cli.commands.landman`)

The independently executable Landman module currently routes synthetic or
user-supplied fixture data only. Root command-family startup is tracked
separately by issue #926 and is not claimed here.

| Command | Current behavior |
|---------|------------------|
| `search` | Executes `ownership` with exactly one of `--sample` or `--records-file`; other operations fail atomically |
| `lookup` | Preserved command surface; title routing currently returns a structured unsupported error |
| `county-info` | Reads embedded county-office reference data; it is not a router provider |
| `providers` | Reports static implementation status and source-context readiness |
| `status` | Reports the same provider rows plus local data-directory status |

```bash
# Packaged public synthetic fixture; no network access or credentials.
python -m worldenergydata.cli.commands.landman search \
  --state TX --county MIDLAND --type ownership --sample --format json

# A custom fixture must be a direct-child .json basename in the current directory.
python -m worldenergydata.cli.commands.landman search \
  --state TX --county MIDLAND --records-file records.json --format csv

# Readiness is contextual; this does not silently select the sample.
python -m worldenergydata.cli.commands.landman providers \
  --operation ownership --sample --format json
```

The fixture output is synthetic research data and is not a legal, acreage, or
title conclusion. Live BLM, county portal, and state GIS acquisition are not
implemented by this command.

---

## LNG Terminals Module (`worldenergydata lng-terminals`)

Global LNG terminal locations and capacities.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata lng-terminals --help` | `bounded-safe` | Show available commands |
| `worldenergydata lng-terminals list` | `fixture-only` | List all terminals |

```bash
# Safety: bounded-safe
worldenergydata lng-terminals --help

# Safety: fixture-only — uses bundled reference data
worldenergydata lng-terminals list --region global
```

---

## Safety Analysis Module (`worldenergydata safety-analysis`)

Cross-source safety observation classification and risk scoring.

| Command | Safety | Description |
|---------|--------|-------------|
| `worldenergydata safety-analysis --help` | `bounded-safe` | Show available commands |
| `worldenergydata safety-analysis classify` | `data-required` | Classify incidents |
| `worldenergydata safety-analysis score` | `data-required` | Compute risk scores |

```bash
# Safety: bounded-safe
worldenergydata safety-analysis --help

# Safety: data-required
worldenergydata safety-analysis classify --source hse
worldenergydata safety-analysis score --output reports/risk_scores.csv
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WORLDENERGYDATA_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `WORLDENERGYDATA_DATA_DIR` | Data directory path | ./data |
| `WORLDENERGYDATA_DB_URL` | Database connection URL | sqlite:///data.db |

### Configuration Files

Configuration can be provided via YAML:

```yaml
# config.yaml
data_sources:
  bsee:
    enabled: true
    fields: [Anchor, Julia, Jack, St. Malo]

analysis:
  npv:
    discount_rate: 0.10
    price_deck: oil_gas_prices.csv
```

---

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |

## Output Formats

Most commands support multiple output formats:

- **excel**: Microsoft Excel workbook (.xlsx)
- **json**: JSON format
- **html**: Interactive HTML report
- **pdf**: PDF document
- **csv**: Comma-separated values
- **parquet**: Apache Parquet format

## See Also

- [README.md](../README.md) - Project overview
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Migration from old structure
- [src/worldenergydata/README.md](../src/worldenergydata/README.md) - Package structure
