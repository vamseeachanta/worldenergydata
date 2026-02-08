# Marine Safety Incidents Database Module

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-active%20development-green.svg)]()
[![Data Sources](https://img.shields.io/badge/data%20sources-10-brightgreen.svg)]()

A comprehensive marine safety incidents database module for collecting, storing, and analyzing incident data from global maritime authorities. Part of the WorldEnergyData project.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
  - [Scrape Commands](#scrape-commands)
  - [Import Commands](#import-commands)
  - [Refresh Commands](#refresh-commands)
  - [Correlation Commands](#correlation-commands)
  - [Statistics Commands](#statistics-commands)
  - [Export Commands](#export-commands)
  - [Database Commands](#database-commands)
- [API Usage](#api-usage)
- [Database Schema](#database-schema)
- [Data Sources](#data-sources)
- [Testing](#testing)
- [Development](#development)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

The Marine Safety module provides automated collection, normalization, and analysis of marine safety incident data from multiple authoritative sources worldwide. It covers all types of marine operations including commercial shipping, offshore energy operations, recreational boating, and fishing vessels.

**Key Capabilities:**
- 🌐 **Global Coverage**: US, International, and regional waters
- 🔄 **Automated Collection**: Web scraping with rate limiting and retry logic
- 📊 **Rich Analytics**: Statistical analysis, trend detection, risk assessment
- 🗄️ **Optimized Storage**: PostgreSQL with normalized schema and indexes
- 🔍 **Flexible Querying**: Filter by date, location, incident type, severity
- 📤 **Multiple Export Formats**: CSV, JSON, Excel, Parquet
- 🛡️ **Data Quality**: Validation, deduplication, and quality scoring

---

## Features

### 1. **Multi-Source Data Collection**
   - Collects data from 10 major international safety authorities
   - Configurable scrapers with respect for robots.txt
   - Rate limiting and concurrent request management
   - Automatic retry logic with exponential backoff

### 2. **Comprehensive Database Schema**
   - Normalized relational design (13 tables)
   - Full-text search capabilities
   - Geospatial indexing for location-based queries
   - Document attachment support
   - Historical data tracking

### 3. **Rich Analysis Capabilities**
   - Statistical summaries by source, type, severity
   - Temporal trend analysis
   - Geographic hotspot identification
   - Root cause analysis
   - Environmental impact assessment

### 4. **Command-Line Interface (CLI)**
   - Beautiful terminal output with Rich library
   - Progress indicators and spinners
   - Interactive confirmations for destructive operations
   - Detailed help and examples

### 5. **Python API**
   - SQLAlchemy ORM models
   - Async database operations
   - Type-safe configuration with Pydantic
   - Comprehensive exception handling

### 6. **Data Export**
   - CSV for spreadsheet analysis
   - JSON for API integration
   - Excel for reporting
   - Parquet for big data processing

### 7. **Enterprise Features**
   - Connection pooling for high concurrency
   - Structured logging with rotation
   - Environment-based configuration
   - Data quality scoring system

---

## Installation

### Prerequisites

- **Python**: 3.9 or higher
- **Database**: PostgreSQL 12+ (recommended) or SQLite 3.31+
- **Operating System**: Linux, macOS, or Windows

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/worldenergydata.git
cd worldenergydata

# Install in development mode
pip install -e .

# Or install marine_safety module directly
pip install -e ".[marine-safety]"
```

### Dependencies

The module requires the following key dependencies:

```
sqlalchemy>=2.0.0      # Database ORM
pydantic>=2.0.0        # Configuration validation
pydantic-settings      # Environment-based config
click>=8.0.0           # CLI framework
rich>=13.0.0           # Beautiful terminal output
httpx>=0.24.0          # Async HTTP client
beautifulsoup4>=4.12.0 # HTML parsing
pandas>=2.0.0          # Data manipulation
geoalchemy2>=0.14.0    # Geospatial support
```

All dependencies are automatically installed during setup.

---

## Quick Start

### 1. **Initialize Database**

```bash
# Using SQLite (development)
marine-safety db init

# Using PostgreSQL (production)
marine-safety db init --db-url postgresql://user:pass@localhost/marine
```

### 2. **Scrape Incident Data**

```bash
# Scrape USCG data for recent years
marine-safety scrape uscg --start-year 2020 --end-year 2023

# Scrape NTSB data with verbose output
marine-safety scrape ntsb --start-year 2020 --output ntsb_data.json --verbose

# Scrape BSEE offshore incidents
marine-safety scrape bsee --vessel-types "drilling rig" --output bsee_data.json
```

### 3. **View Statistics**

```bash
# Show overall statistics
marine-safety stats

# Statistics for specific source
marine-safety stats --source uscg --verbose
```

### 4. **Export Data**

```bash
# Export all data to CSV
marine-safety export csv --output incidents.csv

# Export filtered data to JSON
marine-safety export json --output uscg_2022.json --source uscg --start-date 2022-01-01 --end-date 2022-12-31

# Export to Excel with limit
marine-safety export excel --output report.xlsx --limit 1000
```

### 5. **Using Python API**

```python
from worldenergydata.marine_safety import MarineSafetyConfig
from worldenergydata.marine_safety.database import DBManager
from worldenergydata.marine_safety.scrapers import USCGScraper

# Initialize configuration
config = MarineSafetyConfig()

# Connect to database
db = DBManager(config.database.url)

# Scrape data
scraper = USCGScraper(config.scraper)
incidents = scraper.scrape_date_range(start_year=2020, end_year=2023)

# Save to database
db.bulk_insert_incidents(incidents)

# Query incidents
recent_incidents = db.query_incidents(
    start_date="2023-01-01",
    incident_type="collision",
    severity="serious"
)

# Export to CSV
db.export_to_csv(recent_incidents, "collisions_2023.csv")
```

---

## Configuration

### Environment Variables

The module uses environment variables with the prefix `MARINE_SAFETY_`:

#### Database Configuration
```bash
# PostgreSQL (production)
export MARINE_SAFETY_DB_HOST=localhost
export MARINE_SAFETY_DB_PORT=5432
export MARINE_SAFETY_DB_DATABASE=worldenergydata
export MARINE_SAFETY_DB_USERNAME=postgres
export MARINE_SAFETY_DB_PASSWORD=your_password
export MARINE_SAFETY_DB_SCHEMA=marine_safety

# Connection pooling
export MARINE_SAFETY_DB_POOL_SIZE=5
export MARINE_SAFETY_DB_MAX_OVERFLOW=10
export MARINE_SAFETY_DB_POOL_TIMEOUT=30
export MARINE_SAFETY_DB_ECHO=false
```

#### Scraper Configuration
```bash
export MARINE_SAFETY_SCRAPER_USER_AGENT="WorldEnergyData-MarineSafety/1.0"
export MARINE_SAFETY_SCRAPER_REQUEST_TIMEOUT=30
export MARINE_SAFETY_SCRAPER_MAX_RETRIES=3
export MARINE_SAFETY_SCRAPER_RETRY_DELAY=5
export MARINE_SAFETY_SCRAPER_RATE_LIMIT_DELAY=1.0
export MARINE_SAFETY_SCRAPER_CONCURRENT_REQUESTS=5
export MARINE_SAFETY_SCRAPER_RESPECT_ROBOTS_TXT=true

# Enable/disable specific sources
export MARINE_SAFETY_SCRAPER_BSEE_ENABLED=true
export MARINE_SAFETY_SCRAPER_USCG_ENABLED=true
export MARINE_SAFETY_SCRAPER_NTSB_ENABLED=true
export MARINE_SAFETY_SCRAPER_MAIB_ENABLED=true
```

#### Storage Configuration
```bash
export MARINE_SAFETY_STORAGE_BASE_PATH=data/marine_safety
export MARINE_SAFETY_STORAGE_DOCUMENTS_PATH=data/marine_safety/documents
export MARINE_SAFETY_STORAGE_CACHE_PATH=data/marine_safety/cache
export MARINE_SAFETY_STORAGE_MAX_FILE_SIZE=104857600  # 100MB
```

#### Logging Configuration
```bash
export MARINE_SAFETY_LOG_LEVEL=INFO
export MARINE_SAFETY_LOG_FILE_PATH=logs/marine_safety.log
export MARINE_SAFETY_LOG_MAX_BYTES=10485760  # 10MB
export MARINE_SAFETY_LOG_BACKUP_COUNT=5
export MARINE_SAFETY_LOG_CONSOLE_OUTPUT=true
```

#### General Settings
```bash
export MARINE_SAFETY_DEBUG=false
export MARINE_SAFETY_ENVIRONMENT=production  # development, staging, production, test
```

### Configuration File

Create a `.env` file in your project root:

```bash
# .env
MARINE_SAFETY_DB_HOST=localhost
MARINE_SAFETY_DB_DATABASE=worldenergydata
MARINE_SAFETY_DB_USERNAME=postgres
MARINE_SAFETY_DB_PASSWORD=your_secure_password
MARINE_SAFETY_LOG_LEVEL=INFO
MARINE_SAFETY_ENVIRONMENT=production
```

### Programmatic Configuration

```python
from worldenergydata.marine_safety.config import (
    MarineSafetyConfig,
    DatabaseConfig,
    ScraperConfig
)

# Custom database configuration
db_config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="marine_incidents",
    username="admin",
    password="secure_pass"
)

# Custom scraper configuration
scraper_config = ScraperConfig(
    request_timeout=60,
    max_retries=5,
    rate_limit_delay=2.0
)

# Complete configuration
config = MarineSafetyConfig(
    database=db_config,
    scraper=scraper_config,
    debug=False,
    environment="production"
)
```

---

## CLI Usage

The module provides a comprehensive command-line interface via the `marine-safety` command (also accessible as `wed marine-safety`).

### General Commands

#### `marine-safety --version`
Display version information.

#### `marine-safety info`
Display module information and capabilities.

```bash
marine-safety info
```

---

### Scrape Commands

The `scrape` command group provides web scraping capabilities for data sources that support automated collection.

#### `marine-safety scrape ntsb`
Scrape incident data from the NTSB CAROL (Case Analysis and Reporting Online) database.

**Options:**
- `--start-year INT` - Starting year for data collection
- `--end-year INT` - Ending year for data collection
- `--output PATH` - Output file path for scraped data
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Scrape NTSB data for 2020-2023
marine-safety scrape ntsb --start-year 2020 --end-year 2023

# Scrape with output file and verbose logging
marine-safety scrape ntsb --start-year 2022 --output ntsb_2022.json --verbose
```

#### `marine-safety scrape atsb`
Scrape incident data from the Australian Transport Safety Bureau (ATSB) investigations database.

**Options:**
- `--start-year INT` - Starting year for data collection
- `--end-year INT` - Ending year for data collection
- `--output PATH` - Output file path for scraped data
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Scrape ATSB data for recent years
marine-safety scrape atsb --start-year 2020 --end-year 2023

# Scrape with output file
marine-safety scrape atsb --start-year 2022 --output atsb_data.json --verbose
```

#### `marine-safety scrape uscg`
Scrape incident data from USCG MISLE database.

**Options:**
- `--start-year INT` - Starting year for data collection
- `--end-year INT` - Ending year for data collection
- `--output PATH` - Output file path for scraped data
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Scrape USCG data for 2020-2023
marine-safety scrape uscg --start-year 2020 --end-year 2023

# Scrape with output file
marine-safety scrape uscg --start-year 2022 --output uscg_2022.json --verbose
```

#### `marine-safety scrape bsee`
Scrape incident data from BSEE (Bureau of Safety and Environmental Enforcement).

**Options:**
- `--vessel-types TEXT` - Filter by vessel types (can be repeated)
- `--output PATH` - Output file path
- `--verbose` - Verbose output

**Examples:**
```bash
# Scrape all BSEE data
marine-safety scrape bsee

# Filter by vessel types
marine-safety scrape bsee --vessel-types "drilling rig" --vessel-types "platform"

# Save to file
marine-safety scrape bsee --output bsee_data.json --verbose
```

---

### Import Commands

The `import` command group imports data from various maritime safety authorities. Some sources support automatic download, while others require manual file download first.

#### Automatic Import Sources

These sources support automatic download and import:

#### `marine-safety import ntsb`
Import NTSB marine incident data (automatic download from CAROL database).

**Options:**
- `--start-year INT` - Starting year (default: 2020)
- `--end-year INT` - Ending year (default: current year)
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import NTSB data for default range
marine-safety import ntsb

# Import specific year range
marine-safety import ntsb --start-year 2018 --end-year 2023 --verbose
```

#### `marine-safety import imo`
Import IMO GISIS (Global Integrated Shipping Information System) global casualty data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import IMO global data
marine-safety import imo --start-year 2020 --end-year 2023

# Import with verbose output
marine-safety import imo --verbose
```

#### `marine-safety import atsb`
Import Australian Transport Safety Bureau (ATSB) marine investigation data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import ATSB data
marine-safety import atsb --start-year 2020 --end-year 2023
```

#### `marine-safety import tsb`
Import Canadian Transportation Safety Board (TSB) marine occurrence data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import TSB Canada data
marine-safety import tsb --start-year 2020 --end-year 2023
```

#### `marine-safety import maib`
Import UK Marine Accident Investigation Branch (MAIB) data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import MAIB UK data
marine-safety import maib --start-year 2020 --end-year 2023
```

#### `marine-safety import noaa`
Import NOAA Incident News oil spill and pollution incident data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import NOAA oil spill data
marine-safety import noaa --start-year 2020 --end-year 2023
```

#### `marine-safety import boating`
Import USCG BARD (Boating Accident Report Database) recreational boating incident data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import recreational boating data
marine-safety import boating --start-year 2020 --end-year 2023
```

#### Manual Download Sources

These sources require manual file download before import:

#### `marine-safety import uscg`
Import USCG MISLE (Marine Information for Safety and Law Enforcement) data.

**Note:** This is a stub implementation. USCG MISLE data requires special access.

**Options:**
- `--file PATH` - Path to downloaded MISLE data file
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import from downloaded file
marine-safety import uscg --file /path/to/misle_data.csv
```

#### `marine-safety import bsee`
Import BSEE offshore incident data.

**Note:** This is a stub implementation. BSEE data may require manual download.

**Options:**
- `--file PATH` - Path to downloaded BSEE data file
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import from downloaded file
marine-safety import bsee --file /path/to/bsee_incidents.xlsx
```

#### `marine-safety import emsa`
Import EU EMSA EMCIP (European Marine Casualty Information Platform) data.

**Note:** Requires EMCIP access credentials.

**Options:**
- `--file PATH` - Path to downloaded EMCIP data file
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Import from downloaded EMCIP export
marine-safety import emsa --file /path/to/emcip_export.csv
```

---

### Refresh Commands

The `refresh` command group provides automated scrape + import workflows for supported sources.

#### `marine-safety refresh ntsb`
Automatically scrape and import the latest NTSB data.

**Options:**
- `--start-year INT` - Starting year (default: previous year)
- `--end-year INT` - Ending year (default: current year)
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Refresh NTSB data with defaults
marine-safety refresh ntsb

# Refresh specific year range
marine-safety refresh ntsb --start-year 2020 --end-year 2023 --verbose
```

#### `marine-safety refresh atsb`
Automatically scrape and import the latest ATSB data.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Refresh ATSB data
marine-safety refresh atsb

# Refresh with verbose output
marine-safety refresh atsb --verbose
```

#### `marine-safety refresh all`
Refresh all available data sources that support automatic collection.

**Options:**
- `--start-year INT` - Starting year
- `--end-year INT` - Ending year
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Refresh all sources
marine-safety refresh all

# Refresh all sources for specific years
marine-safety refresh all --start-year 2022 --end-year 2023 --verbose
```

**Note:** For sources that require manual download, the `refresh` command will display instructions on how to obtain the data files.

---

### Correlation Commands

The `correlate` command group provides cross-source incident correlation and linking capabilities.

#### `marine-safety correlate find-matches`
Find potential matching incidents across different data sources based on date, location, vessel name, and other attributes.

**Options:**
- `--threshold FLOAT` - Similarity threshold (0.0-1.0, default: 0.7)
- `--max-days INT` - Maximum days between incidents to consider as potential match (default: 3)
- `--output PATH` - Output file for match results
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Find matches with default settings
marine-safety correlate find-matches

# Find matches with stricter threshold
marine-safety correlate find-matches --threshold 0.85

# Export matches to file
marine-safety correlate find-matches --output matches.json --verbose
```

#### `marine-safety correlate link`
Create links between related incidents identified through correlation analysis.

**Options:**
- `--source-id TEXT` - Source incident ID
- `--target-id TEXT` - Target incident ID
- `--relationship TEXT` - Relationship type (same_incident, related, followup)
- `--confidence FLOAT` - Confidence score (0.0-1.0)
- `--verbose` - Enable verbose output

**Examples:**
```bash
# Link two incidents
marine-safety correlate link --source-id NTSB-2023-001 --target-id USCG-2023-456 --relationship same_incident --confidence 0.95

# Link with automatic relationship detection
marine-safety correlate link --source-id ATSB-2023-001 --target-id IMO-2023-789 --verbose
```

#### `marine-safety correlate stats`
Display correlation statistics showing matches found across data sources.

**Options:**
- `--verbose` - Show detailed statistics

**Examples:**
```bash
# Show correlation statistics
marine-safety correlate stats

# Show detailed breakdown
marine-safety correlate stats --verbose
```

---

### Statistics Commands

#### `marine-safety stats`
Display comprehensive statistics about marine safety incident data in the database.

**Options:**
- `--by-source` - Group statistics by data source
- `--by-year` - Group statistics by year
- `--source [all|uscg|ntsb|bsee|imo|atsb|tsb|maib|noaa|boating|emsa]` - Filter by specific source
- `--verbose` - Show detailed statistics

**Examples:**
```bash
# Show overall statistics
marine-safety stats

# Statistics grouped by data source
marine-safety stats --by-source

# Statistics grouped by year
marine-safety stats --by-year

# Combined grouping with verbose output
marine-safety stats --by-source --by-year --verbose

# Statistics for specific source only
marine-safety stats --source ntsb --verbose
```

**Sample Output:**
```
Marine Safety Database Statistics
=================================

Total Incidents: 45,234
Total Fatalities: 1,456
Total Injuries: 8,234
Date Range: 2015-01-01 to 2024-12-31

By Source:
  NTSB:     3,456 incidents
  USCG:    15,234 incidents
  BSEE:     2,100 incidents
  IMO:     12,500 incidents
  ATSB:     1,234 incidents
  TSB:      2,456 incidents
  MAIB:     3,254 incidents
  NOAA:     2,000 incidents
  BARD:     3,000 incidents
```

---

### Export Commands

#### `marine-safety export FORMAT`
Export marine safety incident data to various formats.

**Formats:**
- `csv` - Comma-separated values
- `json` - JSON format
- `excel` - Excel spreadsheet (.xlsx)
- `parquet` - Apache Parquet

**Options:**
- `--output PATH` - Output file path (required)
- `--source [all|uscg|ntsb|bsee|imo|atsb|tsb|maib|noaa|boating|emsa]` - Data source to export (default: all)
- `--start-date TEXT` - Start date filter (YYYY-MM-DD)
- `--end-date TEXT` - End date filter (YYYY-MM-DD)
- `--limit INT` - Limit number of records to export

**Examples:**
```bash
# Export all data to CSV
marine-safety export csv --output incidents.csv

# Export NTSB data to JSON
marine-safety export json --output ntsb.json --source ntsb

# Export date range to Excel
marine-safety export excel --output 2022_report.xlsx --start-date 2022-01-01 --end-date 2022-12-31

# Export limited records to Parquet
marine-safety export parquet --output sample.parquet --limit 10000
```

---

### Database Commands

#### `marine-safety db init`
Initialize database schema with all tables, indexes, and constraints.

**Options:**
- `--force` - Force recreation of existing database (destructive)
- `--db-url TEXT` - Database connection URL

**Examples:**
```bash
# Initialize with SQLite (default)
marine-safety db init

# Force recreation
marine-safety db init --force

# Initialize PostgreSQL
marine-safety db init --db-url postgresql://user:pass@localhost/marine
```

#### `marine-safety db migrate`
Run database migrations to update schema.

**Options:**
- `--target-version INT` - Target migration version
- `--dry-run` - Show migration plan without executing

**Examples:**
```bash
# Run all pending migrations
marine-safety db migrate

# Migrate to specific version
marine-safety db migrate --target-version 5

# Preview migrations
marine-safety db migrate --dry-run
```

#### `marine-safety db seed`
Seed database with test/sample data.

**Options:**
- `--sample-size INT` - Number of sample records (default: 100)
- `--clear-existing` - Clear existing data before seeding

**Examples:**
```bash
# Seed with 100 records
marine-safety db seed

# Seed with custom size
marine-safety db seed --sample-size 500

# Clear and seed
marine-safety db seed --clear-existing --sample-size 200
```

---

## API Usage

### Database Manager

```python
from worldenergydata.marine_safety.database import DBManager
from worldenergydata.marine_safety.config import get_config

# Initialize database manager
config = get_config()
db = DBManager(config.database.url)

# Create tables
db.create_all_tables()

# Insert incident
incident_data = {
    "incident_id": "USCG-2023-001",
    "incident_date": "2023-06-15",
    "incident_type": "collision",
    "severity_level": "serious",
    "fatalities": 2,
    "latitude": 29.9511,
    "longitude": -90.0715,
    "location_description": "Gulf of Mexico",
    "reporting_agency": "USCG"
}
db.insert_incident(incident_data)

# Query incidents
incidents = db.query_incidents(
    start_date="2023-01-01",
    end_date="2023-12-31",
    incident_type="collision",
    min_severity="moderate"
)

# Get statistics
stats = db.get_statistics(source="uscg")
print(f"Total incidents: {stats['total_incidents']}")
print(f"Total fatalities: {stats['total_fatalities']}")

# Export data
db.export_to_csv(incidents, "collisions_2023.csv")
```

### Scraper Usage

```python
from worldenergydata.marine_safety.scrapers import USCGScraper
from worldenergydata.marine_safety.config import get_config

# Initialize scraper
config = get_config()
scraper = USCGScraper(config.scraper)

# Scrape data
incidents = scraper.scrape_date_range(
    start_year=2020,
    end_year=2023
)

# Process incidents
for incident in incidents:
    print(f"Incident ID: {incident['incident_id']}")
    print(f"Date: {incident['incident_date']}")
    print(f"Type: {incident['incident_type']}")
    print(f"Severity: {incident['severity_level']}")
    print("---")

# Save to file
scraper.save_to_file(incidents, "uscg_incidents.json")
```

### Models

```python
from worldenergydata.marine_safety.database.models import (
    Incident,
    Vessel,
    Investigation
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Create engine
engine = create_engine("postgresql://user:pass@localhost/marine")

# Create session
with Session(engine) as session:
    # Query incidents with joins
    incidents = (
        session.query(Incident)
        .filter(Incident.incident_date >= "2023-01-01")
        .filter(Incident.severity_level == "serious")
        .order_by(Incident.incident_date.desc())
        .limit(10)
        .all()
    )

    # Access related data
    for incident in incidents:
        print(f"Incident: {incident.incident_id}")
        if incident.vessels:
            for vessel in incident.vessels:
                print(f"  Vessel: {vessel.vessel_name}")
        if incident.investigation:
            print(f"  Status: {incident.investigation.investigation_status}")
```

### Configuration

```python
from worldenergydata.marine_safety.config import (
    get_config,
    reload_config,
    MarineSafetyConfig
)

# Get singleton config instance
config = get_config()

# Access nested configurations
print(config.database.host)
print(config.scraper.request_timeout)
print(config.storage.base_path)
print(config.logging.level)

# Reload configuration (e.g., after .env changes)
config = reload_config()

# Create custom configuration
custom_config = MarineSafetyConfig(
    debug=True,
    environment="development"
)
```

### Validators

```python
from worldenergydata.marine_safety.utils.validators import (
    validate_coordinates,
    validate_date_range,
    validate_imo_number
)

# Validate coordinates
is_valid = validate_coordinates(29.9511, -90.0715)

# Validate date range
dates_valid = validate_date_range("2020-01-01", "2023-12-31")

# Validate IMO number
imo_valid = validate_imo_number("9074729")
```

---

## Database Schema

### Schema Design

The database uses a **normalized relational schema** with 13 tables optimized for complex queries and analytics.

**Design Principles:**
- ✅ Third Normal Form (3NF) normalization
- ✅ Foreign key constraints for referential integrity
- ✅ Strategic indexes for common query patterns
- ✅ Full-text search capabilities
- ✅ Geospatial indexing (PostGIS)

### Core Tables

#### 1. **incidents** (Primary Table)
Stores core incident information.

**Key Fields:**
- `incident_id` (PK) - Unique incident identifier
- `incident_date` - Date of incident
- `incident_type` - Type (collision, grounding, fire, etc.)
- `severity_level` - Severity (minimal, minor, moderate, serious, catastrophic)
- `latitude`, `longitude` - Geographic coordinates
- `fatalities`, `injuries`, `missing_persons` - Human impact
- `property_damage_usd` - Financial impact
- `environmental_impact` - Boolean flag
- `reporting_agency` - Source agency (USCG, NTSB, BSEE, etc.)

**Indexes:**
- `idx_date` - Incident date
- `idx_location` - Geographic coordinates (spatial)
- `idx_type` - Incident type
- `idx_severity` - Severity level

#### 2. **vessels**
Vessel details involved in incidents.

**Key Fields:**
- `vessel_id` (PK)
- `vessel_name`
- `imo_number` - International Maritime Organization number (unique)
- `vessel_type` - Type (drilling rig, tanker, cargo, etc.)
- `flag_country` - Country of registration
- `built_year`, `gross_tonnage`, `length_meters`

#### 3. **companies**
Operating companies/owners.

**Key Fields:**
- `company_id` (PK)
- `company_name`
- `country_code`
- `industry_sector`

#### 4. **personnel**
Personnel involved in incidents.

**Key Fields:**
- `person_id` (PK)
- `role` - Position/role on vessel
- `injury_type`, `injury_severity`
- `fatality` - Boolean

#### 5. **investigations**
Investigation details and findings.

**Key Fields:**
- `investigation_id` (PK)
- `incident_id` (FK)
- `investigation_status` - Status (reported, under_investigation, final_report, closed)
- `root_cause`, `contributing_factors`
- `regulatory_violations`
- `recommendations`

#### 6. **documents**
Attached reports and documents.

**Key Fields:**
- `document_id` (PK)
- `incident_id` (FK)
- `document_type` - Type (investigation_report, photo, video, etc.)
- `file_path`, `file_url`
- `file_size`, `mime_type`

#### 7. **environmental_impacts**
Environmental damage details.

**Key Fields:**
- `environmental_id` (PK)
- `incident_id` (FK)
- `spill_type` - Type (oil, chemical, sewage, etc.)
- `spill_volume_gallons`
- `wildlife_impact`, `habitat_impact`

#### 8. **weather_conditions**
Detailed weather and sea conditions.

**Key Fields:**
- `weather_id` (PK)
- `incident_id` (FK)
- `weather_conditions`, `sea_state`, `visibility`
- `wind_speed_knots`, `wave_height_meters`
- `current_speed_knots`

#### 9. **equipment_involved**
Equipment/systems involved.

**Key Fields:**
- `equipment_id` (PK)
- `equipment_name`, `equipment_type`
- `manufacturer`, `model`
- `failure_mode`

#### 10-13. **Relationship Tables**
- `incident_vessels` - Many-to-many: incidents ↔ vessels
- `incident_companies` - Many-to-many: incidents ↔ companies
- `incident_personnel` - Many-to-many: incidents ↔ personnel
- `incident_equipment` - Many-to-many: incidents ↔ equipment

### Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│  incidents  │───────│incident_     │───────│   vessels    │
│             │       │  vessels     │       │              │
└─────────────┘       └──────────────┘       └──────────────┘
      │
      ├───────────────┐
      │               │
      ▼               ▼
┌──────────────┐ ┌──────────────┐
│investigations│ │  documents   │
└──────────────┘ └──────────────┘
      │
      ▼
┌──────────────────────┐
│environmental_impacts │
└──────────────────────┘
```

**See Full Schema:**
- [Optimized Schema SQL](/mnt/github/workspace-hub/worldenergydata/specs/modules/analysis/marine/MARINE_SAFETY_SPEC.md)
- [Entity Relationship Diagram](docs/marine_safety_erd.png) *(to be generated)*

---

## Data Sources

The module collects data from **10 authoritative international sources**:

### 1. **NTSB (National Transportation Safety Board)** 🇺🇸
- **Coverage**: Major US marine accidents
- **URL**: https://data.ntsb.gov/carol-main-public
- **Data Types**: Serious accidents, fatalities, in-depth investigations
- **Historical Data**: 1967 - present
- **Update Frequency**: Real-time
- **Import Command**: `marine-safety import ntsb` (automatic)
- **Scrape Command**: `marine-safety scrape ntsb`

### 2. **IMO GISIS (International Maritime Organization)** 🌐
- **Coverage**: Global, all flag states
- **URL**: https://gisis.imo.org/
- **Data Types**: International casualties, port state control, pollution incidents
- **Historical Data**: 1997 - present
- **Update Frequency**: Continuous
- **Import Command**: `marine-safety import imo` (automatic)

### 3. **ATSB (Australian Transport Safety Bureau)** 🇦🇺
- **Coverage**: Australian waters and Australian-flagged vessels
- **URL**: https://www.atsb.gov.au/marine
- **Data Types**: Marine safety investigations, accident reports
- **Historical Data**: 2000s - present
- **Update Frequency**: Continuous
- **Import Command**: `marine-safety import atsb` (automatic)
- **Scrape Command**: `marine-safety scrape atsb`

### 4. **TSB (Transportation Safety Board)** 🇨🇦
- **Coverage**: Canadian vessels and waters
- **URL**: https://www.tsb.gc.ca/eng/rapports-reports/marine/
- **Data Types**: Marine occurrences, investigation reports
- **Historical Data**: 1990s - present
- **Update Frequency**: Continuous
- **Import Command**: `marine-safety import tsb` (automatic)

### 5. **MAIB (Marine Accident Investigation Branch)** 🇬🇧
- **Coverage**: UK-flagged vessels and UK waters
- **URL**: https://www.gov.uk/maib-reports
- **Data Types**: Commercial vessel accidents, investigation reports
- **Historical Data**: 1990s - present
- **Update Frequency**: Monthly
- **Import Command**: `marine-safety import maib` (automatic)

### 6. **NOAA Incident News** 🇺🇸
- **Coverage**: US waters and international incidents affecting US interests
- **URL**: https://incidentnews.noaa.gov/
- **Data Types**: Oil spills, chemical releases, pollution incidents
- **Historical Data**: 1967 - present
- **Update Frequency**: Real-time
- **Import Command**: `marine-safety import noaa` (automatic)

### 7. **USCG BARD (Boating Accident Report Database)** 🇺🇸
- **Coverage**: US recreational boating accidents
- **URL**: https://uscgboating.org/statistics/accident_statistics.php
- **Data Types**: Recreational boating casualties, fatalities, injuries
- **Historical Data**: 2000s - present
- **Update Frequency**: Annual
- **Import Command**: `marine-safety import boating` (automatic)

### 8. **USCG MISLE (Marine Information for Safety and Law Enforcement)** 🇺🇸
- **Coverage**: US commercial vessels, recreational boating
- **URL**: https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/
- **Data Types**: Vessel casualties, collisions, groundings, sinkings, personnel casualties
- **Historical Data**: 1990s - present
- **Update Frequency**: Continuous
- **Import Command**: `marine-safety import uscg` (requires manual download)

### 9. **BSEE (Bureau of Safety and Environmental Enforcement)** 🇺🇸
- **Coverage**: US offshore oil & gas operations
- **URL**: https://www.bsee.gov/stats-facts/offshore-incident-statistics
- **Data Types**: Platform incidents, blowouts, fires, personnel injuries, environmental spills
- **Historical Data**: 1990s - present
- **Update Frequency**: Quarterly
- **Import Command**: `marine-safety import bsee` (requires manual download)

### 10. **EMSA EMCIP (European Marine Casualty Information Platform)** 🇪🇺
- **Coverage**: European waters, EU-flagged vessels
- **URL**: http://emcip.jrc.ec.europa.eu/
- **Data Types**: Casualties, accidents, incidents in European waters
- **Historical Data**: 2011 - present
- **Update Frequency**: Real-time
- **Import Command**: `marine-safety import emsa` (requires EMCIP access)

### Data Coverage Summary

| Source | Geographic Scope | Vessel Types | Time Range | Records | Auto Import |
|--------|-----------------|--------------|------------|---------|-------------|
| NTSB   | US              | Major accidents | 1967-present | ~10,000 | Yes |
| IMO    | Global          | International fleet | 1997-present | ~50,000 | Yes |
| ATSB   | Australia       | All marine | 2000-present | ~5,000 | Yes |
| TSB    | Canada          | All marine | 1990-present | ~8,000 | Yes |
| MAIB   | UK/International| Commercial vessels | 1990-present | ~15,000 | Yes |
| NOAA   | US/Global       | Oil spills, pollution | 1967-present | ~8,000 | Yes |
| BARD   | US              | Recreational boating | 2000-present | ~50,000 | Yes |
| USCG   | US waters       | All commercial | 1990-present | ~100,000 | Manual |
| BSEE   | US OCS          | Offshore platforms | 1990-present | ~5,000 | Manual |
| EMSA   | EU waters       | All commercial | 2011-present | ~40,000 | Manual |

**Total Estimated Coverage**: 290,000+ incidents

---

## Testing

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=worldenergydata.marine_safety --cov-report=html

# Run specific test file
pytest tests/test_database.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_scraper"
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py                  # Shared fixtures
├── test_config.py               # Configuration tests
├── test_database.py             # Database operations
├── test_models.py               # SQLAlchemy models
├── test_scrapers/
│   ├── test_uscg_scraper.py
│   ├── test_ntsb_scraper.py
│   └── test_bsee_scraper.py
├── test_validators.py           # Data validation
├── test_cli.py                  # CLI commands
└── test_integration.py          # End-to-end tests
```

### Writing Tests

```python
import pytest
from worldenergydata.marine_safety.database import DBManager

@pytest.fixture
def db_manager(tmp_path):
    """Create temporary database for testing"""
    db_url = f"sqlite:///{tmp_path}/test.db"
    db = DBManager(db_url)
    db.create_all_tables()
    return db

def test_insert_incident(db_manager):
    """Test incident insertion"""
    incident_data = {
        "incident_id": "TEST-001",
        "incident_date": "2023-01-01",
        "incident_type": "collision",
        "severity_level": "moderate"
    }

    db_manager.insert_incident(incident_data)

    incidents = db_manager.query_incidents(incident_id="TEST-001")
    assert len(incidents) == 1
    assert incidents[0]["incident_type"] == "collision"
```

### Test Coverage

Current test coverage: **85%** *(target: 90%+)*

---

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/worldenergydata.git
cd worldenergydata

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all extras
pip install -e ".[dev,test,marine-safety]"

# Install pre-commit hooks
pre-commit install
```

### Project Structure

```
src/worldenergydata/modules/marine_safety/
├── __init__.py                  # Module exports
├── cli.py                       # Click CLI interface
├── config.py                    # Pydantic configuration
├── constants.py                 # Enums and constants
├── exceptions.py                # Custom exceptions
│
├── database/
│   ├── __init__.py
│   ├── db_manager.py           # Database operations
│   ├── models.py               # SQLAlchemy ORM models
│   └── migrations/             # Alembic migrations
│
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py         # Abstract base scraper
│   ├── uscg_scraper.py         # USCG MISLE scraper
│   ├── ntsb_scraper.py         # NTSB scraper
│   ├── bsee_scraper.py         # BSEE scraper
│   ├── maib_scraper.py         # MAIB scraper
│   └── ... (other scrapers)
│
└── utils/
    ├── __init__.py
    ├── logger.py               # Logging utilities
    ├── validators.py           # Data validation
    └── parsers.py              # Data parsing utilities
```

### Adding a New Scraper

1. **Create scraper class** inheriting from `BaseScraper`:

```python
# scrapers/new_source_scraper.py
from .base_scraper import BaseScraper
from ..config import ScraperConfig

class NewSourceScraper(BaseScraper):
    """Scraper for New Data Source"""

    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self.base_url = "https://newsource.example.com"

    def scrape_date_range(self, start_year: int, end_year: int):
        """Scrape incidents for date range"""
        incidents = []

        for year in range(start_year, end_year + 1):
            url = f"{self.base_url}/incidents?year={year}"
            response = self._make_request(url)

            incidents.extend(self._parse_response(response))

        return incidents

    def _parse_response(self, response):
        """Parse HTML/JSON response"""
        # Implementation here
        pass
```

2. **Add CLI command** in `cli.py`:

```python
@scrape.command()
@click.option('--start-year', type=int)
@click.option('--end-year', type=int)
def newsource(start_year, end_year):
    """Scrape New Data Source"""
    scraper = NewSourceScraper(config.scraper)
    incidents = scraper.scrape_date_range(start_year, end_year)
    # Save incidents...
```

3. **Add tests**:

```python
# tests/test_scrapers/test_newsource_scraper.py
def test_newsource_scraper():
    scraper = NewSourceScraper(config)
    incidents = scraper.scrape_date_range(2020, 2023)
    assert len(incidents) > 0
```

### Code Style

This project follows:
- **PEP 8** - Python style guide
- **Black** - Code formatting (line length: 100)
- **isort** - Import sorting
- **mypy** - Type checking
- **flake8** - Linting

```bash
# Format code
black src/worldenergydata/modules/marine_safety

# Sort imports
isort src/worldenergydata/modules/marine_safety

# Type checking
mypy src/worldenergydata/modules/marine_safety

# Linting
flake8 src/worldenergydata/modules/marine_safety
```

### Continuous Integration

The project uses GitHub Actions for CI/CD:

```yaml
# .github/workflows/marine-safety-tests.yml
name: Marine Safety Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -e ".[test]"
      - run: pytest --cov
```

---

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                     CLI / Python API                     │
└─────────────────────┬───────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Scrapers │   │ Database │   │  Export  │
│          │   │  Manager │   │  Engine  │
└──────────┘   └──────────┘   └──────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│  Web     │   │PostgreSQL│   │  Files   │
│ Sources  │   │  /SQLite │   │(CSV/JSON)│
└──────────┘   └──────────┘   └──────────┘
```

### Component Responsibilities

#### 1. **CLI Layer** (`cli.py`)
- User interface via Click framework
- Beautiful output with Rich library
- Command routing and argument parsing
- Progress indicators and confirmations

#### 2. **Configuration** (`config.py`)
- Pydantic-based settings with validation
- Environment variable loading
- Nested configuration objects
- Type safety

#### 3. **Scrapers** (`scrapers/`)
- Abstract base class with common functionality
- Source-specific implementations
- Rate limiting and retry logic
- Data normalization

#### 4. **Database** (`database/`)
- SQLAlchemy ORM models
- Connection pooling
- Query builders
- Migration management

#### 5. **Utilities** (`utils/`)
- Logging with rotation
- Data validation
- Parsing helpers
- Error handling

### Design Patterns

- **Factory Pattern**: Scraper instantiation
- **Strategy Pattern**: Different scraping strategies per source
- **Repository Pattern**: Database access abstraction
- **Singleton Pattern**: Configuration management
- **Builder Pattern**: Complex query construction

### Scalability Considerations

- **Connection Pooling**: Handle concurrent requests
- **Async Operations**: Non-blocking I/O for scrapers
- **Batch Inserts**: Efficient bulk operations
- **Indexing Strategy**: Optimize common queries
- **Partitioning**: Date-based table partitioning (future)

---

## Troubleshooting

### Common Issues

#### 1. **Database Connection Errors**

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials
psql -h localhost -U postgres -d worldenergydata

# Check environment variables
echo $MARINE_SAFETY_DB_HOST
echo $MARINE_SAFETY_DB_PASSWORD

# Test connection
marine-safety db init --db-url postgresql://user:pass@localhost/marine
```

#### 2. **Scraper Timeouts**

**Problem**: `httpx.TimeoutException: Request timeout`

**Solutions**:
```bash
# Increase timeout
export MARINE_SAFETY_SCRAPER_REQUEST_TIMEOUT=60

# Reduce concurrent requests
export MARINE_SAFETY_SCRAPER_CONCURRENT_REQUESTS=2

# Enable verbose logging
marine-safety scrape uscg --verbose
```

#### 3. **Import Errors**

**Problem**: `ModuleNotFoundError: No module named 'worldenergydata.marine_safety'`

**Solutions**:
```bash
# Reinstall in development mode
pip install -e .

# Check PYTHONPATH
echo $PYTHONPATH

# Verify installation
pip show worldenergydata
```

#### 4. **Permission Errors**

**Problem**: `PermissionError: [Errno 13] Permission denied: 'data/marine_safety'`

**Solutions**:
```bash
# Create directories with proper permissions
mkdir -p data/marine_safety logs
chmod 755 data/marine_safety logs

# Or change storage path
export MARINE_SAFETY_STORAGE_BASE_PATH=~/marine_data
```

#### 5. **Slow Queries**

**Problem**: Database queries taking too long

**Solutions**:
```sql
-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'marine_safety';

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM incidents WHERE incident_date > '2023-01-01';

-- Create additional indexes
CREATE INDEX idx_incident_date_type ON incidents(incident_date, incident_type);
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Via environment variable
export MARINE_SAFETY_DEBUG=true
export MARINE_SAFETY_LOG_LEVEL=DEBUG

# Or programmatically
from worldenergydata.marine_safety.config import get_config
config = get_config()
config.debug = True
config.logging.level = "DEBUG"
```

### Getting Help

- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/yourusername/worldenergydata/issues
- **Discussions**: https://github.com/yourusername/worldenergydata/discussions
- **Email**: support@worldenergydata.example.com

---

## License

MIT License

Copyright (c) 2024 WorldEnergyData

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Acknowledgments

- **BSEE** - Bureau of Safety and Environmental Enforcement
- **USCG** - United States Coast Guard
- **NTSB** - National Transportation Safety Board
- **MAIB** - Marine Accident Investigation Branch
- **TSB** - Transportation Safety Board of Canada
- **EMSA** - European Maritime Safety Agency
- **IMO** - International Maritime Organization

---

**Version**: 1.1.0
**Last Updated**: 2026-01-27
**Status**: Active Development

For more information, see the [main project README](../../../../../README.md).
