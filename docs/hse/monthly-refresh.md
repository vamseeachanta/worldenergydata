# Monthly public HSE refresh

The runner collects the enabled sources in `config/hse/monthly_sources.yml`.
The configuration includes public investigation archives, statistics files,
listing pages and manual sources. It retains bulk downloads, selected listing
links and provenance. It does not import records into a database or qualify them
for engineering analysis. Retrieval time records collection, not source-data vintage.

```bash
uv run python scripts/hse/refresh_hse_sources.py \
  --config config/hse/monthly_sources.yml \
  --output-root "$WED_HSE_SOURCES_ROOT" --json
```

The module entry point is `python -m worldenergydata.hse.monthly_refresh`.
An explicit `--output-root` or `WED_HSE_SOURCES_ROOT` is required. The operator
selects external storage. `--source ID ...` selects sources, `--month YYYY-MM`
selects the calendar folder and `--dry-run` reports selections without requests
or filesystem writes. With `--json`, the summary is printed to stdout and the
per-source lines are printed to stderr. Each line gives id, status, bytes and rows.
Exit codes are 0 for no required failures, 1 for required or storage failures
and 2 for configuration errors. Optional failures remain visible in the summary.

## Configuration

Unknown and duplicate YAML keys are errors. The optional fields are
`manual_drop_dir`, `link_patterns` and `link_classes`. All other source fields
below are required. Boolean fields require YAML booleans.

| Field | Scope | Value |
| --- | --- | --- |
| `schema_version` | Root | Integer `1` |
| `user_agent` | Root | Non-empty printable ASCII identity, sent unchanged |
| `sources` | Root | Non-empty list of source mappings |
| `id` | Source | Unique lowercase `[a-z][a-z0-9_]*` |
| `authority` | Source | Publishing authority |
| `description` | Source | Dataset and collection scope |
| `licence` | Source | Recorded reuse basis; does not itself grant rights |
| `terms_url` | Source | HTTPS terms evidence URL, without credentials |
| `kind` | Source | `bulk_file`, `listing_page` or `manual` |
| `expect` | Source | `zip`, `csv`, `xlsx`, `pdf`, `html` or `json` |
| `required` | Source | Whether an enabled source failure fails the run |
| `enabled` | Source | Whether collection is enabled |
| `urls` | Source | Non-empty unique HTTPS URLs without credentials |
| `manual_drop_dir` | Manual source | Required relative directory under the output root |
| `link_patterns` | Listing source | Optional list of regular expressions searched against absolute URLs |
| `link_classes` | Listing source | Optional list of single anchor class tokens |

Download basenames must be distinct within a source, portable and free of path
traversal. The names `manifest.json`, `latest.json` and `links.json` are reserved.
Invalid regular expressions, non-list selectors and selectors on other source
kinds are configuration errors. Selector entries require non-empty strings;
class entries contain one token each.

## Access rules

Before a data request to an origin, the runner reads its HTTPS `robots.txt`
with the configured identity and applies `urllib.robotparser`. A disallow rule
prevents the data request. HTTP 401, 403 or 429 on robots blocks that origin. Other
4xx robots responses allow collection. Network errors and 5xx responses prevent
collection with `robots_unavailable`.

Every request, including robots and redirects, observes a minimum one-second
interval per host. Redirects require HTTPS without credentials. A redirected
data destination receives its own robots check. The runner never retries with a
different identity, adds browser-like headers or retries HTTP 401, 403 or 429.
Blocked access requires a manual download permitted by the source terms or a
decision by the data owner. It does not authorise bypassing an access control.

Content is checked before retention. ZIP archives are opened and checked for
integrity; members are never extracted. `.csv` and `.txt` member rows are counted
as lines minus one header, bounded below by zero. This count does not establish
record validity. Other formats receive a light signature or syntax check.

## Outcomes

| Status | Meaning |
| --- | --- |
| `success` | Every URL passed its format check; listing pages yielded kept links |
| `unchanged` | Every digest matches latest; bulk files also pass retained-byte verification |
| `no_links` | The listing pages yielded no links matching the source rules |
| `blocked` | Robots or a data URL returned 401, 403 or 429 |
| `disallowed_by_robots` | Robots rules prohibit the data URL |
| `robots_unavailable` | Robots policy could not be obtained |
| `unexpected_content` | A returned body failed its content check |
| `failed` | Another HTTP, transport or storage error occurred |
| `manual_pending` | No manual files are present; the landing URLs give instructions |
| `manual_present` | Manual files were inventoried with size, digest and UTC mtime |
| `skipped_disabled` | The configuration disables the source |
| `dry_run` | The source would be processed in a live run |

