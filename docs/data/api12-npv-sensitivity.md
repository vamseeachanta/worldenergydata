# API12 NPV discount-rate sensitivity CSV

The opt-in `export_npv_sensitivity` function writes one CSV row per requested
annual effective discount rate using the existing API12 valuation and FDAS
monthly discounting. It delivers the discount-rate export slice of #46.
Existing scalar callers are unchanged; the wider issue remains open.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-16 | Document explicit sensitivity inputs, output basis and deferred scope. |

## Usage

The following inputs are synthetic assumptions for demonstrating the interface.
They are not calibrated economic assumptions or recommended discount rates.
The 5%, 10% and 15% display rates come from the repository user story.

```python
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.analysis.npv_sensitivity_export import export_npv_sensitivity

cfg = {"economics": {"cost": {"CAPEX": 1000.0, "OPEX": 2.0}}}
revenue = pd.DataFrame({
    "Month": [202401, 202402],
    "Monthly Oil Production": [100.0, 200.0],
    "Revenue (USD)": [1000.0, 3000.0],
})
destination = export_npv_sensitivity(
    cfg, revenue, Path("sensitivity.csv"),
    field_id="synthetic-field", api12="000000000001",
    rates=[0.05, 0.10, 0.15],
)
```

CAPEX is an immediate USD outlay at period zero. OPEX is USD per barrel of oil.
Each operating row represents the next consecutive month end in input order;
the caller supplies chronological rows without missing months. The exporter
does not sort dates, fill gaps or infer a calendar from `Month`.
Revenue is USD and production is barrels per month. Revenue accepts API12
dollar signs and comma thousands separators; production must be numeric.
Locale-specific decimal separators are unsupported. Blank `Month` rows are
summary rows and are excluded, matching the scalar API12 convention.

The monthly rate is `(1 + annual_rate) ** (1 / 12) - 1`. For this assumed
two-month case the independent reference is
`-1000 + 800 / (1 + monthly_rate) + 2600 / (1 + monthly_rate) ** 2`.
Tests compare CSV readback with relative tolerance `1e-10` and absolute USD
tolerance `1e-8`. These are numerical regression tolerances, not valuation
uncertainty estimates.

## CSV contract

| Column | Meaning |
| --- | --- |
| `field_id`, `api12` | Explicit caller identifiers; read API12 as text to preserve leading zeros. |
| `discount_rate_annual` | Requested annual effective fraction, in caller order. |
| `rate_basis` | `annual effective`. |
| `cashflow_period` | `monthly`. |
| `timing_basis` | `CAPEX at period 0; receipts at month ends`. |
| `currency` | `USD`. |
| `npv_basis` | `after OPEX and before royalty`. |
| `royalty_status` | `NOT_EVALUATED`; no cited royalty is accepted by this export interface. |
| `npv` | Existing API12 calculation result in USD. |

The exporter deep-copies configuration for each rate, changing only
`economics.cost.discount_rate_annual`, and passes a separate table copy to
`calculate_npv_with_citations`. No discounting formula is duplicated in the
exporter. Missing royalty evidence stays visible; this is not a net valuation.

## Validation and file behavior

CAPEX and OPEX must be explicitly supplied and finite. A supplied original
annual rate must also be finite, even though it is replaced for each case.
Rates must be nonempty, finite, unique and greater than -1 and at most 1.
The stricter lower bound than FDAS deliberately excludes the zero discount
denominator at an annual rate of -100%.
Operating revenue and production must be present, numeric and finite; they
are never silently replaced with zero. Missing columns or months and a table
without operating rows are rejected. Signed finite economic inputs retain
the scalar API's arithmetic semantics; economic calibration is the caller's
responsibility.

All input validation and all calculations finish before file creation.
The destination is opened exclusively, so an existing file is never overwritten.
Its parent directory must already exist. Validation and calculation errors
propagate without creating output. Filesystem write errors also propagate,
but may leave a partial new file; filesystem transactions are outside scope.

## Deferred work

This slice does not complete the story's remaining output and reporting work:
monthly cashflow exports, timeline columns, field summary reports and broader
analysis output integration remain. Multi-field orchestration, field comparison
and configurable per-field scenarios remain separate work. CAPEX scenarios,
charts and executive dashboards are deferred. Workflow flags, external benchmark
validation, real-field qualification and multi-field performance qualification
are also deferred. The exporter supplies neither cited royalty support nor a
new recommended valuation convention.
