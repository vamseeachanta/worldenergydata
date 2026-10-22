# Texas RRC production district labels

The supported production CSV district labels are `01`, `02`, `03`, `04`,
`05`, `06`, `6E`, `7B`, `7C`, `08`, `8A`, `09`, and `10`.
`6E` is a distinct production label; it must not be combined with `06`.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Qualify the production labels against RRC PDQ and preserve special labels and unassigned volumes through CSV routing. |

## Qualified reference and intended use

The authoritative source is the Railroad Commission of Texas
[Production Data Query: General Production Query](https://webapps.rrc.texas.gov/PDQ/generalReportAction.do),
Geographic Region, District selector. Its displayed labels were read on
2026-10-21 (HTTP 200). The page has no publication or revision date;
the retrieval date is an observation date, not a claimed source edition.
The [General Query help, Geographic Region](https://webapps.rrc.texas.gov/PDQ/help/prod_general_about.html#glo_georegion)
(undated; read 2026-10-21, HTTP 200) identifies this selector as a geographic
filter for production information. These references qualify the labels for
local production CSVs whose `district` column contains PDQ display labels.

`6E`, `7B`, `7C`, and `8A` are all present. `6E` is the only label missing
from the previous configured set. The reference establishes membership;
it does not establish county counts, administrative headquarters, or the
meaning of the suffix. Those metadata for `6E` remain unknown (`None`).

The selector also contains `Statewide` and `None Selected`; these are query
controls, not record district codes. Its HTML option values are internal
identifiers, not production labels: for example the option displaying `6E`
has value `07`, and the option displaying `7B` has value `08`.
The implementation does **not** reinterpret those internal identifiers.
Raw database district keys require their own schema-qualified mapping before
use with this CSV contract. Other data products are not qualified by this
production reference. Numeric-only well-download filtering is unchanged.

## Method

A single tuple in `worldenergydata.texas_rrc.districts` supplies the validator,
router, and CLI. Endpoint metadata keys and the YAML configuration are checked
against the same independently transcribed reference in tests. Atlas validation
inherits the validator's qualified set.

The CSV loader preserves district text. Normalization strips spaces, folds case,
and pads numeric labels. Integral decimal spellings retain the existing numeric
CSV behavior (`3.0` becomes `03`); fractional numbers are invalid.
Production processing records `district_status` as `assigned`, `invalid`, or
`missing` before the original distinction would be lost. Blank, absent, and
null districts are `missing`. Nonempty unsupported labels are `invalid`.

For each district, volume is the sum of its input record volumes. Overall
volume is the sum of assigned and unassigned volumes. These are exact
accounting identities, not physical equations or empirical coefficients.
The unassigned CSV row retains both invalid and missing volumes. Summary JSON
counts only assigned districts and reports the invalid and missing record
counts and oil/gas totals separately, as well as combined unassigned totals.
No production record is discarded by district grouping.

## Worked example

Synthetic inputs (oil in BBL; gas in MCF), also exercised by
`tests/unit/texas_rrc/test_production_districts.py`:

| district | lease_number | oil_production | gas_production |
| --- | --- | ---: | ---: |
| 6E | 1 | 100 | 10 |
| 6E | 1 | 25 | 5 |
| 03 | 2 | 50 | 7 |
| invalid | 3 | 20 | 3 |
| blank | 4 | 10 | 2 |

The independent hand calculation gives `6E`: oil `100 + 25 = 125`, gas
`10 + 5 = 15`, one unique lease. District `03` retains oil `50` and gas `7`.
Unassigned oil is `20 + 10 = 30`; gas is `3 + 2 = 5`.
Overall oil is `125 + 50 + 30 = 205`; gas is `15 + 7 + 5 = 27`.
There are two assigned districts, one invalid record, and one missing record.
These inputs are synthetic arithmetic examples, not reported RRC production.

To reproduce, save the table as CSV with the last district cell empty, then call
`TexasRRC().router` with `data.source: csv`, `data.files.production` pointing
to that CSV, `data_types: [production]`, `Analysis.analysis_root_folder` pointing
to the CSV folder, and `Analysis.result_folder` pointing to an output folder.
The router returns `texas_rrc.outputs.districts_csv` and
`texas_rrc.outputs.summary_json`. The regression contains executable configuration
and checks both emitted files for each special district label.
