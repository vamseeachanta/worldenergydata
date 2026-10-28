# Annual disclosure foundation

Annual monetary disclosures now have a typed schema and a small, cited seed
dataset, separate from sanction-point calibration data. Both operator and
project records retain the original amount, currency, magnitude and wording.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Add the schema, seed, provenance and exact-linkage contract for recurring disclosures. |

## API and scope

Import `OperatorDisclosureRecord`, `ScopeType`, `FilingType`,
`NormalizedMetricName` and `load_operator_disclosures_dataset` from
`worldenergydata.cost.data_collection`. The cost package's root exports are
unchanged. Implementation lives under the cost workspace member's
`src/worldenergydata/cost/data_collection/` directory.

The record requires:

- Identity: `operator`, `fiscal_year`, `scope`, `filing_type`.
- Metric: `metric_name_normalized` and `metric_name_reported`.
- Money: finite `Decimal` `amount`, uppercase alphabetic `currency`, magnitude
  `unit` (`units`, `thousand`, `million`, `billion`), and `value_basis`.
- Evidence: `source_title`, absolute HTTP(S) `source_url`, `page_reference`,
  `quoted_text`, `confidence`, `source_priority`.
- Project scope: a nonblank `project_name`. Operator scope forbids that field.

Project metrics cannot appear on operator records, or operator metrics on project
records. Currency validation requires an uppercase alphabetic code supplied by
the caller, without claiming registry membership. Text and decimals are preserved without trimming,
case folding, rescaling, exchange rates or inflation adjustment. Signed amounts
and true zero remain valid. Empty and nonfinite amounts are invalid.

`unit` is the magnitude of the currency amount, not a physical unit or a computed
multiplier. `value_basis` records gross/net, group/parent and real/nominal context
in source terms. A project record's fiscal year identifies the annual disclosure;
its amount can be a lifetime estimate rather than expenditure incurred that year.

The schema reuses `DisclosureCitation` and its confidence/source-priority enums.
It keeps the existing generic `DisclosureRow` ingestion contract unchanged:
its corporate/segment scopes and generic float values are not silently mapped
into this operator/project monetary model. Analytics and downstream consumers
also retain their current APIs. No automatic adapter is introduced here.

## Seed and sources

The seed contains only current-year observations from each report's own edition.
The acceptance cap comes from the [issue plan's acceptance criteria](../../plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md#acceptance-criteria).
There is no download on import or load, no gap filling and no inferred values.

| Scope | Fiscal year | Amount | Currency | Magnitude | Primary source and locator |
| --- | --- | --- | --- | --- | --- |
| Project | 2022 | 16 | NOK | billion | [Annual Report 2022](https://akerbp.com/wp-content/uploads/2023/03/aker-bp-annual-report-2022.pdf), p. 17 (PDF p. 18), two-tieback investment paragraph |
| Project | 2023 | 16 | NOK | billion | [Annual Report 2023](https://akerbp.com/wp-content/uploads/2024/03/aker-bp-annual-report-2023.pdf), p. 12, two-tieback investment paragraph |
| Operator | 2022 | 1626987 | USD | thousand | Annual Report 2022, p. 117 (PDF p. 118), alternative performance measures, CAPEX, Group 2022 column |
| Operator | 2023 | 3267.3 | USD | million | Annual Report 2023, p. 193, alternative performance measures, CAPEX, Group 2023 column |

Each row repeats its own report identity, URL, locator and supporting quote in the
dataset. Both report URLs were opened successfully during source verification.
The project sample is the reported bundle of two subsea tiebacks, with approximate
gross investment in real terms; neither report specifies a base-price year. The
amount is not attributed to either individual tieback. The operator observations
use the consolidated Group column and include investment-related lease payments.
The bundle uses a descriptive source-local `project_name`, identified by the
cited paragraphs, rather than claiming a canonical sanction-record name.

The current-year amount in the earlier report is retained even where the next
report's comparative column rounds it to a different magnitude. Comparative
columns marked restated in the earlier report belong to earlier years and are
excluded. This sample is not a constant-portfolio or comparable-cost series.

## Derived linkage contract

Use `disclosure_row_is_linkable(record.scope.value)` before
`resolve_cost_datapoint_link(record.operator, record.project_name)`.
Only project records participate. Candidate identity requires exact equality of
both `operator` and `project_name` with a `CostDataPoint` from
`load_public_dataset()`, as specified in the issue plan's linkage strategy.
Case, whitespace, aliases and phase names are not normalized.

The existing resolver returns `linked`, `unlinked` or `ambiguous`. Multiple
sanction records for the same pair remain ambiguous; no candidate is selected.
The seed's development bundle is valid but unlinked. Operator rows are always
ineligible regardless of apparent name matches. Linkage is computed on demand;
there is no nullable sanction reference or persistent foreign key in the schema.
Identity linkage alone never establishes amount or ownership comparability.

## Worked example and verification

The [runnable example](../../../examples/workflows/annual-cost-disclosures/README.md)
shows inputs, method and literal answer. No scientific equation is required:
stored money is the reported number and context unchanged. Exact string equality
implements the linkage rule. Expected test amounts are independently transcribed
from the source paragraphs and table cells listed above.

Tests cover missing/blank provenance, malformed URLs, nonfinite money, decimal
precision, scope/metric separation, derived exact linkage, seed size, both annual
series, source-vintage discipline, immutable records, fresh loads, absent-year
preservation and the example's literal output.

## Known limits and follow-up

Restatements and versioning fields are outside this schema and seed. Unknown
fields are rejected. The schema can validate evidence structure, but identifying
a restated source row remains a curation responsibility. High confidence reflects
primary-source transcription, not a quantitative uncertainty or tolerance.

No derived annual changes, normalization, automated ingestion, broad backfill or
economics integration is added. Further linkage hardening belongs to #335,
comparability policy to #336, ingestion/citation automation to #337 and consumer
analytics to #338. Existing implementations of those contracts are preserved.
