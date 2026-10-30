# Annual disclosure currency normalization and comparability

The additive money contract preserves reported amounts, currencies, units,
scales, metric labels and provenance. It produces separate base-year USD
amounts only when the monetary and economic bases are explicit. Incomplete
evidence remains available with `NOT_EVALUATED`, `not_comparable`, reason
codes and null normalized fields. It never substitutes zero for missing data.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-20 | Added a sourced money policy, deterministic utilities and a worked example to make annual disclosure comparisons auditable. |
| 2 | 2026-10-22 | Validate serialized comparison keys and currency syntax, and specify the complete decimal context to keep results reproducible. |

## Contract and scope

`worldenergydata.cost.data_collection` exports `DisclosureMoney`,
`NormalizationPolicy`, `NormalizedDisclosureMoney`,
`normalize_disclosure_money`, `normalize_disclosure_money_rows` and
`money_values_are_comparable`.

The money input is a composition boundary for annual disclosure evidence.
The existing ingest `DisclosureRow` and analytics `DisclosureRecord` are partial
contracts without the complete monetary basis. Callers must explicitly map
their evidence into `DisclosureMoney`; neither ingest nor analytics records are
silently reinterpreted. The sanction dataset, predictor, linkage semantics and
existing analytics behavior are unchanged.

| Input | Required meaning |
| --- | --- |
| `amount` | Finite decimal, retaining the reported magnitude; zero and signed reversals are allowed. |
| `currency`, `unit` | Identical explicit currency codes, such as `EUR` and `EUR`; symbols, combined scale strings and cost-per-volume units are refused. |
| `magnitude_scale` | Exactly `units`, `thousand`, `million` or `billion`, using the short scale. |
| `fiscal_year` | Positive integer calendar-year label. Missing years are never inferred. |
| `as_reported_metric_name` | Original metric label, retained verbatim. |
| `metric_name_normalized` | Caller-declared economic metric used in the comparison key. |
| `scope` | `operator`, `corporate`, `segment` or `project`; these remain distinct. |
| `comparison_basis` | Nonblank caller attestation of accounting perimeter, cash/accrual, gross/net interest and other relevant economic definitions. |
| `period_basis` | Exactly `calendar_year_flow`; other fiscal calendars and closing balances need a different rate convention. |
| `price_basis` | Exactly `nominal`; already rebased amounts must not be rebased again. |
| `provenance` | Source metadata carried unchanged in an independent deep snapshot. Citation verification remains the ingest contract's responsibility. |

`NormalizationPolicy` requires a policy identifier, annual escalation rate and
its evidence. The target is USD and the default base year is 2020, as specified
in the [issue-336 plan](../../plans/2026-04-22-issue-336-currency-normalization-and-comparability-policy-for-annual-disclosures.md).
The base year can be supplied explicitly. The plan's illustrative 3.0% rate
has no qualified empirical series here, so it is **required input**, never a
default. Assumptions must be labelled **assumed, based on previous experience**.
Explicit `None` for the rate or missing evidence yields `NOT_EVALUATED`,
including same-year and same-currency rows; the policy must be complete.

## Method and sources

Let `A` be the reported amount, `S` its magnitude multiplier, `F[y,c]` the
annual USD-per-currency-unit rate, `r` the supplied annual nominal price
escalation assumption, `y` the reported year and `b` the target year.

```text
nominal_USD = A * S * F[y,c]
base_year_USD = nominal_USD * (1 + r) ** (b - y)
```

