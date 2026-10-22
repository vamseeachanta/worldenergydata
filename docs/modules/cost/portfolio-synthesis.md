# Portfolio cost synthesis

The portfolio API adds compatible observed award ranges toward a disclosed total
and allocates totals through separately sourced joint architecture scenarios.
The supplied worked example is synthetic. It demonstrates the method without
asserting estimates for any real development.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-19 | Introduced explicit basis checks, residuals and conserving scenarios to make inference auditable. |
| 2 | 2026-10-20 | Required real-money reference years, preserved numeric JSON decimals and identified allocation boundary cases to retain their comparison basis. |
| 3 | 2026-10-22 | Added CSV quantity kinds to distinguish requirement allocations from accounting buckets with the same identity. |
| 4 | 2026-10-22 | Required complete scenario shares and explicit non-nominal years, validated report inputs and overlap membership, and corrected numeric displays and metric sources to preserve the evidence basis. |

## Accounting method and sources

The [repository synthesis plan](../../plans/2026-07-16-issue-1041-bidirectional-cost-synthesis.md)
(2026, planned tasks 3–6 and Pseudocode) defines these accounting identities:

- Eligible subtotal: `E = sum(non-overlapping compatible observed amounts)`.
- Residual: `R = T - E`, with interval bounds `[T.low - E.high, T.high - E.low]`.
- Coverage: `E / T`; residual fraction: `R / T`. The displayed residual percentage
  multiplies this fraction by the mathematical percent conversion factor.
- Joint scenario: `sum(requirement shares) + unallocated share = 1`.
- Unreconciled variance: `T - sum(allocated requirements) - unallocated`.

