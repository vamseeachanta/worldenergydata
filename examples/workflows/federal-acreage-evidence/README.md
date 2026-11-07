# Federal acreage evidence — synthetic pilot

Run `uv run python -m worldenergydata examples/workflows/federal-acreage-evidence/input.yml`.
The workflow writes a self-contained HTML report and a JSON twin from the same
validated result. No live data is downloaded. The fixture is authored synthetic
data distributed under the repository licence (MIT), with a fixed retrieval date
and licence note in its `SourceRef`; it contains no live records or title evidence.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Source the pilot arithmetic and mark unlocated leases and parcel-only lease status ambiguous to prevent unsupported lease conclusions. |

## Inputs and method

The fictional tract uses the New Mexico Principal Meridian naming convention;
it does not establish a pilot jurisdiction or represent a real prospect.
The model covers one section with exactly 40 acres per quarter-quarter. Lots,
irregular surveys and multi-section geometry require a subsequent extension.

The nominal cell area follows BLM, *Specifications for Descriptions of Land*
(revised 2017), chapter II, printed pages 8–9
([public source](https://www.blm.gov/sites/default/files/SpecificationsForDescriptionsOfLand.pdf)).
The pilot fixes nominal cells at 40 acres; this does not establish surveyed area.
The section-number range follows the same chapter.

The hectare conversion uses the international acre, not the survey-foot acre:
NIST *Handbook 44* (2026), Appendix C, **Units of Area**
([public source](https://www.nist.gov/document/2026-nist-handbook-44-appendix-c))
gives 1 acre = 0.40468564224 hectares exactly. The implementation uses its
rounded reciprocal. The existing fixture's 0.5-acre discrepancy tolerance is a
synthetic demonstration policy, not a statutory or survey acceptance limit.
Live use requires validation of the acre definition, actual surveyed areas,
record completeness and a justified tolerance; these are not established here.

Intersection uses tract-cell / record-cell set intersection; coverage and lease
buckets use set unions, so duplicate claims cannot inflate acreage. Missing
record coverage is gross area minus the located coverage union; it does not
establish private land or absence of an unlocated federal record.

## Worked answer

Hand-derived acreage: eight tract cells give 320 acres. R1 covers four cells,
R2 two, R5 one, and R6 repeats one R1 cell. The coverage union has seven cells
(280 acres), the active lease union five (200 acres), expired leases two
(80 acres), and the uncovered cell one (40 acres). R3 is outside the tract;
R4 has missing geometry. R5's 16.1874 hectares divided by the cited hectares-per-acre factor
rounds to 40.0 acres, within the pilot tolerance. R6 emits a 40-acre overlap exception.

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

## Explicit evidence gaps

A lease with null or empty cell geometry may intersect any tract cell. Its
presence therefore makes both lease-split totals ambiguous while preserving
located coverage. An intersecting parcel record also leaves the lease split
ambiguous: public-land geometry alone does not establish nonleased acreage.
These cases add visible exceptions and cannot produce `evidence_complete`.

Independent test calculations: a located cell gives 40 acres; eight tract cells
give 320 acres, so 280 acres lack located records. A second unlocated lease
prevents determination of the leased union. An active and an expired lease
claiming the same cell yield a 40-acre coverage union and an ambiguous split.
The regression docstrings write out these calculations independently.

The existing six-record demonstration remains 320 acres gross, 280 acres located
coverage, 200 acres supported active leases, 80 acres expired leases and 40 acres
without located records. Its unlocated record is a parcel, not a lease; its
geometry and county/title coverage remain explicit gaps.

Live MLRS acquisition remains with issue 913. Arbitrary polygons, irregular lots,
county title chains and a verified jurisdiction choice remain later slices.
