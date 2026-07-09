# Plan for #910: Inventory /mnt/ace ecosystem data roots for underwriting readiness

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-07-09
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/910
> **Client:** N/A
> **Project:** N/A
> **Lane:** lane:claude
> **Review artifacts:** scripts/review/results/2026-07-09-plan-910-claude.md | scripts/review/results/2026-07-09-plan-910-codex.md | scripts/review/results/2026-07-09-plan-910-codex-r2.md | scripts/review/results/2026-07-09-plan-910-codex-r3-content.md | scripts/review/results/2026-07-09-plan-910-codex-r4-content.md | scripts/review/results/2026-07-09-plan-910-codex-subagent.md | scripts/review/results/2026-07-09-plan-910-gemini.md

---

## Resource Intelligence Summary

### Existing repo code

- Found: `scripts/setup-data-link.sh` documents the current partial-symlink topology for bulk BSEE/HSE data under `/mnt/ace/worldenergydata/data`.
- Found: `tests/integration/test_data_symlink.py` is the strongest checked-in proof that the repo uses per-subtree symlinks, not a whole-tree `data/` symlink.
- Found: `docs/data/LOCAL_DATA_PATTERN.md` defines the local-only data pattern for large public, re-downloadable data.
- Found: `docs/data/TWO_TIER_DATA.md` describes the two-tier data intent, but its whole-tree symlink text conflicts with the current script and integration test.
- Found: `docs/data/source-refresh-acceptance-criteria.md`, `data/source-refresh-acceptance-contract.json`, and `scripts/audit/validate_source_refresh_contract.py` define the existing source-readiness contract vocabulary. The #910 inventory will map to this vocabulary where useful, but it will not reuse freshness/completeness terms as direct substitutes for data-root inventory status.
- Found: `data/catalog.yaml`, `module-manifest.yaml`, `scripts/generate_catalog.py`, `scripts/generate_data_catalog.py`, and `scripts/generate_metadata.py` provide catalog and metadata precedents. Recursive generators will not be reused directly across all `/mnt/ace` roots because #910 requires bounded discovery only.
- Gap: no checked-in script or report currently inventories `/mnt/ace/*/data`, `/mnt/ace/worldenergydata/data`, and named private/legacy roots for landman underwriting readiness.
- Gap: no checked-in report currently distinguishes public downloaded modules, configured-only placeholders, derived artifacts, partial/error roots, and private/legacy quarantine roots across the repo ecosystem.

### Standards

| Standard | Status | Source |
|---|---|---|
| Source refresh acceptance contract | applicable as vocabulary input, not a direct replacement for #910 inventory status | `docs/data/source-refresh-acceptance-criteria.md`, `data/source-refresh-acceptance-contract.json` |
| Local data residence pattern | applicable | `docs/data/LOCAL_DATA_PATTERN.md`, `scripts/setup-data-link.sh`, `tests/integration/test_data_symlink.py` |
| Formal `docs/DATA_RESIDENCE_POLICY.md` | gap | referenced by `docs/data/LOCAL_DATA_PATTERN.md`, but missing in this checkout |

### LLM Wiki pages consulted

- No relevant wiki pages were consulted. This issue is repo-data inventory work with `Client: N/A`.

### Documents consulted

- Issue #910: defines required roots, inventory fields, status vocabulary, landman tags, bounded discovery, and private/legacy quarantine.
- Parent issue #909: establishes the underwriting-data epic and dependent child issues for onshore, country, Arkansas, BLM, county-title, and diligence-pack work.
- Issue #462 and `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md`: prior source-readiness contract lineage and validator pattern.
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`: prior bounded capability/readiness methodology.
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`: prior bounded data audit method using `du`, `find -maxdepth`, metadata/config/catalog reads, and no refresh.
- `docs/reports/data-freshness-scorecard-2026-06-08.md`: latest checked-in source freshness scorecard artifact.
- Drive-index search for `worldenergydata onshore landman underwriting mnt ace data inventory`: returned no relevant landman/energy inventory document; top hits were unrelated CAD archive files under a broad local archive root, and `master_document_index` timed out while two indexes were stale.

### Gaps identified

- The implementation will create a bounded inventory script from scratch.
- The implementation will create a human-facing HTML report and small machine-readable sidecar from scratch.
- The implementation will add focused unit tests from scratch for bounded traversal, status classification, quarantine behavior, landman tags, and report rendering.
- The implementation will update existing data documentation to link the new inventory and correct the stale whole-tree symlink wording in `docs/data/TWO_TIER_DATA.md`.
- The implementation will not ingest, copy, normalize, or deeply inspect private/client/legacy data.

