# worldenergydata-decommissioning

`decommissioning` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.decommissioning` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Unknown data and calibration exclusions

Missing documentation is absent availability. Unknown regulatory keys raise
`ValueError`. Calibration reports unsupported rows, and missing final production
leaves the current idle duration and cessation year unknown. These behaviors
address #1281; the pinned knowledge pack describes its historical code revision.

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-21 | Document unknown-data behavior and row accounting with a reproducible example, so missing evidence cannot be interpreted as a numerical result. |

### API behavior

- `DataCompletenessScorer`: missing scalar availability (`NaN`, `None`, `pd.NA`)
  scores as absent and remains in the gap list. This behavior already existed
  before the changes to the other routes.
- `get_regulations` and `get_lead_time`: unknown regions raise `ValueError`;
  a missing requirement in a known region also raises `ValueError`. Queries
  remain case-insensitive. Requirement names are region-specific: UKCS uses
  `decommissioning_programme`, not `decommissioning_plan`. Callers that previously
  tested for an empty list or zero must handle the exception.
- `CalibrationResult.total_records`: count of exact supported asset-type rows
  assigned to an assessment, including fits that retain baseline factors for
  insufficient data. `input_records` counts all input rows. `skipped_records`
  and `skipped_rows` disclose every unsupported or missing type; each exclusion
  has a zero-based `row_position`, the supplied `asset_type` (missing becomes
  `None`), and the reason `unsupported_asset_type`. Positions remain unambiguous
  with duplicate DataFrame index labels. The input is not modified.
- `years_covered` uses assigned rows only; no assigned rows give no measured
  span, reported as zero. The existing minimum span convention for nonempty
  assigned history is retained. `coverage_pct` continues to measure asset types
  with data-driven fits; it is not a percentage of input rows.
- `LateLifeAssessment`: a missing or non-finite final `oil_bbl` produces `None`
  for `current_production_bopd`, `months_idle`, and `estimated_cessation_year`,
  with `production_data_status="unknown_final_month"`. The final row is selected
  chronologically, independently of input order. An observed decline can still
  flag the field. A fully missing series also has unknown peak and decline.
  An observed final zero remains a measured zero and retains the existing
  cessation sentinel zero (not applicable). Consumers must handle optional
  numerical fields; `dataclasses.asdict` and JSON preserve `None` as `null`.

### Method and sources

No empirical coefficient or engineering acceptance limit is introduced.
Missing-scalar recognition follows [pandas 2.2.3 documentation (2024),
`pandas.isna`, Examples](https://pandas.pydata.org/pandas-docs/version/2.2/reference/api/pandas.isna.html).
The accounting equation is `input_records = total_records + skipped_records`:
assigned and excluded input positions form disjoint sets. This is the additive
principle in *Discrete Mathematics: An Open Introduction*, third edition
(2019), [section 1.1, Additive and Multiplicative
Principles](https://discrete.openmathbooks.org/dmoi3/sec_counting-addmult.html).
The year span is the difference between the latest and earliest assigned year;
its existing minimum is unchanged. Unknown-key and missing-month policies are
specified in #1281. Lookup tests compare with the repository's stored records
in `_regulations_data.py`; they do not validate legal currency.

### Worked example: inputs, method and answer

All dimensions, costs, years and availability values below are synthetic inputs,
not sourced measurements or recommended parameters. There are three removal
rows: two supported jackets and one unsupported type, so assigned plus skipped
is `2 + 1 = 3`. The assigned year span is `2022 - 2020 = 2` years. No fitted
cost factor is used as an expected answer. All documentation categories are
missing, so each contribution is zero and their weighted sum is zero for any
weights. Two zero-volume production rows followed by an unknown observation
cannot establish the current idle duration or a cessation year. A region absent
from the regulatory database supplies no known obligations or numerical lead time.

```python
import pandas as pd

from worldenergydata.decommissioning.cost_calibration import CostModelCalibration
from worldenergydata.decommissioning.data_completeness import DataCompletenessScorer
from worldenergydata.decommissioning.late_life import LateLifeIdentifier
from worldenergydata.decommissioning.regulations import get_regulations

categories = (
    "as_built_drawings", "inspection_records", "well_records",
    "mooring_documents", "environmental_surveys",
)
score = DataCompletenessScorer().score(
    "Synthetic", dict.fromkeys(categories, float("nan"))
)
print(score.overall_score)

removals = pd.DataFrame({
    "asset_type": ["jacket", "spar", "jacket"],
    "water_depth_m": [100, 100, 100],
    "weight_tonnes": [500, 500, 500],
    "cost_musd": [5, 5, 5],
    "year": [2020, 1900, 2022],
})
result = CostModelCalibration().fit(removals).calibration_result()
print((result.input_records, result.total_records,
       result.skipped_records, result.years_covered))
print(result.skipped_rows[0].row_position)

production = pd.DataFrame({
    "year": [2025, 2025, 2025], "month": [1, 2, 3],
    "oil_bbl": [0.0, 0.0, float("nan")],
})
assessment = LateLifeIdentifier().assess_field("Synthetic", production)
print((assessment.current_production_bopd, assessment.months_idle,
       assessment.estimated_cessation_year))
print(assessment.production_data_status)

try:
    get_regulations("unknown")
except ValueError:
    print("unknown regulatory key")
```

Expected output, derived above:

```text
0.0
(3, 2, 1, 2.0)
1
(None, None, None)
unknown_final_month
unknown regulatory key
```

### Verification and remaining limits

The decommissioning unit suite covers missing documentation scalars, all stored
regulatory lookups, unknown regions and requirements, unsupported calibration
keys, duplicate input labels, all-skipped and empty inputs, repeated calibration,
and missing or non-finite final production in field and portfolio output.

The changes do not validate calendar continuity, duplicate production dates,
negative production, the legal currency of regulatory records, or the empirical
cost and screening factors. Earlier missing production still terminates a trailing
idle-row count; a physically absent final calendar row cannot be identified
without a caller-supplied reporting horizon. Those checks remain NOT_EVALUATED.
Existing empty-history defaults, screening thresholds, fixed month-length
conversion and capped cessation projection remain screening assumptions.
