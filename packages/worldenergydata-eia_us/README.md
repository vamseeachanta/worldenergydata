# worldenergydata-eia_us

`eia_us` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.eia_us` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

Independent arithmetic examples, source revisions, units and the explicit
zero-reference comparison contract are documented in
[Production benchmarks](docs/production-benchmarks.md).
