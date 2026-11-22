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

## Observed site climate

`build_site_climate_index` indexes seasonal wave observations by region,
station and registered source. The caller assigns regions and selects one
complete version of each observed archive file. For example, given an open
`ArchiveStore` named `store` and its `selected_entries`, run the following
from the repository root.

```python
import json
from pathlib import Path

from worldenergydata.metocean.site_climate import build_site_climate_index

metadata = json.loads(Path("data/modules/metocean/first_set.json").read_text("utf-8"))
rows = (row for entry in selected_entries for row in store.read_rows(entry))
index = build_site_climate_index(rows, {"42001": "west"}, station_metadata=metadata)
```

Each entry lists the sorted SHA-256 digests of its input files. Its seasonal
summaries separate peak and dominant periods. Coverage timestamps bound the
valid wave heights in UTC. Heights are in metres and periods in seconds.
An empty season has zero counts and null percentiles. Empty input yields an
empty entry list.

Distinct archive rows at a common timestamp count separately by default.
With `unique_timestamps=True`, the first sample with a valid height takes
precedence within each station and source. If all heights at that timestamp
are missing, the first sample is retained. Its paired periods stay with it.
Input order determines precedence, and the digest list includes all input
files considered. Region labels support station lookup without spatial
averaging. Readiness is `observations_only`. Design return periods require a
separate analysis.
