# Plan: Issue #268 — Implement metocean adapter (Open-Meteo API)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/268
**Status:** plan-review
**Tier:** T3 (new adapter implementation)
**Prerequisite:** #271 (output_dir wiring)

## Plan

### Task 1 — Read current stub
`src/worldenergydata/scheduler/jobs/metocean_refresh.py` — understand current scaffold.
`src/worldenergydata/modules/metocean/` — understand existing module structure.

### Task 2 — Add Open-Meteo client
`src/worldenergydata/modules/metocean/clients/open_meteo.py`:
```python
class OpenMeteoClient:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def fetch(self, lat: float, lon: float, variables: list[str]) -> dict:
        # GET request with hourly wind_speed_10m, wave_height, etc.
        # Returns parsed JSON
```
No API key required. Rate limit: free tier, 10K calls/day.

### Task 3 — Wire into job
Update `metocean_refresh.py`:
- For each configured location, call `OpenMeteoClient.fetch()`
- Write results to `output_dir` as `metocean_YYYYMMDD_{lat}_{lon}.json`
- Return `JobResult(status="completed", records=N)`

### Task 4 — Add unit tests with mocked HTTP
`tests/unit/metocean/test_open_meteo_client.py`:
- Mock `requests.get` returning fixture JSON
- Assert `fetch()` returns expected structure
- Assert job writes correct output files

### Task 5 — Run bounded live fetch
```bash
uv run python -m worldenergydata.scheduler run-job metocean_refresh \
  --config config/scheduler/scheduler_config.yml --max-records 5
```

## Acceptance Criteria
- `metocean_refresh` job writes real data (not stub 2 records)
- `data/modules/metocean/` contains at least one timestamped JSON output
- Unit tests mock HTTP and pass
