# Baker Hughes ingestion example

Summary: a missing optional header and an unmatched exact filter remain visible
in loader diagnostics and the completeness report. Inputs are synthetic; the
example establishes the software contract rather than source-data accuracy.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-22 | Added an independently enumerated example for schema and completeness diagnostics. |

## Inputs

Create a workbook sheet named `Pivot Table` with these rows. `County` is
deliberately absent. All other optional headers are present; blank depths are
missing values. Letters identify synthetic categories only.

| PublishDate | Country | StateProvince | BasinName | RigCount |
| --- | --- | --- | --- | --- |
| 2026-01-01 | A | X | B | 2 |
| 2026-01-08 | A | Y | B | 3 |

For both rows, set `DrillFor=Gas`, `Location=Land`, `Trajectory=Vertical`,
`WellType=Development`, and leave `WellDepth` and `WaterDepth` blank.

## Method

```python
from worldenergydata.baker_hughes.loader import load_pivot_table
from worldenergydata.baker_hughes.report import generate_report

matched = load_pivot_table("synthetic.xlsx", country="A")
report = generate_report(matched, source="pivot")
unmatched = load_pivot_table("synthetic.xlsx", country="Z")
empty_report = generate_report(unmatched, source="pivot")
```

The schema is validated before renaming and filtering. Comparisons are exact:
both source countries equal `A`, and neither equals `Z`. The report counts rows
and observes date bounds; it does not sum rigs or infer missing dates.

## Answer and independent check

Two enumerated rows match `A`, with counts preserved as `[2, 3]`. The earlier
calendar date is January 1 and the later is January 8. Thus `record_count=2`
and `date_range={"min": "2026-01-01", "max": "2026-01-08"}`.
`matched.attrs["schema"]` reports `status="incomplete"` and
`missing_optional=["County"]`. The report's overall completeness is
`incomplete`, even though all three dimension inventories and bounds are
available (`omitted_fields=[]`).

No row matches `Z`. `unmatched.attrs["ingestion"]["status"]` is `no_match`,
and `empty_report` has `record_count=0`, incomplete completeness,
`omitted_fields=["date_range"]`, and `bounds_status="undefined"`.
No `NaT` bound is emitted. The retained schema diagnostic still names `County`.

Executable evidence:
`tests/unit/baker_hughes/test_worked_ingestion.py::test_worked_ingestion`.
Expected results above follow by direct enumeration, independently of loader
output. No engineering equation, coefficient, conversion or tolerance is used.

## Sources and limits

The schema and diagnostic contract is defined by #1335 and knowledge pack
section 12. Parsing and reshaping use
[pandas 2.3.3 to_datetime](https://pandas.pydata.org/pandas-docs/version/2.3.3/reference/api/pandas.to_datetime.html)
and [DataFrame.melt](https://pandas.pydata.org/pandas-docs/version/2.3.3/reference/api/pandas.DataFrame.melt.html).
DataFrame attrs are transient metadata; export callers must persist the returned
report separately if diagnostics must survive storage. Numeric coercion and
unit qualification are tracked separately in #1334 and #1336. The separate
workbook collector does not use these loaders.
