# worldenergydata-canada

`canada` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.canada` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Offline development-well depth enrichment

`DevelopmentWell` in `worldenergydata.canada.development_wells` defines a
caller-normalized input, rather than an ArcGIS attribute map. Its required
fields are `uwi`, `field_name`, nullable `water_depth_m`, `depth_unit`,
`depth_datum` and `source`. Only explicitly supplied `m` units are supported.
Field linkage is exact and case-sensitive; UWI is an opaque identifier.
A case mismatch contributes no measurements, even when the legacy
case-insensitive lookup recognizes a representative field default. In that
case, the supplied field depth or default is retained and the sidecar reports
`linked_well_count=0` with no contributing identifiers.
Source fields, units, linkage and measurement authenticity require independent
qualification before engineering use. A source string is lineage evidence,
not proof of access permission or measurement validity.

`canada_field_to_concept(metadata, wells=records)` and
`build_canada_field_concept(metadata, wells=records)` opt into enrichment.
The median of linked non-null depths takes precedence over field metadata.
Without usable measurements, the supplied field depth, unchanged representative
default, or missing depth is retained in that order. Omission of `wells`
preserves the legacy result, including its `data_source` value.

`enrich_canada_field_metadata(metadata, records)` also returns a
`water_depth_provenance` sidecar containing the depth origin, datum,
contributing identifiers, sources, linked count and input manifest. The
FieldConcept `data_source` retains the origin, input digest and
`measurement_status=NOT_EVALUATED`. The sidecar carries the detailed evidence;
FieldConcept has no per-property provenance schema. `measured_median` describes
the caller-declared record basis; it does not certify the measurements.

Null depths remain null. A true zero remains a contributor. Duplicate UWI
records and inconsistent contributing datums raise `ValueError`, preventing
implicit weighting or mixing vertical references. The median follows the
[Python 3.11 Library Reference (retrieved 2026), statistics.median](https://docs.python.org/3.11/library/statistics.html#statistics.median):
the middle value for odd sample sizes and the mean of the middle pair for even
sample sizes. Exact fractions avoid intermediate overflow and dependence on an
application's decimal arithmetic context. Nonnegative depths follow
`FieldConcept.must_be_non_negative` in
`src/worldenergydata/field_development/models.py`, schema version 1.0.0.
No empirical coefficient or new engineering acceptance limit is introduced.

`development_wells_manifest(records)` returns schema version 1, record count,
metre units, sorted source references and a SHA-256 digest. The digest covers
UTF-8 JSON of records sorted by unique UWI, with sorted keys, compact separators,
unescaped Unicode, normalized float depths and explicit nulls. Changing linkage,
source, datum or depth changes the digest; input order does not. The digest
establishes normalized input identity, not source authenticity, freshness or
completeness. No record payload is returned in the manifest or persisted.

All new test data are synthetic, with expected medians calculated in test
docstrings. No regulator records, locations or derived field depths are bundled.
Live discovery, metadata/terms qualification, coordinate mapping, transport,
bounded paging, external caching and collection manifests remain later work
under issue #818, pending the publisher access decision recorded there.
