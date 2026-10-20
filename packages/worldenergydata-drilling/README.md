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

Compatibility details: `well_id` accepts non-Boolean integers and finite integral
floats, normalized to decimal strings; rig and field keys still require text.
`fit_learning_curve(pd.DataFrame())` now raises `ValueError` for missing columns
rather than returning 0.85. An empty frame with `well_position` and `days_to_drill`
columns still returns the legacy default. Native numeric NaN values have
`missing_<column>` reasons; positive and negative infinity remain `nonfinite`.
