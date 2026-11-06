# Read-only FDAS workbook reconciliation

The reconciliation freezes the V30 workbooks before inspecting their systems,
parameters, project identities, units and monthly windows. It generates JSON,
CSV, HTML and a SHA-256 output manifest without editing a source workbook.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/cost/build_fdas_workbook_reconciliation.py \
  --output "${TMPDIR:?}/fdas-comparison"
```

Use a fresh output directory. Existing files are preserved, and a collision
is rejected before writing. Generated outputs are local analysis artifacts;
generation does not authorize circulation. Stakeholder circulation remains
maintainer-gated under [issue 1017](https://github.com/vamseeachanta/worldenergydata/issues/1017).

## Inputs and accounting method

The frozen schema and byte fingerprints are recorded in
`config/analysis/lower_tertiary/fdas_workbook_vintages.json`. The references are
`lease_assumptions.xlsx` and `financial_project_summary.xlsx` in
`docs/modules/bsee/analysis/production/FDAS_V30/`. The first supplies system
parameters and unit notes. The second supplies summary cost cells and dated
monthly arrays. Core document metadata is excluded from inventories.

The accounting source is the same directory's
`generate_financial_summary_V30.py`, specifically its facilities booking block,
monthly drilling/completion multiplication and project-summary aggregation.
Facilities are host + SURF + booster pumps + injection pumps + dry systems +
the injection facility. Development CAPEX is facilities + drilling + completion.
Summary subtotals are non-additive. OPEX, royalty, revenue, cash flow and NPV
are explicitly excluded from development CAPEX.

The injection facility is separately cross-referenced to assumptions row 15;
it is booked only for a project with first oil. Installation has no independent
workbook cost column, so no installation allocation is invented. Each output
project carries its own cell crosswalk, parameter inventory, monthly cost trace,
native USD values, assumption vintage and unresolved checks.

Formula handling follows [openpyxl 3.1, load_workbook, data_only](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html).
`read_cell` exposes formula text separately from cached values. The reconciliation
does not calculate formulas or substitute zero for missing values. A stored
formula is excluded from numeric accounting; a full financial-engine rerun is
not established by monthly/component consistency checks.

## Worked example: workbook bridge

All amounts below are workbook assumptions, not independent disclosures.
`financial_project_summary.xlsx`, `Project_Summary!E3:I3`, records host + SURF +
booster pumps + injection pumps + dry systems:

```text
2,000.0 + 0.0 + 0.0 + 0.0 + 630.0 = 2,630.0 USD MM
```

`lease_assumptions.xlsx`, `assumptions!D15`, adds the injection facility:

```text
2,630.0 + 100.0 = 2,730.0 USD MM = Project_Summary!J3
965.6 + 821.7 = 1,787.3 USD MM = Project_Summary!K3 + L3
2,730.0 + 1,787.3 = 4,517.3 USD MM development CAPEX
```

The native monthly facilities sum differs from J3 by less than USD 0.1 because
the stored monthly host spread is rounded. Exact residuals are retained in
JSON. Nonzero residuals remain `UNRESOLVED`; no arbitrary acceptance tolerance
is installed. The HTML displays small nonzero amounts as less than USD 0.1
with their sign rather than displaying a false zero.

## Interval comparison API

`Basis`, `Interval`, `CostValue` and `compare` support explicit, independent
comparisons. All monetary quantities use finite `Decimal` values.
The interval equation follows task 6 of the repository's
`docs/plans/2026-07-16-issue-1044-fdas-workbook-reconciliation.md`:

```text
variance = [workbook_low - comparison_high,
            workbook_high - comparison_low]
```

For an invented arithmetic example, W = [100.0, 120.0] and C = [90.0, 110.0]
give variance = [-10.0, 30.0]. With a caller-supplied threshold of 25.0 in the
same unit, the interval crosses the materiality boundary and is
`uncertain_materiality`. These inputs are test quantities, not engineering
defaults or an adopted materiality policy.

Exact agreement is required on currency, price basis and year, ownership,
scope, CAPEX/OPEX basis, units, period and assumption vintage, plus project and
component identity. Unknown fields prevent subtraction even when both sides
are unknown. A missing threshold prevents an acceptance verdict. Variance
categories are scope, basis, timing, currency, assumption vintage, missing
evidence and model error. A category without supporting evidence remains
unresolved. An interval crossing the threshold never becomes a point estimate.

## Coverage and limits

- Workbook inventory covers ten projects and five system parameter columns.
- Existing controlled single-project cost-map and dated-event APIs are consumed
  separately, with source digests, requirement IDs, award links, targets,
  exclusions, overlaps and residual intervals. These are partial upstream
  evidence, not completed portfolio synthesis or workbook equivalence.
  The existing cell crosswalk is verified against workbook digests, values,
  units, vintage and controlled project identity before linking requirements.
- The full portfolio synthesis, trace-contract and correlated-estimator
  manifests are unavailable in this implementation's data basis. Estimator
  backtests and inferred top-down allocations are `NOT_EVALUATED`.
- External project and component identities require an evidenced crosswalk;
  similar names are not aliases. In particular, Tiber is not silently mapped
  to a combined development. Workbook ownership and price year are not
  established, so external workbook variances are `NOT_EVALUATED`.
- Full V30 financial reproduction requires the production/economics basis and
  remains `NOT_EVALUATED`. V50 adoption and after-tax/NOL changes remain outside
  this comparison; see [issue 899](https://github.com/vamseeachanta/worldenergydata/issues/899).

The remaining integration checkpoint is frozen upstream portfolio and estimator
manifests, an evidenced project/component/time crosswalk, and a sourced
materiality policy. No workbook assumption becomes canonical through this report.
