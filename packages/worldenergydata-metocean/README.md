# worldenergydata-metocean

`metocean` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.metocean` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Optional metocean-api dependency

The LGPL `metocean-api` library is available through a single optional extra:

```sh
pip install 'worldenergydata[metocean-api]'
# Or install the domain distribution directly:
pip install 'worldenergydata-metocean[metocean-api]'
# Or enable the extra in the uv workspace:
uv sync --extra metocean-api
```

Default installations do not request this library. The workspace setup command
`uv sync --all-extras` and CI jobs using it select this extra on Python 3.11 and
newer, including its geospatial and NetCDF dependency stack.

The root extra forwards to
the domain extra, which pins the inspected
[metocean-api release](https://pypi.org/project/metocean-api/1.1.14/).
The optional library requires Python 3.11 or newer. Its requirement is ignored on
Python 3.10, preserving the distributions' declared Python >=3.10 range.
That release's wheel includes the LGPL license in its distribution metadata.
Its transitive dependencies include geospatial and NetCDF packages; platform
availability must be checked before installing the extra.

This slice supplies the dependency boundary only. It does not provide a dataset
adapter or restrict direct upstream calls. The planned adapter will cover NORA3
and NorKyst800 only. Cached sample retrieval tests and corrections to the external
tool skill examples remain follow-up work. No live retrieval is validated here.

## Reanalysis calibration

`worldenergydata.metocean.calibration` provides delta change, EQM, QDM,
Hs-conditioned QDM, joint Hs–Tm02 diagnostics and contiguous time-block validation.
See the [calibration guide](src/worldenergydata/metocean/calibration/README.md)
for assumptions, citations, provenance and the opt-in published-data benchmark.