### Execution mode

- Planning used `parallel-readonly` resource intelligence and provider review.
- Approved implementation will use `single-lane` execution because the planned script, tests, HTML report, JSON sidecar, and data-documentation edits share a single inventory contract.
- No implementation will start until #910 has both `status:plan-approved` on GitHub and the local plan-approved marker required by `issue-planning-mode`.
- TDD will be enforced with a RED checkpoint: the implementer will write `tests/unit/audit/test_ace_data_root_inventory.py`, run the focused test command, capture the expected failures, and only then implement the script/report generation.

### Evidence (embedded verification)

**Issue statuses** (verified 2026-07-09T02:39:40Z via `gh issue view`):

```json
{"number":910,"state":"OPEN","title":"docs(data): inventory /mnt/ace ecosystem data roots for underwriting readiness","url":"https://github.com/vamseeachanta/worldenergydata/issues/910","labels":["documentation","priority:high","cat:data","domain:quality","lane:claude","status:needs-plan"]}
{"number":909,"state":"OPEN","title":"epic(landman): underwriting data acquisition and country/state coverage matrix","url":"https://github.com/vamseeachanta/worldenergydata/issues/909","labels":["enhancement","priority:high","cat:data","domain:ingest","lane:claude","epic","status:needs-plan"]}
```

**File existence** (verified 2026-07-09T02:39:40Z and 2026-07-09T02:44:00Z):

```text
EXISTS: scripts/setup-data-link.sh
EXISTS: tests/integration/test_data_symlink.py
EXISTS: docs/data/LOCAL_DATA_PATTERN.md
EXISTS: docs/data/TWO_TIER_DATA.md
EXISTS: docs/data/DATA_MAP.md
EXISTS: docs/data/source-refresh-acceptance-criteria.md
EXISTS: data/source-refresh-acceptance-contract.json
EXISTS: data/catalog.yaml
EXISTS: module-manifest.yaml
EXISTS: scripts/audit/data_freshness_scorecard.py
EXISTS: scripts/audit/validate_source_refresh_contract.py
EXISTS: scripts/generate_catalog.py
EXISTS: scripts/generate_data_catalog.py
EXISTS: scripts/generate_metadata.py
MISSING: docs/DATA_RESIDENCE_POLICY.md
MISSING: src/worldenergydata/common/data_resolver.py
MISSING (new - this plan will create): scripts/audit/inventory_ace_data_roots.py
MISSING (new - this plan will create): tests/unit/audit/test_ace_data_root_inventory.py
MISSING (new - this plan will create): docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.html
MISSING (new - this plan will create): docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.json
```

**Line excerpts**:

```text
$ sed -n '1,16p' scripts/setup-data-link.sh
#!/usr/bin/env bash
# Setup partial data symlinks for worldenergydata.
#
# Per the 2026-03-24 relocation (RELOCATION-LOG.md at /mnt/ace/worldenergydata),
# bulk public data (~9.4 GB across HSE raw + BSEE bin/zip) lives outside the
# git repo. Smaller modules (BSEE current, paleowells, marine_safety,
# vessel_hull_models, etc.) stay in the repo. This script wires the three
# relocated subtrees as per-path symlinks INTO the repo's data/ tree, leaving
# everything else untouched.
```

```text
$ sed -n '1,20p' tests/integration/test_data_symlink.py
"""Integration tests for symlink-based data flow.

These tests verify the partial-symlink data architecture introduced by #359:
- Git repo holds smaller modules in-tree (BSEE current, paleowells,
  marine_safety, vessel_hull_models, schemas, catalogs -- ~389 MB total)
- /mnt/ace/worldenergydata/data/ holds the bulk relocated subtrees
  (HSE raw 6.7 GB, BSEE bin 2.5 GB, BSEE zip 230 MB)
- scripts/setup-data-link.sh wires the relocated subtrees as PER-PATH
  symlinks INSIDE the repo's data/ tree (NOT a whole-tree symlink -- that
  would erase access to the in-tree modules)
```

```text
$ sed -n '8,19p' docs/data/TWO_TIER_DATA.md
`scripts/setup-data-link.sh` creates a symlink from the repo's `data/` directory
to the external storage mount:

```
data/ -> /mnt/ace/worldenergydata/data/
```
```

**Bounded `/mnt/ace` inventory evidence** (read-only subagent result, 2026-07-08T21:36:44-05:00):

