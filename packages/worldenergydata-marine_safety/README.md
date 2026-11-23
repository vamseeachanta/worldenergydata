# worldenergydata-marine_safety

`marine_safety` domain of the **worldenergydata** namespace, carved out as a
uv workspace member (ADR 0001 Phase 2 — domain-package split, batch 4, #529).

Importable transparently as `worldenergydata.marine_safety` once the workspace
is installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for
the shared `worldenergydata.common` layer.

Curated/runtime datasets live at the workspace-root `data/modules/marine_safety/`
and are resolved at runtime via `worldenergydata.common.data_resolver`
(`WED_DATA_ROOT` or the workspace-root `data/` directory) — they are not shipped
in this wheel.
