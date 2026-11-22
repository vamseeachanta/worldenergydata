# BOEM FieldReserves family

Refs [issue 855](https://github.com/vamseeachanta/worldenergydata/issues/855),
[issue 847](https://github.com/vamseeachanta/worldenergydata/issues/847) and
[issue 844](https://github.com/vamseeachanta/worldenergydata/issues/844).

The 2023 vintage names are verified against the
[annual listing](https://www.data.boem.gov/Main/HtmlPage.aspx?page=estimated2023).
The current production-master and Appendix B names are verified against the
[family listing](https://www.data.boem.gov/Main/FieldReserves.aspx).
Retrieval instants, source sizes and SHA-256 digests are recorded in
`manifest.json`: all ten records, including the production-master and Appendix B
definition pages, are emitted by the fetch code with observed HTTP statuses.
The four archive digests match the earlier retrieval underlying the row counts.
The originals remain in the
caller-configured cache. No original archive or full curated table is in Git.

| Archive | Verified content | Disposition |
|---|---|---|
| `2023 Hist.zip` | `2023 HIST/2023 OFFLDHIST.xlsx`, sheet `2023 OFFLDHIST`; also an Access copy | Typed history loader; 42,044 rows and 1,336 fields at retrieval |
| `mastproddelimit.zip` | Headerless ten-column `mastproddelimit.txt` | Typed production-master loader; 4,044 field-lease rows at retrieval |
| `2023 FldMoPro.zip` | Only `2023 FldMoPro/2023 FldMoProd.accdb` | Fetch-only; monthly typed loader is unfulfilled pending an Access decoder |
| `appendbdelimit.zip` | Five-column `appendbdelimit.txt` | Typed lease-to-field index with archive provenance; no reserves or reservoir quantities |

Table 1. Archive classifications are based on downloaded content.

Appendix B columns are lease number, field code, area, block and combined
area/block, matching the [BOEM definition page](https://www.data.boem.gov/Main/HtmlPage.aspx?page=appendixB).
The previous hypothesis of reservoir-level content is not supported.
The Appendix B loader preserves all five columns as strings, including leading
zeros in block numbers. Whitespace around identifiers is stripped; empty
identifiers, changed column counts and renamed or duplicate archive members are
rejected. Each source relationship is retained: a lease is not assumed to map
to only one field. Combined area/block text is preserved without reconstruction.
These identifiers carry no physical units and require no conversion constants.

The first-line shape (header presence and quoting) of the Appendix B member in
the archive recorded by `manifest.json` has not yet been verified. Alias header
rows are rejected anywhere in the member, including after data rows; an empty
member raises an explicit "no Appendix B rows" error. No lease-number pattern
is inferred from the synthetic test rows.

The master grain is **field and lease**, with cumulative production and a
first-production month. It is not a monthly field production time series.
Oil/condensate are labelled STB and gas MCF on the
[master definition page](https://www.data.boem.gov/Main/HtmlPage.aspx?page=fieldNames2).
Water units are not stated there. The history workbook headers do not state
oil/gas units; source values are retained without conversion. Unit qualification
is required before those values enter calculations.

At retrieval the master contains eight `################` cells across three
columns. Their numerical values and the cause of the markers are not established.
These cells become nullable floats, with the exact marker and column retained in
`SOURCE_MARKERS`; they are never replaced with zero. Consumers must account for
these missing values before accepting aggregates.

Every supported row carries `SOURCE_URL`, `SOURCE_MEMBER`, `SOURCE_SHA256` and
`RETRIEVED_UTC`. Field and lease codes remain strings. Raw inputs are preserved
in the cache and checked against manifest size/digest before cached curation.

## Refresh and terms

Run `scripts/bsee/fetch_fieldreserves_family.py --cache-root <configured-cache>`
with the package importable. A fresh empty output directory is required.
`--cached` verifies previous downloads and curates without network access.
Cached curation now requires provenance and bytes for Appendix B as well as
history and the production master. It emits `curated_appendix.csv` alongside
the existing curated tables, with per-column dtypes in `schema.json`. Every
archive is verified and parsed before any curated output is written. Existing
curated files, including the Appendix B output, are preserved by refusing a
repeat run. A previously curated cache therefore requires a fresh output
directory rather than an overwrite.
The annual standalone catalog in `config/bsee.yml` follows the existing reserves
workbook pattern. Appendix B is marked supported by the standalone typed
entry point; no generic `registry_dir` is assigned for it. The catalog does not
install a scheduler or widen the weekly BSEE host allowlist. The weekly scheduler
reads its configured or built-in dataset list,
neither of which includes these two specs. A full run of
`scripts/refresh_bsee_all.py` (also `--skip-ogor`) iterates the registry and
includes them: it downloads the archives and writes generic workbook/delimited
bins, whose headerless master parsing consumes the first data row as a header.
An owner decision is needed on exclusion from that manual refresh; those bins
are not the typed curated outputs. The generic registry preserves raw workbook/delimited bins; typed
curation reads the complete archive directly, preserving headerless first rows.

The fetcher uses one connection, a 30-second request timeout, a two-second pause
between requests and a 64 MiB response limit. Redirects and HTTP refusals stop
the request; there are no retries, so server-requested waits are not followed.
Robots policy and the disclaimer are fetched before archives. A changed
disclaimer requires terms review. Archives and members are validated by exact
names; uncompressed loader members are capped at 80 MiB.

The [source disclaimer](https://www.data.boem.gov/Main/HtmlPage.aspx?page=Disclaimer)
states: “This data is not for navigational use.” A redistribution licence is
**not stated by the source**. All committed value fixtures are labelled synthetic;
none are excerpts of downloaded records. `synthetic_manifest.json` is regenerated
from their bytes and fixed retrieval metadata, and compared in an offline test.

Remaining scope: Access decoding and monthly schema qualification; vintages
2001–2022; consumers in issue 844; oil/gas unit qualification for history and water
unit qualification for the production master. Appendix B classification is
settled and typed curation is supported; downstream joins remain separate work.
