# OpenLane artifact replay report

## Summary

No flow was executed by this reporter. PRESENT means a file was read;
REPORTED means a finite numeric value was read from the selected metrics key.
Neither status establishes correctness, timing closure, DRC/LVS signoff or manufacturability.
Missing evidence is NOT_EVALUATED; no acceptance limits are assumed.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Add evidence replay before collecting run evidence. |

## Recorded environment

Values are supplied by the manifest; tool execution and provenance authenticity are not verified.

| Field | Recorded value |
| --- | --- |
| openlane_version | NOT_EVALUATED |
| container_image_digest | NOT_EVALUATED |
| pdk_revision | NOT_EVALUATED |
| standard_cell_library | NOT_EVALUATED |

## Metrics

Units, corner and analysis assumptions must be checked against the selected tool output.
Values are copied without conversion or rounding; no numerical assessment is performed.

| Category | Status | Value | Evidence key and basis |
| --- | --- | --- | --- |
| Timing | NOT_EVALUATED | unavailable | metric selection or evidence not supplied |
| Area | NOT_EVALUATED | unavailable | metric selection or evidence not supplied |
| Power | NOT_EVALUATED | unavailable | metric selection or evidence not supplied |
| DRC | NOT_EVALUATED | unavailable | metric selection or evidence not supplied |
| LVS | NOT_EVALUATED | unavailable | metric selection or evidence not supplied |

## Artifact inventory and role keywords

SHA-256 covers the artifact bytes as read; a supplied digest mismatch stops replay.
File presence does not validate the artifact format or contents.

| Artifact | Status | Relative path | SHA-256 | Semiconductor role keywords |
| --- | --- | --- | --- | --- |
| rtl | NOT_EVALUATED | not supplied | unavailable | RTL design and logic synthesis |
| config | NOT_EVALUATED | not supplied | unavailable | Flow configuration and timing constraints |
| metrics | NOT_EVALUATED | not supplied | unavailable | Final metrics and reproducible data extraction |
| timing | NOT_EVALUATED | not supplied | unavailable | Static timing analysis and timing closure |
| power | NOT_EVALUATED | not supplied | unavailable | Power analysis and activity assumptions |
| drc | NOT_EVALUATED | not supplied | unavailable | Design rule checking and physical verification |
| lvs | NOT_EVALUATED | not supplied | unavailable | Layout versus schematic and connectivity verification |
| def | NOT_EVALUATED | not supplied | unavailable | Placement, routing and physical implementation |
| gds | NOT_EVALUATED | not supplied | unavailable | Mask layout and layout exchange |
| log | NOT_EVALUATED | not supplied | unavailable | Flow debugging and execution traceability |

## Interpretation and next steps

- Timing: inspect setup/hold corners, constraints and unconstrained paths before claiming closure.
- Area: identify the metric scope; cell area, core area and die area describe different quantities.
- Power: record corner, activity assumptions and whether the result is estimated or measured.
- DRC/LVS: inspect the respective reports and tool completion; missing results never imply clean checks.
- DEF/GDS: retain physical views and logs with the resolved configuration and PDK revision.

## Sources

- [OpenLane Newcomers](https://openlane2.readthedocs.io/en/latest/getting_started/newcomers/index.html):
  Run directory, Final Results and Signoff Steps
  (rolling documentation, retrieved 2026-10-19).
- [Python hashlib: SHA-256 and Usage](https://docs.python.org/3/library/hashlib.html#usage)
  (Python 3 documentation, retrieved 2026-10-19).
