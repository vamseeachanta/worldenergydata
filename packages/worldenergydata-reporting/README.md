# worldenergydata-reporting

`reporting` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.reporting` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## JSON dates and generated HTML

JSON exports use ISO 8601 date strings at millisecond precision. Generated HTML
contains presentation content without Python lint-suppression text.

### Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Specify date and HTML contracts with a reproducible example. |

### Date contract

The `data` array is produced with `orient="records"`, `date_format="iso"` and
`date_unit="ms"`, then wrapped with the `summary` object. This contract is tested
with pandas **2.3.3**, using its
[DataFrame.to_json documentation](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.DataFrame.to_json.html)
(`date_format`, `date_unit`, and missing-value conversion). Explicit precision
retains milliseconds and truncates finer fractions.

- Naive datetimes keep their clock fields without a timezone suffix:
  `2026-01-02T03:04:05.123`.
- Aware datetimes are normalized to UTC with `Z`. For example,
  `2026-01-02T03:04:05.123+02:00` becomes `2026-01-02T01:04:05.123Z`:
  subtract the input offset from its clock time. The original offset is lost.
- `pd.NaT` becomes JSON `null`.

ISO 8601-1:2019 is the date-format reference
([ISO catalogue](https://www.iso.org/standard/70907.html)). Full-standard
conformance is NOT_EVALUATED: the public catalogue returned HTTP 403 during
source retrieval, and no licensed text was used. The serialized behavior above
is established by the accessible pandas documentation and literal test cases.
This contract covers datetime columns; summary values retain the existing
`default=str` behavior and are outside the datetime-column guarantee.

### Worked example

Input: a two-row frame containing one naive date and one missing date, with an
empty summary. These are synthetic format examples, without engineering inputs.

```python
from types import SimpleNamespace

import pandas as pd

from worldenergydata.reporting.export import export_report

result = SimpleNamespace(
    data=pd.DataFrame({"date": [pd.Timestamp("1970-01-02"), pd.NaT]}),
    summary={},
)
manifest = export_report(result, formats=["json"], output_dir="output")
```

Method: retain the first row's clock fields, append the explicit millisecond
fraction, map the missing date to `null`, and wrap the records with the summary.
The exact file text is shown below (indentation follows the existing writer;
there is no trailing newline inside the file):

```json
{
  "data": [
    {
      "date": "1970-01-02T00:00:00.000"
    },
    {
      "date": null
    }
  ],
  "summary": {}
}
```

`test_documented_two_row_example_is_exact` checks both the exported bytes and
this block against a hand-written literal.

### HTML cleanliness

Python suppression markers (`noqa`, `pylint:`, `type: ignore`) belong outside
emitted template strings. Rendering regressions exercise the empty, summary,
and plot branches; a source-level check inspects every template string segment.
This rule applies to generator-owned text, without rewriting user-supplied data.
The separate `DataValidator.generate_interactive_report` writer embeds Plotly
for offline use; its integration test parses balanced tags and checks the gauge
and summary against a hand-calculated quality score.
