# worldenergydata-metocean

`metocean` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.metocean` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Statistics extra

Statistical analysis uses the optional, pinned `metocean-stats==1.2.0` backend.
Install it with `uv sync --package worldenergydata-metocean --extra statistics`.
For repository tests, retain the root test tooling as well:

```sh
uv sync --frozen --package worldenergydata --package worldenergydata-metocean --all-extras
uv run --no-sync pytest tests/unit/metocean/statistics
```

The PR metocean shard explicitly installs the member extras and requires statistics
test collection. BSEE screening depends on this statistics extra, so root installs
(including the full CI matrix on Python 3.10–3.12) also install the backend.
Metocean-only installs can omit it. CI sets `WED_REQUIRE_METOCEAN_STATS=1` so a
missing backend fails collection instead of silently excluding statistics tests.

## Reanalysis calibration

`worldenergydata.metocean.calibration` provides delta change, EQM, QDM,
Hs-conditioned QDM, joint Hs–Tm02 diagnostics and contiguous time-block validation.
See the [calibration guide](src/worldenergydata/metocean/calibration/README.md)
for assumptions, citations, provenance and the opt-in published-data benchmark.
