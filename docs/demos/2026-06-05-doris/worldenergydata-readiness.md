# Doris demo prep - worldenergydata readiness

Assessment date: 2026-05-28  
Demo date: 2026-06-05  
Audience fit: Doris Group offshore/subsea operator and engineering users.

Source-of-truth module inventory: `MODULE_INDEX.md` and `module-manifest.yaml`.

Smoke environment used:

```bash
PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python ...
```

`uv run` was attempted first, but this sandbox could not initialize the default uv cache under `/home/vamsee/.cache/uv` because that path is read-only. The same smoke commands were rerun with the repository virtualenv. For a normal shell, use `UV_CACHE_DIR=/tmp/uv-cache uv run ...` if uv hits the same cache issue.

## Readiness matrix

| Module | Status | Demo artifact | Fit for Doris | Command |
|---|---:|---|---|---|
| `bsee` | GREEN | `notebooks/quickstart_bsee.py`; `data/modules/bsee/current/wells/well_data.csv`; `data/modules/bsee/current/production/production.csv` | Best lead: real Gulf of Mexico well inventory, operators, water depth, spud activity, and production sample. | `PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_bsee.py` |
| `sodir` | RED | `notebooks/quickstart_sodir.py`; `src/worldenergydata/sodir/api_client.py` | Norway is high-fit, but current runnable path is not demo-ready. Quickstart masks a stale import and direct live fetch returns SODIR 400 Invalid URL. | `PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_sodir.py`; direct API probe using `SodirAPIClient('https://factmaps.sodir.no')` |
| `ukcs` | AMBER | `tests/unit/ukcs/test_field_production.py`; `tests/unit/ukcs/test_field_economics.py`; `src/worldenergydata/scheduler/jobs/ukcs_refresh.py` | UKCS is relevant, but checked path is test/sample logic only; scheduler adapter is explicitly a stub. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/ukcs/test_field_production.py tests/unit/ukcs/test_field_economics.py` |
| `brazil_anp` | AMBER | `tests/unit/brazil_anp/test_field_production.py`; `tests/unit/brazil_anp/test_field_economics.py`; `src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py` | Brazil pre-salt is relevant, but current smoke is model/test logic; scheduler adapter is a stub with no cached demo dataset. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/brazil_anp/test_field_production.py tests/unit/brazil_anp/test_field_economics.py` |
| `mexico_cnh` | AMBER | `tests/unit/mexico_cnh/test_validators.py`; `tests/unit/mexico_cnh/data/test_mexico_cnh_data.py` | Mexico GOM fit is strong, but live value depends on SIH/Selenium scraping or prepared exports. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/mexico_cnh/test_validators.py tests/unit/mexico_cnh/data/test_mexico_cnh_data.py` |
| `eia_us` | AMBER | `tests/unit/eia_us/test_state_production.py`; `tests/unit/eia_us/test_basin_production.py`; `tests/unit/eia_us/test_alaska_production.py` | Useful US context, but live API path needs EIA setup/key and no cached production demo was found. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/eia_us/test_state_production.py tests/unit/eia_us/test_basin_production.py tests/unit/eia_us/test_alaska_production.py` |
| `lower_tertiary` | GREEN | `/tmp/doris-lower-tertiary.csv`; `/tmp/doris-lower-tertiary.html`; `config/analysis/lower_tertiary/fields/` | Strong offshore economics story: 10 GoM Lower Tertiary fields, portfolio economics, capex, and HTML-ready output. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m worldenergydata lower-tertiary portfolio-economics --output-csv /tmp/doris-lower-tertiary.csv --output-html /tmp/doris-lower-tertiary.html` |
| `metocean` | GREEN | `src/worldenergydata/metocean/clients/open_meteo_client.py`; live Open-Meteo forecast output | Strong subsea engineering fit: no-key Gulf of Mexico wave, wind-wave, and current forecast query returned 24 hourly records. Avoid statistics/weather-window path until `metocean_stats` is installed. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY' ... OpenMeteoClient().fetch_forecast(28.5, -88.5, forecast_days=1) ... PY` |
| `fdas` | GREEN | `notebooks/quickstart_fdas.py`; `examples/fdas_complete_workflow.py`; CLI NPV table | Strong decision-support slice: NPV, IRR, MIRR, payback, sensitivity, cashflow waterfall. | `PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_fdas.py` |
| `vessel_fleet` | GREEN | `data/modules/vessel_fleet/curated/construction_vessels.csv`; `data/modules/vessel_fleet/curated/drilling_riser_components.csv` | Good offshore construction/riser equipment support story for subsea installation planning. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY' ... pandas read_csv vessel_fleet curated files ... PY` |
| `vessel_hull_models` | GREEN | `data/modules/vessel_hull_models/hulls/sea_cypress.obj`; `tests/unit/vessel_hull_models/test_plotly_3d.py` | Good visual/engineering asset: OBJ hull parsed successfully with 13,536 vertices and 17,720 faces. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY' ... OBJParser().parse('data/modules/vessel_hull_models/hulls/sea_cypress.obj') ... PY` |
| `well_production_dashboard` | AMBER | `/tmp/doris-well-dashboard.json`; `src/worldenergydata/well_production_dashboard/cli.py`; `tests/unit/well_production_dashboard/test_field_aggregation.py` | Dashboard concept fits Doris, but current CLI output is placeholder zeros and logs verification/index initialization problems. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m worldenergydata.well_production_dashboard.cli analyze API001 --output /tmp/doris-well-dashboard.json` |
| `hse` | GREEN | `data/modules/hse/hse_incidents.db`; `tests/unit/hse/test_bsee_hse_db_import.py` | Good safety add-on: local DB has 97,993 HSE incidents, 51,487 toxic-release rows, and 66,561 violation rows. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/hse/test_bsee_hse_db_import.py tests/unit/hse/importers/test_data_quality_validators.py` |
| `pipeline_safety` | GREEN | `data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv`; `tests/unit/pipeline_safety/` | Useful secondary safety context: 2,795 pipeline incident rows available locally. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY' ... pandas read_csv('data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv') ... PY` |
| `marine_safety` | GREEN | `notebooks/quickstart_marine_safety.py`; `data/modules/marine_safety/input/*.csv`; `examples/marine_safety/reports/*.html` | Good offshore/marine safety side story: curated fatality, foundering, and hatch datasets plus prebuilt HTML reports. | `PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_marine_safety.py` |
| `safety_analysis` | AMBER | `src/worldenergydata/safety_analysis/risk_index/scorer.py`; `tests/unit/safety_analysis/risk_index/test_scorer.py` | Useful ML/risk toolkit, but demo smoke used synthetic records; needs a real HSE/pipeline/marine adapter demo dataset for buyer-facing use. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/safety_analysis/risk_index/test_scorer.py tests/unit/safety_analysis/test_classification_pipeline.py` |
| `canada` | AMBER | `tests/unit/canada/common/test_uwi_parser.py`; `tests/unit/canada/test_canada.py` | Secondary regional context only; parser and clients test, but no live/cached Canadian production demo dataset was found. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/canada/common/test_uwi_parser.py tests/unit/canada/test_canada.py` |
| `texas_rrc` | AMBER | `tests/unit/texas_rrc/test_validators.py`; `src/worldenergydata/texas_rrc/` | Secondary onshore context; validators pass, but no cached Texas production demo dataset was found. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/texas_rrc/test_validators.py` |
| `lng_terminals` | GREEN | `data/modules/lng_terminals/reports/lng_terminals_list.html`; `src/worldenergydata/lng_terminals/query.py` | Good infrastructure add-on: in-memory global LNG terminal query returned 8 North America export terminals totaling 121.8 MTPA. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY' ... LngTerminalClient().query(LngTerminalQuery(region=['north_america'], terminal_type=['export'])) ... PY` |
| `landman` | AMBER | `tests/unit/landman/test_landman.py`; `src/worldenergydata/landman/` | Low fit for Doris offshore/subsea demo; tests pass, but no buyer-ready offshore artifact was found. | `PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/landman/test_landman.py` |

