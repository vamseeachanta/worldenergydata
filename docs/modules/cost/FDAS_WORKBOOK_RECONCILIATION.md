# FDAS workbook reconciliation

The read-only builder inventories the frozen V30 workbooks, maps their cost
cells, and compares monthly sums with summary values. It keeps workbook
assumptions separate from disclosed, mapped, allocated and modeled evidence.
Unknown compatibility or an absent approved materiality policy produces
`NOT_EVALUATED`. No workbook value is promoted to a disclosure.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Initial inventory, comparison and report to expose evidence gaps. |

## Three slices

1. Frozen inventory: SHA-256, sheet dimensions and header signatures, formula
   locations, cached-value availability, systems, parameter cells and units,
   exact internal project identities, assumption vintage and monthly window.
   Public inventories use opaque identities and exclude workbook core metadata.
2. Reconciliation: explicit summary-cell dispositions, facilities residual,
   development and D&C bridges, monthly/component sums, and optional external
   interval comparisons with exact accounting-basis matching. Raw decimals stay
   in JSON/CSV; HTML displays one decimal place without changing decisions.
3. Integrated output: portfolio summary, project drill-down, both existing
   cost-map directions, workbook cash-flow traces, external comparisons,
   estimator availability, upstream gaps and provenance legend.

## Regeneration

Install the repository's existing dependencies, including `openpyxl`, or use a
tool environment with `openpyxl`, `scikit-learn` and `pydantic`. Set `PYTHONPATH`
to `src:packages/worldenergydata-cost/src:packages/worldenergydata-core/src`.
Then run:

```sh
python scripts/cost/build_fdas_workbook_reconciliation.py \
  --output reports/cost/fdas_workbook_reconciliation
python examples/fdas_workbook_reconciliation.py
```

The builder writes `index.html`, `reconciliation.csv`, `monthly.csv`,
`reconciliation.json` and `manifest.json`. It does not recalculate Excel formulas.
A missing formula cache is an error, never a zero. Digest/schema drift requires
an explicitly reviewed new freeze; the builder never refreshes the freeze.
Repeated builds with identical inputs are byte-identical. The manifest pins
workbook, contract, implementation and existing cost-map input hashes and output
hashes, with no wall-clock timestamp or absolute path.

## Method and sources

The [approved reconciliation plan](../../plans/2026-07-16-issue-1044-fdas-workbook-reconciliation.md)
(2026, task 6) specifies compatible interval subtraction and fail-closed
materiality. For reference interval W and comparison C:

```text
V = [W.low - C.high, W.high - C.low]
M = max(absolute_limit, relative_limit * max(abs(W.low), abs(W.high)))
immaterial: V.low >= -M and V.high <= M
material: V.high < -M or V.low > M
uncertain_materiality: otherwise
```

Interval subtraction follows [Shape Interrogation for Computer Aided Design
and Manufacturing, online edition](https://web.mit.edu/hyperbook/)
(December 2009, section 4.7, equation 4.43). The interval's largest absolute
endpoint is the explicit denominator policy; no midpoint is substituted.
Absolute and relative limits have no default: they require a supplied policy,
its source and boolean approval. Material or uncertain differences fail unless
their classification has evidence; missing evidence and unresolved model error
cannot pass merely because they were classified.

The frozen `financial_project_summary.xlsx` defines summary costs in
`Project_Summary!E1:M1,P1:Q1`. Monthly cost columns are defined in each project
sheet's `F1:G1,I1,K1:L1`. Development CAPEX is facilities + drilling + completion;
D&C is drilling + completion. Neither subtotal is added to its children again.
Facilities less host, SURF, booster pump, injection pump and dry-system costs is
shown as an explicit residual. Its equality to the system's facility input is
checked against `lease_assumptions.xlsx`, `assumptions!B15:F15`; equality does
not establish independent provenance. Unit denominators come from that sheet's
column G. Conversion of millions to native USD uses the mega factor in the
[NIST SI Prefixes table](https://www.nist.gov/pml/owm/metric-si-prefixes)
(accessed 2026-10-19). All other financial coefficients remain workbook inputs.

## Worked example

The executable example uses synthetic inputs W=[100,120] and C=[80,90] USD
on identical project, component, time, currency, unit, ownership, scope, CAPEX,
price and assumption/normalization vintage bases. Subtraction by hand gives
[100-90,120-80]=[10,40]. With the synthetic example limit M=25, the interval
crosses the acceptance boundary: `uncertain_materiality`, `FAIL` without an
evidenced explanation. These fixture numbers set no production acceptance
policy. Omitting the policy instead yields `NOT_EVALUATED` while retaining
the variance. The test docstrings independently derive these expected values.

For the frozen workbook, each opaque project has fifteen rows, including
aggregates and explicit installation/other gaps. `monthly.csv` preserves every
observed workbook month; the HTML annual view is a sum, never interpolation.

## Optional external evidence

`--comparisons evidence.json` accepts a `comparisons` list and optional `policy`.
Each entry requires `project_id`, `component`, `workbook_basis`, `basis_evidence`
and `comparison` (with `basis`, `amount.low`, `amount.high`, `provenance`, `source`).
The complete basis schema is the `Basis` dataclass. Reference amount, period,
units and vintage always come from the frozen workbook. All basis fields must
agree before subtraction. Other workbook basis claims require explicit evidence;
this interface records that claim rather than independently certifying it.
Optional `classification` and `evidence` explain a material variance. Policies
require `absolute`, `relative`, `source` and a boolean `approved`. Monetary
inputs are decimal strings; null bounds are unavailable. Duplicate comparisons
and attempts to replace the frozen reference basis are rejected.

## Known limits and later slices

The three required upstream portfolio, trace and estimator manifests are absent
in this revision. Their consumption and estimator backtests are
`NOT_EVALUATED`; the existing cost-map views are displayed as separately sourced
evidence, without asserting compatibility with workbook identities. Existing
cell-to-requirement links are retained and hash/identity checked, but a complete
external project/component/time equivalence contract remains required. No
portfolio grand total is inferred across overlapping components or cost bases.
Non-cost parameter units remain explicitly unevaluated. Monthly aggregation
does not establish complete V30 financial-engine reproduction. A sourced,
approved production materiality policy remains required.

V50 differences remain under #899. No after-tax/NOL behavior changes, canonical
assumption promotion or workbook mutation are included. Stakeholder circulation
requires explicit maintainer approval under #1017.
