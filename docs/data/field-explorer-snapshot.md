# Explorer browser snapshot contract

A snapshot packages all four analytical tables and browser shards from exact,
committed local inputs. The manifest binds every artifact to its SHA-256, byte
count, record count, columns, primary key, sort order, provenance and admission.
Only complete exact-revision readback yields a publication receipt. The old
refresh entry point delegates to this publisher and requires full configuration.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-20 | Define deterministic local construction and guarded publication to replace floating partial refreshes. |

## Inputs and admission

Copy `config/hf_export/explorer_snapshot.example.json` to a committed admission
configuration. The template is deliberately blocked: its licences and evidence
are unresolved, dataset and repository identities are placeholders, and shard
bounds require explicit inputs. It is not a redistribution approval.

The five required input roles are Explorer detail, global atlas, performance,
parametric economics and the canonical `config/fields.yml` registry. Each role
binds a safe repository-relative path, a raw-byte SHA-256, public classification,
confirmed redistribution, a consistent licence, and a public HTTPS evidence URL.
The caller must reconcile the historical card's unresolved licence with any
proposed dataset licence. No automatic conversion of public access into a
redistribution grant occurs. Mixed or unresolved licences fail preflight.

Production reads use `git show` at the supplied full source commit, after
requiring that commit to equal clean HEAD, including untracked files. The
configuration is itself read from the same commit. Omit `source_git_sha` from
that committed configuration: the loader supplies verified HEAD, avoiding a
self-referential commit hash. A supplied conflicting SHA fails. A configuration
or source changed after admission must have its hashes reviewed again.

## Method and identity

There are no new engineering equations or coefficients. Existing values are
projected without recalculating economics. Expected counts are independently
obtained by enumeration in the tests.

- `field_id` preserves the canonical registry ID, independently of display name,
  aliases and mutable FDP slug. Aliases must resolve to only one field.
- `well_id` is `bsee-api12:` plus the authoritative string API12; slot is display
  data. Each `parent_field_id` must join exactly one field.
- `field_route_key` and `well_route_key` use `route-id-v1`: NFC stable-ID bytes,
  lowercase unpadded base32hex, prefixed `r1-`. See RFC 4648 (2006), section 7.
- All collections sort by their declared primary keys, using Unicode code-point
  order and numeric order for scenario keys. No locale or timestamp participates.
- Canonical JSON uses sorted keys, compact separators, UTF-8, finite numbers and
  a final LF. This is a projection convention, not RFC 8785 canonicalization.
- Browser shards append sorted records until either configured record or byte
  bounds would be exceeded. A record larger than the byte bound fails; an empty
  collection has an explicit empty shard. Manifest order defines traversal.
- Field/well counts come from records and must agree with performance coverage.
  A missing performance row is permitted only with explicit zero-well coverage;
  economics then remains `not_evaluated`. Unlisted or withheld scenarios are
  excluded. Unknown surfaced economics fields fail.

Known presentation structures, including SVG, links, CSS and timeline layout,
are omitted by explicit column projection. Retained text rejects HTML tags,
encoded tags, executable URI forms, and invalid controls. Mathematical comparison
characters remain text. Consumers must escape every value when creating HTML.

## Output and analytical migration

The output inventory contains:

- `fields.json`, `wells.json`, `countries.json`, `parametric_economics.json`;
- `README.md` with all four HF analytical configs;
- bounded `browser/<collection>/part-<ordinal>.json` files;
- `browser/manifest.json`, with inline closed column schemas and relationships.

Manifest schema `1.0.0` and projection `field_explorer_browser` are a new browser
contract. The manifest deliberately contains no containing HF commit SHA.
Analytical schema `2.0.0` uses JSON rather than the previous Parquet representation.
The receipt declares `versioned_migration_required`; compatibility with existing
Parquet consumers is **not established**. Live invocation requires explicit
migration acceptance. Retained legacy files at the target are outside the
manifest and must not be combined with the new snapshot. No remote files are
deleted by the publisher.

