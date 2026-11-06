# Subsea equipment geometry investigation

The companion `subsea_equipment_observations.csv` records seven public-source
observations, three untranscribed research findings and six explicit gaps. The
observations support source discovery and preliminary stack-up investigation.
Suitability as engineering analysis inputs is NOT_EVALUATED: configuration,
assembly boundaries and mass basis require confirmation from drawings. No
universal geometry range is established.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| A | 2026-10-19 | Add source-specific completion-package observations and explicit geometry gaps to prevent unsupported stack-up inputs. |
| B | 2026-10-21 | Distinguish published but untranscribed research findings from source gaps and clarify component weight provenance. |
| C | 2026-11-05 | Preserve printed weight labels and assembly uncertainty; clarify search scope and validate observation metadata. |
| D | 2026-11-06 | Defer mixed-source weight units, remove weight-basis notes from dimensions, retain exact research-status coverage and identify field-specific validation failures. |
| E | 2026-11-06 | Defer the unresolved LMRP ton unit and preserve its printed weight basis; strengthen provenance and invalid-field checks and reflow the contract text. |
| F | 2026-11-06 | Identify URL, pending-value, confidence and range validation failures; cover invalid metadata for every status and reflow the investigation text. |

Revision C uses the local authoring date; its commit date is 2026-11-06 UTC.

## Dataset contract

The authoritative collection is maintained here with the riser component data.
The CSV is a separate observation table; it neither replaces the generic
`drilling_riser_components.csv` rows nor promotes those rows to sourced facts.
An observation ID identifies one parameter from one source. Equipment classes
use component, bore, pressure rating and generation; missing class attributes
are stated explicitly. Ram count is included for the requested BOP/LMRP search
scope and is not applicable to the completion packages. Classes are not keyed
to a deployment. Source-specific observations do not characterize every member
of a class.

`REPORTED` means the fact appears in the cited document, not that the input is
qualified for analysis. Confidence `A` means manufacturer-hosted literature.
`NOT_FOUND` means no value was established in the bounded pass, not that the
quantity is zero or absent from every public source. `NOT_TRANSCRIBED` means a
published finding is identified in the cited research record but its numeric
value is not entered here. That status is also used in `value`. For the
pending BOP and LMRP weight leads, `unit` is also `NOT_TRANSCRIBED`: the BOP
findings use different units and weight bases, and the LMRP ton type is unstated.
Pending height rows retain a requested target unit, which does not assert a
conversion or a source unit.
At transcription, create a separate row per source and basis, record its unit
as printed and retain the primary source URL; no force-to-mass conversion is
implied by a pending row. Existing observation IDs are retained for traceability;
a `-GAP` suffix does not override the row's current status. `NOT_EVALUATED` denotes
unestablished confidence or intended-use eligibility. `NOT_REPORTED` in `range`
means no range was supplied. `ft_in` preserves feet-and-inches text without
conversion. No equations, inferred constants, design limits or conversions are
used. Each row carries its public URL, document, locator and retrieval date.

## Sources and unresolved configuration