```text
/mnt/ace/worldenergydata/data          16G  main relevant public inventory root: external/, modules/, spain/
quarantine_root_001                   772G  broad archive root; tracked outputs use redacted ID only
quarantine_root_002                   1.3G  third-party typewell root; license/provenance quarantine
quarantine_root_003                   7.2M  sibling repo data root; tracked outputs use redacted ID only
quarantine_root_004                   704K  adjacent repo root; tracked outputs use redacted ID only
quarantine_root_005                    29G  private/legacy production root; tracked outputs use redacted ID only
```

**First-level `/mnt/ace/*/data` evidence** (verified by Codex review with `find /mnt/ace -maxdepth 2 -type d -name data`):

```text
14 first-level data roots observed.
Tracked artifacts will name public/allowlisted roots only and will represent private,
client, adjacent-repo, and unknown roots as redacted quarantine IDs.
```

**Observed `worldenergydata` data modules** (read-only subagent result):

```text
bsee             3.7G  downloaded local corpus
hse              6.7G  raw HSE corpus
texas_rrc        5.1G  downloaded manifest; source package/config present
kansas_kgs       144M  data manifest exists; no matching src package/config observed
oklahoma_occ      79M  data manifest exists; no matching src package/config observed
colorado_ecmc    237M  data manifest exists; no matching src package/config observed
pressure_screen  2.5M  derived output; 30,100 wells screened
spain/cores      568K  refreshed 2026-07-07; 4,375 records; no matching package/config observed
```

**Drive-index search evidence**:

```text
$ python scripts/data/drive-index-search/search.py "worldenergydata onshore landman underwriting mnt ace data inventory" --json --caller plan-resource-intel
WARNING: index og_standards_inventory is 193 days stale (threshold 90)
WARNING: index master_document_index is 83 days stale (threshold 60)
warning: index master_document_index timeout ... -- skipping
Top returned hits were unrelated CAD archive files under a broad local archive root.
```

**Reproduction proofs**:

N/A - #910 is a documentation/inventory issue. It does not allege a runtime failure.

Distinct sources consulted: issue #910, parent issue #909, `scripts/setup-data-link.sh`, `tests/integration/test_data_symlink.py`, `docs/data/LOCAL_DATA_PATTERN.md`, `docs/data/TWO_TIER_DATA.md`, source-refresh contract files, prior reports #349/#350/#462, bounded `/mnt/ace` command evidence, and drive-index search.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-07-09-issue-910-mnt-ace-ecosystem-data-inventory.md` |
| Plan index row | `docs/plans/README.md` |
| Tests | `tests/unit/audit/test_ace_data_root_inventory.py` |
| Implementation | `scripts/audit/inventory_ace_data_roots.py` |
| HTML inventory report | `docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.html` |
| Machine-readable inventory sidecar | `docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.json` |
| Data documentation link/update | `docs/data/DATA_MAP.md` |
| Data architecture correction | `docs/data/TWO_TIER_DATA.md` |
| Plan review - Claude | `scripts/review/results/2026-07-09-plan-910-claude.md` |
| Plan review - Codex r1 | `scripts/review/results/2026-07-09-plan-910-codex.md` |
| Plan review - Codex r2 | `scripts/review/results/2026-07-09-plan-910-codex-r2.md` |
| Plan review - Codex r3 content | `scripts/review/results/2026-07-09-plan-910-codex-r3-content.md` |
| Plan review - Codex r4 content | `scripts/review/results/2026-07-09-plan-910-codex-r4-content.md` |
| Plan review fallback - Codex subagent | `scripts/review/results/2026-07-09-plan-910-codex-subagent.md` |
| Plan review - Gemini | `scripts/review/results/2026-07-09-plan-910-gemini.md` |

---

## Deliverable

A bounded, reviewed `/mnt/ace` ecosystem data-root inventory will exist as an HTML report plus JSON sidecar, with a tested generator that classifies downloaded, derived, configured-only, partial/error, missing, and private/legacy roots for landman underwriting readiness.

---

## Pseudocode

