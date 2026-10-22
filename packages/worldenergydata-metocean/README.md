# worldenergydata-metocean

`metocean` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.metocean` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Reanalysis calibration

`worldenergydata.metocean.calibration` provides delta change, EQM, QDM,
Hs-conditioned QDM, joint Hs–Tm02 diagnostics and contiguous time-block validation.
See the [calibration guide](src/worldenergydata/metocean/calibration/README.md)
for assumptions, citations, provenance and the opt-in published-data benchmark.

## Backend contracts and examples

See the [optional backend guide](OPTIONAL_BACKENDS.md) for dependency integration
prerequisites, joint-model return contracts, contour methods, the two-dataset
adapter and an independently calculated synthetic example.
