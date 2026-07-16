# Plan for #1040: portfolio required-assets and award-coverage map

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1040
> **Blocked by:** owner-approved #1039 contract
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final artifacts PENDING

## Resource Intelligence Summary

- The live sanctioned-project table exposes development type, host type, well count, SURF length, water depth, and scope notes needed to infer requirements, but missing quantities must remain explicit unknowns.
- The live award registry retains coarse `production_hub`, `sps`, `surf`, `installation`, `drilling_rig`, and `other` classes and the full value-basis vocabulary. This issue will link and deepen those records rather than duplicate them.
- `field_development` already contains concept, layout, graph, host-enrichment, and symbol vocabularies. The cost requirements layer will consume compatible concepts but will remain in the cost package so cost provenance and accounting are not coupled to visualization code.
- `config/fields.yml` resolves Big Foot and other registered fields but does not cover the full 80-project cost portfolio. The approved pilot will therefore freeze a cost-project identity/crosswalk surface rather than assume field-registry completeness.

## Artifact Map

| Action | Path |
|---|---|
| Extend | `data/modules/cost/curated/project_asset_requirements.csv` |
| Extend | `data/modules/cost/curated/award_asset_links.csv` |
| Extend | `data/modules/cost/curated/cost_project_identity.csv` |
| Extend | `data/modules/cost/curated/cost_award_identity.csv` |
| Extend | `data/modules/cost/curated/cost_requirement_identity.csv` |
| Create | `data/modules/cost/derived/award_accounting_normalized.csv` |
| Generate | `data/modules/cost/derived/cost_map_contract_manifest.v2.json` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/asset_requirements.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/award_linkage.py` |
| Create | `scripts/cost/build_asset_award_coverage.py` |
| Create | `tests/unit/cost/test_asset_requirements.py` |
| Create | `tests/unit/cost/test_award_asset_linkage.py` |
| Generate | `reports/cost/project_asset_award_coverage.csv` |
| Generate | `reports/cost/project_asset_award_coverage.html` |

## Deliverable

An empirically complete project → requirement → award decision surface using the owner-approved pilot taxonomy, with physical-scope coverage and disclosed-value coverage computed separately.

## Planned Tasks and TDD Order

1. Contract preflight tests will require the owner-approved v1 manifest/hash and reject silent enum or identity drift.
2. RED migration tests will require native amount/currency, an orthogonal `bound_type` (`point|floor|ceiling|closed_range|open_range`), price vintage, ownership, phase/scope, `capex_basis`, and conversion provenance. Rows whose source lacks those facts will carry `unknown` and remain excluded from arithmetic; the legacy GranMorgu conversion will fail closed until resourced.
3. Architecture rules will produce minimum requirement sets for tieback, FPSO, semi, spar, TLP/dry-tree, fixed platform, and unknown architectures.
4. Overrides will record project-specific quantities and exceptions with provenance; rules will never manufacture quantities.
5. Award linkage will resolve controlled opaque source-award and cost-project IDs through the four v1 identity registries and an explicit crosswalk. IDs will not derive from row order or mutable content; corrections will preserve them, tombstones will prevent reuse, and collision/foreign-key/split-merge checks will fail closed. `validation_group_id` will bind aliases/phases/derived rows for later grouped validation.
6. Coverage will enumerate all live sanctioned projects and awards, record `requirements_unknown` where evidence is insufficient, and report exact counts at build time.
7. Generated outputs and manifest v2 will expose normalized accounting eligibility and the exact contract consumed by downstream issues.

## TDD Test List

- `test_each_supported_architecture_emits_approved_minimum_requirements`
- `test_unknown_architecture_emits_requirements_unknown`
- `test_missing_quantity_remains_unknown`
- `test_alias_resolution_is_exact_or_explicitly_ambiguous`
- `test_every_source_award_has_a_stable_identity`
- `test_bundled_award_links_many_to_many_without_value_copy`
- `test_award_linkage_preserves_all_value_basis_values`
- `test_missing_native_currency_or_capex_basis_fails_closed_for_arithmetic`
- `test_legacy_conversion_without_fx_provenance_is_excluded`
- `test_alias_phase_and_derived_rows_share_validation_group_id`
- `test_not_public_counts_as_scope_evidence_not_value_coverage`
- `test_every_live_project_and_award_is_visited_once`
- `test_requirement_and_value_coverage_are_independent`
- `test_generated_matrix_is_deterministic`

## Acceptance Criteria

- [ ] Every live project will receive requirements or `requirements_unknown`.
- [ ] Every live award will carry independent axes: link resolution (`linked|unlinked|ambiguous`), scope coverage (`unknown|none|partial|full`), bundle topology (`bundle_group_id` or unbundled), counting disposition (`included|excluded|overlap` plus reason), and value basis including `not_public`.
- [ ] Architecture-specific systems and quantities will be evidence-backed.
- [ ] The build will print and persist the exact project/award set it visited.
- [ ] Coverage percentages will state numerator, denominator, exclusions, and live baseline date.
- [ ] Native value-basis, currency, and provenance semantics will remain unchanged.
- [ ] HTML and machine-readable outputs will regenerate without hand edits.
- [ ] Manifest v2 will pin schema/input hashes and will be the fail-closed handoff to #1041/#1042.
- [ ] Manifest v2 will carry the common envelope: contract version, schema hash, ordered input hashes, producer commit, generated-at policy, Decimal/rounding policy, and output hashes.

## Pseudocode

```text
assert preflight(manifest_v1)
RED accounting-row tests -> migrate source facts or explicit unknown
for each project_id: derive requirements or requirements_unknown
for each award_id: resolve project_id; link requirements many-to-many
count scope coverage independently from monetary eligibility
emit normalized rows + manifest v2
```

## Attested Evidence — 2026-07-16

Live-table enumeration and header inspection at `090228fb` verified that the award table lacks currency and structured accounting bases. This feature will address that gap; no runtime defect is alleged, so reproduction is N/A.

## Implementation and Closeout Gates

Each literal requirement node will run alone in `tests/unit/cost/test_asset_requirements.py`; each identity/linkage/coverage/report node will run alone in `tests/unit/cost/test_award_asset_linkage.py`, using the exact base `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --extra test python -m pytest -p no:cacheprovider --noconftest -o addopts=''` plus the literal file/node ID and `-xq`. Tests will be introduced one slice at a time, not collected before their slice. Every node will record behavior-relevant RED, identical-command minimal GREEN, refactor, and unchanged-command GREEN. Builders will use stable ordering, exact `Decimal`, locale `C`, UTC, injected build time, escaping, safe URLs, and two-run SHA equality. Legal/de-identification scans, T3 code/artifact review, issue comment, exact v1/v2 manifest verification, and cleanup audit will pass before close. No email, external send, or stakeholder circulation will occur.

## Out of Scope

Cost allocation, model training, FX conversion, silent requirement completion, and workbook reconciliation will remain outside this issue.

## Complexity: T3

This will scale a many-to-many, provenance-sensitive contract across the entire live portfolio.
