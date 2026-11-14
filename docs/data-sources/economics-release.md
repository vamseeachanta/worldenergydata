# Explorer economics release decision

The committed economics can be released as explicitly labelled life-to-date
values for records already marked `surfaced`. Every other status remains
withheld, including records whose stale inputs still contain numbers. This
decision covers export preparation and the repository's Field Atlas display;
it does not record a new external publication or a full-cycle valuation.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Document the conditional release and enforce withholding at export and display boundaries. |

## Basis and sources

The reviewed release contract in #976 resolves the diagnosis in #971:
these are life-to-date, pre-tax values at the existing discount rate, with sunk
capital charged against production to date. A negative NPV is possible even
when undiscounted net cashflow is positive. No new price, reserve-fraction,
discount-rate or positivity acceptance limit is introduced here.

The authoritative inputs are:

- [Performance contract](../../reports/lower_tertiary/lifecycle/_performance.json):
  the release status, basis, nullable economics and reserve provenance.
- [Explorer bundle](../../reports/field-atlas/results/explorer_results_bundle.json):
  the economics carried to public consumers.
- [Sensitivity snapshot](../../reports/lower_tertiary/parametric/lt_economics_parametric.json):
  the independent grid snapshot and recorded baseline matches.
- [Report builder](../../scripts/lower_tertiary/generate_field_economics_report.py):
  the existing affine price-sensitivity derivation.
- [OpenStax, Principles of Finance (2022), section 16.2, equation 16.1](https://openstax.org/books/principles-finance/pages/16-2-net-present-value-npv-method):
  NPV is present-value inflows minus present-value outflows.

The independent synthetic test example has an immediate capital outflow of
100 monetary units and two units of output sold at price `p`. With immediate
receipts, `NPV(p) = -100 + 2p`; at `p = 40`, NPV is `-20`; at `p = 60`,
NPV is `20`; breakeven is `100 / 2 = 50`; sensitivity is `2`.
These are hand calculations, not output from the implementation under test.
They check preservation of signed values and suppression, rather than a
production forecast or a discounted model implementation.

## Evidence and release policy

The offline propagation test compares each exported economics level with the
committed performance contract and each contract record with the Explorer
bundle. It also compares the sensitivity snapshot's recorded baseline NPV with
the surfaced performance NPV. The current snapshots agree. This establishes
propagation of the reviewed correction, not independent validation of the cost
model or reserves.

The release boundaries enforce the following rules:

- Field levels require `economics_status == surfaced`, the known life-to-date
  basis and finite numeric NPV, breakeven and sensitivity. A surfaced record
  with an unsupported basis or invalid levels stops export preparation.
- All other statuses suppress every economics level, even if populated.
  Missing fields and future unknown statuses cannot grant release.
- Sensitivity rows require permission in both the current performance
  contract and the sensitivity snapshot. A historical grid cannot override
  current withholding. Empty grids retain their table schema.
- The Field Atlas uses the same status, basis and numeric requirements, labels
  the life-to-date basis and links suppressed values to its release-gate note.
- Dataset-card generation explains these conditions. The withholding note
  remains applicable to suppressed records; a blanket removal would be false.

## Known limits and way forward

Full-cycle NPV, full-cycle breakeven, independent financial plausibility and
current external dataset contents are **NOT_EVALUATED** by this change.
The existing reserve and early-life policy is inherited without a new
financial acceptance claim. No source production data or valuation is changed.

External dataset publication and the separate website's `capabilities.yaml`
remain follow-up work. That registry must preserve its `status: withheld`
guard and exclude withheld columns from `highlight_columns` and rendered
output. Local row-level `surfaced` status does not override registry-level
withholding or authorize changing it. A publishing review must pin the final
dataset revision and check the separate website gate before changing that
registry entry. Refs #978.