## Suggested demo order

1. `bsee` GoM production and well inventory: start with real offshore data, operator counts, water-depth distribution, and a production sample.
2. `metocean` Gulf of Mexico design conditions: live Open-Meteo wave/wind/current query for a GoM coordinate; keep it operational and engineering-focused.
3. `fdas` economics: show NPV, IRR, MIRR, payback, and sensitivity using `notebooks/quickstart_fdas.py`.
4. `lower_tertiary` portfolio economics: show the 10-field GoM portfolio CSV/HTML output and total capex summary.
5. `vessel_fleet` and `vessel_hull_models`: pivot from reservoir/production economics into subsea construction assets, riser components, and hull geometry.
6. Safety add-on if time allows: `hse`, `marine_safety`, and `pipeline_safety` have real local datasets and make a credible risk/safety appendix.
7. Hold or mention as roadmap: `sodir`, `ukcs`, `brazil_anp`, `mexico_cnh`, `eia_us`, `well_production_dashboard`, `safety_analysis`, `canada`, `texas_rrc`, and `landman`.

## Per-module notes

### `bsee` - GREEN

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_bsee.py
```

Observed output: loaded 57,281 well records with 19 columns; production sample has 100 records. The notebook renders water-depth, operator, spud-year, and depth-class plots under Agg.

Artifact paths:

- `notebooks/quickstart_bsee.py`
- `data/modules/bsee/current/wells/well_data.csv`
- `data/modules/bsee/current/production/production.csv`

### `sodir` - RED

Smoke commands:

```bash
PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_sodir.py
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.endpoints import SODIR_ENDPOINTS
client = SodirAPIClient('https://factmaps.sodir.no', timeout=10)
cfg = SODIR_ENDPOINTS['fields']
print(client.get(cfg['endpoint'], params={'table': cfg['table_id']}))
PY
```

Observed output: quickstart initialized the client but skipped live fetch because `SodirDatasets` cannot be imported from `worldenergydata.sodir.datasets`; direct API probe retried and failed with SODIR 400 `Invalid URL`.

Artifact paths:

- `notebooks/quickstart_sodir.py`
- `src/worldenergydata/sodir/datasets.py`
- `src/worldenergydata/sodir/endpoints.py`

### `ukcs` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/ukcs/test_field_production.py tests/unit/ukcs/test_field_economics.py
```

