# Operator cost benchmarking analysis

[Open the report](operator_cost_benchmarking.html). The companion
[facts JSON](operator_cost_benchmarking_facts.json) retains computational
precision, source metadata and descriptive cohort statistics. The
[percent-format notebook](../../notebooks/gtm/operator_cost_benchmarking.py)
shows the inputs, method and a worked answer. Both outputs run offline.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Cited historical disclosures and descriptive cohorts expose the FDAS analytics surface. |

Table 1. Documentation revision history.

## Inputs and qualification

The annual seed covers Chevron, Shell and BP for fiscal years 2020–2023.
Every value is transcribed from the linked annual-report table, with publisher,
filing edition, PDF page, retrieval date, fiscal definition and PDF SHA-256.
The sources were retrieved on 2026-10-20. The seed is labelled
**Illustrative seed — not yet ingested**; it does not represent current coverage
or the canonical annual dataset. Shell's 2021 amount follows the 2023 filing,
which differs from the 2022 filing. No restatement reason is inferred.

Sanction costs come from the existing `cost/data_collection/public_dataset.py`.
Their original filing evidence has not been reverified for this report. These
curated nominal amounts are separate from annual operator totals. Costs of
different types and activities are never pooled into the same cohort. Region
and water-depth bands are descriptive proxies; onshore and reservoir-play
comparisons are not established. Repeated project observations may occur in
the curated inputs; cohort counts mean observations, not unique projects.
Outliers carry an operator, sanction year, one-based source row and canonical
source-record SHA-256 in the facts JSON, allowing the originating observation
to be located without replicating project-specific text in the report.

## Method and worked example

Arithmetic annual change is current CAPEX minus previous CAPEX, and relative
change is that difference divided by previous CAPEX. A missing year or zero
denominator has no annual percentage change. Qualified changes require both
rows to carry an identical, explicit upstream comparability basis; this report
does not assign one. The existing disclosure analytics module supplies the raw
arithmetic through `DisclosureAnalyticsQuery.operator_capex`.

Chevron Annual Report 2023, Financial Highlights, PDF page 22, gives 2022
CAPEX of 11,974 and 2023 CAPEX of 15,829 USD million. Thus the change is
15,829 − 11,974 = 3,855 USD million and 3,855 / 11,974 = **32.2%**, rounded
for display. The result is an ungated arithmetic change, with no normalized
cost trend established.

Cohort medians and inclusive quartiles describe nominal amounts. Inner fences
are Q1 − 1.5 IQR and Q3 + 1.5 IQR, where IQR = Q3 − Q1, following the
[NIST/SEMATECH e-Handbook, section 1.3.3.7, Box Plot](https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm)
(web edition retrieved 2026-10-20). Inclusive interpolation places endpoints
at the minimum and maximum. The report coverage policy requires four
observations before flags are calculated; this does not establish statistical
significance. For the independent test fixture `[10, 20, 30, 40, 100]`, median
= 30, Q1 = 20, Q3 = 40, IQR = 20 and the upper fence = 70; only 100 is flagged.
No fiscal amounts are added to the sanction-cost distribution.

## Regeneration and checks

From an installed repository environment:

```bash
uv run python notebooks/gtm/operator_cost_benchmarking.py
uv run python -m pytest tests/unit/cost/test_disclosure_seed_dataset.py tests/unit/cost/test_benchmark_report.py tests/unit/cost/test_notebook_operator_cost_benchmarking.py
```

`REPORT_DATE` is a pinned edition date. Update it deliberately when changing
the input vintage. `OPERATOR_COST_REPORT_OUT` redirects both outputs for
isolated execution. The integration test executes the notebook and compares
both outputs byte for byte against the committed artifacts. HTML embeds CSS,
SVG and selector logic; source hyperlinks are citations, not external assets.

## Pending dependencies

- [Annual dataset](https://github.com/vamseeachanta/worldenergydata/issues/334): canonical ingestion is absent; cited seed inputs are supplied here.
- [Comparability](https://github.com/vamseeachanta/worldenergydata/issues/336): FX, inflation and fiscal-definition qualification remain pending.
- [Registry](https://github.com/vamseeachanta/worldenergydata/issues/343): automated source coverage is pending.
- [Lineage](https://github.com/vamseeachanta/worldenergydata/issues/344): restatement and amendment status is NOT_EVALUATED.
- [Citation sidecars](https://github.com/vamseeachanta/worldenergydata/issues/361): the existing provenance mapping is retained pending schema adoption.

OPEX is NOT_EVALUATED because no qualified OPEX series is supplied. A durable
workflow registration remains separate from this notebook and HTML artifact.
