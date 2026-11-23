# Tabular input validation worked example

Synthetic CSVs exercise the rejection contracts for rig counts, depths and
subsea components. Each defective row is loaded separately: either loader
rejects a whole input rather than returning repaired data. Accepted examples
have independent hand checks below; they establish input validation only.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-22 | Add shared synthetic inputs and hand checks for numeric rejection, declared units and literal CSV text. |

## Inputs and execution

Inputs live in `tests/fixtures/tabular_validation/`:

- `rig_counts.csv`: count, depth, unit declaration and source-header choices.
- `rigid_jumpers.csv`: positive numeric fields, optional weight and literal text.
- `mooring.csv`: MBL, optional weight and literal text.
- `suppliers.csv`: a synthetic lookup record with literal country text `NA`.

`tests/unit/test_tabular_validation_example.py` reads these CSVs without
pandas missing-value substitution. It writes each rig row to an Excel workbook
with the appropriate pivot or summary sheet because the rig loaders consume
Excel. Summary cases use counts only; depth cases apply to pivots. Component
cases are written individually to temporary CSVs, omitting only the example's
`case` column. The inputs are synthetic and have no catalog provenance.

Test nodes:

- `tests/unit/test_tabular_validation_example.py::test_pivot_worked_csv`
- `tests/unit/test_tabular_validation_example.py::test_summary_worked_csv`
- `tests/unit/test_tabular_validation_example.py::test_component_worked_csv`
- `tests/unit/test_tabular_validation_example.py::test_supplier_worked_csv`

## Defects and dispositions

| Input case | Defect or control | Expected disposition |
| --- | --- | --- |
| Rig `missing_count` | Empty count cell | Reject `rig_count`, without replacing it with zero. |
| Rig `invalid_count` | `bad` in count cell | Reject `rig_count`. |
| Rig `fractional_count` | `1.5` rigs | Reject `rig_count`, without truncating to a whole rig. |
| Rig `locale_count` | `1,234` without locale declaration | Reject `rig_count`, without guessing a separator convention. |
| Rig `invalid_well_depth` | `bad` well depth | Reject `well_depth_ft`, without turning it into missing depth. |
| Rig `invalid_water_depth` | `bad` water depth | Reject `water_depth_ft`. |
| Rig `unit_mismatch` | `WellDepth_m` with caller declaration `ft` | Reject the conflicting unit declaration. |
| Rig `undeclared_unit` | Ambiguous headers with no declaration | Reject; `depth_unit` is required. |
| Component `positive_infinity` | `inf` in OD or MBL | Field validation error: value must be positive and finite. |
| Component `not_a_number` | `NaN` in OD or MBL | Field validation error; not treated as an absent value. |
| Component `negative_weight` | Weight `-1` | Weight validation error. |
| Component `infinite_weight` | Weight `inf` | Weight validation error. |
| Component `invalid_numeric_text` | Weight text `NA` | Numeric validation error; optional weight cannot conceal the token. |
| Component `absent_weight` | Empty weight and notes cells | Accept with absent weight and notes; literal manufacturer `NA` survives. |
| Supplier empty lookup | `get("")` | Reject blank key before loading data. |
| Supplier clean lookup | `get("alpha")` | Return the synthetic record; country remains literal `NA`. |

Rig errors are `ValueError` with field and row (or unit-contract context).
Component errors are Pydantic `ValidationError` naming the field. No defective
row yields a partially repaired record. Rig DataFrame metadata records the
accepted count policy and validated source/output depth units.

## Accepted clean cases and hand checks

The count example enumerates three rigs, hence the expected result is `3`.
The zero-count control enumerates none, hence `0`; this is distinct from an
empty cell. The summary reshape has one state and one date, hence one output
row per accepted case. No fractional count is rounded or truncated.

The clean pivot depth is `3.048 m`. From
[NIST SP 811 (2008), Appendix B.6](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf),
the international foot defined by the 1959 agreement is exactly `0.3048 m`.
Thus `3.048 / 0.3048 = 10 ft`; the expected `well_depth_ft` is exactly `10.0`
for this example. Its empty water-depth cell remains missing. The zero-depth
control has `0 ft` in both fields, which remains `0.0` without conversion.
These exact examples need no chosen engineering tolerance.

For the clean rigid-jumper record, OD `2`, wall `0.5` and pressure `3` are
finite and strictly positive; weight `1` is finite and nonnegative. For the
clean mooring record, MBL `3` and weight `1` satisfy the same sign checks.
Literal manufacturer, material/grade and notes strings `NA` remain text.
All these magnitudes are synthetic choices, not physical capacities or design
limits. The zero boundaries and rejection rules are the input-domain contracts
in #1334 and #1305, not constants taken from engineering standards.

## Limits and way forward

Declared or labelled units can still be wrong in the original source.
Workbook provenance, independent source-count accuracy, datum and signed
evidence remain unverified. Subsea field suffixes do not qualify source units;
weight-unit discrepancies, geometry and catalog adequacy remain unresolved.
Use qualified source metadata before an engineering decision. Input rejection
and the worked example do not establish design fitness.