```text
PUBLIC_INSPECTION_ALLOWLIST = {
    /mnt/ace/worldenergydata/data,
}

PUBLIC_WORLDENERGYDATA_SUBROOTS = {
    modules/bsee,
    modules/hse,
    modules/texas_rrc,
    modules/kansas_kgs,
    modules/oklahoma_occ,
    modules/colorado_ecmc,
    modules/pressure_screen,
    spain/cores,
}

QUARANTINE_CLASSES = {
    broad_archive_root,
    private_legacy_root,
    client_or_project_root,
    adjacent_repo_root,
    knowledge_archive_root,
    third_party_license_unclear_root,
    unknown_non_allowlisted_root,
}

DISCOVERY_LIMITS = {
    first_level_data_root_depth: 2,
    public_sample_depth: 3,
    max_entries_per_public_root: 40,
    max_manifest_files_per_public_root: 5,
    max_manifest_bytes: 65536,
    per_root_timeout_seconds: 10,
    follow_symlinks: false,
}

function discover_data_roots(base_root, explicit_roots):
    collect first-level children matching /mnt/ace/*/data with max_depth exactly 2
    add explicit allowlisted public roots such as /mnt/ace/worldenergydata/data
    add explicit private/legacy roots only as redacted quarantine rows
    do not follow symlinks
    return sorted unique candidate roots

function classify_root_before_inspection(root):
    if root is not in PUBLIC_INSPECTION_ALLOWLIST: return private/legacy with "unknown root not allowlisted"
    return inspectable_public

function inspect_root(root):
    root_class = classify_root_before_inspection(root)
    if root_class is private/legacy:
        assign stable redacted ID such as quarantine_root_001
        do not run du or any tree-size walker
        optional local-only stat may check existence/type, but tracked outputs do not include raw path
        do not list children
        do not read manifests
        do not record representative files
        return row with status private/legacy, redacted root ID, size_bucket "not measured", source class, and quarantine reason
    run bounded root-level size check only for inspectable public roots; if timeout occurs, record "size not measured"
    list representative children only under PUBLIC_WORLDENERGYDATA_SUBROOTS using public_sample_depth and max_entries_per_public_root
    read at most max_manifest_files_per_public_root manifest/catalog/metadata files
    read no more than max_manifest_bytes from any manifest/catalog/metadata file
    derive owner/repo, geography, source authority, status, and landman tags
    return inventory row

function classify_status(row):
    if root is private/client/legacy/quarantine pattern: private/legacy
    elif root is known derived output: derived
    elif data and manifest evidence exist: downloaded
    elif config exists but no data root: configured-only
    elif representative evidence shows warnings, empty files, stale errors, or incomplete manifests: partial/error
    else missing

function render_outputs(rows):
    write small JSON sidecar containing only metadata, classifications, and representative evidence
    never include raw path, child paths, manifest content, or representative files for private/legacy rows
    write HTML report grouped by public modules, derived roots, configured-only/missing roots, country roots, sibling repo roots, and quarantine roots
    include command/evidence appendix, exact traversal caps, data-residence limitations, and machine-local coverage statement
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `tests/unit/audit/test_ace_data_root_inventory.py` | TDD coverage for bounded discovery, classification, quarantine, landman tags, and report rendering |
| Create | `scripts/audit/inventory_ace_data_roots.py` | Bounded generator for the inventory report and JSON sidecar |
| Create | `docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.html` | Human-facing inventory artifact per HTML-default rule |
| Create | `docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.json` | Small machine-readable sidecar for later #911/#917/#918 work |
| Modify | `docs/data/DATA_MAP.md` | Link the new inventory and identify stale data-residence wording to reconcile |
| Modify | `docs/data/TWO_TIER_DATA.md` | Correct stale whole-tree symlink/DataResolver wording to match `scripts/setup-data-link.sh` and `tests/integration/test_data_symlink.py` |
| Modify | `docs/plans/README.md` | Add this plan to the active plan index |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_discovers_first_level_data_roots_only` | discovery uses bounded `/mnt/ace/*/data` style roots and does not crawl deeply | temp tree with nested large-looking paths | only first-level data roots and explicit roots returned |
| `test_unknown_roots_default_to_private_legacy` | non-allowlisted roots are quarantined before any child listing | synthetic private and unknown data roots | `status: private/legacy`, reason `unknown root not allowlisted`, zero child-read calls |
| `test_private_legacy_roots_are_quarantined_without_deep_listing` | private/archive roots are classified before recursive inspection | roots matching private, client/project, adjacent-repo, archive, and broad-shared-drive classes | `status: private/legacy`, no `du`, child listing, or manifest reads |
| `test_discovery_limits_are_enforced` | exact depth, entry, manifest, byte, timeout, and symlink limits are enforced | temp tree with deep dirs, symlink loop, many files, oversized manifest | no symlink follow; max depth 2 discovery; max sample depth 3; max 40 entries; max 5 manifests; max 65,536 bytes each |
| `test_tracked_outputs_redact_quarantine_paths` | tracked HTML/JSON do not publish raw private/quarantine root tokens | rows with synthetic private root names and raw paths | output contains `quarantine_root_001` style IDs and no raw private path/name substrings |
| `test_private_roots_do_not_use_tree_size` | private rows do not call recursive size walkers | synthetic private root with size function spy | size walker is not called; tracked row size bucket is `not measured` |
| `test_downloaded_module_status_from_manifest_and_size` | public modules with data and manifest evidence classify as downloaded | synthetic `texas_rrc` root with manifest and size | row status `downloaded` with representative manifest |
| `test_derived_root_status` | derived outputs classify separately from downloaded source roots | synthetic `pressure_screen` root with summary output | row status `derived` and pressure/depletion tag |
| `test_configured_only_status` | configured source without materialized data is not reported as downloaded | config row with missing data root | row status `configured-only` |
| `test_partial_error_status` | warnings, empty representative files, or manifest error flags map to partial/error | synthetic manifest with warning/error evidence | row status `partial/error` |
| `test_landman_relevance_tags_are_constrained` | landman tags use #910 vocabulary only | rows for well, pressure, HSE, macro/country, and irrelevant roots | allowed tag set only |
| `test_html_report_has_required_sections` | human-facing output includes public modules, country roots, sibling roots, and quarantine sections | representative rows | HTML includes all section headings and evidence appendix |
| `test_json_sidecar_is_small_and_path_safe` | sidecar records metadata/classification, not large samples or private contents | representative rows with private root | JSON has bounded fields and no deep private file list |

