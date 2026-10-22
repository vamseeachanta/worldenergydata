# HSE source registry and authority correction

The HSE holdings originate from BSEE, OSHA and EPA. UK HSE offshore statistics
remain unacquired; enforcement notices are a separate source. The registry
records source identity, stated terms, access and storage restrictions for
offline inspection. Validation confirms the record structure and policy
consistency, not current reachability or permission to collect.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| Initial | 2026-10-22 | Document the authority correction and registry validation so source labels and reuse restrictions can be checked together. |

## Evidence and scope

The source table and **Never collect** rules in issue #1325 (2026-10-17) define
the source inventory and collection restrictions. The existing
[source review](../../data/modules/hse/offshore/source_review.json), dated
2026-10-17, records the available terms evidence and access failures. The
[HSE data audit](../../reports/hse/wrk012_hse_data_audit.md), International
Offshore Safety table, identifies the UK offshore-statistics acquisition gap.
This change preserves the correction already present in the repository and
adds structured manifest fields and registry references to prevent drift.

The registry migration performs no network collection. Recorded observations
are historical, not a claim that a source was reached again. Unknown licences
stay `unverified`; free public access is not a reuse licence. The source table
contains nine source identities, with CSB and SEC represented separately.
OSHA and EPA represent the existing holdings alongside BSEE. The registry has
eleven entries, including unreachable sources for discovery rather than intake.

## Registry format

The authoritative file is
[`data/modules/hse/offshore/source_registry.json`](../../data/modules/hse/offshore/source_registry.json).
The schema revision is `2`, defined here. Revision `1` used descriptive licence
and access strings without validation. Revision `2` keeps those statements in
`licence_statement` and `access_detail`, introduces controlled values, and
records verification and storage policy explicitly. Consumers of the earlier
free-form `licence` field should use `licence_statement` for the original
statement and `licence` for the controlled classification.

The top level requires `schema_version` and a nonempty `sources` list. Each
entry requires the following fields; unknown evidence is explicit rather than
silently omitted.

| Field | Rule |
|---|---|
| `source` | Unique lowercase identifier, starting with a letter; underscores and digits are permitted. Surrounding whitespace is stripped before checking duplicates. |
| `url` | Public HTTPS source URL, without credentials or whitespace. |
| `licence` | `OGL-3.0`, `US-federal-work`, `attribution-permitted`, `all-rights-reserved` or `unverified`. |
| `licence_statement` | Nonempty recorded description of the source's terms; not a new legal conclusion. |
| `access_status` | `public`, `public_landing_only`, `blocked`, `unavailable`, `unverified` or `not_recollected`. |
| `terms_verification` | `verified` or `unverified`, independent of access status. |
| `terms_check_date` | Calendar date in `YYYY-MM-DD` notation, or `null` if no terms check is recorded. A failed terms-page attempt may have a date while verification remains unverified. |
| `terms_url` | HTTPS terms-evidence URL, or `null` if unavailable. |
| `terms_status` | Nonempty explanation of terms evidence or uncertainty. |
| `storage_policy` | `metadata_only` or `text_permitted`. All current entries use `metadata_only`. |

Optional fields retain the earlier `notes`, `access_date`, `robots_status`,
`collection_policy`, `verification_basis` and `alternate_urls`. `access_detail`
preserves the earlier access description. Dates use the required `YYYY-MM-DD`
notation and must be real dates; compact dates and timestamps are refused.
Unknown fields, duplicate source identifiers and duplicate JSON object keys
are refused. Registry validation accepts no prior schema revision implicitly.

`verified` terms require a known licence classification, evidence URL and check
date. `text_permitted` additionally requires public access and a reuse licence;
reserved rights and unverified terms always forbid text storage. This is a
structural prerequisite, not a substitute for checking the scope of a licence.
Source-specific exceptions still apply. No entry currently authorizes raw
report text or images. Metadata can include links and an original paraphrase
only where `collection_policy` allows it; IOGP, NOPSEMA and CSB allow no summary.

