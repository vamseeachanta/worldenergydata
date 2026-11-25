# Italian concession CSV structural inspection

## 1. Summary

The complete public CSV passed structural inspection at the time of retrieval
on 23 November 2026: 3,663 data records span 2004-2026, with no duplicate full
identity tuples and no exactly empty month cells. The decision remains
`REVIEW_MAPPING`; FDAS production remains `REQUIRES_MAPPING`. Structure alone
does not establish numeric meaning, completeness or field readiness.

## Revision history

| Revision | Date (UTC) | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-23 | Full-file structural inspection was added to resolve the earlier partial-byte limitation. |

Table 1. First issue of this inspection record; the dated source assessment remains unchanged.

## 2. Source and retained evidence

Publisher: MASE / UNMIG, *Produzione nazionale di idrocarburi*.

- [Production page](https://unmig.mase.gov.it/ricerca-e-coltivazione-di-idrocarburi/produzione-nazionale-di-idrocarburi/)
- [CSV locator](https://unmig.mase.gov.it/wp-content/uploads/dati/produzione/produzione-2026.csv)
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The page states: “I dati sono distribuiti con licenza Creative Commons
Attribuzione 4.0 Internazionale”. Attribution for this inspection: Source:
MASE / UNMIG, *Produzione nazionale di idrocarburi*, CC BY 4.0; accessed
23 November 2026. The inspection summarizes structure without changing source
values. The page and CSV were each requested once, without credentials or
redirect following; both returned HTTP 200.

| Evidence | Retrieved at (UTC) | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Production page | 2026-11-23T01:06:45.260218Z | 97,001 | `60e984bbfe67d7a59ae11d968fca1f1b361ff6773079a8aaf12091bba897c243` |
| Complete CSV | 2026-11-23T01:07:48.129926Z | 502,041 | `7cff01957f9fd21d75b2f95c60c84321b3400c82c0b170881ae69dfbd1d72d9f` |

Table 2. Response-body identifiers, distinct from publisher vintage or a freshness claim.

The raw CSV, page, response headers, retrieval metadata and JSON inspection
report are retained outside Git in task scratch storage as `production.csv`,
`terms.html`, `production.headers`, `terms.headers`, `production.json`,
`terms.json` and `inspection.json`. The saved CSV was read back, verified
against its recorded digest, and inspected. The saved report was read back and
compared with the in-memory report. This is local retention; backup is not
established. No source rows or concession names are reproduced here.

## 3. Method and results

`worldenergydata.international_sources.italy_inspection.inspect_csv` takes bytes,
a caller-selected byte cap and an expected SHA-256. The live check used
5,000,000 bytes. Oversize inputs, digest mismatch, invalid UTF-8, header drift,
wrong record widths, null characters, invalid years, empty required identities
and malformed CSV prevent a valid report. Empty files and header-only files
also fail. The schema is the exact 19-column header retained in
`docs/data/eu-tail-source-assessment.json`.

Every data record is inspected. Duplicate detection uses all six unmodified
identity/context cells: mineral, year, location flag, title, operator and region.
Physical start and end lines locate records, including quoted multiline cells.
Duplicate identities are disclosed with all source start lines; records are
neither aggregated nor discarded. An invalid record stops at its first location.

The observed mineral categories are `GPL`, `Gas`, `Gasolina` and `Olio`.
The twelve empty-month counters are all zero. This means only that each month
cell contains text; it does not establish that every month has measured output.
All month and annual-total tokens remain text. Empty text, whitespace, unknown
tokens and literal zero remain distinguishable. No locale, totals arithmetic,
physical units, conversions or future-month semantics are inferred.

## 4. Offline reproduction

After separately acquiring and qualifying a local copy, the retained observation
can be reproduced with the standard library and the source tree on `PYTHONPATH`:

```python
import json
from pathlib import Path
from worldenergydata.international_sources.italy_inspection import inspect_csv

report = inspect_csv(
    Path("production.csv").read_bytes(),
    expected_sha256="7cff01957f9fd21d75b2f95c60c84321b3400c82c0b170881ae69dfbd1d72d9f",
    max_bytes=5_000_000,
)
print(json.dumps(report, ensure_ascii=False, indent=2))
```

A newer publisher file requires a new retrieval observation and independent
expected digest. Recomputing an expected digest from an unknown replacement
does not authenticate the retained observation. Acquisition and rights checks
are caller responsibilities; the inspector performs no network or cache writes.

## 5. Verification

The existing assessment suite passed 26 tests at BASE. Before implementation,
all 37 new synthetic cases failed because the inspector was absent. After
implementation, all 165 tests in `tests/unit/international_sources/` and
`tests/unit/sources/test_eu_tail_assessment.py` passed without skips.
The synthetic cases cover BOM/no-BOM, quoted separators and multiline cells,
exact headers, duplicate headers and identities, record widths, required cells,
calendar years, raw tokens, byte caps, expected digests and malformed bytes.
Existing tests retain the concession-mapping and restricted-source reuse gates.
Black, isort, flake8, Bandit, direct file hooks, the repository structure check,
the engineering-register check and Gitleaks passed. The documented recipe
reproduced the retained JSON report. Markdownlint was unavailable; hosted
checks and second-provider review remain pending.

The package tests referenced below were included in that run. The test command
uses the repository's documented `--noconftest` mode, empty default reporting
options, disabled pytest cache and task-local temporary storage.

## 6. Known limits and failure-path sweep

The whole `international_sources` package was inspected with:

```sh
rg -n 'except|\bcontinue\b|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|\b(int|float)\(|unit|cache|0\.05|5 ?%' src/worldenergydata/international_sources
```

The sweep records 14 behavior locations below; none swallows an exception.
There are no error-path empty-result returns or empty-result cache writes.
Counter initialization is a count, not an assumed production value.
Paths below are relative to `src/worldenergydata/international_sources/`.
Each detection test is in the package suite run in section 5.

| Location | Behavior or limitation | Detection |
| --- | --- | --- |
| `argentina.py:53` | Missing resource lists produce no candidates; completeness is not established. | No detection check exists for the missing list; issue pending. |
| `argentina.py:55` | Non-CSV records are filtered. | `test_non_csv_and_unmeasured_sizes_do_not_become_download_candidates` |
| `argentina.py:61` | Invalid declared sizes become unknown. | `test_non_csv_and_unmeasured_sizes_do_not_become_download_candidates` |
| `argentina.py:66` | Sorting uses zero only after the known/unknown discriminator. | `test_catalogue_preserves_rights_frequency_and_smallest_resource` |
| `client.py:64` | JSON decimal text is converted to finite binary float. | `test_overflowing_json_number_is_rejected` |
| `client.py:116` | Invalid JSON/UTF-8 is re-raised, not suppressed. | `test_non_json_or_ambiguous_json_fails_closed` |
| `colombia.py:20` | Source oil/gas units are declared as bbl/Mcf. | `test_gas_uses_its_own_column_without_inventing_oil_or_water` |
| `colombia.py:105` | Year/month text is converted after digit checks. | `test_invalid_monthly_period_is_rejected` |
| `colombia.py:107` | Invalid periods are re-raised. | `test_invalid_monthly_period_is_rejected` |
| `colombia.py:113` | Empty/null volumes remain unknown. | `test_source_nulls_preserve_unknown_volumes` |
| `italy_inspection.py:46` | Invalid UTF-8 is re-raised. | `test_invalid_encoding_quoting_and_nulls_are_rejected` |
| `italy_inspection.py:54` | Empty-cell counters start at zero and count exact empty text only. | `test_literal_tokens_and_quoted_separators_are_preserved` |
| `italy_inspection.py:73` | Four ASCII calendar digits become an integer; numeric production is untouched. | `test_year_is_an_explicit_calendar_integer` |
| `italy_inspection.py:86` | Malformed CSV is re-raised with its start line. | `test_invalid_encoding_quoting_and_nulls_are_rejected` |

Table 3. Failure-path and assumption inventory, including unchanged package behavior.

Numeric locale interpretation, annual-total reconciliation, semantic duplicate
normalization, units and reference conditions, title-to-field relationships,
FDAS inputs, source registration and any country chain remain outside this
slice. Existing dated assessment JSON/HTML remains unchanged. Structural
success does not establish those requirements. The source catalogs were not
available in the inspected workspace; no catalog registration or dataset
readiness is claimed. Second-provider review and hosted checks remain pending.