---

## Acceptance Criteria

- [ ] Tests are written before implementation: `tests/unit/audit/test_ace_data_root_inventory.py`.
- [ ] RED checkpoint is captured before implementation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/unit/audit/test_ace_data_root_inventory.py -q` fails for the expected missing implementation behavior.
- [ ] Focused tests pass: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/unit/audit/test_ace_data_root_inventory.py -q`.
- [ ] The generator supports a dry-run or temp-root mode so tests do not require live `/mnt/ace`.
- [ ] Live run succeeds with bounded discovery only and no downloads: `python scripts/audit/inventory_ace_data_roots.py --root /mnt/ace --max-root-depth 2 --sample-depth 3 --max-entries 40 --max-manifests 5 --max-manifest-bytes 65536 --timeout-seconds 10 --no-follow-symlinks --html docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.html --json docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.json`.
- [ ] Public/allowlisted rows record path, size, repo/root owner, geography, source authority, status, representative manifests/files, and landman relevance tags.
- [ ] Private/legacy and unknown non-allowlisted rows in tracked HTML/JSON record only a redacted quarantine ID, root class, status, landman tag, `size_bucket: not measured`, and quarantine reason; they do not record raw root paths, raw root names, child paths, manifest contents, representative files, or recursively measured tree sizes.
- [ ] Status values are limited to `downloaded`, `derived`, `configured-only`, `partial/error`, `missing`, and `private/legacy`.
- [ ] Landman tags are limited to `title/lease`, `well/permitting`, `production`, `pressure/depletion`, `infrastructure`, `HSE/environmental`, `macro/country`, `subsurface/geology`, and `not relevant`.
- [ ] The inventory includes evidence for Texas RRC, Kansas KGS, Oklahoma OCC, Colorado ECMC, `pressure_screen`, HSE, BSEE, Spain CORES, third-party typewell roots, adjacent repo roots, tiny placeholder data roots, and private/legacy roots when present on the live filesystem; non-public roots are represented with redacted quarantine IDs in tracked outputs.
- [ ] The report explicitly states that `/mnt/ace` coverage is machine-local and partial, not a universal claim about every machine.
- [ ] The report quarantines private/client/legacy roots and Kaggle ROGII until provenance/legal status is explicit.
- [ ] The implementation does not copy large data into git and does not include private/client file contents in tracked artifacts.
- [ ] The implementation includes output-redaction validation for the generated HTML/JSON and fails if raw private/quarantine root paths or names appear in tracked outputs.
- [ ] `docs/data/TWO_TIER_DATA.md` is corrected to describe the current per-subtree symlink topology and not cite missing `src/worldenergydata/common/data_resolver.py` as an existing source file.
- [ ] The HTML report states that `docs/DATA_RESIDENCE_POLICY.md` is missing and that the corrected `TWO_TIER_DATA.md`, `scripts/setup-data-link.sh`, and `tests/integration/test_data_symlink.py` are the accepted local evidence for #910.
- [ ] Legal/security scan is run as a full scan against this checkout, not workspace-hub root or diff-only mode: `cd /mnt/local-analysis/workspace-hub && scripts/legal/legal-sanity-scan.sh --repo=../worldenergydata`.
- [ ] A targeted generated-output redaction check is run after the live inventory: `python scripts/audit/inventory_ace_data_roots.py --validate-redactions --html docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.html --json docs/reports/2026-07-09-worldenergydata-ace-data-root-inventory.json`.
- [ ] Plan and code/artifact review artifacts are posted to `scripts/review/results/`.

