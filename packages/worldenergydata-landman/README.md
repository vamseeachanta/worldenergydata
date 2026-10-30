# worldenergydata-landman

`landman` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.landman` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

Recorder access and title-chain feasibility metadata are available through
`worldenergydata.landman.recorder_coverage`. See the
[county recorder coverage guide](../../docs/data-sources/onshore/county-recorder-coverage.md)
and the [offline example](../../examples/landman/recorder_coverage.py).
The catalog performs no record acquisition and makes no title-completeness claim.
