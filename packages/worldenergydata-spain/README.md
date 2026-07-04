# worldenergydata-spain

Spain CORES source package for per-field monthly oil and gas production.

The initial [#763](https://github.com/vamseeachanta/worldenergydata/issues/763)
slice covers the official CORES statistical-series workbooks for indigenous
crude oil and natural gas production. CORES publishes oil in tonnes and gas in
GWh, so this package exposes documented conversion constants and loader rows
normalized for the unified production adapter.

## CORES live refresh

[#806](https://github.com/vamseeachanta/worldenergydata/issues/806) adds a
direct-source live refresh lane for the official CORES workbooks:

- statistics page: <https://www.cores.es/en/estadisticas>
- crude oil workbook: <https://www.cores.es/sites/default/files/archivos/estadisticas/crude-oil-production.xlsx>
- natural gas workbook: <https://www.cores.es/sites/default/files/archivos/estadisticas/gas-production.xlsx>

The live loader reads the `Production` worksheet explicitly because the real
CORES files include a non-data `Start` sheet before the production data.

Library code accepts a caller-supplied cache root; the operational target is:

```text
/mnt/ace/worldenergydata/data/spain/cores/
  raw/
  normalized/
  metadata/
```

Example:

```python
from pathlib import Path

from worldenergydata.spain.production import CoresLiveProductionLoader

loader = CoresLiveProductionLoader(
    cache_root=Path("/mnt/ace/worldenergydata/data/spain/cores")
)
loader.refresh(force_refresh=True)
production = loader.load_all_production()
```

Full normalized oil, gas, and merged production CSVs are written under the
cache root. The committed Ayoluengo fixture stays small and can be refreshed
from the live oil frame with `refresh_ayoluengo_fixture`.
