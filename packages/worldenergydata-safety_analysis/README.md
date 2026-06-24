# worldenergydata-safety_analysis

`safety_analysis` domain of the **worldenergydata** namespace, carved out as a
uv workspace member (ADR 0001 Phase 2 — domain-package split, batch 4, #529).

Importable transparently as `worldenergydata.safety_analysis` once the
workspace is installed (`uv sync --all-extras`). Depends on
`worldenergydata-core` for the shared `worldenergydata.common` layer.

The ML/BERT stacks are optional — install via the `safety-ml` / `safety-bert`
extras.
