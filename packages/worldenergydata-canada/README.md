# worldenergydata-canada

`canada` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.canada` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Local C-NLOER PDF acquisition

`worldenergydata.canada.production.cnloer_client.CnloerPdfClient` downloads one
annual field report at a time. Supply an explicit `cache_dir`, a positive
`timeout` in seconds and a positive integer `max_bytes`; operational limits
are caller inputs. Call `download(year=year, field_code=code)` with a report year
and one of `h`, `he`, `n`, `t`, `w`. These are the per-field stems linked from the
[C-NLOER statistics page](https://www.cnloer.ca/information/statistics/), not
all-field totals. Annual filenames include the year before the field stem.

Use a dedicated local cache directory. The client creates an ignore-all
`.gitignore` and refuses existing ignore files with any other contents, including
negation patterns. Cache artifacts shall never be force-added or published.
C-NLOER reuse rights remain unresolved; both raw PDFs and derived volumes remain
restricted pending the maintainer's licence review.

A successful download returns the path to a content-addressed PDF candidate and
writes an annual report manifest beside it. The manifest records the existing
`canada-cnloer` source identity, URL, field, report year, retrieval timestamp,
SHA-256 digest, byte count and publication restriction. Cache hits verify the
saved bytes against the manifest without network access. `force_refresh=True`
fetches again; previous snapshots remain available. HTTP failures, oversized
bodies and responses without a PDF header leave the last successful manifest
unchanged. Redirects outside the fixed regulator HTTPS origin are refused,
including URLs with an explicit port such as `:443`.
Transport and filesystem exceptions propagate; there is no synthetic
fallback. The timeout bounds socket operations, not total elapsed download time.

The header check follows ISO 32000-1:2008, *Document management — Portable
document format — Part 1: PDF*, clause 7.5.2, File Header. It identifies a PDF
candidate and does not establish structural validity. Digests follow
[FIPS PUB 180-4 (2015), Secure Hash Standard](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf),
clause 6.2, SHA-256; a digest establishes byte identity, not source authenticity.

Production parsing and scheduler registration are later slices of
[the live-refresh issue](https://github.com/vamseeachanta/worldenergydata/issues/814).
The current annual PDF uses grouped numbers, reservoir subrows, explicit totals
and blank future periods; these require parser tests before refresh can claim
valid production records. No production refresh or source freshness is claimed
by this download-only client.