A failure of any URL fails that source. Required `manual_pending` and `no_links`
also fail the run. Disabled sources and dry runs do not count as required failures.
Manual presence records received files; it does not validate their contents or freshness.

## What is kept

Bulk sources retain downloaded files and provenance. Listing pages retain only
the selected URLs, visible link text and response metadata. Full HTML and
navigation text are not written to disk. Linked documents are not downloaded.
The listing rules select public report metadata; personal names are outside
the collection scope described in [the source registry](source-registry.md).

## Output layout

```text
<output_root>/
  <source_id>/
    <YYYY-MM>/
      <URL basename>      # bulk files only
      <digest>-<basename> # changed bulk bytes in an existing month, when needed
      manifest.json
      links.json          # listing pages only
    latest.json
  refresh-summary.json
  refresh.log             # cron wrapper only
```

Each URL record includes the requested and effective URLs, HTTP status, byte
count, SHA-256, content type, ETag, Last-Modified and UTC retrieval timestamp.
ZIP member records include names, sizes and text row counts. Failures carry a
reason. Retained file paths are relative to the output root.
Listing page records have `retained: links_only` and no `path`; their digest and
byte count describe the fetched page held in memory, not a retained HTML file.

Bulk payload files are write-once. Identical bytes reuse an existing path. If a
month's basename already contains different bytes, the new file uses the first
12 hexadecimal characters of its SHA-256 followed by `-` and that basename.
A conflicting digest-prefixed path causes a failure and retains the existing
bytes. Earlier manifests continue to reference bytes matching their recorded
digests.

An unchanged bulk manifest points at the earlier retained files. Listing page
digests are compared with the previous latest manifest without a stored HTML
file. The listing index is regenerated in the selected month, including when
the page is unchanged. An empty combined index gives `no_links`. `latest.json`
copies the newest `success` or `unchanged` manifest by calendar month; older
backfills do not move the pointer backwards. A partial download failure leaves
the previous latest pointer and its bytes intact. Manual files remain in the
configured drop directory. The summary includes per-source outcomes, counts,
required failures, UTC start/finish times and the path and digest of the parsed
configuration. These local saves do not establish backup or publication.

Listing indexes contain sorted, deduplicated absolute links and their visible
text. When either selector field is configured, a URL pattern match or an exact
anchor class token match retains the link. Without either field, PDF targets
and URLs containing `/sites/` or `/media/` are retained. Explicit empty lists
select no links unless the other field matches. For duplicate URLs, the first
non-empty title is retained; a later non-empty title replaces an empty one.

To add a source, append a mapping to the YAML file, verify its public access and
reuse terms, choose a unique id and run a dry run. No runner changes are needed.
For manual collection, place received files under `manual_drop_dir` and rerun.

## Scheduling and offline example

```cron
17 3 2 * * WED_HSE_SOURCES_ROOT=<output_root> <repo>/scripts/cron/hse-monthly-refresh.sh
```

The placeholders identify the selected external directory and checkout. The
wrapper requires `WED_HSE_SOURCES_ROOT`, resolves the checkout from its own
location and preserves an explicit `REPO_ROOT` environment override. It runs
from that root, appends a dated exit code to `refresh.log` and returns the runner's
code. The scheduler job `hse_sources_refresh` uses its explicit `output_dir`. Its existing
`monthly` interval means every 30 days at 03:30, rather than a calendar day.
Select one scheduling mechanism to avoid duplicate runs.

The synthetic fixture in `tests/unit/hse/test_monthly_refresh.py` builds an
in-memory ZIP containing `records.csv` and `readme.bin`. The CSV has one header
and two data lines. `httpx.MockTransport` supplies both robots and data responses.
No network connection or real sleep is used.

```bash
uv run python -m pytest --noconftest \
  tests/unit/hse/test_monthly_refresh.py -k zip_success_provenance_and_unchanged -q
```

The first run records `success`, two rows, the archive digest and a latest
manifest for `2026-11`. The second run requests the same synthetic bytes for
`2026-12`, records `unchanged` and retains the path to the November archive.
The fixtures establish runner behaviour only, not public-source availability.
