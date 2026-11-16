# Royalty assumptions versions

The no-argument default is explicitly **`legacy-v1`**. It retains the complete
shipped assumptions table, including the rounded deep-water royalty fraction
`0.188`. Opt-in **`source-note-v2`** changes only those royalties to `0.1875`.
The difference is `0.0005`, or USD 500.0 per USD 1,000,000.0 gross revenue.
The rounded fraction is a compatibility value, not a legal rate.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-15 | Version the assumptions explicitly while retaining caller results. |

Table 1. Initial version guide.

## Selection and rates

```python
from worldenergydata.fdas.core.config import AssumptionsManager

default = AssumptionsManager()  # assumptions_version == "legacy-v1"
legacy = AssumptionsManager(version="legacy-v1")
source_note = AssumptionsManager(version="source-note-v2")
```

| Development-system key | `legacy-v1` fraction | `source-note-v2` fraction |
| --- | ---: | ---: |
| `dry` | 0.125 | 0.125 |
| `subsea15` | 0.188 | 0.1875 |
| `subsea20` | 0.188 | 0.1875 |
| `default` or unknown key | 0.188 | 0.1875 |

Table 2. Illustrative royalty fractions; unknown keys use the existing default row.

Each manager owns a fresh table. `DEFAULT_ASSUMPTIONS` remains the legacy table;
all costs, prices and discount assumptions agree between the built-in versions.
DataFrame construction, `from_dict` and `from_excel` retain supplied values and
report `assumptions_version == "custom"`. A custom DataFrame combined with an
explicit built-in selector raises `ConfigurationError`; unknown selectors also
raise it. Factory signatures are unchanged.

Without a fiscal deck, `CashflowEngine` reads the selected table. A fiscal deck
takes precedence over the assumptions. An explicit `royalty_rate`, including
zero, takes precedence for flat, none and deckless paths; sliding-scale decks
require monthly production rates and reject an explicit flat override.

## Source basis and worked arithmetic

- [BOEM Sale 249 Final Notice](https://www.govinfo.gov/content/pkg/FR-2017-07-14/pdf/2017-14868.pdf#page=3),
  Federal Register 82, 14 July 2017, p. 32579, "Royalty Rate": historical
  sale-specific percentages of 12.5% below 200 m and 18.75% at or above 200 m.
- [NIST SP 811](https://www.nist.gov/pml/special-publication-811/nist-guide-si-chapter-7-rules-and-style-conventions-expressing-values#7102),
  2008 edition, section 7.10.2: percent represents 0.01; therefore
  `12.5 / 100 = 0.125` and `18.75 / 100 = 0.1875`.
- [OpenStax, Principles of Finance](https://openstax.org/books/principles-finance/pages/16-2-net-present-value-npv-method),
  2022 edition, section 16.2, "Net Present Value Calculation": present-value
  summation. First-month time zero and effective monthly conversion are the
  repository's `core.financial.calculate_npv` convention, not textbook timing.

Sources were retrieved for the plan on 2026-11-15 and checked again on
2026-11-16. Source vintages are given above; retrieval is not a legal effective date.

For two consecutive synthetic months, each with USD 1,000,000.0 gross revenue
and explicitly zero costs, royalty equals gross times fraction and net equals
gross less royalty. Dry royalty/net are USD 125,000.0 / 875,000.0 per month;
deep-water legacy values are USD 188,000.0 / 812,000.0, versus source-note values
of USD 187,500.0 / 812,500.0. Zero-discount NPVs are respectively USD 1,750,000.0,
1,624,000.0 and 1,625,000.0. At a synthetic 10.0% annual rate, the expected NPV
is `net_0 + net_1 / 1.10**(1/12)`. All example inputs are synthetic.

## Reproduction and qualification limits

Version selection alone does not reproduce a historical run: original inputs,
overrides, dependency versions and algorithms are also required. A fiscal deck
can override the selected royalty. No reports or production datasets are changed.
These table conventions do not establish current Gulf law, actual lease terms,
water depth, sale date, royalty relief or tax treatment. A development-system
key does not qualify a lease. Broader fiscal qualification remains separate.
