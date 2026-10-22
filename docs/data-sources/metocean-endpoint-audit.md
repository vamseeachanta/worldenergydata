# Metocean endpoint audit and source access

The endpoint register describes anonymous access, account requirements and publisher terms for every source. Four small observation/forecast probes validate response structure, units and UTC timestamps. Availability does not establish completeness, reuse rights for every dataset, or engineering suitability.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-22 | Inventory access evidence, replay publisher responses and expose source-health diagnostics to identify unusable endpoints |

## Register and access

The packaged `data/source_register.json` is authoritative. `base_url` and `endpoints` identify request origins and path prefixes. An offline AST audit checks URL assignments in every client and the shared constants. Configurable ERDDAP servers need their own row before use in an audited workflow; registering an origin does not grant rights to all datasets on it.

`none` means the listed public service can be requested without registration. `account` also conservatively gates legacy rows whose anonymous access has not been confirmed; those rows carry `auth_evaluation=NOT_EVALUATED`. They are not advertised as confirmed account-only services. A terms link is an evidence locator, not a verified reuse grant. Existing disabled-source eligibility is preserved.

| Source | Base URL | Access | Endpoint documentation | Terms |
| --- | --- | --- | --- | --- |
| coops | https://api.tidesandcurrents.noaa.gov/api/prod | none | [documentation](https://api.tidesandcurrents.noaa.gov/api/prod/) | [terms](https://tidesandcurrents.noaa.gov/disclaimers.html) |
| met_norway | https://api.met.no/weatherapi | none | [documentation](https://api.met.no/weatherapi/oceanforecast/2.0/documentation) | [terms](https://docs.api.met.no/doc/TermsOfService.html) |
| irish_weather_buoys | https://erddap.marine.ie/erddap | none | [documentation](https://erddap.marine.ie/erddap/tabledap/IWBNetwork.graph) | [terms](https://erddap.marine.ie/erddap/tabledap/IWBNetwork.graph) |
| canada_gdwps | https://dd.weather.gc.ca | account (anonymous access unconfirmed) | [documentation](https://eccc-msc.github.io/open-data/msc-data/nwp_gdwps/readme_gdwps_en/) | [terms](https://eccc-msc.github.io/open-data/licence/readme_en/) |
| brazil_pnboia | https://www.marinha.mil.br/chm/dados-do-goos-brasil/pnboia | account (anonymous access unconfirmed) | [documentation](https://www.marinha.mil.br/chm/dados-do-goos-brasil/pnboia) | [terms](https://idem.marinha.mil.br/geonetwork/geonetwork/api/records/26de5378-8016-428e-83cb-993d745b5cdf) |
| australia_auswave | https://www.bom.gov.au | account | [documentation](https://www.bom.gov.au/nwp/doc/auswave/data.shtml) | [terms](https://www.bom.gov.au/copyright) |
| india_incois | https://incois.gov.in | account (anonymous access unconfirmed) | [documentation](https://incois.gov.in/site/dataholdings.jsp) | [terms](https://incois.gov.in/site/dataholdings.jsp) |
| indonesia_bmkg | https://maritim.bmkg.go.id | none | [documentation](https://maritim.bmkg.go.id/apidoc) | [terms](https://maritim.bmkg.go.id/apidoc) |
| pirata | https://www.pmel.noaa.gov/tao | account (anonymous access unconfirmed) | [documentation](https://www.pmel.noaa.gov/tao/data_deliv/deliv-nojava-pir.html) | [terms](https://www.pmel.noaa.gov/tao/data_deliv/deliv-nojava-pir.html) |
| ncep_wave_hindcast | https://www.emc.ncep.noaa.gov | account (anonymous access unconfirmed) | [documentation](https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/wavemodels.php) | [terms](https://www.weather.gov/disclaimer) |
| ndbc_archive | https://www.ndbc.noaa.gov | none | [documentation](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf) | [terms](https://www.weather.gov/disclaimer) |
| ndbc_realtime | https://www.ndbc.noaa.gov | none | [documentation](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf) | [terms](https://www.weather.gov/disclaimer) |
| ndbc_spectral | https://www.ndbc.noaa.gov | none | [documentation](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf) | [terms](https://www.weather.gov/disclaimer) |
| ndbc_stations | https://www.ndbc.noaa.gov | none | [documentation](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf) | [terms](https://www.weather.gov/disclaimer) |
| ndbc_currents | https://www.ndbc.noaa.gov | account (anonymous access unconfirmed) | [documentation](https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf) | [terms](https://www.ndbc.noaa.gov/data/realtime2/) |
| nhc_best_track | https://www.nhc.noaa.gov | account (anonymous access unconfirmed) | [documentation](https://www.nhc.noaa.gov/data/) | [terms](https://www.nhc.noaa.gov/data/) |
| open_meteo | https://marine-api.open-meteo.com | none | [documentation](https://open-meteo.com/en/docs/marine-weather-api) | [terms](https://open-meteo.com/en/terms) |
| erddap_ioos | https://erddap.ioos.us/erddap | none | [documentation](https://erddap.ioos.us/erddap/tabledap/documentation.html) | [terms](https://erddap.ioos.us/erddap/legal.html) |
| erddap_gcoos | https://erddap.gcoos.org/erddap | none | [documentation](https://erddap.gcoos.org/erddap/tabledap/documentation.html) | [terms](https://erddap.gcoos.org/erddap/legal.html) |
| erddap_coastwatch | https://coastwatch.pfeg.noaa.gov/erddap | none | [documentation](https://coastwatch.pfeg.noaa.gov/erddap/tabledap/documentation.html) | [terms](https://coastwatch.pfeg.noaa.gov/erddap/legal.html) |
| era5 | https://cds.climate.copernicus.eu/api | account | [documentation](https://cds.climate.copernicus.eu/en/how-to-api) | [terms](https://cds.climate.copernicus.eu/disclaimer-privacy) |
| cmems | https://stac.marine.copernicus.eu/metadata/catalog.stac.json | account | [documentation](https://help.marine.copernicus.eu/en/articles/8283072-copernicus-marine-toolbox-api-subset) | [terms](https://marine.copernicus.eu/user-corner/service-commitments-and-licence) |
| hycom | https://ncss.hycom.org/thredds/ncss | none | [documentation](https://www.hycom.org/dataserver) | [terms](https://www.hycom.org/dataserver) |

