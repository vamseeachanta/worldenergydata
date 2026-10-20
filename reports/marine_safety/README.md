# Marine Safety Incident Analysis

The public-input analysis is **not yet re-derived**. The TSB download returned
HTTP 403; combined and filtered counts are `NOT_EVALUATED`. The historical total
could not be sourced. Earlier charts remain unverified.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-19 | Record public-input provenance and require count agreement because the historical total could not be sourced. |
| 2 | 2026-10-20 | Record the unresolved count difference and licences; retain verified provenance and retry HTTP 403 once with an explicit User-Agent. Disclose that whitespace-only descriptions are now excluded and `capsiz` replaces `capsize` to include Capsizing; move generated revision history into the manifest. |

## Inputs and measured counts

[marine_safety_input_manifest.json](../../config/marine_safety_input_manifest.json) records exact URLs, UTC retrieval
or attempt times, SHA-256 digests, source row counts and analysis counts.
The raw CSVs are retained outside Git in an external content-addressed archive;
no raw payload is committed. The manifest paths are relative to that archive.

| Input | Download result | Records |
| --- | --- | ---: |
| Canadian TSB marine occurrence export | HTTP 403 Forbidden | NOT_EVALUATED |
| DLP historical USCG recreational boating accident export | Fetched from a pinned release revision | 80,340 |
| IMO GISIS | Excluded: requires an account and manual export | NOT_EVALUATED |

The DLP release is the historical **BARD recreational boating** dataset, rather
than the separate MISLE investigation dataset. The upstream file is named
`Accidents.csv`; `upstream_name` records this separately from the historical
archive filename. The measured 80,340 records do not reproduce the 93,237
reported in #1529, a difference of 12,897 records. The cause is not established:
different exports or line counts versus record counts are possible explanations.
The historical archive filename does not establish equivalence.
Its exact URL and revision are pinned in the manifest.

The one open input is the [TSB occurrence CSV](https://www.tsb.gc.ca/sites/default/files/stats/MARSISdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv).
The [official catalog](https://open.canada.ca/data/en/dataset/ad8d1b73-df09-4521-9bdb-61c529328218)
identifies that download. Its digest, retrieval date and row count are
`NOT_EVALUATED`; an attempt date is recorded separately. A source update must be
fetched and recorded before it can be used, rather than silently changing counts.
The existing shared catalog did not identify either of these exact releases;
the manifest is the collection record maintained in this repository.

The [DLP release README](https://raw.githubusercontent.com/data-liberation-project/boating-accident-reports-1995-2012-muckrock/e637c182915bdc441e63a13641eaaf9a2c541463/README.md)
identifies original records as public domain and converted CSVs as CC0.
The TSB catalog states [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).
Licence names, terms URLs and evidence URLs are recorded per source in the manifest.

## Worked example

Set `MARINE_SAFETY_RAW_DIR` to an approved external data directory. Retain it
between runs; content-addressed originals are never overwritten. The temporary
download uses the environment's `TMPDIR`, outside Git.

```bash
# Install the repository's marine-safety dependencies using its normal setup.
# The archive directory is supplied by the environment, not hardcoded here.
python3 scripts/marine_safety/incident_inputs.py \
  --raw-dir "$MARINE_SAFETY_RAW_DIR" \
  --manifest config/marine_safety_input_manifest.json

# Offline agreement check: requires both retained inputs.
python3 scripts/marine_safety/incident_inputs.py \
  --raw-dir "$MARINE_SAFETY_RAW_DIR" --check

# Generate reports only after both inputs pass digest and count checks.
bash scripts/marine_safety/analyze_incidents.sh
```

The fetch command attempts both sources and writes the manifest even if a
network request fails. An HTTP 403 response is recorded as an HTTP access
rejection, without assuming that the file has been withdrawn, and is retried
once with an explicit application User-Agent. Network failures are recorded
separately. If a download fails, a previously fetched source is retained only
when its archived bytes, schema and row count still verify; its original
download date is preserved alongside the new attempt and failure details.
The command exits nonzero when either verified source is unavailable.
The loader requires both sources, the expected columns, matching digests,
matching source row counts and matching analysis counts. Missing or invalid
inputs cause a clear error and nonzero exit before report creation. Fetching a
new release deliberately updates the manifest; review its count changes.

The method concatenates the two source tables without deduplication or date
filtering. It removes missing, empty and whitespace-only descriptions.
Foundering selects incident types matching `founder|capsiz|sinking` without case
sensitivity. Relative to the earlier method, whitespace-only descriptions are
now excluded and `capsiz` replaces `capsize` to include Capsizing; both changes
can move counts relative to earlier pages. Fatal incidents have deaths greater
than zero. Missing death counts
are treated as zero for selection; unreported deaths cannot be counted. These
are **record counts**, not unique worldwide incidents or population risk rates.
Hatch classification and detailed charts are outside the count agreement claim.
The runner uses regex mode and does not call a model.

The fetched DLP input has 80,340 rows; TSB and all combined/filtered counts remain
`NOT_EVALUATED`. The tests use an explicitly synthetic example: two TSB records
and three DLP records give five input rows; two empty descriptions are removed,
leaving three analysed rows, two foundering rows and two fatal-incident rows.
These fixture values are specified in the test, not obtained from production
constants. Negative controls change each manifest count and require rejection.
Synthetic records are never used as public engineering input.

```bash
python3 -m pytest --noconftest -o addopts='' \
  tests/unit/marine_safety/test_incident_inputs.py \
  tests/unit/marine_safety/test_report_verification.py
```

## Earlier report files

- **executive_summary.html** - unverified historical dashboard; current input status is stated above its charts
- **hatch_analysis.html** - unverified historical hatch/door/opening report
- **foundering_analysis.html** - unverified historical foundering report
- **fatality_analysis.html** - unverified historical fatal-incident report

Report generation may overwrite earlier outputs. Use `MARINE_SAFETY_REPORT_DIR`
to direct new reports to a separate output directory. The count manifest does
not remove the unverified notices from earlier charts or detail pages.
