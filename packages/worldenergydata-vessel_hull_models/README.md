# worldenergydata-vessel_hull_models

`vessel_hull_models` domain of the **worldenergydata** namespace, carved out as
a uv workspace member (ADR 0001 Phase 2 — domain-package split, batch 4, #529).

Importable transparently as `worldenergydata.vessel_hull_models` once the
workspace is installed (`uv sync --all-extras`). Depends on
`worldenergydata-core` for the shared `worldenergydata.common` layer, and on
`worldenergydata-vessel_fleet` for the curated drilling-rig dataset that the
rig-hull loader enriches.

## Data relocation choice — option (ii) (data stays at a shared root)

The curated geometry dataset (hull `.obj` meshes, marine components) is ~38 MB
of binary data. Shipping that inside the wheel is unreasonable, so — unlike the
`vessel_fleet` / `lng_terminals` members (option (i)) — the data is NOT moved
into the package. It stays at the workspace-root
`data/modules/vessel_hull_models/` and is resolved at runtime via
`worldenergydata.common.data_resolver` (`WED_DATA_ROOT`, or the workspace-root
`data/` directory). No unit test depends on the 38 MB data — they all inject
temporary fixtures — so the test suite passes without it present.