Documentation/terms requests were made on 2026-10-22; URL, UTC time, HTTP status and response digest are in [the evidence manifest](metocean-endpoint-evidence.json). Brazil's documentation request returned HTTP 403; its API/download access remains NOT_EVALUATED. Four explicit live data-schema checks and the two current Copernicus public-catalogue checks passed on 2026-10-22. Their exact requests, UTC times, HTTP statuses and decoded-response digests are retained in the same evidence manifest and register. An HTTP 200 documentation page is not a successful data probe. Legacy locations are inventory records, not supported parsers.

## Terms and traffic policy

- NOAA NDBC and CO-OPS: public-domain statements and exceptions are linked in the register. Check product disclaimers. Only small sample requests are made; systematic-request limits are NOT_EVALUATED.
- MET Norway: attribution under the linked CC BY 4.0 terms, an identifying User-Agent with contact information, caching and avoidance of unnecessary traffic are required. The operator supplies the User-Agent. No numeric traffic limit is assumed.
- Marine Institute: the buoy dataset metadata identifies CC BY 4.0. The recorded ERDDAP subset retains source values and units. Other ERDDAP servers have dataset-specific licences; consult dataset metadata as well as each server's legal page.
- Open-Meteo: free API access is for non-commercial use under its terms; commercial access requires a subscription. No inference of unrestricted commercial access is made.
- Other legacy regional sources: reuse permission, systematic access and rate limits remain NOT_EVALUATED unless the existing register evidence says otherwise. Disabled sources remain disabled.
- Every row has a `rate_limit` evidence locator. No unverified numeric request limit is enforced or promised. Probes make one request with no retry or redirect and use an operator-supplied timeout.