Browser and analytical rows must match exactly. Countries describe the global
catalog; catalog field counts never imply rich field/well drill-down readiness.
The repository inventory test independently checks the issue's ten rich fields,
fifty-six wells and three zero-well fields. Production does not hardcode them.

## Worked example

Run the synthetic example without a token, SDK, network or output directory:

```sh
python examples/hf_export/snapshot_example.py
```

Inputs are two registry fields, one API well attached to the first field, one
country with two catalog fields, and no surfaced economics. The method sorts
IDs, resolves the parent, checks explicit zero coverage for the second field,
and shards with the chosen example bound of one record. By enumeration the
answer is fields **2**, wells **1**, countries **1**, catalog fields **2**, and
parametric economics **0**. The output says `publication: not_published` and
includes the manifest digest. The automated test compares these independent
counts and rebuilds every byte twice. The example's source SHA and licence
records are synthetic test data, unsuitable for live publication.

## Invocation and failure recovery

In a clean checkout with a committed, reviewed admission configuration:

```sh
python scripts/hf_export/publish_explorer_snapshot_to_hf.py \
  --config config/hf_export/admission.json --source-sha "$SOURCE_SHA" \
  --dataset-id "$DATASET_ID" --dry-run
```

Preview is the default and performs no network calls, filesystem writes or
credential lookup. Real registry YAML requires PyYAML. Only live writes import
`huggingface_hub`. Live publication additionally requires `--publish`, an exact
`--expected-parent`, `--accept-json-migration`, and environment-backed `HF_TOKEN`.
This change does not run live publication or provision credentials.

One `create_commit(parent_commit=...)` contains every generated file. A race
fails without a receipt. Every raw file, including the manifest and dataset card,
is then read through `resolve/<returned-sha>/...`; public reads send no token,
allow only HTTPS same-origin redirects and require `x-repo-commit` to match.
Exact bytes, digests, schemas, counts, joins and analytical/browser parity are
revalidated before the receipt is emitted to stdout. SDK errors are redacted.

An upload that succeeds followed by readback failure can advance the remote head.
It yields no receipt and must never be promoted. There is no automatic retry,
rollback, deletion or history rewrite. Consumers must pin a previous verified
SHA externally; rollback means reverting that external pin. Floating consumers
must be inventoried and migrated before live use.

## Sources

- RFC 8259 (2017), sections 4, 6 and 8.1: unique object members, finite JSON
  numbers and UTF-8 interoperability. [Public text](https://www.rfc-editor.org/rfc/rfc8259.txt).
- RFC 4648 (2006), sections 7 and 10: base32hex and independent golden vectors.
  [Public text](https://www.rfc-editor.org/rfc/rfc4648.txt).
- Hugging Face Hub API reference, retrieved 2026-10-20: `create_commit`,
  `parent_commit`, `CommitOperationAdd`, `CommitInfo.oid`.
  [API reference](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api).
- Hugging Face download guide, retrieved 2026-10-20: exact full-length commit
  revisions. [Download guide](https://huggingface.co/docs/huggingface_hub/guides/download).
- Python hashlib documentation, retrieved 2026-10-20: SHA-256 raw-byte digests.
  [Library reference](https://docs.python.org/3/library/hashlib.html).
- Issue #1045 and its linked reviewed plan: artifact inventory, API12 identity,
  source admission, exact-revision receipt and scope.

## Known limits and later slices

Source-level admission is implemented, but authoritative source-registry linkage,
column-specific legal evidence and real licence reconciliation remain required
before live publication. Strict JSON column schemas are implemented in Python;
standalone JSON Schema documents and shared website fixtures remain follow-up.
Deterministic Parquet compatibility, protected publication workflow, consumer
inventory and attestation are also follow-up. The legacy results bundle remains
historical; this builder reads the underlying committed sources directly.
No website changes, solver runs, live dataset writes or promotion occurred.

## Baseline

None.

## Hooks that could not run

The hook framework is reserved for the commit runner. Direct file checks are
reported in the pull request; no hook installation or configuration is changed.

## Follow-up

Resolve real source rights, migrate analytical consumers, review the publication
workflow and complete independent review before live use.
