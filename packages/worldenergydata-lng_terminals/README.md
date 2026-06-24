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
