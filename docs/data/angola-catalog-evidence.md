# Angola catalog evidence reader

The optional offshore catalog extension exposes dated research alongside legacy
catalog attributes. Exact-ID evidence views retain scope, source URLs, date
bounds and uncertainty. They do not establish current engineering suitability.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Added reader usage and a synthetic example to explain scope and publication gates. |

## Contract and method

The [extension overview for issue 1144](../../data/modules/offshore_assets/README.md#angola-evidence-extension)
and the [artifact contract](../../data/modules/offshore_assets/schema.yaml)
define the method. The issue's final dispositions (2026) require exact evidence
identities, separate field/development/phase scopes, and preservation of upper
date bounds. No engineering equation or empirical coefficient is introduced.

Read a persisted bundle before projecting evidence:

```python
from worldenergydata.field_development.catalog_integration import (
    CatalogEvidence,
    read_bundle,
)

bundle = read_bundle(export_directory, public_only=True)
reader = CatalogEvidence(bundle)
view = reader.entity(entity_id)
record = reader.record(record_id)
```

`read_bundle` checks artifact hashes, foreign keys, decisions and dependency
closure. Use `public_only=True` for public consumption. `CatalogEvidence` takes
an already validated bundle; it is a query layer, not an authorization gate.
An in-memory draft can also be queried locally after building it.

- `entity` returns the registry row, direct record groups, source records,
  incident relationships, crosswalk candidates and accepted legacy groups.
  It includes the pinned legacy catalog digest. Unknown identifiers raise
  `KeyError`; returned objects are detached copies.
- Records retain their `link_status`, original observation and multiplicity.
  Candidate subject links remain candidates. Supporting evidence for a
  supplemental scope retains its original subject and scope.
- `record` looks up a single exact record ID, including inherited-cost parent
  references. An inherited record never becomes an independent cost observation.
- Same-name fields, phases and developments remain separate. Relationship
  evidence does not allocate costs, depths or milestones across scopes.
  Only accepted `same_entity` crosswalk groups contribute legacy attributes.

The [atlas adapter](../../scripts/field_atlas/catalog_extension.py) adds optional
`research_evidence` to extension field entries. Nonfield entries appear under
`meta.catalog_extension.nonfield_entities`, outside the `fields` collection.
Each carries its entity type, readiness and exact-ID evidence view. Source
records retain their URLs and source vintages; absent vintages remain unknown.
Country badges, legacy-only entries and non-Angola entries retain their existing
semantics. Catalog row counts remain distinct from registered identity counts.

The evidence tables remain authoritative in the bundle. The views are consumer
projections, not a second curated observation or source dataset.

## Worked example: inputs

Run the authored synthetic example with a new output directory outside the
repository. Existing destinations are refused:

```bash
uv run --no-project python scripts/field_development/example_catalog_evidence.py \
  --output "$TMPDIR/catalog-example"
```

The example writes its inputs, pinned manifest, validated draft bundle,
`field-evidence.json` and `answer.json`. The source URL uses the reserved
example domain and is not research evidence. No source retrieval is required.

| Input | Supplied scope and values |
| --- | --- |
| Example field | Field belonging to Example development; block and water depth unknown |
| Example phase | Separate phase belonging to Example development |
| Milestone | Field milestone bounded by the synthetic calendar date `2004-01-01`; precision `upper_bound_day` |
| Legacy catalog | A single Example field row; its same-name candidate remains pending |
| Costs and inherited costs | Empty input tables; no cost is assumed |

## Worked example: method and answer

The method hashes and validates the supplied inputs, builds typed registry
identities, writes and rereads the draft, then queries the field by its exact
namespaced ID. The development identity comes from the explicitly supplied
development membership. No match is promoted to accepted.

Independent hand count: one field plus one phase plus one development gives
three registry identities. Only the field enters the field collection; the
other two are nonfields. One field observation plus one field milestone gives
two direct record groups. The unreviewed legacy candidate gives zero accepted
groups. The original upper date bound remains a bound.

```json
{
  "state": "local_draft_not_for_publication",
  "registered_fields": 1,
  "registered_nonfields": 2,
  "accepted_legacy_groups": 0,
  "field_record_groups": 2,
  "milestone_precision": "upper_bound_day",
  "source_urls": ["https://example.org/catalog-evidence"]
}
```

The [example regression](../../tests/modules/field_development/test_catalog_evidence_example.py)
checks this independently enumerated answer, rejects public consumption and
refuses reuse of an existing output directory. The
[reader regressions](../../tests/modules/field_development/test_catalog_evidence.py)
also cover separate development costs, inherited references, duplicate record
multiplicity, accepted legacy groups and deferred records.

## Publication limits and remaining work

The research snapshot and signed release decisions are not supplied by this
example. It cannot establish Angola completeness or approve factual exports.
Public rows require the maintainer-reviewed eligibility matrix and source
release evidence described in the contract. Accepted equivalence additionally
requires a candidate-bound identity decision. Missing decisions remain
unresolved; all-deferred export remains an error.

Actual research publication and independent review remain prerequisites before
using a released extension. The legacy catalog is not rewritten by this reader.
