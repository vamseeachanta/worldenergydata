# worldenergydata-lng_terminals

`lng_terminals` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 4, #529).

Importable transparently as `worldenergydata.lng_terminals` once the workspace
is installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for
the shared `worldenergydata.common` layer.

## Data relocation (option (i) — data travels with the package)

The curated seed dataset, collector caches, and the optional `lng_terminals.yml`
config override (~0.2 MB total) ship INSIDE this member at
`worldenergydata/lng_terminals/_data/` and are resolved package-relative by
`config.py`. The domain is self-contained — no repo-root or external data mount
is required — and the data ships in the built wheel.

## Collector capacity and cache safety

Empty refreshes preserve cached records and success metadata. GIE throughput
requires explicit units and a referenced conversion basis; unknown capacity
remains unset with a warning. See the [capacity basis guide](../../docs/modules/lng/capacity_basis.md)
for the input contract, sources and a worked example.
