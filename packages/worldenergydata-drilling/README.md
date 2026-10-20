# worldenergydata-drilling

`drilling` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

Importable transparently as `worldenergydata.drilling` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

The [detector contract](src/worldenergydata/drilling/docs/detector-contracts.md)
defines per-row reconciliation, numeric/date parsing, calendar-month windows,
and learning-fit dispositions, with an executable worked example. Diagnostic
entry points retain rejection, duplicate, default and clipping evidence; the
existing DataFrame and scalar entry points remain available.