The recorded OPRED OGL statement, Havtil attribution permission and IADC
reserved-rights statement retain the earlier review date. BSEE federal-authored
status and third-party scope remain unverified rather than being promoted to a
blanket reuse licence. UK HSE's unconfirmed OGL scope also remains unverified.
SEC has an access-attempt date but no terms-check date because its blocked
robots request did not reach the terms page. Existing descriptive statements
are evidence pointers, not freshly retrieved source quotations.

## Listing and validation

With the repository's Python environment and workspace packages available:

```sh
python -m worldenergydata.hse.source_registry validate
python -m worldenergydata.hse.source_registry list
python -m worldenergydata.hse.source_registry list --json
```

The listing is sorted by source and includes licence, access, terms-check date,
storage policy and URL. JSON output retains `null` dates. Text output displays
an unknown date as `unverified`. Both commands validate before producing output;
an unreadable or invalid registry returns a nonzero status without echoing its
contents. No command downloads documents or creates a collection database.

An installed distribution without repository data must supply the registry:

```sh
python -m worldenergydata.hse.source_registry list \
  --registry data/modules/hse/offshore/source_registry.json --json
```

The registry is referenced by the acceptance contract and module manifest using
repository-relative paths, and by `schema.yaml` relative to its own directory.
The collection importer continues to admit curated packets under its existing
privacy and review gates. The registry is an offline inventory, not a new
downloader or runtime authorization service.

## Worked example: correcting the contract row

**Inputs.** Issue #1325 (2026), Current state and Labels, records the original
mislabelled row. The HSE audit identifies existing holdings and explicitly
marks UK HSE offshore statistics **Not acquired**. The following JSON excerpts
show only the source-identity fields; counts and source-vintage fields are
outside this correction.

Before, as recorded in issue #1325:

```json
{
  "module_id": "hse",
  "display_name": "HSE Offshore Safety",
  "source_authority": "UK Health and Safety Executive",
  "source_url_or_api": "https://www.hse.gov.uk/offshore/statistics.htm"
}
```

**Method.** Identify the authority from the held datasets, not the module's HSE
abbreviation. Preserve the separate acquisition gap. Point to the registry for
additional public offshore sources; a registry entry does not mean acquisition.
Apply the same distinction in the manifest and module schema.

**Answer.** The accepted identity fields are:

```json
{
  "module_id": "hse",
  "display_name": "HSE incidents and public offshore evidence",
  "source_authority": "BSEE; OSHA; EPA (existing datasets)",
  "source_url_or_api": "https://www.bsee.gov/; https://www.osha.gov/; https://www.epa.gov/toxics-release-inventory-tri-program",
  "uk_hse_offshore_statistics_status": "not_acquired",
  "source_registry": "data/modules/hse/offshore/source_registry.json"
}
```

For a second policy example, NOPSEMA has a source-table URL but no verified
licence or check date. Its existing timeout is classified as `unavailable`,
with `licence: unverified`, `terms_check_date: null` and
`storage_policy: metadata_only`. This is a discovery record. It does not
qualify report-text storage or authorize another access attempt. An attempted
change to `text_permitted` fails validation because neither verified reuse
terms nor public access is established. No numerical engineering input or
acceptance limit is inferred.

## Verification and limits

`test_source_identity.py` guards the actual authorities, acquisition gap and
registry pointers across the contract, manifest and module schema.
`test_source_registry.py` checks required fields, controlled values, real
calendar dates, duplicate sources and keys, policy prerequisites and CLI
behavior using synthetic fixtures. Expected policy results are stated in the
test docstrings independently of the implementation. Its consistency checks
cover the offshore loader's source enum, authority and host maps, committed
packet sources, and URL literals in the existing acquisition/import loaders.
The latter checks URLs statically without importing or running downloaders.

The registry retains blocked and unverified entries, does not certify robots
permissions or current source terms, and does not resolve the collection's
existing pilot, bulk-review or external-index gaps. No source content or event
data is acquired by this change. Independent source review remains required
before expanding collection or storage permissions.
