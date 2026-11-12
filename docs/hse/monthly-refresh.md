# Monthly public HSE refresh

The runner collects the enabled sources in `config/hse/monthly_sources.yml`.
The initial set contains BSEE investigation and non-compliance archives, two
BSEE listing pages and a manual PHMSA landing page. It retains raw downloads
and provenance. It does not import records into a database or qualify them for
engineering analysis. Retrieval time records collection, not source-data vintage.

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

Unknown and duplicate YAML keys are errors. All source fields below are required
except `manual_drop_dir`. Boolean fields require YAML booleans.

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

Download basenames must be distinct within a source, portable and free of path
traversal. The names `manifest.json`, `latest.json` and `links.json` are reserved.

## Access rules

Before a data request to an origin, the runner reads its HTTPS `robots.txt`
with the configured identity and applies `urllib.robotparser`. A disallow rule
prevents the data request. HTTP 401 or 403 on robots blocks that origin. Other
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
| `success` | Every URL returned content matching the configured format |
| `unchanged` | Every digest matches verified retained files referenced by latest |
| `blocked` | Robots returned 401/403, or a data URL returned 401/403/429 |
| `disallowed_by_robots` | Robots rules prohibit the data URL |
| `robots_unavailable` | Robots policy could not be obtained |
| `unexpected_content` | A returned body failed its content check |
| `failed` | Another HTTP, transport or storage error occurred |
| `manual_pending` | No manual files are present; the landing URLs give instructions |
| `manual_present` | Manual files were inventoried with size, digest and UTC mtime |
| `skipped_disabled` | The configuration disables the source |
| `dry_run` | The source would be processed in a live run |

A failure of any URL fails that source. Required `manual_pending` also fails the
run. Disabled sources and dry runs do not count as required failures. Manual
presence records received files; it does not validate their contents or freshness.

## Retained files

```text
<output_root>/
  <source_id>/
    <YYYY-MM>/
      <URL basename>
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

An unchanged manifest points at the earlier retained files; duplicate bytes are
discarded. Its listing index is regenerated in the selected month. `latest.json`
copies the newest `success` or `unchanged` manifest by calendar month; older
backfills do not move the pointer backwards. A partial download failure leaves
the previous latest pointer and its bytes intact. Manual files remain in the
configured drop directory. The summary includes per-source outcomes, counts,
required failures, UTC start/finish times and the path and digest of the parsed
configuration. These local saves do not establish backup or publication.

Listing indexes contain sorted, deduplicated absolute links and their visible
text for PDF targets and URLs containing `/sites/` or `/media/`. Linked
documents are not downloaded.

To add a source, append a mapping to the YAML file, verify its public access and
reuse terms, choose a unique id and run a dry run. No runner changes are needed.
For manual collection, place received files under `manual_drop_dir` and rerun.

## Scheduling and offline example

```cron
17 3 2 * * WED_HSE_SOURCES_ROOT=/mnt/ace/worldenergydata/data/modules/hse/sources <repo>/scripts/cron/hse-monthly-refresh.sh
```

The wrapper requires the environment variable, runs from the repository root,
appends a dated exit code to `refresh.log` and returns the runner's code. The
scheduler job `hse_sources_refresh` uses its explicit `output_dir`. Its existing
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
