# Field-development standards provenance

This register separates publication metadata from applicability to the implemented
methods. All engineering conformity checks remain **NOT_EVALUATED**, and U1 in the
knowledge pack remains **UNVERIFIED**. The
[machine-readable register](standards-provenance.json) records the evidence and
missing qualification for each claim. It is an offline documentation inventory;
it does not emit result citations or authorize engineering use.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Record publication evidence separately from applicability so an identified reference cannot imply conformity. |

## Evidence and applicability

| Implementation | Evidence in hand | Applicability and citation sidecars |
| --- | --- | --- |
| `flow_assurance.py`, `screen_erosion_risk` | Pack section 3, E1 and S1; `flow_assurance_types.py`, `FlowAssuranceThresholds`. The earlier API attribution has already been removed. | Configurable liquid-velocity heuristic. No standards derivation is established for the limit or tier ratios. No API edition, title or clause has been verified; no standards citation should be inferred from the continuity calculation. |
| `dexpi.py`, XML adapter | The [DEXPI publisher index](https://dexpi.org/specifications/), heading “DEXPI P&ID Specification 1.4”, confirms that publication title and version. | Structural interoperability subset with local extension attributes. Governing edition and clauses remain unselected. The local `dexpi-aligned-1.0` marker is not a published DEXPI version. Round-trip tests do not validate an external schema or receiving tool. This is not a numeric calculation sidecar. |
| `dexpi.py`, ISO reference | The module explicitly disclaims full ISO conformity. The briefing section B4, Feature 9, gives only a family-level background reference. | No governing ISO part, edition, publication title or clause is verified. The [candidate ISO catalog page](https://www.iso.org/standard/29556.html) returned HTTP 403; its identity was not confirmed. This is not a numeric calculation sidecar. |
| `symbols/__init__.py`, style reference | Original schematic artwork; module docstring says style only. The briefing section B3 names ANSI/ISA-5.1-2024. | The [briefing's ANSI reference](https://blog.ansi.org/ansi/ansi-isa-5-1-2024-instrumentation-symbols/) returned HTTP 403. A [candidate ISA product page](https://www.isa.org/products/ansi-isa-5-1-2024-instrumentation-and-control-symbols) returned HTTP 404. No title, edition or clause is independently verified. This is not a numeric calculation sidecar. |

The public pages were checked on 2026-10-19. Metadata verification is limited to
the DEXPI index heading; specification contents were not reviewed. That index
also distinguishes newer DEXPI XML serialization from the earlier Proteus XML
approach. Selecting the newest specification automatically would not qualify
this Proteus-shaped adapter. No licensed text, artwork or acceptance values are
reproduced here.

## Slice boundary and verification

This first slice adds no equation, coefficient, numeric acceptance limit or
runtime behavior. Existing hydraulic equations and configured screening values
are outside this metadata review. Their presence in the pack does not establish
independent validation or standards provenance.

`test_standards_provenance.py` checks offline that the requested claims remain
explicitly unresolved, verified metadata has an open publisher locator,
unverified bibliography fields remain empty, code evidence resolves, and sidecar
applicability distinguishes heuristics from nonnumeric references. Expected
categories come from the code evidence and source locators above, rather than
calculations performed by the implementation. These are documentation contract
tests, not engineering validation or live link checks.

Later slices should select and inspect authorized editions and clauses, validate
the DEXPI adapter against the selected schema, qualify symbol mappings and
screening inputs, and integrate eligible numeric output citations through #361.
Missing evidence must remain explicit until that work is reviewed. No result
sidecar schema or resolver is introduced by this slice.
