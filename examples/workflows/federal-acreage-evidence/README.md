# Federal acreage evidence — synthetic pilot

Run `uv run python -m worldenergydata examples/workflows/federal-acreage-evidence/input.yml`.
The workflow writes a self-contained HTML report and a JSON twin from the same
validated result. No live data is downloaded. The fixture is authored synthetic
data distributed under the repository licence (MIT), with a fixed retrieval date
and licence note in its `SourceRef`; it contains no live records or title evidence.

The fictional tract uses the New Mexico Principal Meridian naming convention;
it does not establish a pilot jurisdiction or represent a real prospect.
The model covers one section with exactly 40 acres per quarter-quarter. Lots,
irregular surveys and multi-section geometry require a subsequent extension.

Hand-derived acreage: eight tract cells give 320 acres. R1 covers four cells,
R2 two, R5 one, and R6 repeats one R1 cell. The coverage union has seven cells
(280 acres), the active lease union five (200 acres), expired leases two
(80 acres), and the uncovered cell one (40 acres). R3 is outside the tract;
R4 has missing geometry. R5's 16.1874 hectares converts to 39.999937 acres,
within the 0.5-acre tolerance. R6 emits a 40-acre overlap exception.

The result is `evidence_partial`: three exceptions and 40 acres without records.
Every numerical acreage value carries provenance. No-record acreage is derived
from tract gross area minus federal-record coverage, rather than a federal-record
value; its source names both inputs. Unknown lease status or
conflicting units produce explicit ambiguity markers rather than a fabricated
split. No usable intersecting records produces `evidence_blocked`.

Federal land records are not evidence of title. County recorder / title-chain
records were NOT evaluated. This gap is always displayed separately in both
outputs. The FIXTURE-DATA banner identifies the synthetic source.

The provider protocol will permit the live MLRS provider from
[issue 913](https://github.com/vamseeachanta/worldenergydata/issues/913) to replace
fixture acquisition without changing the evidence or report contracts.
