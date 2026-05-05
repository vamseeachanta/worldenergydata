# Plan: Issue #362 — Operator cost benchmarking HTML report

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/362
**Status:** plan-review
**Tier:** T3 (new report generation script)
**Depends on:** #334–#338 (disclosure dataset, DONE), #349 (capability inventory)

## Plan

### Task 1 — Assess available disclosure data
```bash
python3 -c "
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset
df = load_public_dataset()
print(df.shape, df.columns.tolist()[:10])
print(df.groupby('operator')['year'].unique().head(5))
"
```
Understand what operators, years, and cost fields are available.

### Task 2 — Write `scripts/gtm/generate_cost_benchmarking_report.py`
Outputs `reports/gtm/YYYY-MM-DD-operator-cost-benchmarking.html`.
Required sections:
- KPI summary: operators covered, year range, field count
- Per-operator cost distribution (box plot by cost category)
- Regional comparison (CAPEX/OPEX by GoM / North Sea / Brazil)
- Year-over-year cost trend per major operator
- Data provenance / citation table

### Task 3 — Style consistent with existing reports
Follow patterns in `reports/gtm/2026-05-04-bsee-field-analysis-comprehensive.html`:
- KPI card grid (CSS Grid)
- Plotly CDN-based charts
- Sticky header tables

### Task 4 — Run and review output
```bash
uv run python scripts/gtm/generate_cost_benchmarking_report.py
open reports/gtm/*cost-benchmarking*.html
```

## Acceptance Criteria
- HTML report generated under `reports/gtm/`
- At least 3 operators shown with multi-year cost trends
- Plotly charts are interactive (hover, zoom)
- Report is self-contained (no external assets beyond Plotly CDN)
