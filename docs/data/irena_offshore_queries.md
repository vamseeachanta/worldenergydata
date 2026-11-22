# Offline offshore wind queries

## Summary

Country/year selection makes caller-normalized offshore wind observations
available for analysis with capacity in MW and generation in GWh or MWh.
The entire input is validated before selection. Row citations and source URLs
are retained. This extends the [offline loader](irena_offshore_wind.md);
it does not establish native-source accuracy or permission to reuse data.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add country/year queries and explicit generation units for offline analysis. |

## Python interface

```python
from pathlib import Path

from worldenergydata.energy_mix.query import query_export

result = query_export(
    Path("permitted-normalized.csv").read_bytes(),
    countries=["Denmark", "Germany"],
    start_year=2023,
    end_year=2024,
    generation_unit="MWh",
)
```

The country names and years above illustrate caller inputs, not source coverage.
Country matching is case insensitive, follows the loader's country key, and
never infers a country code. Repeated countries select each row once. Input
row order is retained. Year bounds are inclusive; either may be omitted.
`countries=None` selects all countries; an empty iterable selects none.
Unknown countries or years without observations return only the CSV header.
Invalid observations fail even when they would be excluded by the query.
No totals are inferred: an area aggregate supplied in the input remains an
individual observation and is never added to its member countries.

The result is UTF-8 CSV bytes. Default GWh queries retain all original field
values. MWh queries replace only `generation_gwh` with `generation_mwh` and
convert nonblank generation. Blank means unavailable; reported zero remains
zero. Capacity remains MW. MWh query results are a separate output contract;
the loader continues to require the original GWh header and rejects MWh input.

## Unit basis

The [BIPM SI Brochure](https://www.bipm.org/documents/20126/41483022/SI-Brochure-9.pdf),
ninth edition (2019), version 4.01 (June 2026), section 3, table 7, defines
giga as a factor of `10^9` and mega as `10^6`. Hence:

```text
generation_mwh = generation_gwh * (10^9 / 10^6)
               = generation_gwh * 1000
```

The hour cancels in this conversion. This equation converts energy units;
no generation is inferred from capacity. Decimal arithmetic retains supplied
digits without binary floating-point rounding. Scientific notation keeps
extreme exponents compact. Conversion fails if exact decimal representation
is unavailable. No measurement uncertainty or accuracy limit is assigned.

The independent synthetic test example is `20.25 GWh * 1000 = 20250 MWh`.
Tests also cover missing generation, reported zero, decimal precision, compact
extreme exponents, country/year selection and command output preservation.
These are hand-calculated examples, not independently verified IRENA values.

## Command interface

```bash
python -m worldenergydata.energy_mix query \
  --input permitted-normalized.csv \
  --country Denmark --country Germany \
  --start-year 2023 --end-year 2024 \
  --generation-unit MWh --output selected.csv
```

Omit `--output` to write CSV to standard output. Output files must not already
exist, and the input cannot be overwritten. Query-specific options require
`query`; provenance options require `load`. A query retains each row's source
URL and citation but does not emit a manifest. Keep the original input and its
loader manifest separately: the original digest does not describe a filtered
or converted result. Existing `load` and refused `fetch` operations remain
available.

## Source access and later slices

On 2026-10-19 the first source request, to the
[IRENA robots endpoint](https://www.irena.org/robots.txt), returned HTTP 403
with an Azure WAF challenge. Source access stopped there; the current landing
page, export schema and reuse terms were not retrieved. No native observations
are added and no automatic fetching is enabled. The BIPM document returned
HTTP 200 and supplied the conversion basis above.

Native-export ingestion, verified capacity/generation observations and their
reuse rights remain later slices of issue 1095. Source accuracy, rights and
intended-use checks are **NOT_EVALUATED** by this offline query interface.
