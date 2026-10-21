# worldenergydata-cost

`cost` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.cost` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

For provenance-preserving project accounting, dated workbook comparisons and
grouped CAPEX estimation, see the
[portfolio cost model guide](../../docs/modules/cost/portfolio-cost-model.md).
Its generated worked example uses synthetic inputs and qualifies no real-project
estimate.
