# worldenergydata-economics

`economics` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.economics` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.


Valuation uses the canonical `worldenergydata-fdas` dependency. Annual schedule
accounting lives in `worldenergydata.economics.cash_flow`; pass
`schedule.net_cashflows()` to `worldenergydata.fdas.core.financial.calculate_npv`
with `period="annual"`. The former `economics.dcf` module and result DTOs have
been removed. See [calculation bases and migration](../../docs/architecture/economics-views.md)
and [the offline worked example](../../examples/economics_views.py).
