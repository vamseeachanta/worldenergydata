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