The FX direction comes from the starred currency note in the Federal Reserve's
[G.5A annual 2020 table, revised November 1, 2021](https://www.federalreserve.gov/releases/g5a/20210104/).
The rates are averages of daily noon buying rates; they are neither closing
rates nor transaction-weighted rates. Calendar-year averaging is an explicit
comparison approximation. It does not represent formal financial-statement
translation or remove intra-year exchange-rate volatility.

Price rebasing uses [NIST HB 135 (2020), section 3.3.3.1, equation 3-13](https://doi.org/10.6028/NIST.HB.135-2020).
A later target year multiplies the price factor; an earlier target year uses
its reciprocal. This is price escalation, with `1 + r > 0`, not investment
discounting. NIST supplies the equation, not an upstream-industry inflation
rate. There is no purchasing-power-parity adjustment or claim of a measured
constant-price series.

Magnitude multipliers are defined as unity, 10³, 10⁶ and 10⁹. The powers
correspond to kilo, mega and giga in
[NIST SP 330 (2019), Table 7](https://doi.org/10.6028/NIST.SP.330-2019).
Those powers define this financial short-scale convention; money is not an
SI quantity.

The immutable bundled FX table is deliberately small:

| Currency | Year | USD per reported currency unit |
| --- | --- | --- |
| EUR | 2019 | 1.1194 |
| EUR | 2020 | 1.1410 |
| GBP | 2019 | 1.2768 |
| GBP | 2020 | 1.2829 |

Every observation cites the G.5A table above. USD uses the identity ratio in
every year. No other currency or year is filled, inverted or interpolated.
A supplied `FxTable` must have a version, finite positive rates, citations and
unique currency/year keys; USD observations are refused because its identity
ratio is fixed. Both reported currency/unit fields and supplied FX observations
require three uppercase ASCII letters. No symbols, whitespace, case conversion
or alias expansion are supported. This is a syntax check, not verification
against a currency registry. Invalid reported codes remain in the raw snapshot
with `unsupported_currency` or `unsupported_unit`; invalid FX codes raise
validation errors before the table can be used. The source responses were
opened on 2026-10-20; this module performs no network requests.

Arithmetic uses a fresh decimal context with 28 significant digits and
`ROUND_HALF_EVEN`, following the
[Python 3.10 decimal context](https://docs.python.org/3.10/library/decimal.html#decimal.Context).
Every context parameter is explicit, including exponent bounds of -999999 and
999999, capitals set to 1, clamp set to 0 and initially clear flags. Invalid
operations, division by zero, overflow and underflow are trapped; other traps
are disabled. Neither the current context nor mutable `DefaultContext` settings
alter the result. Overflow and underflow produce `NOT_EVALUATED`. Output is not
quantized to cents or millions; JSON represents decimals as strings. Display rounding belongs to the consumer.

## Output and comparison policy

The Pydantic output model supplies a schema through
`NormalizedDisclosureMoney.model_json_schema()` and JSON serialization through
`model_dump_json()`. A normalized row has these independent fields:

- `as_reported`: complete deep snapshot of the money input.
- `normalized_amount`, `normalized_currency`, `normalized_unit`,
  `normalized_magnitude_scale`, `normalized_base_year`: USD in individual units.
- `normalization_method`: `fx_then_base_year_adjustment_v1`.
- `policy_id`, `policy_fingerprint`, `fx_table_version`: reproducibility metadata.
- `fx_rate`, `fx_source`, `annual_escalation_rate`, `escalation_source`: exact
  applied policy inputs and their evidence.
- `normalization_status`, `comparability_status`, `reasons`, `comparison_key`:
  eligibility and basis information.

The batch view preserves order and emits one result for every input. Missing
fields, mismatched currency/unit pairs, unsupported scales, scopes, periods
or price bases and missing FX or escalation evidence produce explicit reason
codes. Nonfinite input numbers and malformed policies raise validation errors.
Arithmetic outside the decimal context's range yields
`decimal_calculation_failed` with no normalized value.

`money_values_are_comparable(a, b)` requires two successful results with exactly
the same normalized metric, scope, declared economic basis, currency, target
year, method and full policy fingerprint. A changed assumption, source,
table version or table order conservatively creates a different policy.
JSON validation rejects a serialized comparison key that disagrees with the
row's metadata. The comparison gate also reconstructs the tuple from that
metadata and refuses a stale key. These consistency checks do not authenticate
the reported evidence or the policy fingerprint's origin.
Currency conversion does not establish equivalent asset boundaries, ownership
shares, accounting treatments, cash timing or metric definitions. A nonblank
basis is an attestation by the caller, not an independently verified fact.
Do not treat the row's `comparable` status alone as a pairwise comparison.

## Worked example

[Executable example](../../../examples/cost/normalize_annual_disclosures.py)
uses synthetic disclosures, not real filings. In an environment with the cost
package dependencies installed, run:

```sh
python examples/cost/normalize_annual_disclosures.py
```

Both rows declare calendar-year nominal capex, operator scope, consolidated
cash expenditure and net interest. The supplied rate is the explicit 3.0%
scenario described above, assumed, based on previous experience.

| Input | Amount | Currency/unit | Scale | Year |
| --- | --- | --- | --- | --- |
| First disclosure | 2 | EUR/EUR | million | 2020 |
| Second disclosure | 2.282 | USD/USD | million | 2020 |

Independent hand calculation:

```text
First:  2 * 1,000,000 * 1.1410 * 1 = 2,282,000 USD
Second: 2.282 * 1,000,000 * 1 * 1  = 2,282,000 USD
```

The monetary results are equal and the pair is comparable under the declared
basis and shared policy. Original EUR and USD values remain separate.
If the second row instead declares gross interest, the comparison gate refuses
the pair even if the amounts coincide.

For the price-year direction, a synthetic USD amount of 100.0 in 2019 becomes
103.0 in 2020 under the same assumed rate. Conversely, 103.0 USD in 2021
rebases to 100.0 USD in 2020. These follow equation 3-13 by multiplication and
division; tests spell out each independent calculation.

## Validation and remaining limits

The focused suite covers raw preservation, unit pairing, all supported scales,
published EUR/GBP quote direction, forward/reverse rebasing, zero and signed
amounts, missing evidence, unavailable FX, decimal failures, policy changes,
economic-basis gating, serialization and the executable example. It also covers
independent metadata changes with stale keys, ambiguous matching currency/unit
pairs, invalid custom FX codes and altered default/current decimal contexts.

Live FX ingestion, non-calendar fiscal averages, transaction/closing rates,
qualified escalation series, restatements and adapters for existing downstream
analytics remain follow-up work. Do not copy these results into a raw field
named `reported_capex_usd_mm`; that would conflate normalized and reported data.
