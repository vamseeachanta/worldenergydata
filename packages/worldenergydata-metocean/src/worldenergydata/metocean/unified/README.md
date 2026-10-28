# Unified metocean queries

A location and inclusive UTC time interval return one attributed observation
table, source outcomes, and missing-parameter descriptors. Actual sample times
are retained; absent observations are not interpolated into apparent coverage.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Document request filtering, optional adapters and an offline example so partial coverage can be assessed. |

## Python interface

```python
from datetime import datetime
from worldenergydata.metocean.unified import MetoceanQuery, UnifiedMetoceanClient

query = MetoceanQuery(
    lat=28.5, lon=-88.5,
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 1, 2),
    parameters=("Hs", "wind_speed"),
)
result = UnifiedMetoceanClient().query(query)
print(result.source_status)
print(result.data)
```

The long table contains `timestamp`, `parameter`, `value`, `source`, and `unit`.
Naive input times mean UTC; offset-aware times are converted to UTC. Output
timestamps retain the existing naive-UTC schema. Both interval endpoints are
included; a date-only CLI end means midnight at the start of that date.
Only finite values with requested parameter names and matching native units
are retained. Adapter unit mismatches fail that source rather than relabel values.

`sources_used` lists contributors only. `source_status` distinguishes `OK`,
`EMPTY`, `FAILED` and `NOT_EVALUATED` for geographically selected sources.
Failures do not discard successful sources. Exception text is not included in
aggregation diagnostics because upstream errors can contain private information.

## Source selection and configuration

The regional selection boxes inherited from `coverage.py` are **assumed, based
on previous experience**; they are candidate-routing heuristics, not verified
station or dataset coverage limits. NDBC and CO-OPS use the nearest station
from the existing metadata clients. No station-distance acceptance limit is
assumed. The existing degree-space lookup does not establish representativeness.

| Source | Automatic behavior | Required configuration or limit |
| --- | --- | --- |
| NDBC | Regional station discovery and historical observations | Station availability determines data returned. |
| CO-OPS | Regional station discovery and requested currents/water levels | Both products are requested when selected; product failures are reported at source level. |
| MET Norway | Regional combined forecast | Forecast rows outside the requested interval are discarded; historical availability is not assumed. |
| Open-Meteo | Global candidate, existing historical marine method | Publisher time/model availability still applies. |
| ERDDAP | Global candidate | Explicit `erddap_dataset` and `erddap_bbox=(west,east,south,north)`; otherwise `NOT_EVALUATED`. Bounds crossing the date line require separate requests. |
| ERA5 | Global candidate | Explicit `source_fetchers["era5"]` adapter; otherwise `NOT_EVALUATED`. |
| CMEMS | Global candidate | Explicit `source_fetchers["cmems"]` adapter; otherwise `NOT_EVALUATED`. |

A configured source fetcher is a callable accepting `MetoceanQuery` and returning
the long-table schema above. The aggregation layer assigns its source label.
ERA5 and CMEMS integrations can call the existing `ERA5Client.retrieve` and
`CMEMSClient.subset` SDK wrappers, but dataset selection, authorized access and
file decoding belong to the callable. The SDK wrappers return dataset-specific
downloads, not interchangeable observation records. No default dataset,
credential, output path, spatial radius or conversion coefficient is invented.

Native units and parameter mappings follow the existing client dataclasses and
`PARAMETER_UNITS` in `unified_query.py`. These mappings retain existing wave-period
semantics; they do not certify equivalence of different providers' period
definitions. `coverage_gaps` detects entirely absent requested parameters only;
it is not an hourly completeness or quality assessment.

## CLI and visualization

```sh
wed metocean unified --lat 28.5 --lon -88.5 \
  --start 2023-01-01 --end 2023-01-02 --parameters Hs,wind_speed \
  --output combined.csv --dashboard combined.html
```

Use `--erddap-dataset` and `--erddap-bbox` to supply an ERDDAP selection.
The CLI prints per-source outcomes before summary statistics. The existing
Plotly dashboard provides attributed time series and source comparisons.
Its map markers denote the query location, not the measurement station.

## Reproducible offline worked example

```sh
python -m worldenergydata.metocean.unified.example "$OUTPUT_DIR"
```

Set `OUTPUT_DIR` to a scratch destination outside the repository. All providers
are replaced by explicit synthetic fetchers, so this example makes no network
requests. It exercises automatic routing at the repository's Gulf of Mexico
and North Sea coordinates; it does not establish live service availability.

Inputs are significant wave heights of 2.0, 4.0 and 6.0 m at midnight,
half an hour later, and the following midnight. The method is inclusive time
filtering followed by concatenation with each source's identity. Independent
hand calculation gives mean Hs = (2.0 + 4.0 + 6.0) / 3 = **4.0 m** for each
source. The Gulf selection has six sources and 18 rows; the North Sea selection
has five sources and 15 rows. CSV and interactive HTML files are written for
both locations. Tests assert those counts and the hand-calculated mean.

## Sources and remaining work

- [RFC 5870 (2010), sections 3.3 and 3.4.2](https://www.rfc-editor.org/rfc/rfc5870):
  latitude/longitude bounds. No physical constants or engineering equations
  are introduced by this aggregation change.
- Existing repository contracts: `clients/copernicus_clients.py` documents
  current SDK entry points and publisher setup references; native observation
  dataclasses document units and time fields; `coverage.py` supplies inherited
  routing assumptions; tests write out independent synthetic calculations.
- Follow-up: dataset-specific ERA5/CMEMS decoders with retained public fixtures,
  verified station-distance/coverage criteria, provider-specific period names,
  and temporal completeness checks. Live publisher calls and credentialed
  downloads are not covered by the offline tests.
