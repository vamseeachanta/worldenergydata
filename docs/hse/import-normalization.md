# Import normalization

Statistics CSV imports preserve literal text and exact integral counts while
representing missing data as `None`. Pipeline narratives identify missing text;
Mexico report parsing recognizes grouped numbers and accented Spanish headers.
These rules concern parsing, without qualifying source units or engineering results.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Document explicit parsing contracts and a synthetic example to prevent silent missing-value and number corruption. |

## Statistics missing-value policy

The packaged statistics importer, its compatibility import and the physical
legacy copy read CSV with `dtype=str`, `na_values=["NA", ""]` and
`keep_default_na=False`. Only exact `NA` and empty cells are CSV missing tokens.
`N/A`, `null`, `NaN`, whitespace and other text remain literal. Before field guards,
scalar nulls (`None`, floating NaN, pandas NA and NaT) become `None` in a copy of
the record. Lists and dictionaries remain unchanged. See the pandas 2.3
[read_csv](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.read_csv.html)
and [isna](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.isna.html)
references for the parser options and scalar missingness.

Count strings accept signed digits and an optional zero-only fractional part
with surrounding whitespace trimmed: `3.0` becomes integer `3`, using exact
integer conversion without an intermediate float. Exponents, nonzero fractions
and nonfinite text become `None`. Signs retain legacy behavior; count ranges are
not validated. This grammar retains the contracts in PRs #1395 and #1614.
Direct dictionary callers supply already typed values: actual scalar nulls are
normalized, literal text remains literal, count strings use the same grammar,
and other non-null values retain their types, including numeric floats.

A missing required `report_date` or `operator` fails packaged validation. The
compatibility import resolves to that packaged implementation. The physical
legacy source retains its historical schema and base-class validation. Its
other legacy files remain present; their independent execution and possible
retirement require a separate maintainer decision.

## Worked synthetic CSV example

Input (no external data):

```csv
incident_id,report_date,operator_name,fatality_count,facility
sample-a,2026-01-01,Synthetic operator,NA,NA
sample-b,2026-01-01,NA,,text
sample-c,2026-01-01,Synthetic operator,3,text
sample-d,2026-01-01,Synthetic operator,3.0,N/A
```

Method: fetch the CSV, normalize each record and validate it. Exact missing
tokens become scalar nulls, then `None`; dates become Python datetimes; mapped
text is retained. By hand, `3.0 = 3 + 0/10 = 3`. The answer below projects the
normalized records to the supplied columns and validation result:

| bsee_incident_id | report_date | operator | fatality_count | facility_name | valid |
| --- | --- | --- | --- | --- | --- |
| sample-a | datetime(2026, 1, 1) | Synthetic operator | None | None | True |
| sample-b | datetime(2026, 1, 1) | None | None | text | False |
| sample-c | datetime(2026, 1, 1) | Synthetic operator | 3 | text | True |
| sample-d | datetime(2026, 1, 1) | Synthetic operator | 3 | N/A | True |

Every record also contains the same date as `incident_date`. Other optional
counts and `field_name` are `None`; absent `severity` is omitted. The example
is exercised by `tests/unit/hse/importers/test_statistics_missing_values.py`.

## Pipeline text and Mexico formats

Pipeline text aliases skip scalar nulls and empty or whitespace-only strings.
The first available alias is used; when none is available, ID and location stay
`None` through the report and appear as `missing` in the narrative. Literal
strings supplied directly by dictionary callers are preserved.

PDF numeric parsing gives precedence to nonzero-leading comma groups of three
digits with an optional dot fraction, following PR #1399. Thus `1,234` is `1234`,
`1,234,567` is `1234567` and `1234.5` is unchanged. The grouping size and symbols
are supported by Unicode CLDR **48.2**, Latin symbols and decimal pattern
`#,##0.###` in the [root number data](https://github.com/unicode-org/cldr/blob/release-48-2/common/main/root.xml).
The old decimal-comma fallback is retained: `12,5` becomes `12.5`, and
zero-leading `0,125` becomes `0.125`. This precedence resolves ambiguity by policy;
it does not detect the locale or units of a live PDF. Identifier columns and the
existing majority-conversion heuristic are unchanged.

Excel headers use NFKD followed by removal of combining marks before mapping
(including custom mapping keys). This uses Python 3.11
[unicodedata.normalize and combining](https://docs.python.org/3.11/library/unicodedata.html).
For example, `Producción Aceite` maps to `oil_production`. `required_columns`
on `normalize_columns`, `load`, `parse_production_report` and `parse_well_report`
accepts source headers or canonical targets and raises with the missing/unmapped
name. Generic optional unknown headers remain available. Specialized production
parsing requires a recognized production measure; well parsing requires a
recognized well identifier, coordinate or depth. A wholly unrecognized schema
raises with the original column names. Callers can declare stricter requirements;
no particular hydrocarbon or coordinate layout is assumed.

Chrome language and download preferences share one dictionary passed once to
[Selenium Chromium Options.add_experimental_option](https://www.selenium.dev/selenium/docs/api/py/selenium_webdriver_chromium/selenium.webdriver.chromium.options.html).
Tests inspect the options object without launching a browser.
