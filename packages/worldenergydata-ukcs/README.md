# worldenergydata-ukcs

`ukcs` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.ukcs` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## NSTA field metadata

`NSTAFieldMetadataClient.load_field_metadata(field_name)` reads the public
offshore fields theme and, when field depth is absent or invalid, the wells
top-holes theme. `enrich_ukcs_field_metadata` provides the same normalization
for offline attribute snapshots. Field names are matched exactly after trimming
and case normalization; ambiguous field records raise an error.

Operator, depth and oil-field startup year pass through `FieldMetaMapping` to
`FieldConcept`, whose region remains `uk`. Status, startup/discovery dates,
raw licensee/equity entries, coverage and source digests stay on the metadata
dictionary. Equity units and totals are not inferred. Gas and condensate startup
dates are retained without being labelled first oil. FDP consents remain
`NOT_EVALUATED` because the inspected fields schema has no consent-date field.

`screen_ukcs_field_metadata(meta)` and `run_ukcs_reference_chain(field_meta=meta,
...)` retain coverage and provenance beside the ranking. Both label it
`metadata_screening_only` and return `recommendation_ready=False`; source
availability does not establish the reservoir, host or commercial basis needed
for a field recommendation. Existing economics remain pre-tax chain plumbing.

The [worked example](../../docs/domains/ukcs/nsta-field-metadata.html) documents
the source schemas, synthetic inputs, median calculation and expected result.
The public service access is read-only; tests use offline fixtures.
