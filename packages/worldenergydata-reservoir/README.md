# worldenergydata-reservoir

`reservoir` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

Importable transparently as `worldenergydata.reservoir` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

The resource estimation API supports constant, uniform, triangular and normal
inputs, validated oil volumetrics, interpolated P90/P50/P10 exceedance estimates
and sensitivity results for tornado charts. See the
[method and worked example](../../docs/analysis-guides/probabilistic-resource-estimation.md)
for units, sources, reproducibility and limits on reserves classification.
