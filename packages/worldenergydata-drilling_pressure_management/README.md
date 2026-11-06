# worldenergydata-drilling_pressure_management

`drilling_pressure_management` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.drilling_pressure_management` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Explicit annular pressure loss

`PressureWindowAnalyzer.analyze` requires `annular_pressure_drop_psi` in psi.
Calls that omit it raise `TypeError`. Callers must supply a measured or separately
calculated loss, including an explicit zero when no loss applies to the case.
Unknown loss is a missing input. The accepted `flow_rate_gpm` argument does not
calculate annular friction. Explicit positional and keyword loss arguments retain
their order and meaning.

The [SLB Energy Glossary entry for equivalent circulating density](https://glossary.slb.com/en/terms/e/equivalent_circulating_density)
(undated) identifies annular pressure drop as an input to ECD. This API change
introduces no physical coefficient or acceptance limit. The existing hydrostatic
coefficients and MPD threshold are not qualified by this change. ECD position in
the pressure window and multi-mode system filtering remain open under #1290.
The knowledge pack records behavior at its historical code pin.
