# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-01-13-well-data-verification-dashboard/spec.md

> Created: 2025-01-13
> Version: 1.0.0

## Overview

While the primary data storage remains file-based (CSV, Excel, YAML), this schema defines the structured data models and optional database tables for caching and performance optimization.

## Data Models

### Well Master Data
```python
class Well:
    api12: str  # Primary key
    api10: str
    well_name: str
    field_name: str
    operator: str
    water_depth: float
    completion_date: datetime
    spud_date: datetime
    status: str  # active, inactive, abandoned
    coordinates: dict  # {lat, lon}
    last_updated: datetime
```

### Production Data
```python
class ProductionRecord:
    id: int  # Auto-increment primary key
    api12: str  # Foreign key to Well
    production_date: date
    oil_volume: float  # BBL
    gas_volume: float  # MCF
    water_volume: float  # BBL
    days_on_production: int
    oil_rate: float  # BOPD
    gas_rate: float  # MCFD
    water_rate: float  # BWPD
    data_source: str  # BSEE, Manual, Import
    created_at: datetime
    updated_at: datetime
```

### Economic Data
```python
class EconomicMetrics:
    id: int  # Auto-increment primary key
    api12: str  # Foreign key to Well
    calculation_date: date
    oil_price: float  # $/BBL
    gas_price: float  # $/MCF
    revenue: float  # USD
    opex: float  # USD
    capex: float  # USD
    net_cash_flow: float  # USD
    npv: float  # USD
    discount_rate: float
    created_at: datetime
```

### Validation Results
```python
class ValidationResult:
    validation_id: str  # Primary key (UUID)
    api12: str  # Foreign key to Well
    validation_date: datetime
    validation_type: str  # completeness, outlier, economics
    status: str  # passed, warning, failed
    issues: json  # Array of issue objects
    metadata: json  # Additional validation details
    user: str
    created_at: datetime
```

### Dashboard Cache
```python
class DashboardCache:
    cache_key: str  # Primary key
    data_type: str  # overview, metrics, chart
    data: json  # Cached JSON data
    expires_at: datetime
    created_at: datetime
```

## Optional SQL Schema

For PostgreSQL or SQLite implementation:

```sql
-- Wells table
CREATE TABLE wells (
    api12 VARCHAR(12) PRIMARY KEY,
    api10 VARCHAR(10) NOT NULL,
    well_name VARCHAR(100),
    field_name VARCHAR(50),
    operator VARCHAR(100),
    water_depth DECIMAL(10, 2),
    completion_date DATE,
    spud_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Production data table
CREATE TABLE production_records (
    id SERIAL PRIMARY KEY,
    api12 VARCHAR(12) REFERENCES wells(api12),
    production_date DATE NOT NULL,
    oil_volume DECIMAL(12, 2),
    gas_volume DECIMAL(12, 2),
    water_volume DECIMAL(12, 2),
    days_on_production INTEGER,
    oil_rate DECIMAL(10, 2),
    gas_rate DECIMAL(10, 2),
    water_rate DECIMAL(10, 2),
    data_source VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api12, production_date)
);

-- Economic metrics table
CREATE TABLE economic_metrics (
    id SERIAL PRIMARY KEY,
    api12 VARCHAR(12) REFERENCES wells(api12),
    calculation_date DATE NOT NULL,
    oil_price DECIMAL(10, 2),
    gas_price DECIMAL(10, 2),
    revenue DECIMAL(15, 2),
    opex DECIMAL(15, 2),
    capex DECIMAL(15, 2),
    net_cash_flow DECIMAL(15, 2),
    npv DECIMAL(15, 2),
    discount_rate DECIMAL(5, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api12, calculation_date)
);

-- Validation results table
CREATE TABLE validation_results (
    validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api12 VARCHAR(12) REFERENCES wells(api12),
    validation_date TIMESTAMP NOT NULL,
    validation_type VARCHAR(50),
    status VARCHAR(20),
    issues JSONB,
    metadata JSONB,
    user_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dashboard cache table
CREATE TABLE dashboard_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    data_type VARCHAR(50),
    data JSONB,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_production_api12_date ON production_records(api12, production_date);
CREATE INDEX idx_production_date ON production_records(production_date);
CREATE INDEX idx_economic_api12 ON economic_metrics(api12);
CREATE INDEX idx_validation_api12 ON validation_results(api12);
CREATE INDEX idx_validation_date ON validation_results(validation_date);
CREATE INDEX idx_cache_expires ON dashboard_cache(expires_at);
CREATE INDEX idx_wells_field ON wells(field_name);
CREATE INDEX idx_wells_status ON wells(status);
```

## Data Migration Strategy

### From CSV/Excel to Database
1. Parse existing CSV files in `/data/modules/bsee/`
2. Transform data to match schema structure
3. Validate data integrity during migration
4. Create migration logs for audit trail

### Incremental Updates
1. Track last update timestamp
2. Process only new/modified records
3. Update cache tables
4. Maintain data versioning

## Performance Considerations

### Indexing Strategy
- Primary indexes on API12 for all tables
- Composite indexes for date-based queries
- JSON indexes for JSONB fields (PostgreSQL)

### Partitioning (for large datasets)
- Partition production_records by year
- Partition validation_results by month
- Archive old data after 5 years

### Caching Strategy
- Cache dashboard queries for 5 minutes
- Cache well lists for 1 hour
- Invalidate cache on data updates

## Data Retention Policy

- **Production Data**: Keep all historical data
- **Validation Results**: Keep for 2 years
- **Dashboard Cache**: Auto-expire after 1 hour
- **Audit Logs**: Keep for 5 years

## Backup Strategy

- Daily backups of all tables
- Weekly full backups
- Monthly archives to cold storage
- Test restore procedures quarterly