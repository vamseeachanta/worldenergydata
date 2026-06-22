# worldenergydata Module Index

Auto-generated 2026-02-20. Source: `module-manifest.yaml` (WRK-252).
Total modules indexed: **27** (18 data-source + 7 infrastructure + 2 analysis/visualization).

---

## Production Data Modules (9 regional sources)

| Module | Region | Key Data Types | Status |
|--------|--------|---------------|--------|
| `bsee` | Gulf of Mexico, USA | wellbore, production, casing, drilling, completions, paleowells | stable |
| `sodir` | Norwegian Continental Shelf | wellbore, production, fields, discoveries, surveys, blocks | stable |
| `ukcs` | UK Continental Shelf, North Sea | production, wells, completions, field economics | stable |
| `brazil_anp` | Brazil (pre-salt, Santos, Campos) | production, wells, fiscal regimes | stable |
| `mexico_cnh` | Mexico / GOM Mexican Waters | production, wells, fields, blocks, contracts | stable |
| `canada` | Alberta, BC, Saskatchewan, Manitoba | wellbore, production, permits | stable |
| `texas_rrc` | Texas, USA | production, wellbore, drilling permits | stable |
| `eia_us` | United States, Alaska | production, drilling productivity, basin analysis | stable |
| `lower_tertiary` | Gulf of Mexico | field economics, NPV, production forecast | stable |

## Safety and Regulatory Modules

| Module | Region | Key Data Types | Status |
|--------|--------|---------------|--------|
| `hse` | Gulf of Mexico, USA | HSE incidents, injuries, spills, violations, penalties | stable |
| `pipeline_safety` | United States | pipeline incidents, gas distribution/transmission, hazardous liquid | stable |
| `marine_safety` | Global (USCG, MAIB, NTSB, TSB) | marine incidents, casualties, investigations, trends | stable |
| `safety_analysis` | Global | safety observations, incident classification, risk scores | stable |

## Economics and Financial Modules

| Module | Region | Key Data Types | Status |
|--------|--------|---------------|--------|
| `fdas` | Gulf of Mexico | NPV, MIRR, IRR, cashflow, development systems | stable |

## Environment and Metocean Modules

| Module | Region | Key Data Types | Status |
|--------|--------|---------------|--------|
| `metocean` | Global, Gulf of Mexico | wave, wind, current, tidal, temperature, forecasts | stable |

## Infrastructure and Asset Modules

| Module | Region | Key Data Types | Status |
|--------|--------|---------------|--------|
| `lng_terminals` | Global | terminal locations, capacities, infrastructure | beta |
| `subsea` | Global | manifold suppliers (key players), mooring components, rigid jumper specs | stable |
| `vessel_fleet` | Global | construction vessels, drilling risers, BOP equipment | stable |
| `vessel_hull_models` | Global | hull geometry (OBJ), rig hulls | stable |
| `well_production_dashboard` | Gulf of Mexico | interactive dashboards, well metrics, field aggregation | stable |
| `landman` | United States | mineral ownership, lease records, BLM claims, well records | stable |

## Infrastructure Modules (shared utilities)

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `production` | Unified cross-regional production query | `UnifiedProductionClient`, `ProductionQuery` |
| `common` | Shared utilities — logging, settings, exceptions, units | `get_logger`, `Settings`, `EnergyUnits`, `ValidationError` |
| `validation` | Data validation framework | `DataValidator`, `ValidationSchema`, `ValidationRules` |
| `scheduler` | Automated data refresh orchestrator (WRK-076) | `DataScheduler`, `SchedulerConfig` |
| `reporting` | Report generation templates and utilities | HTML/Excel/JSON templates |
| `analysis` | Placeholder (migrated to `lower_tertiary`) | — |
| `testing` | Shared test utilities and fixtures | cleanup, data, performance helpers |

---

## Agent Quick Reference

### Query available regions
```python
from worldenergydata.production import UnifiedProductionClient
client = UnifiedProductionClient()
result = client.query(ProductionQuery(regions=["ncs", "gom", "brazil", "ukcs"]))
```

### Fetch BSEE Gulf of Mexico data
```python
from worldenergydata.bsee import bsee, BSEEData, BlockRouter
# Route by block number
cfg = {"data": {"block": "759"}}
result_cfg = bsee.router(cfg)
```

### Fetch Norwegian shelf data
```python
from worldenergydata.sodir import Sodir
s = Sodir()
```

### Fetch UK shelf data
```python
from worldenergydata.ukcs import ...
```

### Fetch EIA US production data
```python
from worldenergydata.eia_us import ...
```

### Fetch Brazil ANP data
```python
from worldenergydata.brazil_anp import ...
```

### Fetch Mexico CNH data
```python
from worldenergydata.mexico_cnh import MexicoCNH
cnh = MexicoCNH()
```

### Fetch Canada AER/BCER data
```python
from worldenergydata.canada import AERClient, BCERClient, UWIParser
parser = UWIParser()
uwi = parser.parse("100.16-09-010-09W4.00")
```

### Fetch metocean / environmental data
```python
from worldenergydata.metocean import NDBCClient, COOPSClient, OpenMeteoClient
client = NDBCClient()
```

### Run HSE / safety analysis
```python
from worldenergydata.hse import BSEEIncidentsImporter, DataQualityValidator
from worldenergydata.safety_analysis import SafetyDataLoader, RiskScorer
```

### Run field economics
```python
from worldenergydata.fdas import calculate_npv, calculate_all_metrics
results = calculate_all_metrics(cashflows, discount_rate=0.10)
```

### Get shared logger / config
```python
from worldenergydata.common import get_logger, get_settings
logger = get_logger(__name__)
settings = get_settings()
```

---

## Scheduler Status

Modules wired into the WRK-076 automated refresh scheduler:

| Module | Scheduler Job | Authority |
|--------|--------------|-----------|
| `bsee` | `bsee_refresh` | `config/scheduler/scheduler_config.yml` |
| `sodir` | `sodir_refresh` | `config/scheduler/scheduler_config.yml` |
| `ukcs` | `ukcs_refresh` | `config/scheduler/scheduler_config.yml` |
| `brazil_anp` | `brazil_anp_refresh` | `config/scheduler/scheduler_config.yml` |
| `eia_us` | `eia_us_refresh` | `config/scheduler/scheduler_config.yml` |
| `metocean` | `metocean_refresh` | `config/scheduler/scheduler_config.yml` |
| `lng_terminals` | `lng_terminals_refresh` | `config/scheduler/scheduler_config.yml` |

Config-only, no active scheduler job (config present but not wired):
`texas_rrc` (config/texas_rrc.yml), `mexico_cnh` (config/mexico_cnh.yml)

Not yet scheduled:
`canada`, `hse`, `marine_safety`, `pipeline_safety`