Observed output: 46 passed in 2.79s. Scheduler adapter says Tier 2 stub and returns `skipped`.

Artifact paths:

- `tests/unit/ukcs/test_field_production.py`
- `tests/unit/ukcs/test_field_economics.py`
- `src/worldenergydata/scheduler/jobs/ukcs_refresh.py`

### `brazil_anp` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/brazil_anp/test_field_production.py tests/unit/brazil_anp/test_field_economics.py
```

Observed output: 30 passed in 2.81s. Scheduler adapter says Tier 2 stub and returns `skipped`.

Artifact paths:

- `tests/unit/brazil_anp/test_field_production.py`
- `tests/unit/brazil_anp/test_field_economics.py`
- `src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py`

### `mexico_cnh` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/mexico_cnh/test_validators.py tests/unit/mexico_cnh/data/test_mexico_cnh_data.py
```

Observed output: 100 passed in 3.09s. Live SIH scraping is not quick-demo safe without Selenium/browser setup and known export flow.

Artifact paths:

- `tests/unit/mexico_cnh/test_validators.py`
- `tests/unit/mexico_cnh/data/test_mexico_cnh_data.py`
- `src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py`

### `eia_us` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/eia_us/test_state_production.py tests/unit/eia_us/test_basin_production.py tests/unit/eia_us/test_alaska_production.py
```

Observed output: 49 passed in 2.60s. Live EIA demo needs API setup/key or pre-cached query output.

Artifact paths:

- `tests/unit/eia_us/test_state_production.py`
- `tests/unit/eia_us/test_basin_production.py`
- `tests/unit/eia_us/test_alaska_production.py`

### `lower_tertiary` - GREEN

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m worldenergydata lower-tertiary portfolio-economics --output-csv /tmp/doris-lower-tertiary.csv --output-html /tmp/doris-lower-tertiary.html
```

Observed output: wrote CSV and HTML; analyzed 10 fields; total cumulative capex reported as $55,500 M.

Artifact paths:

- `/tmp/doris-lower-tertiary.csv`
- `/tmp/doris-lower-tertiary.html`
- `config/analysis/lower_tertiary/fields/`

### `metocean` - GREEN

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
from worldenergydata.metocean.clients.open_meteo_client import OpenMeteoClient
with OpenMeteoClient() as client:
    result = client.fetch_forecast(28.5, -88.5, forecast_days=1)
