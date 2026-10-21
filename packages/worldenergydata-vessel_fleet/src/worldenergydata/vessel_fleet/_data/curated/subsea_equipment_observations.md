# Subsea equipment geometry investigation

The companion `subsea_equipment_observations.csv` records seven public-source
observations, three untranscribed research findings and six explicit gaps. The
observations support source discovery and preliminary stack-up investigation.
Suitability as engineering analysis
inputs is NOT_EVALUATED: configuration, assembly boundaries and mass basis
require confirmation from drawings. No universal geometry range is established.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| A | 2026-10-19 | Add source-specific completion-package observations and explicit geometry gaps to prevent unsupported stack-up inputs. |
| B | 2026-10-21 | Distinguish published but untranscribed research findings from source gaps and clarify component weight provenance. |

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
value is not entered here. That status is also used in `value`; the `unit`
remains the requested target unit and does not assert a conversion or a source
unit. Existing observation IDs are retained for traceability; a `-GAP` suffix
does not override the row's current status. `NOT_EVALUATED` denotes
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
  undated, Specifications on page 2: combined package dimensions and weight.
  The dimensional axes are labelled. The relationship to the OVS configuration
  and the weight discrepancy are unresolved. Neither sheet supersedes the
  other in this table. Values shall not be combined into a synthetic assembly.
- [BSEE Well Information](https://www.data.bsee.gov/Main/Well.aspx),
  accessed 2026-10-19: the inspected index provides well-data and submission
  discovery. It does not itself establish equipment dimensions. The gap rows
  are investigation targets, not findings about all underlying filings.
- [Research record #1140](https://api.github.com/repositories/574746314/issues/comments/6111983634),
  dated 2026-10-11 and accessed 2026-10-21: row 19 identifies combined-stack
  height; rows 1, 4 and 19 identify whole-stack weights; row 20 identifies an
  approximate separate LMRP weight in air. These findings are NOT_TRANSCRIBED,
  not absent. Source units, dry/submerged basis, assembly boundaries and exact
  configurations require confirmation before transcription into analysis
  inputs. The source for row 1 carries a Restricted document label; no value or
  text from that sheet is added here. The API URL identifies the dated comment
  directly; it does not constitute independent verification of the originals.

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
