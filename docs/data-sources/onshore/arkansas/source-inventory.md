# Arkansas source metadata inventory

This bounded inventory separates oil and gas regulator discovery targets from
county recording and mineral-title research. The AOGC landing page could not be
opened; no live dataset availability, download format or redistribution right
was established. The state county directory was accessible, but no county
recording system or title record was inspected. The validator and example run
offline using the Python standard library.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-26 | Added metadata checks, explicit uncertainty and an offline example to bound discovery before acquisition. |

## Evidence and boundaries

Only official public landing-page HTML was requested. Response bodies and
request receipts containing the URL, UTC check time and HTTP status are retained
outside the repository. No forms were submitted, credentials used, dataset
payloads requested or observations committed.

| Official landing page | UTC check time | HTTP status | Body bytes received | Interpretation |
| --- | --- | --- | --- | --- |
| [AOGC](https://www.aogc.state.ar.us/) | 2026-10-26T11:02:40Z | 403 | 5421 | Inaccessible; regulator discovery targets remain unverified. |
| [State agency candidate](https://portal.arkansas.gov/agency/arkansas-oil-and-gas-commission/) | 2026-10-26T11:02:55Z | 404 | 187125 | Candidate address did not resolve to an agency page; excluded from inventory. |
| [State agency directory](https://portal.arkansas.gov/agencies/) | 2026-10-26T11:03:05Z | 200 | 400000 | Response stopped at the request size cap; incomplete and excluded from inventory. |
| [County government directory](https://portal.arkansas.gov/county-government-services/) | 2026-10-26T11:03:41Z | 200 | 293786 | Landing-page identity confirmed; county-specific access and rights remain unknown. |

The received body sizes above sum independently to 886332 bytes. These bounded
metadata requests stayed within the 2 MB operational download budget for this
discovery slice; that budget is a task constraint, not a scientific constant.
HTTP status and byte counts come from the saved request receipts. A successful
landing-page check says nothing about dataset completeness, freshness, automated
access, licensing or redistribution permission.

## Inventory and field contract

Each row requires `source_url`, `source_category`, `dataset_type`, `access_method`,
`format`, `rights_status`, `verification_status` and `verification_time`.
Missing fields, blank values, non-string values and unexpected fields are
rejected. Values are trimmed; inputs are copied rather than mutated.

| Field | Meaning and accepted values |
| --- | --- |
| `source_url` | HTTP(S) landing URL without credentials, query or fragment; syntax validation does not authenticate the publisher or establish reachability. |
| `source_category` | `regulator` or `county_title`; categories cannot be combined. |
| `dataset_type` | Regulator: `wells`, `production`, `permits`, `fields`, `spacing_pooling_orders`. County/title: `county_directory`, `recorded_leases`, `mineral_title`. A mismatched category is rejected. |
| `access_method` | `unknown`, `landing_page`, `interactive_lookup`, `bulk_download`, `api` or `manual_request`; describes dataset access evidence, not merely the ability to open the source page. |
| `format` | Nonempty dataset-format description, or the literal `unknown`; HTML landing-page access does not establish a dataset format. |
| `rights_status` | `unknown` or `restricted`; this first slice does not qualify affirmative permission. Unknown rights never authorize redistribution. |
| `verification_status` | `unverified` or `landing_page_verified`; neither asserts verified dataset availability. |
| `verification_time` | Timezone-aware ISO timestamp of the metadata check, including an unsuccessful attempt for an unverified row; not the dataset vintage. |

The following regulator entries are **discovery targets**, not assertions that
these datasets exist at the recorded URL. They share an inaccessible agency
landing page because no dataset-specific endpoint was verified. Wells,
production, permits and fields are regulator questions. Spacing/pooling orders
are a lease-relevant regulatory question; they cannot establish recorded lease
ownership, mineral title, encumbrances or a title chain. The county directory is
only a starting point for locating the responsible recording office; it is not
a title database, assessor ownership feed or statewide lease registry.

```json
[
  {
    "source_url": "https://www.aogc.state.ar.us/",
    "source_category": "regulator",
    "dataset_type": "wells",
    "access_method": "unknown",
    "format": "unknown",
    "rights_status": "unknown",
    "verification_status": "unverified",
    "verification_time": "2026-10-26T11:02:40Z"
  },
  {
    "source_url": "https://www.aogc.state.ar.us/",
    "source_category": "regulator",
    "dataset_type": "production",
    "access_method": "unknown",
    "format": "unknown",
    "rights_status": "unknown",
    "verification_status": "unverified",
    "verification_time": "2026-10-26T11:02:40Z"
  },
  {
    "source_url": "https://www.aogc.state.ar.us/",
    "source_category": "regulator",
    "dataset_type": "permits",
    "access_method": "unknown",
    "format": "unknown",
    "rights_status": "unknown",
    "verification_status": "unverified",
    "verification_time": "2026-10-26T11:02:40Z"
  },
  {
    "source_url": "https://www.aogc.state.ar.us/",
    "source_category": "regulator",
    "dataset_type": "fields",
    "access_method": "unknown",
    "format": "unknown",
    "rights_status": "unknown",
    "verification_status": "unverified",
    "verification_time": "2026-10-26T11:02:40Z"
  },
  {
    "source_url": "https://www.aogc.state.ar.us/",
    "source_category": "regulator",
    "dataset_type": "spacing_pooling_orders",
    "access_method": "unknown",
    "format": "unknown",
    "rights_status": "unknown",
    "verification_status": "unverified",
    "verification_time": "2026-10-26T11:02:40Z"
  },
  {
    "source_url": "https://portal.arkansas.gov/county-government-services/",
    "source_category": "county_title",
    "dataset_type": "county_directory",
    "access_method": "unknown",
    "format": "unknown",
    "rights_status": "unknown",
    "verification_status": "landing_page_verified",
    "verification_time": "2026-10-26T11:03:41Z"
  }
]
```

By hand, this inventory contains five regulator targets and one county directory:
six metadata rows, five unverified, with unknown dataset access and rights for
all six. These are row counts, not counts of distinct websites or confirmed
datasets. No county lease or title source is represented as verified.

## Executable offline example

Run from the repository root with Python available; no package installation or
network access is needed. The reserved `.invalid` addresses, timestamp, access
method and format below are synthetic examples, not live source evidence.

```sh
PYTHONPATH=src "${PYTHON:-python3}" - <<'PY'
import json

from worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory import (
    summarize_inventory,
)

rows = [
    {
        "source_url": "https://example.invalid/regulator/wells",
        "source_category": "regulator",
        "dataset_type": "wells",
        "access_method": "unknown",
        "format": "unknown",
        "rights_status": "unknown",
        "verification_status": "unverified",
        "verification_time": "2026-10-15T00:00:00Z",
    },
    {
        "source_url": "https://example.invalid/county/leases",
        "source_category": "county_title",
        "dataset_type": "recorded_leases",
        "access_method": "manual_request",
        "format": "synthetic record image",
        "rights_status": "unknown",
        "verification_status": "unverified",
        "verification_time": "2026-10-15T00:00:00Z",
    },
]
print(json.dumps(summarize_inventory(rows), indent=2, sort_keys=True))
PY
```

Independently tallying these literal inputs gives one regulator row plus one
county/title row, both unverified with unknown rights; only the regulator row
has unknown access. The expected output is therefore:

```json
{
  "county_title_sources": 1,
  "regulator_sources": 1,
  "total_sources": 2,
  "unknown_access_sources": 1,
  "unknown_rights_sources": 2,
  "unverified_sources": 2
}
```

The same validator is available as
`python -m worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory`
with a JSON array on standard input and `PYTHONPATH=src`. Invalid metadata exits
unsuccessfully without echoing supplied values. Neither interface performs
network requests or produces a redistribution approval.

## Open work

Confirm dataset-specific AOGC landing pages when accessible, then document
access terms, formats, coverage, update cadence and identifiers before any
acquisition. County recording, mineral-title interpretation and underwriting
joins need separate source evidence. Storage policy, ingestion and wider source
discovery remain open. This inventory has no readiness-matrix dependency.
