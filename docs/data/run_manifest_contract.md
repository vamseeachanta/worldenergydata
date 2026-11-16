# Well-operations run manifest contract

Version 1 defines repository-local, read-only metadata records for BSEE insight
runs. A structurally valid manifest may remain blocked. `declared-eligible` means
that supplied declarations pass this contract; it never grants publication rights.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-11-16 | Define validated records before discovery and execution adapters. |

## Record and serialization

`worldenergydata.common.run_manifest` provides frozen `RunManifest`, `CatalogRef`,
`SourceDatasetRef` and `OutputRef` dataclasses. `RunManifest.from_dict()` and
`from_yaml()` validate complete records; `to_dict()` and `to_yaml()` return new
mappings or deterministic safe YAML text in field order. All keys are required,
unknown keys are rejected, and arrays become immutable tuples. Serialization uses
supplied times without a clock, network access or filesystem writes.

The synthetic round-trip fixture in `tests/unit/common/test_run_manifest.py`
contains every field. Run identity includes `run_id`, `attempt_id`, schema version,
creation time and opaque code reference. Catalog evidence includes its opaque ID,
version, generation timestamp and lowercase SHA-256. Source evidence includes
ID/version, domain, authority, HTTPS citation, license/class, retrieval timestamp,
data-as-of date, content SHA-256, derivation references and freshness criterion.
Output references contain canonical relative paths and SHA-256 hashes. Probe
selection, limitations and rerun/supersession identities complete the record.

Unavailable evidence uses explicit nulls with a nonempty `unavailable_reason` on
that source, catalog or output record. Nulls never qualify. Empty derivation arrays
also block eligibility. Dates use YYYY-MM-DD; timestamps include seconds and a
timezone. Source vintage cannot postdate retrieval; catalog generation and source
retrieval cannot postdate run creation. Hashes describe declarations, not verified
bytes. No units, numeric freshness threshold or current-time assumption is supplied.

## Screening and boundaries

All six states round-trip: `real`, `empty`, `stale`, `missing_module_dir`,
`external_only`, `lfs_stub`. Only `real` can be declared eligible, with complete
BSEE/public-federal/public-domain declarations and an HTTPS BSEE citation. Other
scopes, mixed sources and unknown classifications remain blocked. External roots
are represented by opaque catalog/dataset IDs; filesystem locations are excluded.
An adapter must establish freshness and verify hashes, source inventory, citations,
rights and authenticated review. This module performs none of those operations.

For `wiki_publication.Source`, dataset ID/version, domain, authority, source class,
URL, retrieval, vintage, content hash and derivation map directly; `license` maps
to `terms_class`. Bundle catalog references must pin the catalog ID/version/hash.
The downstream adapter must add findings, aggregate data vintage, review decisions,
license-check date and clean-run evidence; this manifest cannot supply approval.

## Scanner ownership and later slices

| Script | Disposition | Responsibility |
| --- | --- | --- |
| `scripts/generate_data_catalog.py` | Keep; canonical | Dataset discovery, external roots and catalog evidence. |
| `scripts/generate_catalog.py` | Keep for now | Module schema files and legacy catalog consumers. |
| `scripts/generate_metadata.py` | Keep | Per-module freshness metadata. |
| `scripts/reporting/inventory_production_data.py` | Leave untouched | Production inventory report. |
| `scripts/reporting/inventory_safety_data.py` | Leave untouched | Safety inventory report. |

Future JSONL history will key attempts by `(run_id, attempt_id)`, reject duplicates,
and require explicit lineage for new attempts or supersession. Append atomicity,
concurrency and durability are not implemented. Generation, a real catalog example,
read-only probes and history remain under #450; readiness, workflow execution and
publication remain under #451, #452 and #453. Manifests remain in this repository
for now; copying them into a wiki is deferred. Version 1 will require convergence
with the verified ecosystem standard tracked by workspace-hub #2975.
