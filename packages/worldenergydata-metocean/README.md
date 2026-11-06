# worldenergydata-metocean

`metocean` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.metocean` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Unified queries

The [unified query guide](src/worldenergydata/metocean/unified/README.md)
describes attributed multi-source results, explicit source outcomes, the CLI,
optional dataset adapters and a reproducible offline worked example.

## Reanalysis calibration

`worldenergydata.metocean.calibration` provides delta change, EQM, QDM,
Hs-conditioned QDM, joint Hs–Tm02 diagnostics and contiguous time-block validation.
See the [calibration guide](src/worldenergydata/metocean/calibration/README.md)
for assumptions, citations, provenance and the opt-in published-data benchmark.
