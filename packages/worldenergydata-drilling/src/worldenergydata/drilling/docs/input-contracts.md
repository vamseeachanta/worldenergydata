# Drilling model and calculator input contracts

The model and direct-call boundaries reject invalid numeric values, incomplete
sequences and empty campaigns. These are API domain requirements for
[issue 1344](https://github.com/vamseeachanta/worldenergydata/issues/1344), not
empirical engineering acceptance limits. The existing calculation formulas,
coefficients and legacy result keys are retained.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-11-04 | Define numeric domains, complete sequences and empty-campaign rejection to prevent silently incomplete or nonfinite cost results. |

## Numeric requirements

Real inputs accept finite `numbers.Real` scalars, including Python integers,
floats, fractions and NumPy real scalars. Values are converted to Python floats
and checked for finiteness after conversion. Python and NumPy Booleans, complex
numbers, `Decimal`, numeric text, unit-bearing strings, `None`, NaN and either
infinity are rejected. Counts accept positive `numbers.Integral` values,
including NumPy integers; floating-point counts such as `2.0` are rejected.
Values that cannot be represented as finite Python floats are rejected, including
integer counts beyond that representability boundary. A nonzero input that
converts to zero is also rejected, preserving the sign domain through conversion.
This is a numerical
representation constraint, not a campaign-size qualification.

| Input | Required unit | Domain |
| --- | --- | --- |
| `location_coords` | Decimal degrees, `(latitude, longitude)` | Exactly two finite reals; latitude from -90 to 90 and longitude from -180 to 180, including endpoints; tuples and lists accepted |
| `water_depth_ft` | ft | Nonnegative finite real; zero accepted |
| `planned_md_ft` | ft | Positive finite real |
| `rig_day_rate_usd`, direct `day_rate` | USD/day | Positive finite real |
| `mobilization_cost_usd`, direct `mob_cost` | USD | Nonnegative finite real; zero accepted |
| `learning_curve_factor`, direct `lc_factor` | Dimensionless | Finite real in `(0, 1]`; one means no learning |
| `base_time_days`, `base_well_days`, `base_days_per_well` | days | Positive finite real |
| `well_position` | One-based position | Positive integer; zero and negative positions rejected even when the previous implementation returned the base duration |
| `n_wells_batch`, `n_wells_standalone` | wells | Positive integer; the standalone argument remains ignored after validation |
| `discount_rate` | Dimensionless | Finite real of either sign; remains ignored after validation, with no discounting interpretation |

Table 1. Required units and numeric domains at the model and calculator boundaries.

Plain numbers carry no unit metadata. Callers supply the declared units;
conversion, currency conversion, coordinate datum identification and detection
of mislabeled finite numbers are not established. Geographic bounds do not
establish a coordinate datum or physical suitability. No relationship between
measured depth and water depth is inferred. Default bore design and pressure
classification, category enums and nonblank rig/campaign names remain outside
this contract.

## Sequence and empty-campaign requirements

Each campaign contains at least one well. A `well_id` contains a nonwhitespace
character and is unique within the campaign. Identity comparison is exact and
case sensitive; surrounding whitespace is preserved. Thus `A`, `a` and `A ` are
distinct identifiers, and a sequence must use the exact stored identifiers.

An omitted sequence or explicit `[]` uses insertion order. Any nonempty sequence
contains each campaign well ID exactly once. Duplicate sequence IDs, unknown IDs
and omission of any well are rejected with `ValueError`; no well is silently
dropped or appended. `ordered_wells()` returns a new list retaining the original
site objects in the specified order.

Empty campaigns are rejected at construction. `ordered_wells()` and both public
campaign-cost entry points revalidate current campaign and nested site state,
including in-place list changes, mutated fields, subclasses and objects made
with `model_construct()`. An emptied campaign therefore raises `ValueError`
before any mobilization charge or default duration is produced. Calculator
campaign arguments require `DrillCampaign` instances; mappings and duck-typed
objects are rejected. Subclass inputs are validated using the base-model fields;
subclass-specific calculation behavior is not applied.

Sequence validation enforces completeness; sequence order does not change the
existing cost formulas, which use well count and average depth. Spatial moves,
per-site duration differences and schedule optimization are not calculated.

## Results and compatibility

Input or output domain validation failures raise `ValueError` (including Pydantic's
`ValidationError` subtype). Positive duration results and finite monetary
results are required; overflow is rejected before break-even cost comparison.
Campaign costs are positive USD magnitudes; savings are finite signed USD.
Mobilization allocation can be zero, including output underflow from a positive
cost. The nonzero-to-zero rejection above applies to input conversion.
Learning durations that underflow to zero
are rejected rather than presented as positive drilling durations.
Overflow of intermediate arithmetic, including the raw depth sums used in the
heuristic, is rejected even when an algebraic rearrangement could yield a finite
result. No new numerically stabilized formula is introduced by this contract.

Valid historical arguments retain their arithmetic. Previously tolerated invalid
values now fail, including `discount_rate=None`, `n_wells_standalone=0`, Boolean
inputs, numeric text and floating-point counts. Arrays and Series are rejected;
these calculator boundaries accept scalars. Constructing a campaign copies and
validates its site values; subsequent mutation of the caller's original site
does not alter the campaign. `ordered_wells()` preserves the identities of the
sites within that campaign. Default factors and the legacy
break-even sentinel `1` remain unchanged. Strict floating-point cost comparisons
can still tie when small differences are below representable precision. Physical
duration calibration and monetary comparison tolerance remain unqualified;
[issue 1342](https://github.com/vamseeachanta/worldenergydata/issues/1342) retains
duration qualification scope. No finite upper magnitude establishes engineering
readiness.

## Acceptance and sweep reconciliation

Executable coverage is in
`tests/unit/drilling/test_input_contracts.py`. Synthetic hand calculations check
20 days followed by 10 days, 100 USD shared across two wells as 50 USD/well, and
100 USD + 10 USD/day times 30 days as 400 USD. These establish arithmetic and
unit conventions, not independent physical calibration.

| Acceptance criterion / historical sweep rows | Disposition and focused evidence |
| --- | --- |
| Finite values and signs; rows 23–26, 41, 49 | Model and direct-call domain tests reject each nonfinite, nonnumeric and wrong-sign class; first-position factors and output overflow are checked |
| Complete unique sequences; rows 19–21 | `test_sequence_preserves_all_wells_exactly_once`, `test_sequence_rejects_duplicate_unknown_and_omitted_identifiers`, `test_campaign_rejects_duplicate_well_identifiers` |
| Empty campaigns; rows 33–35 | `test_empty_campaign_is_rejected`, `test_mutated_campaign_is_revalidated_at_consumption`; no empty duration is assumed |
| Unit requirements; rows 46–48 | Table 1 and `test_hand_calculated_units_and_ignored_compatibility_arguments`; actual units and datum cannot be inferred from scalars |
| Sequence-independent costs; row 42 | Complete sequences are required; the existing count/average-depth cost model is retained |
| Bore design and pressure defaults; rows 17–18 | Not established: classification qualification and category enums are outside this issue's numeric, sequence and empty-campaign criteria |

Table 2. Coverage of the accepted API requirements and explicit limits of the historical sweep.

Numeric domains, sequence completeness and empty-campaign rejection have
executable guards and focused tests. The unit criterion is defined by Table 1
and checked through the synthetic hand calculation; unit tags are not validated.
Independent physical qualification, unit-tag validation and the historical
knowledge-pack source/digest reconciliation are not established by these tests.