## CDS and Copernicus Marine

The [current CDS setup](https://cds.climate.copernicus.eu/en/how-to-api) specifies `https://cds.climate.copernicus.eu/api` and `cdsapi>=0.7.7`. The older `/api/v2` retirement date/status is **NOT_EVALUATED**: an accessible vendor retirement statement was not obtained. Requests use the currently documented endpoint. The supported `cdsapi` interface is retained; the separate advanced API package is optional according to that page.

The [Marine migration page](https://help.marine.copernicus.eu/en/articles/8612591-switching-from-old-to-new-services) states that legacy MOTU services no longer exist. Downloads use Copernicus Marine Toolbox. The public Marine STAC catalogue is metadata, not a download endpoint.

Install the domain distribution's optional extra, `worldenergydata-metocean[copernicus]`. The adapters require environment variables only: `CDSAPI_KEY`, or both `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD`. They do not fall back to stored credential files. CDS logging is quiet with debugging disabled; raised SDK diagnostics omit underlying exception text. Keep SDK debug logging disabled. No credential values belong in code, command arguments, fixtures or reports.

Both services require an account and the applicable dataset agreements. Credentialed tests are marked `network` and `credentialed`, and skipped unless `METOCEAN_CREDENTIAL_TESTS=1`, the required environment credentials and an operator-chosen tiny selection are present. CDS inputs are `METOCEAN_CDS_DATASET` and `METOCEAN_CDS_REQUEST` (JSON). Marine inputs are `METOCEAN_MARINE_DATASET` and `METOCEAN_MARINE_SELECTION` (JSON). Test downloads go to pytest's temporary directory. Authenticated retrieval, optional-SDK installation and output qualification are **NOT_EVALUATED** by the offline tests.

## Live and replay checks

Recorded samples are in `tests/fixtures/metocean/endpoints/`; their [provenance manifest](../../tests/fixtures/metocean/endpoints/provenance.json) records publisher, exact URL, HTTP status, UTC retrieval time, original response digest, retained sample digest and any row selection. NOAA samples are observations; the MET sample is a forecast. MET metadata and the first forecast entry were retained; all numerical values are unchanged. Marine Institute sample attribution: Marine Institute, Irish Weather Buoy Network, CC BY 4.0. MET sample attribution: MET Norway, CC BY 4.0; row selection is the recorded modification.

`parse_sample` exercises the existing clients' parsers. NDBC missing `MM` heights remain missing. CO-OPS JSON omits units and zone, so the probe validates `units=metric`, `time_zone=gmt`, `datum=MLLW` and the water-level product in the request before interpreting the response. Timestamps are returned as explicit UTC. MET's published `sea_surface_wave_height` and ERDDAP's `WaveHeight`/`Tp` are mapped explicitly.

Offline tests replay the same schema checks. Opt-in live tests cover NDBC realtime text, CO-OPS, Marine Institute ERDDAP and MET Norway; HTML, changed columns/units, non-UTC timestamps, empty samples and HTTP failures have negative controls. No arbitrary oceanographic plausibility threshold is introduced.

```sh
python -m pytest --noconftest -o addopts='' tests/unit/metocean/test_endpoint_samples.py
METOCEAN_LIVE_TESTS=1 METOCEAN_ENDPOINT_TIMEOUT="$REQUEST_TIMEOUT_SECONDS" \
  METOCEAN_USER_AGENT="$IDENTIFYING_USER_AGENT" \
  python -m pytest --noconftest -o addopts='' tests/unit/metocean/test_endpoint_live.py -m network
```

## Source-health report

`source_health` returns a list of rows and can write both JSON and a short Markdown snapshot. Reissuing to the same report files appends revision-history rows; earlier revision rows are preserved. Existing files that are not recognized reports are rejected before either output is rewritten. Inject an HTTP client to replay failures offline. Provide a timeout and identifying User-Agent for live use:

```python
from pathlib import Path
import httpx
from worldenergydata.metocean.source_health import source_health

with httpx.Client(timeout=request_timeout_seconds, trust_env=False) as http:
    table = source_health(
        http=http, user_agent=identifying_user_agent,
        json_path=Path("health.json"), markdown_path=Path("health.md"),
    )
```

Statuses are `OK`, `RETIRED`, `CREDENTIALS_REQUIRED` and `UNREACHABLE`. `OK` requires the supported sample schema, units and UTC checks. `RETIRED` means the checked URL returned HTTP 404/410: it may have moved; the status does not establish publisher-wide retirement. Authentication rejection is separate from retirement. Sources without a supported cheap probe are `UNREACHABLE` with **NOT_EVALUATED** detail and a null last-checked time. Account/key sources remain `CREDENTIALS_REQUIRED` without an authenticated request, even if local credentials exist. `last_checked` is the UTC start time of the report's request batch; null means no request was attempted. The report performs no SDK download.

HTTP classifications follow [RFC 9110 (2022)](https://www.rfc-editor.org/rfc/rfc9110.html), sections 15.3–15.6, and [RFC 6585 (2012)](https://www.rfc-editor.org/rfc/rfc6585.html), section 4. No physical equation, coefficient or engineering acceptance limit is used.

## Worked example: two station-days

Inputs: NDBC station `42001`, UTC date `2026-10-21`, and CO-OPS station `9414290`, UTC date `2025-01-01`, water level relative to MLLW in metres. These are deliberately different recorded dates, not a paired-station hydrodynamic comparison. The exact original requests are in the fixture provenance. NDBC's rolling realtime text contained the selected day; CO-OPS was requested for one full GMT day.

Method: fetch through `fetch_station_day`, select the requested UTC date, retain missing values, sort valid values chronologically, count received/nonmissing rows, and report the first and last valid value. There is no interpolation, averaging, extrapolation, joint analysis or completeness assertion. NDBC WVHT and CO-OPS datum-relative water level are distinct quantities.

```sh
python examples/metocean/endpoint_station_day.py
```

The default is offline replay through the same request-building API. The [committed CSV answer](../../examples/metocean/endpoint_station_day.csv) is reproduced by the example test:

| Source | Station | UTC day | Received rows | Nonmissing values | First valid UTC / value (m) | Last valid UTC / value (m) |
| --- | --- | --- | --- | --- | --- | --- |
| NDBC WVHT | 42001 | 2026-10-21 | 144 | 69 | 00:10 / 1.8 | 23:50 / 0.9 |
| CO-OPS MLLW water level | 9414290 | 2025-01-01 | 240 | 240 | 00:00 / 0.035 | 23:54 / 0.355 |

Expected values are literal fixture rows, independently transcribed into test docstrings. NDBC has 144 retained data lines, 75 marked `MM` for height, leaving 69 numerical heights. CO-OPS has 240 rows at six-minute spacing: `24 × 60 / 6 = 240`. These are descriptions of the supplied records, not universal acceptance counts. CO-OPS source precision is preserved.

For a live example, pass `--live`, `--user-agent`, `--timeout`, `--ndbc-day` and `--coops-day`. Choose an NDBC day still present in the realtime file. An absent day raises an explicit error; use the separate archive workflow for older NDBC years. `--output` writes CSV to a caller-selected file.

## Known limits and later work

The register covers more sources than the four supported data probes. Unprobed legacy sources, unrestricted reuse rights, numeric traffic limits, CDS legacy retirement confirmation, authenticated downloads, installed SDK interoperability and engineering suitability remain **NOT_EVALUATED**. Current catalogue checks do not validate account credentials. The health report is a point-in-time diagnostic and performs no automatic retries or bulk requests. External review remains required before merge.
