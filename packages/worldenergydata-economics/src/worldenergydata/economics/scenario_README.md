# Development scenario cash flow

This model computes well production profiles, component and scheduled costs,
margin revenue, period and cumulative cash flow, discounted cash flow and NPV.
The formulas below are standalone model definitions. No workbook-specific
method, scenario or source data is required.

Import inputs from `worldenergydata.economics.scenario_inputs` and functions from
`worldenergydata.economics.scenario`. The existing economics package supplies
revenue multiplication, net cash flow and discounting through `dcf`.

## Units and period basis

All monetary inputs and outputs use USD, with no implicit million-dollar scale.
Oil price and variable operating cost use USD/barrel; production rates use
barrels/day and volumes use barrels. `Periods.duration_years` defines each
whole economic period. `production_days` is a separate, explicit tuple: a period
need not use calendar day counts. Discount rates and retention fractions are
per economic period. An annual rate must be converted by the caller before a
shorter period is used; no automatic rate conversion occurs.

Index zero is the first modeled period. Drilling start, drilling duration,
completion duration and production delay are nonnegative integers in periods.
First production is at their sum. Both retention and addition tuples span the
entire horizon. For the first producing period, rate equals initial rate plus
addition. Later rate equals previous rate times current retention plus current
addition. A supplied zero retention with an addition replaces the previous
rate. Multiple wells are summed; no capacity constraint is inferred.

## Method and interfaces

- `production_profile`: schedule to rates and rates times supplied days.
- `cost_breakdown`: base component sum, engineering fraction on that sum,
  contingency on the supplied choice of base or base plus engineering.
- `activity_cost_usd`: duration times day rate, with decimal half-up rounding
  to an explicit increment. An increment of zero disables rounding.
- `expenditure_profile_usd`: sum explicit capital or operating outflows per
  period. The unscheduled cost estimate is independent of its allocation;
  callers supply allocations and reconcile their sum to the intended estimate.
- `revenue_usd`: volume times price, using the shared schedule constructor.
- `net_cash_flow_usd`: revenue minus capital and operating outflows.
- `discounted_cash_flow_usd` and `npv_usd`: shared discount engine, with
  exponent `first_discount_period + index`. Zero starts at time zero; one
  discounts the first supplied flow once. Empty standalone flow series have
  NPV zero. Numeric zeros occupy periods; missing data must be resolved upstream.
- `evaluate_scenario`: gross revenue minus variable operating cost, multiplied
  by the supplied net margin fraction, less scheduled capital and operating
  outflows. Fixed outflows are not multiplied by that fraction. All intermediate
  production and financial series are returned as frozen output objects.
- `compare_scenarios`: input-order results and NPV differences from the first
  scenario. Horizons, day counts, duration and discount bases must match.

The share applies to operating margin, so this calculation is not a general
royalty or tax model. Negative oil prices and negative cash flows are supported;
cost outflows, production and additions are nonnegative. Empty well tuples model
no production. Wells whose start is beyond the horizon remain nonproducing.
Tuples and frozen dataclasses prevent input mutation. Invalid fractions,
nonfinite inputs and mismatched horizons raise `ValueError`.

## Input gaps

Every quantity below is required; none has a default engineering value.

| Unqualified quantity | Required input or boundary responsibility |
|---|---|
| Time origin, drilling/completion sequence and later developments | Well start, durations, delay and modeled horizon |
| Well productivity, decline, extra production and resets | Initial rates, period retention and additions |
| Production/revenue day counts | Explicit production days in every period; separate runs for other integration bases |
| Currency and currency-year basis | Convert to USD at the boundary; qualify estimate year and freshness upstream |
| Oil price, escalation and growth | Complete explicit oil-price deck; no extrapolation |
| Operating costs and margin deductions | Complete variable-cost deck and explicit scheduled operating outflows |
| Net revenue share and ownership/royalty interpretation | Complete margin-share deck and qualified interpretation upstream |
| Facility, installation, hookup, mooring, well equipment and export costs | USD component amounts; no catalogue prices or assumed counts |
| Drilling/completion unitization and productivity factors | Supplied activity days/day rates or externally qualified component estimates |
| Engineering and contingency percentages and inclusion bases | Fractions and explicit contingency inclusion boolean |
| Drilling/completion allocation and schedule spending | Explicit expenditure period, category and USD amount |
| Rounding precision and source display scale | Explicit USD rounding increment; boundary conversion to USD |
| Discount rate, period spacing and first-flow convention | Per-period rate, period duration and first discount period |
| Annual group sizes, overlaps, subtotal inclusion and chart coordinates | Explicit upstream grouping and reconciliation; no source layout is inferred |
| Hardcoded summary values and auxiliary arithmetic | Qualify upstream; no source helper table is embedded |

Mathematical identities, tuple indices and exact currency-unit conversions are
not engineering estimates. No standards-derived constant or clause is supplied.
Unknown inputs must not be replaced with zero merely to satisfy the interface.

## Limits and verification

This is a deterministic, whole-period, oil-only model. It does not predict
reservoir behavior, calendar drilling progress, price forecasts or fiscal terms.
Taxes, abandonment, financing and other costs require explicit outflows. Cost
estimates do not establish expenditure timing. No IRR, annual bucket convention,
workbook layout, visual schedule bar or chart helper is reproduced automatically.
Cache agreement alone does not qualify any engineering estimate.

Tests under `tests/unit/economics/scenario` use illustrative examples with
independent hand arithmetic, annuity identities, zero-rate and no-well limits.
No workbook fixture is required. With workspace dependencies installed, run
`python -m pytest tests/unit/economics/scenario` from the repository root.
