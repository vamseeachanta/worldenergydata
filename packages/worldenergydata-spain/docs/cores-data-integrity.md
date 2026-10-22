# CORES data integrity

CORES ingestion preserves Spanish numeric text, distinguishes workbook acquisition
from cache checks, and retains missing quantities through reporting. The safeguards
address issue #1293 without qualifying density, heating value or economic inputs.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-21 | Document parsing, freshness and missing-data safeguards with a worked example. |

## Parsing contract and sources

[Unicode CLDR 48 (2025), Spanish locale data](https://www.unicode.org/Public/cldr/48/)
records a comma decimal symbol and a period grouping symbol in
`common/main/es.xml`, `numbers/symbols[@numberSystem='latn']`. The inherited
`common/main/root.xml` decimal pattern `#,##0.###` supplies grouping in threes.
These files were read from the public CLDR release source. The
[Spain agent pack](../src/worldenergydata/spain/docs/agent-pack.md), section 6,
SF1–SF5 and SF7–SF10, records the affected input and output contracts.

Only text cells follow this convention: `1.234` means one thousand two hundred
and thirty-four, `1.234,5` means that quantity plus one half, and `1,234` means
one plus two hundred and thirty-four thousandths. Native Excel numeric cells
already carry a value; numeric `1.234` remains unchanged. Both XLSX readers retain
cell types so that column inference cannot erase this distinction.

Empty cells and dash placeholders represent missing observations. Malformed text,
nonfinite values, negative monthly production and fractional years raise
`CoresParseError`. Annual summary rows and rows without a year remain excluded.
Plain `Total`, `Grand total`, `Total general` and unnamed columns are excluded.
A longer field name containing the word “Total” remains a field.

Case, accents, punctuation and surrounding whitespace follow the existing density
lookup normalization. Duplicate normalized field/month keys raise before merging.
The product merge requires one-to-one keys and uses the first oil display name,
or the first gas display name when oil is absent, consistently across months.

## Worked example

The following inputs are synthetic parser examples, not physical measurements.
An explicitly supplied audit returns a factor of **2 barrels per source unit**.
No density or heating-value coefficient is inferred or qualified here.

| Month | Field A source cell | Excluded Total cell | Independent answer, barrels |
| --- | --- | --- | --- |
| January | Text `1.234` | Text `1.234` | 2468.0 |
| February | Text `1.234,5` | Text `1.234,5` | 2469.0 |
| March | Native number `1.234` | Native number `1.234` | 2.468 |
| April | Missing | Missing | Unknown |
| May | Native number `0` | Native number `0` | 0.0 |

The method uses decimal place value and the explicit synthetic factor:

- January: `(1 × 1000 + 234) × 2 = 2468`.
- February: `(1 × 1000 + 234 + 5 / 10) × 2 = 2469`.
- March: `(1 + 234 / 1000) × 2 = 2.468`.
- May: `0 × 2 = 0`; zero is an observed value.

The source for the grouping and decimal interpretation is CLDR above; the factor
is a declared synthetic input. Expected values are independent hand calculations,
written in `tests/unit/spain/test_cores_integrity.py` docstrings. The XLSX regression
writes text and native numbers into a workbook and checks the reader boundary.

April contributes no production observation. If the merged monthly frame contains
April because gas was observed, the oil total is incomplete and becomes JSON
`null`, with `oil_bbl_missing_observations`. If an entire row is absent from both
products, no reporting calendar is invented: completeness covers rows present in
the merged frame. Completely observed totals use ordinary summation. All-missing
products remain unknown. HTML labels unknown totals and draws no bars for missing
monthly quantities; a measured zero retains its zero value.

## Acquisition and scheduled refresh

Each downloaded workbook records `acquired_at_utc` and `cache_reused=false`.
Reusing bytes preserves that acquisition time and sets `cache_reused=true`.
`checked_at_utc` records the cache operation. An orphaned cache without acquisition
evidence has an unknown acquisition time, rather than a fabricated download date.

For the complete oil/gas source, `refreshed_at_utc` is the earliest acquisition
instant among both workbooks. This conservative minimum prevents a single-product
update from claiming that the complete source was refreshed. If either time is
unknown, the complete source time is unknown. For example, January oil acquisition
and February gas acquisition still give a January complete-source timestamp.
This is provenance logic from the agent pack SF4, not a freshness acceptance limit.

Scheduled runs fetch by default. Explicit `force_refresh=false` permits offline
cache reuse; `force_refresh` must be boolean. Scheduler `last_refresh` comes from
the source acquisition evidence; `last_checked` records processing completion.
The report labels both meanings. Historical caches with no per-workbook acquisition
evidence need an actual download to establish those times.

## Missing evidence and remaining limits

Fixture extraction keeps absent gas missing. Without a supplied conversion audit,
fixture conversion is `NOT_EVALUATED`, the audit is null, and no default factor is
claimed. An invalid HTTP source date emits a warning before any stored fallback.
Direct report period bounds require valid `YYYY-MM` strings in increasing order.
Incomplete oil totals do not enter the report's economics selection.

Shared empty-production reference-chain behavior remains tracked by #1289. This
change does not qualify source units, density, heating values or prices, establish
an external freshness threshold, add missing calendar months, verify cached-byte
digests, or change the separate production adapter's economic input defaults.
Regressions use synthetic inputs; no live CORES download is needed for the tests.
