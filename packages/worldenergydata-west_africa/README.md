# worldenergydata-west_africa

`west_africa` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.west_africa` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

See [production and fiscal correctness](src/worldenergydata/west_africa/docs/correctness.md)
for supported report layouts, explicit rate units, failure behavior and a worked
cash-allocation example. Legacy fiscal assumptions remain NOT_EVALUATED for
statutory applicability.