print(f"records={result.records_count} source={result.source.value}")
for row in result.data[:3]:
    print(row.forecast_time.isoformat(), row.wave_height_m, row.wind_wave_height_m, row.current_speed_ms)
PY
```

Observed output: 24 Open-Meteo forecast records for GoM coordinate 28.5, -88.5; first rows included wave height, wind-wave height, and current speed. Client/unit converter tests also passed: 60 passed in 4.49s.

Artifact paths:

- `src/worldenergydata/metocean/clients/open_meteo_client.py`
- `tests/unit/metocean/test_clients.py`
- `tests/unit/metocean/test_unit_converter.py`

Caveat: `tests/unit/metocean/statistics/test_scatter_diagram.py` and `test_weather_windows.py` fail collection without `metocean_stats`; avoid that statistics path for the demo.

### `fdas` - GREEN

Smoke commands:

```bash
PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_fdas.py
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/fdas/test_financial.py tests/unit/fdas/integration/test_end_to_end.py tests/modules/fdas/integration/test_end_to_end.py
```

Observed output: notebook printed NPV, IRR, MIRR, payback, scenario comparison, and charts. Tests: 57 passed in 25.86s.

Artifact paths:

- `notebooks/quickstart_fdas.py`
- `examples/fdas_complete_workflow.py`
- `docs/modules/fdas/USER-GUIDE.md`

### `vessel_fleet` - GREEN

Smoke commands:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
import pandas as pd
print(pd.read_csv('data/modules/vessel_fleet/curated/construction_vessels.csv').head(5).to_string(index=False))
print(pd.read_csv('data/modules/vessel_fleet/curated/drilling_riser_components.csv').head(5).to_string(index=False))
PY
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/vessel_fleet/test_storage_csv.py tests/unit/vessel_fleet/test_storage_parquet.py tests/unit/vessel_fleet/test_rig_fleet_bridge.py
```

Observed output: construction vessels include Sleipnir, Thialf, Balder, Aegir, and Pioneering Spirit; riser component rows print cleanly. Combined vessel/hull test batch: 72 passed in 8.53s.

Artifact paths:

- `data/modules/vessel_fleet/curated/construction_vessels.csv`
- `data/modules/vessel_fleet/curated/drilling_riser_components.csv`

### `vessel_hull_models` - GREEN

Smoke commands:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
from pathlib import Path
from worldenergydata.vessel_hull_models.geometry.obj_parser import OBJParser
path = Path('data/modules/vessel_hull_models/hulls/sea_cypress.obj')
mesh = OBJParser().parse(path)
print(mesh.get_stats())
PY
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/vessel_hull_models/test_plotly_3d.py tests/unit/vessel_hull_models/geometry/test_obj_parser.py
```

Observed output: `sea_cypress.obj` parsed with 13,536 vertices, 17,720 faces, and dimensions around 22.95 x 4.28 x 8.57 model units.

Artifact paths:

- `data/modules/vessel_hull_models/hulls/sea_cypress.obj`
- `data/modules/vessel_hull_models/INVENTORY.md`
- `tests/unit/vessel_hull_models/test_plotly_3d.py`

### `well_production_dashboard` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m worldenergydata.well_production_dashboard.cli analyze API001 --output /tmp/doris-well-dashboard.json
```

Observed output: command exited and wrote `/tmp/doris-well-dashboard.json`, but logs included query index and verification initialization problems, and visible metrics were placeholder zeros. Tests: field aggregation path passed; dashboard test file is skipped because referenced modules do not exist.

Artifact paths:

- `/tmp/doris-well-dashboard.json`
- `src/worldenergydata/well_production_dashboard/cli.py`
- `tests/unit/well_production_dashboard/test_field_aggregation.py`

### `hse` - GREEN

Smoke commands:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/hse/test_bsee_hse_db_import.py tests/unit/hse/importers/test_data_quality_validators.py
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect('data/modules/hse/hse_incidents.db')
for name in [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]:
    print(name, con.execute(f'select count(*) from {name}').fetchone()[0])
PY
```

Observed output: 54 passed in 5.68s. Local DB row counts include 97,993 `hse_incidents`, 51,487 `toxic_releases`, and 66,561 `violation_incidents`.

Artifact paths:

- `data/modules/hse/hse_incidents.db`
- `tests/unit/hse/test_bsee_hse_db_import.py`

### `pipeline_safety` - GREEN

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
import pandas as pd
df = pd.read_csv('data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv')
print(f'rows={len(df)} cols={len(df.columns)}')
print(df.head(3).to_string(index=False))
PY
```

