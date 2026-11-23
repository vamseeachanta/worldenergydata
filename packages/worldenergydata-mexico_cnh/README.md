# worldenergydata-mexico_cnh

`mexico_cnh` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.mexico_cnh` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

Production ingestion can use the public SENER workbook without Selenium.
`BulkProductionClient` discovers and retains raw XLSX bytes with a digest receipt;
`SenerProductionAdapter` normalizes observed monthly volumes and checks FDAS
input completeness. Fiscal economics and concept screening remain explicitly
`NOT_EVALUATED` when their required inputs are missing.

See [method, sources and worked example](../../docs/data/mexico-production-chain.html)
and [runnable example](../../examples/mexico_cnh/production_chain.py).