[Boost Numeric Interval documentation](https://www.boost.org/doc/libs/latest/libs/numeric/interval/doc/interval.htm)
(2006, “Interval Arithmetic”, “Numbers, rounding, and exceptional behavior”,
“Operations and functions”) supplies the interval inclusion and outward rounding
principles. Its public page was read for this implementation. Addition and
subtraction use directed Decimal rounding; positive-denominator division uses a
reciprocal interval and all multiplication corners. This is an arithmetic
implementation, not a claim of compliance with a cost estimating standard.

Arithmetic uses a declared computational policy of 50 significant decimal digits
and outward rounding. Infinite endpoints must be open. Fractions whose target
lower bound is nonpositive are unavailable, while their monetary residuals remain
visible. These enclosures are not probability or confidence intervals and make
no independence claim about shared inputs.

Scenario allocation follows the plan's largest-remainder rule: compute exact
rational shares in units of an explicit quantum, floor them, then distribute the
remaining units in descending fractional-remainder order. Requirement identities
break ties lexically; the unallocated bucket follows requirements on equal ties.
A non-aligned total fails rather than changing the target. No floating-point
cost calculation is used.

Joint rows conserve their own totals. Independent marginal bands cannot be added.
For a ranged total, both boundary scenarios are emitted as limiting cases. The
marginal bands also enclose intermediate quantized totals using the floor of the
lowest raw share and the ceiling of the highest raw share. This handles the
nonmonotonicity of largest-remainder apportionment. Endpoint allocations alone
would miss that behavior. Open target endpoints remain open in observed outputs;
limiting scenario rows and conservative marginal bands do not assert that an
open endpoint is an observed possible total.

## Evidence and eligibility

`Basis` requires currency, price basis (including a constant-money year when
applicable), ownership, scope, CAPEX definition and project phase. All must be
known and must match exactly for a valued included award. No FX conversion,
price rebasing, gross-up or cross-phase comparison happens automatically. Source
amounts must already have a documented compatible comparison basis.

Every non-nominal price basis, including `constant`, `real-2020` and `Real Terms`,
requires `basis_year` as an integer calendar year; an embedded year in a label
does not replace that field. The year participates in exact basis matching.
Nominal inputs may omit it. Placeholder tokens such as `TBD`, `-`, `NA` and
`null` are rejected in every comparison field, regardless of capitalization.
An explicitly supplied year is validated and compared for either price basis.
JSON fractional numbers are parsed directly as Decimal, including amounts,
shares and the output quantum. Manifests retain these fractions as exact decimal
strings rather than converting them through binary floating point.

A bundled award can reference several requirements but contributes money once
per award identity. Conflicting versions of one identity fail. A recognized
EPCI overlap group allows at most one included award, including undisclosed
included awards. Other members carry an
explicit overlap disposition and reason. Overlap discovery itself requires
upstream scope evidence; this implementation cannot infer commercial overlap.

`point`, `range` and `band` may contribute with compatible bases. `not_public`
remains visible and contributes no amount. Lease, midstream, combined-project and
backlog amounts require exclusion; a separately sourced project-only CAPEX split
can instead enter as its own point or range. This conservative handling avoids
converting lease payments or shared contracts into project CAPEX.

Excluded and overlap rows retain their original basis, amount, source and reason
in the HTML ledger. Their diagnostic subtotals include compatible amounts only.
They never enter the eligible subtotal. Asset references are separate from money
and do not imply disclosed asset splits.

`Scenario` requires an architecture, source reference, nonnegative joint shares,
an explicit unallocated share and an `allocated` or `modeled` derivation.
Every compatible scenario must list every project requirement explicitly.
An explicit zero share is permitted; an omitted requirement fails validation
instead of receiving an invented zero allocation or marginal band.
Architecture selection uses exact equality, keeping dry-tree, tieback, floating,
platform and LNG-heavy relationships separate. No numerical priors are built in.
Sources are caller assertions retained for review, not automatically authenticated
research evidence. Scenario families must be qualified before real portfolio use.

## Worked example: inputs, method and answer

All example amounts and shares below are synthetic inputs, explicitly chosen for
an independent hand calculation. They are not industry coefficients or estimates.
The unit is one monetary unit in the declared USD basis.

| Input | Value | Basis/source |
| --- | --- | --- |
| Disclosed target | 100.0 | Synthetic gross development CAPEX at FID |
| Included bundled award | 20.0 to 30.0 | Synthetic compatible award covering two work packages |
| Excluded lease contract | 50.0 | Synthetic non-CAPEX scope |
| Reference shares | host 60.0 %, wells 30.0 %, unallocated 10.0 % | Synthetic joint scenario |
| Alternative shares | host 20.0 %, wells 70.0 %, unallocated 10.0 % | Synthetic joint scenario |
| Allocation quantum | 0.01 | Explicit computational input, not an acceptance limit |

The bundled award counts once: eligible cost is `[20.0, 30.0]`. Subtraction gives
`[100.0 - 30.0, 100.0 - 20.0] = [70.0, 80.0]` residual. The residual percentage is
`[70.0 %, 80.0 %]`; coverage is `[20.0 %, 30.0 %]`. The lease is shown separately.

The reference joint allocation gives `60.0 + 30.0 + 10.0 = 100.0`; the alternative
gives `20.0 + 70.0 + 10.0 = 100.0`. Each has zero unreconciled variance. Unallocated
cost is 10.0, while the observed residual stays `[70.0, 80.0]`. They measure
different things. Host marginal range is `[20.0, 60.0]`, wells `[30.0, 70.0]`;
the two minima or maxima do not describe a conserving joint scenario.

The generated [HTML example](../../../reports/cost/project_cost_map.html) links
project totals to requirements and back, with a solid observed panel and dashed
inferred panel. Labels also distinguish the views without relying on color.
The CSV retains open bounds and exact explicit scenario derivations. Money bounds
serialize outwards at the supplied quantum; fraction bounds serialize to 0.001
(one tenth of a percent). HTML bounds display outwards to one decimal place.
Joint allocation rows additionally carry `allocation_case`, `target_total`,
`target_endpoint`, `target_open` and `limiting`; observed rows leave these columns
empty. The case key is scoped by project and scenario. Ranged totals have distinct
`lower-bound` and `upper-bound` limiting cases, including when a target endpoint
is open. Allocation amount bounds describe the hypothetical joint calculation;
`target_open` describes whether its target endpoint is attainable. Point totals
have a single `point` case with `limiting=false`. HTML retains each exact target
total and the same case qualifiers, separately from rounded monetary displays.

The output quantum must be finite and strictly positive, including when no
scenarios are supplied. Interval open flags must be JSON booleans; strings and
numbers are rejected. Numeric bounds use fixed-point notation at the declared
display or serialization precision, independent of the input exponent.

For `project_metric` rows, CSV `source` contains a sorted JSON array of the
distinct sources used by that metric. Compatible subtotals cite their valued
award sources; residuals and ratios also cite the target. Foreign-basis and
undisclosed rows retain their sources in the award ledger but do not enter
compatible subtotal source sets. An empty subtotal has an empty source array.
Award and allocation rows retain their individual source strings.

Every CSV row carries `quantity_kind`: `project_metric` for observed totals and
ratios, `award` for ledger contributions, `requirement` for scenario allocations,
and `unallocated` or `unreconciled_variance` for the corresponding accounting
bucket. Requirement identities may equal either bucket name; consumers distinguish
these rows by quantity kind as well as project, scenario, identity and case.

```bash
export PYTHONPATH=src:packages/worldenergydata-cost/src
uv run --no-project --with pydantic --with scikit-learn python \
  scripts/cost/build_project_cost_map.py \
  --input data/modules/cost/examples/portfolio_synthesis.json \
  --output-dir reports/cost
```

The command writes HTML, CSV and a v3 manifest. The manifest pins the exact input,
producer modules, scenario set and outputs, using the input revision date rather
than wall-clock time. Running twice with identical inputs and code yields equal
bytes. Output directories should be dedicated to generated cost-map artifacts.

## Portfolio integration and known limits

Input JSON follows the worked example. Every contribution declares its own basis;
there is no implicit inheritance from the project basis. The API is available in
`worldenergydata.cost.portfolio`; the builder accepts multiple projects.

A `portfolio` evidence status requires `--manifest`, `--manifest-sha256` and
`--data-root`. Preflight requires contract version `2.0.0`, verifies the pinned
manifest digest, all input and schema digests, rejects paths outside the data root,
and requires the synthesis input itself to be pinned. This integrity check does
not qualify taxonomy completeness or the engineering validity of source evidence.
The input schema and upstream adapter must be checked against the eventual
requirements-map contract before real ingestion.

Only the pilot v1 manifest exists in the current repository. Therefore the
example is marked `synthetic`; no real portfolio totals, allocation coefficients
or approved reuse claims are supplied. Missing compatible scenarios produce
`NOT_EVALUATED` with unavailable unallocated cost and variance. Missing evidence
never becomes a zero allocation or a guessed coefficient.

Later integration depends on the requirements map in issue #1040, its v2 contract,
qualified architecture scenarios and sourced basis mappings. Historical FX,
inflation, model fitting, automatic scope splitting and workbook edits remain
outside this implementation. Second-provider review remains for the maintainers.
