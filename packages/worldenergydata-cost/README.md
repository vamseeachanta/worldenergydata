# worldenergydata-cost

`cost` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.cost` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

Annual disclosure revisions use optional immutable metadata and append-only parent
links. Current and history selectors preserve original evidence while annual views
carry the selected version. See the [revision contract and worked example](../../docs/modules/cost/disclosure-revisions.html).