---

## Adversarial Review Summary

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | UNAVAILABLE | Claude Code is installed but noninteractive review is not logged in/trusted in this session. See review artifact. |
| Codex r1 | MAJOR | Initial review blocked on pre-quarantine inspection, unenforced traversal bounds, data-residence conflict not gated, and missing execution/TDD gate detail. |
| Codex r2 | MAJOR | Re-review blocked on raw quarantine path leakage in tracked outputs and unsatisfied provider-review gate. |
| Codex r3 content | MAJOR | Content re-review confirmed core fixes but blocked on diff-only legal scan coverage and raw private-root tokens in the r1 review artifact. |
| Codex r4 content | APPROVE | Confirmed r3 content blockers closed: full legal scan, redacted review artifact, output redaction policy, no private `du`, bounded traversal. |
| Codex subagent fallback | MAJOR | Fallback review additionally blocked recursive private-root size checks and mis-targeted legal scan. |
| Gemini | UNAVAILABLE | Gemini CLI is installed but noninteractive authentication is unavailable in this session. See review artifact. |

**Overall result:** CONTENT PASS / PROVIDER-GATE BLOCKED. Codex r4 approved the plan content, but Claude and Gemini remain unavailable. Keep this plan in `draft` and keep the GitHub issue at `status:needs-plan` unless a second provider review lands or the user explicitly accepts degraded plan-review coverage.

Revisions made based on review:
- Moved quarantine classification before any child listing or manifest reads.
- Added an explicit public inspection allowlist and default quarantine for unknown roots.
- Added exact traversal, entry, manifest-byte, timeout, and no-symlink-follow limits.
- Added tests for unknown-root quarantine, private-root no-child-read behavior, traversal caps, and symlink-loop resistance.
- Made `docs/data/TWO_TIER_DATA.md` correction a planned file change and acceptance criterion.
- Added execution mode and RED-phase TDD checkpoint requirements.
- Changed private/quarantine tracked output policy to redacted IDs only, with no raw root path/name and no recursive tree-size measurement.
- Added output-redaction validation and corrected the legal scan command to target the `worldenergydata` checkout.
- Changed the legal scan acceptance criterion from diff-only to full-repo scan so newly generated untracked HTML/JSON artifacts are included.
- Redacted raw private-root tokens from the initial Codex review artifact before promotion.
- Added Codex r4 content approval. No GitHub `status:plan-review` label will be applied until provider coverage is satisfied or explicitly degraded by the user.

---

## Risks and Open Questions

- **Risk:** private/client/legacy roots can leak sensitive or provenance-unclear information if tracked artifacts include raw local root names or paths. The implementation will classify roots before inspection, quarantine unknown/non-allowlisted roots by default, and write only redacted quarantine IDs to tracked outputs.
- **Risk:** `/mnt/ace` is machine-local. The report will state that it reflects this host at the run timestamp and will avoid "all machines" claims.
- **Risk:** `docs/data/TWO_TIER_DATA.md` conflicts with `scripts/setup-data-link.sh` and `tests/integration/test_data_symlink.py`. #910 will correct that doc for the current partial-symlink topology; the missing formal `docs/DATA_RESIDENCE_POLICY.md` can be filed as follow-on if needed after #910.
- **Risk:** Kaggle ROGII may be useful for typewell work but cannot be treated as public-source-ready until license/provenance handling is explicit.
- **Open:** whether #910 should also create a reusable status taxonomy document outside the report. Default plan: keep taxonomy inside the generator/tests/report and let #911/#917 reuse the JSON sidecar.

---

## Complexity: T2

**T2** - documentation plus a bounded audit script, unit tests, a human-facing HTML report, and a machine-readable sidecar. The work is multi-file but does not modify production application behavior or ingest data.
