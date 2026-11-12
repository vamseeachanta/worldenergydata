# Cost projects to field-development catalog

Issue: [1898](https://github.com/vamseeachanta/worldenergydata/issues/1898),
parent [1038](https://github.com/vamseeachanta/worldenergydata/issues/1038).

`data/modules/cost/curated/project_field_crosswalk.csv` joins the cost register
to the catalog shipped with `worldenergydata.field_development.past_projects`.
The API is `worldenergydata.cost.project_field_crosswalk`. The join contains
identities and evidence, with no monetary values or newly inferred field data.

## Keys and cardinality

`PROJECT_ID` is the explicit locator `PROJECT:<exact PROJECT>`. The suffix is
the existing portfolio-trace natural key, including punctuation and case.
Repeated observations with the same exact label share that locator; a source
rename requires reconciliation. This locator is not an issued opaque cost ID.
`PROJECT` retains the source label, including its phase or combined scope.
`COST_PROJECT_ID` separately retains the issued opaque ID when an active held
identity exists (currently Big Foot). Join that column to opaque cost-map IDs;
do not join the natural locator column directly to opaque IDs. Blank means no
issued identity is held, rather than a fabricated new ID.

Input tables that contain controlled `PROJECT_ID` references are resolved
through `cost_project_identity.csv`. Only active, non-tombstoned project rows
qualify. The `SOURCE_TABLE` basename means the file directly under cost curated,
and `SOURCE_RECORD_LOCATOR=PROJECT=<label>` must exist there. `DISPLAY_LABEL`
and `ALIASES` do not authenticate a controlled reference. Inactive, ambiguous
or unknown IDs fail validation. When a table carries both columns, they must
agree. A staging file with the same basename cannot supply a curated locator.

`CATALOG_FIELD_ID` is a held catalog `project_id`, identical to `canonical_id`
in `config/fields.yml`. Join it to `PastProject.project_id` for the existing
attributes, including water depth, play and development system. Attributes
absent from that catalog remain absent. The crosswalk supplies no reservoir
or production values beyond those already held by downstream field sources.

One row represents one project/field pair. Several rows may link a project to
several fields; the same pair cannot repeat. A blank field ID represents one
explained project and cannot coexist with mapped rows for that project.
Group by `PROJECT_ID` when measuring coverage. Expanding a many-field join
duplicates project observations: no per-field cost allocation is established.

## Matching and evidence

- `exact_name`: equal catalog display name after case/whitespace normalization.
- `alias`: equal alias explicitly held in `config/fields.yml`.
- `operator_block`: equal nonempty normalized operator and identical full sets
  of structured blocks, with one catalog candidate. Only `OPERATOR`, `BLOCK`
  or semicolon-delimited `BLOCKS` columns supply these inputs. Blocks use
  `AA001` form; no blocks are extracted from prose. Phase/bundle labels require
  manual interpretation. Operator changes and spelling variants are not inferred.
  Any provided `BLOCK`/`BLOCKS` value is a structured input: non-`AA001` values
  reject that CSV rather than being parsed as prose. If both columns are populated,
  their sets must agree.
- `manual`: a specific, evidenced interpretation of the held project label.
- `unmatched`: no accepted link, with a nonempty `REASON` and low confidence.

The first two methods carry high confidence; operator/block carries medium.
Manual confidence is explicit. Confidence describes the identity link, not the
qualification of any cost figure. Automated methods are recomputed during
readback. Any deterministic match must remain present in a manual group.
Ambiguous candidates remain unresolved. No substring, phase stripping or fuzzy
matching is performed. This is deliberately stricter than the canonical field
registry's punctuation-insensitive resolver; no new field aliases are introduced.

All rows carry `PROVENANCE=derived`, including manual interpretations. `EVIDENCE`
is JSON with the following keys:

| Key | Meaning |
| --- | --- |
| `project_sources` | Sorted unique inventory locators, such as `data/modules/cost/curated/sanctioned_projects.csv#PROJECT=Big Foot`; controlled-reference tables use `#PROJECT_ID=<id>`. |
| `catalog_fields` | The single linked catalog ID, or an empty list for an explanation. |
| `basis` | Nonempty description of the held evidence and interpretation. |
| `limitation` | Required for mapped rows: identity link only; project scope retained; no allocation or scope equivalence. |
| `unmapped_scope` | Explicit remaining scope names for a partial link; those names also appear in the limitation. Empty when no partial coverage is declared. |

Table 1. Evidence fields are revalidated against the inventory and linked ID.

The held snapshot contains 194 projects, with 8 mapped and 186 explained
(194/194 accounted for, exceeding the issue's 90% mapped-or-explained criterion).
The 43 Asia-Pacific and Caspian staging projects and the 66 Europe staging
projects are all explained with the reason class "Outside catalog scope
(non-GoM)"; none receives a catalog ID.
The field catalog contains 11 Gulf of Mexico entries and an empty worldwide
slice. The mapped count is separate from explained coverage. Three manual links
retain initial-phase or rename wording already present in the cost register.
Tiber–Guadalupe links to `tiber` with an explicit partial-coverage limitation:
Guadalupe has no catalog ID and receives no invented ID or allocation.
The CLI reports this separately as one `partial` project within the eight mapped.

## Validation and refresh

From the repository root:

```bash
python scripts/cost/validate_project_field_crosswalk.py
```

The read-only command returns JSON counts and exits nonzero on validation
failure. `--root` selects alternate repository inputs. `--crosswalk` checks a
candidate CSV against the catalog and pinned inputs. The held output keeps its
own independent manifest digest check; a candidate need not have the held output
digest. The command loads
the implementation from this checkout, without requiring installation of all
domain packages.

Inventory includes all PROJECT- or PROJECT_ID-bearing CSVs recursively under
`data/modules/cost/curated/` and `staging/`, excluding exactly the crosswalk
itself. Other CSVs do not add projects. The four current register tables
(sanctions, awards, statements, revisions) are required. Malformed CSVs fail
loudly. Staging currently holds the Asia-Pacific and Caspian tranche and the
Europe tranche; adding or removing a staging project intentionally requires
reconciliation and manifest refresh in the same change.

This inventory rule includes `sanctioned_projects_2026.csv` (a derived
restatement) and `sanctioned_project_cost_years.csv` (statement-year metadata).
Their labels refer to projects already held in `sanctioned_projects.csv`:
they add source locators and manifest inputs, not independent observations or
additional projects. Derived and sidecar filenames receive no implicit exclusion;
new project-bearing source tables continue to be discovered recursively.
Regenerating either table requires crosswalk evidence reconciliation and
manifest refresh under the procedure below, even if project labels are unchanged.

For a refresh:

1. Load `load_cost_projects(root)` and `load_catalog(root)`. The catalog loader
   checks ID/name/block agreement with the canonical identity file. Operators
   come from `past_projects.yml`; aliases come from `config/fields.yml`.
2. Use `build_crosswalk(projects, fields)` for deterministic candidate rows.
   Review existing manual decisions and explanations against the changed
   sources; retain them only when supported. Update their structured evidence
   to the current inventory. A generic candidate rebuild does not preserve
   manual decisions.
3. Call `validate_crosswalk(rows, projects, fields)` before saving CSV with
   `COLUMNS` as the header. Review source and crosswalk diffs.
4. Save `build_manifest(root)` to
   `data/modules/cost/curated/project_field_crosswalk.manifest.json` after the
   final CSV is saved. Read it back with `validate_repository(root)`.
5. Run `tests/unit/cost/test_project_field_crosswalk.py` and
   both `tests/ci/test_project_field_crosswalk_routes.py` and
   `tests/ci/test_cost_crosswalk_data_routes.py`.

The manifest records the complete participating input set, both catalog YAMLs,
controlled identities and the crosswalk SHA-256. Its declared `utf8-lf` digest
domain decodes UTF-8 with an optional BOM, normalizes CRLF and lone CR to LF,
then hashes UTF-8 bytes. Checkout line endings therefore do not cause platform
drift. Input additions, removals or content changes require review and refresh;
updating a digest alone does not establish a valid identity interpretation.

The package source route covers cost code changes. A cost-data prefix route runs
the full cost suite for curated or staging changes, including crosswalk/manifest-only
edits. Targeted routes also cover either catalog YAML and the validation script.
The catalog route retains the existing field-development shard and adds the
catalog's own integration contract.
No existing cost value or field identity source is rewritten.