Observed output: 2,795 rows and 48 columns loaded from the local incident CSV. Pipeline-safety pytest cases also passed before the combined secondary batch reached unrelated marine-safety fixture errors.

Artifact paths:

- `data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/database.csv`
- `tests/unit/pipeline_safety/`

### `marine_safety` - GREEN

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python notebooks/quickstart_marine_safety.py
```

Observed output: loaded 20 fatality incidents, 15 foundering incidents, and 30 hatch incidents; foundering fatality total was 38. Prebuilt HTML reports exist under `examples/marine_safety/reports/`.

Artifact paths:

- `notebooks/quickstart_marine_safety.py`
- `data/modules/marine_safety/input/fatality_incidents.csv`
- `data/modules/marine_safety/input/foundering_incidents.csv`
- `data/modules/marine_safety/input/hatch_incidents.csv`
- `examples/marine_safety/reports/full_cause_analysis_report.html`

### `safety_analysis` - AMBER

Smoke commands:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/safety_analysis/risk_index/test_scorer.py tests/unit/safety_analysis/test_classification_pipeline.py
```

Observed output: 41 passed, 1 skipped, 20 warnings in 8.93s for risk scorer and classification pipeline. A broader loader batch had errors/timeouts. A direct synthetic risk-score probe produced two scores (`DRILL` critical, `LIFT` high), but that is not yet a real buyer-facing dataset.

Artifact paths:

- `src/worldenergydata/safety_analysis/risk_index/scorer.py`
- `tests/unit/safety_analysis/risk_index/test_scorer.py`

### `canada` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/canada/common/test_uwi_parser.py tests/unit/canada/test_canada.py
```

Observed output: included in secondary batch with Canada, Texas RRC, LNG, and Landman: 180 passed in 5.15s. No cached Canadian production demo dataset was found.

Artifact paths:

- `tests/unit/canada/common/test_uwi_parser.py`
- `tests/unit/canada/test_canada.py`

### `texas_rrc` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/texas_rrc/test_validators.py
```

Observed output: included in secondary batch with Canada, Texas RRC, LNG, and Landman: 180 passed in 5.15s. No cached Texas production demo dataset was found.

Artifact paths:

- `tests/unit/texas_rrc/test_validators.py`
- `src/worldenergydata/texas_rrc/`

### `lng_terminals` - GREEN

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python - <<'PY'
from worldenergydata.lng_terminals.query import LngTerminalClient, LngTerminalQuery
client = LngTerminalClient()
res = client.query(LngTerminalQuery(region=['north_america'], terminal_type=['export']))
print(f'terminals={res.total_count} capacity_mtpa={res.total_capacity_mtpa}')
print(res.data[['terminal_name','country','capacity_mtpa','operator']].head(5).to_string(index=False))
PY
```

Observed output: 8 North America export terminals with 121.8 MTPA total capacity; first rows include Sabine Pass, Freeport, Cove Point, Cameron, and Corpus Christi LNG.

Artifact paths:

- `data/modules/lng_terminals/reports/lng_terminals_list.html`
- `src/worldenergydata/lng_terminals/query.py`

### `landman` - AMBER

Smoke command:

```bash
PYTHONPATH='src:../assetutilities/src' MPLCONFIGDIR=/tmp/mplcfg .venv/bin/python -m pytest --noconftest -q tests/unit/landman/test_landman.py
```

Observed output: included in secondary batch with Canada, Texas RRC, LNG, and Landman: 180 passed in 5.15s. No Doris-relevant offshore demo artifact was found.

Artifact paths:

- `tests/unit/landman/test_landman.py`
- `src/worldenergydata/landman/`

## Totals

- GREEN: 10 modules
- AMBER: 9 modules
- RED: 1 module

Strongest 3 for Doris:

1. `bsee` - real Gulf of Mexico offshore production/well context.
2. `metocean` - live no-key GoM wave/wind/current forecast query for engineering context.
3. `fdas` plus `lower_tertiary` - economics story with runnable NPV/IRR/cashflow and 10-field GoM portfolio output.