- [Trident-OVS Light Well Intervention System](https://www.trendsetterengineering.com/files/864/),
  H013638, June 2022, Equipment Specifications on page 2: EDP envelope and
  deployed weights. The kilogram figures are transcribed directly; the sheet's
  `T` unit is not interpreted. Deployed weight is not identified as dry or
  submerged. The LRP entry includes its connector.
- [Trident Modular Intervention System](https://www.trendsetterengineering.com/files/862/),
  undated, Specifications on page 2: EDP / LRP dimensions and weight.
  The sheet does not state whether the figures describe a combined assembly
  or each module. Its weight uses `weight_as_published`; only the OVS entries
  use `deployed_weight_as_published`. The dimensional axes are labelled.
  The relationship to the OVS configuration and the weight discrepancy are
  unresolved. Neither sheet supersedes the other in this table. Values shall
  not be combined into a synthetic assembly.
- [BSEE Well Information](https://www.data.bsee.gov/Main/Well.aspx),
  accessed 2026-10-19: the inspected index provides well-data and submission
  discovery. It does not itself establish equipment dimensions. The gap rows
  are investigation targets, not findings about all underlying filings.
  Their `source_url` records search scope rather than dimensional evidence.
  Manufacturer literature was not searched for these six gap components in
  this pass. The earlier research record cited below documents a prior
  manufacturer-literature search that found no riser-adapter height or
  tubing-hanger spool envelope. This is prior search evidence for
  `ADAPTER-HEIGHT-GAP` and `SPOOL-HEIGHT-GAP`, rather than a new search.
- [Research record #1140](https://api.github.com/repositories/574746314/issues/comments/6111983634),
  dated 2026-10-11 and accessed 2026-10-21: row 19 identifies combined-stack
  height; rows 1, 4 and 19 identify whole-stack weights; row 20 identifies an
  approximate separate LMRP weight in air. The BOP weight lead uses the
  basis-neutral `weight_as_published` parameter: the cited rows mix dry,
  submerged and unstated bases. Its `unit` remains `NOT_TRANSCRIBED` until
  each source unit and basis can be recorded separately as published.
  The LMRP lead also uses `weight_as_published` and unit `NOT_TRANSCRIBED`:
  its in-air basis is recorded, but the printed ton type remains unresolved.
  No ton-to-kilogram conversion is selected.
  These findings are NOT_TRANSCRIBED,
  not absent. Source units, dry/submerged basis, assembly boundaries and exact
  configurations require confirmation before transcription into analysis
  inputs. The source for row 1 carries a Restricted document label; no value or
  text from that sheet is added here. Future transcription of a finding from
  a Restricted-labelled source must retain its contractor public-page URL
  and Restricted note on each resulting row. The API URL identifies the dated
  comment directly; it does not constitute independent verification of the originals.
- [Earlier research record #1140](https://api.github.com/repositories/574746314/issues/comments/5810649761),
  dated 2026-09-24: component sums provide separate LMRP height estimate leads;
  the record also identifies flex-joint drag-diameter and stiffness-class
  leads. These are not independently qualified dimensions or stiffness inputs
  in this table. The LMRP height row remains NOT_FOUND for a directly sourced
  assembly dimension in this bounded pass; the component-sum lead is an
  estimate requiring confirmation of assembly boundaries and configuration.

Only individual attributed facts and links are retained; source PDFs, images
and substantial text are not redistributed. No reuse licence is asserted.
Source editions are recorded where printed; the modular sheet is undated.
Retrieval dates do not establish current manufacture or equipment availability.

## Coverage and next evidence

Coverage by water depth and equipment configuration is not quantified. No BSEE
filing census or APD/WAR schema audit has been completed in this dataset.
Combined BOP/LMRP height, whole-stack weights and approximate separate LMRP
weight are identified in the dated research record and remain NOT_TRANSCRIBED
in this dataset. Separate LMRP height, frame widths, paired dry and submerged
mass, flex-joint stiffness, riser-adapter height, SSTT, retainer-valve, THRT and
tubing-hanger spool envelopes remain unestablished by this pass. The CSV records
six selected height gaps as NOT_FOUND; this list also identifies parameters
beyond those rows. Derived hydrodynamic checks remain NOT_EVALUATED pending
sourced geometry and an applicable method.

Further collection will require manufacturer drawings with defined assembly
boundaries and exact configuration attributes. The separate completion-package
sheets require reconciliation before an analysis input can be selected. No
licensed-standard parameters or text are copied. API 16A, 16D, 16Q, 17G and
ISO 13628-7 scope metadata remain later collection work.

Related database work: [riser classes](https://github.com/vamseeachanta/worldenergydata/issues/1138)
and [component CSV alignment](https://github.com/vamseeachanta/worldenergydata/issues/1046).
Investigation scope: [subsea geometry](https://github.com/vamseeachanta/worldenergydata/issues/1140).
The downstream consumer is the `digitalmodel` riser stack-up drawing and
analysis basis; no automatic transfer into that consumer is introduced.
