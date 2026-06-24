# worldenergydata-vessel_fleet

`vessel_fleet` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 4, #529).

Importable transparently as `worldenergydata.vessel_fleet` once the workspace
is installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for
the shared `worldenergydata.common` layer.

## Data relocation (option (i) — data travels with the package)

The curated dataset (construction vessels, drilling rigs, riser components;
~0.7 MB) ships INSIDE this member at `worldenergydata/vessel_fleet/_data/` and
is resolved package-relative by the loaders and `FleetRouter`. This makes the
domain self-contained — no repo-root or external data mount is required — and
the data ships in the built wheel.
