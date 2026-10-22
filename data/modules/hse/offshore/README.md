# Public offshore evidence — issue #1325

This source-neutral collection sits beside the existing Gulf-only HSE ORM. Existing holdings originate from BSEE, OSHA and EPA. UK HSE offshore statistics have **not** been acquired. The registry records licences, access restrictions and whether verification is current or carried from the earlier collection.

Only public metadata, links and permitted original paraphrases belong in this collection. IOGP, NOPSEMA and CSB intake permits links and metadata only, with no summary. Do not retain report text, images, individual names or contact details. Public organisations and installations identify events. Unknown facts remain null; zero means an explicit count. A procedural notice must not be interpreted as a mechanical root-cause finding.

## Pilot evidence and current access

The pilot packet contains two currently verified source documents. The unverified notice remains a candidate link only; its cached dates and status are excluded from both committed packets. **The pilot review gate has not passed.**

The IADC alert omits the installation and event date. Its association is curated from the issue seed mapping, rather than an automatic match. SEC access stopped after its robots request returned 403; the filing supplies no admitted facts. OPRED publishes an observed time without a timezone, so the event remains date-only. Decimal coordinates derive from the published DMS values. Basin labels are geographic derivations. BSEE references combining area/block and date are collection keys, not agency-assigned report numbers.

## Intake and storage

Run `scripts/import_offshore_hse.py` with the repository Python environment. `--data-root` or `WED_DATA_ROOT` must point outside the repository. Storage is `modules/hse/offshore` beneath that root. The command never downloads pages or writes into the old HSE ORM.

1. Import `pilot.json` with `--packet` and `--digest`. Pilot intake permits one canonical event only.
2. Have an independent reviewer verify the exact pilot and its text inventory against official sources. A receipt requires `verdict: pass`, `reviewer_role: independent_agent`, `reviewed_event_ids` and `dataset_sha256`. Submit it with `--pilot-review` and `--pilot-event-id`. Approval requires three distinct public sources; cached evidence cannot satisfy it. The role string is an attestation, not authenticated maintainer approval.
3. Only after pilot approval, import curated candidates with `--stage candidate`. Candidate intake is separate from bulk acceptance.
4. Supply `--existing-indexes` with complete identity-only exports of both canonical datasets, including HSE BSEE investigation rows and marine USCG/MAIB/NTSB records. Reconciliation consumes the indexes, records their digests, and replaces matched events with external links carrying the curated operation, failure mode, failure summary and equipment annotations. Never represent a missing database by an empty complete index.
5. Independently recheck at least 10% of the reconciled canonical records, then supply `--bulk-review` and the same indexes. Acceptance requires 50 events, pilot approval, consumed complete indexes and a matching review digest.
6. Export with `--export` and a new directory name. Outputs include events, citations, external links, dedup log, review gates and SHA-256 manifest. Differing existing exports are not overwritten.

Index JSON has top-level keys `hse` and `marine_safety`, each containing `complete: true` and `records: [...]`. Identity rows require `record_id`, date-only `event_date`, ISO country and `installation_name`; optional fields are `installation_aliases` and `block_or_lease`. For `ingest(existing=...)`, each identity also needs `module`, limited to those two module names. Internal canonical IDs and extra fields are rejected. An unknown installation may be empty for BSEE date/block matching. Lease and area/block alternatives may be separated by semicolons. Export completeness and absence of personal names require review by the exporter; structural checks cannot authenticate those assertions.

Exact `(source, source_ref)` references are unique. Reruns add no duplicate evidence rows. Event matching requires normalized installation names or reviewed aliases, country and dates within two days; BSEE also uses exact date plus lease/area-block. Ambiguity stops intake for explicit review. Approximate spelling matches are not accepted. Matches and exact duplicates are logged with rule, score and disposition. Existing datasets are linked, never copied. Every evidence-table mutation invalidates bulk/index acceptance receipts.

Intake refuses a matching row when its operation, failure mode, failure summary or equipment membership differs from the stored event or non-empty link annotations. Equipment is compared as a set: order and repeated items do not change membership, including on intake with the same event ID. Equivalent intake preserves the stored equipment list and review digest. A conflict requires explicit review; intake preserves the curated classification. An event ID already linked to an existing record cannot create a second link through `ingest(existing=...)`. Both refusals roll back the entire packet, including source evidence, deduplication logs and review receipts.

## Privacy and review limits

The importer rejects unreviewed string values and contact patterns before persistence. The reviewed-text inventory must be curated and independently checked; the importer does not generate it. Contact checks also cover external identities. This is an admission control, not universal personal-name recognition: a falsely approved inventory can still contain a name. Review receipts have a closed schema and cannot carry free-form reviewer names or notes. `InjuryIncident.injured_person_name` is untouched.

## Collection disposition

The earlier collection recorded a 50-event packet in external storage. Its original digests remain in the manifest, but the packet was not located for this revision; current-policy validation and canonical placement are unverified. It remains **candidate data**, with 52 source rows. Historical review receipts were not imported as current approvals. The earlier independent source review checked five candidates (10% of 50), plus a partial pilot check; `source_review.json` binds those results to corrected sample record hashes and records the expected historical packet digest separately. `sample.json` contains those five records and the pilot. Only this small sample, pilot, links, registry, review report and compact manifest belong in Git.

Complete canonical HSE and marine-safety indexes are unavailable. The private source-identity catalog is also unavailable and has not been modified. **Bulk acceptance and canonical placement remain blocked.** The preserved candidates must not be presented as 50 deduplicated accepted events or qualified engineering inputs. The manifest records these limitations and failed acceptance criteria. Maintainer review remains required before merge.

## Source registry

The [registry documentation](../../../../docs/hse/source-registry.md) defines
the controlled licence and access values, historical terms-check dates and
metadata-only storage policy. It includes a before/after contract-row example.
Run `python -m worldenergydata.hse.source_registry validate` to check the registry
or replace `validate` with `list --json` to inspect its entries offline.
Registry validation does not fetch a source or approve collection.
