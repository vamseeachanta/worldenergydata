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
uv sync --frozen --package worldenergydata --package worldenergydata-metocean --extra test --extra statistics
uv run --no-sync pytest tests/unit/metocean/statistics
```

The PR domain workflow installs this extra only in the metocean shard.

## Reanalysis calibration

`worldenergydata.metocean.calibration` provides delta change, EQM, QDM,
Hs-conditioned QDM, joint Hs–Tm02 diagnostics and contiguous time-block validation.
See the [calibration guide](src/worldenergydata/metocean/calibration/README.md)
for assumptions, citations, provenance and the opt-in published-data benchmark.
