# Annual cost disclosures example

The example prints the curated annual monetary observations and derives exact
project links, preserving the amount, currency and magnitude from each report.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Add a runnable example of the annual disclosure foundation. |

With the cost package and its dependencies installed, run from the repository root:

```sh
python examples/workflows/annual-cost-disclosures/example.py
```

Inputs are the loader's cited current-year report observations. The method is
identity transcription followed by project-only exact name matching; it performs
no monetary calculation. The answer is:

```text
scope | fiscal year | reported metric | as-reported amount
project | 2022 | total investments | 16 NOK billion
project | 2023 | total investments | 16 NOK billion
operator | 2022 | CAPEX | 1626987 USD thousand
operator | 2023 | CAPEX | 3267.3 USD million
project linkage: unlinked
project linkage: unlinked
operator linkage: ineligible
operator linkage: ineligible
```

The amounts and years come from the current-year columns and investment
paragraphs in [the source table](../../../docs/modules/cost/ANNUAL_DISCLOSURES.md#seed-and-sources).
The development bundle has no exact sanction-record counterpart. That is a valid
unlinked result. Operator records are excluded before invoking the resolver.

The two operator amounts use different scales. Subtracting them directly would
be invalid. No year-over-year change or currency conversion is computed here.
