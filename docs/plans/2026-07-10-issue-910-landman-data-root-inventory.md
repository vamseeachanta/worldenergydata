# Plan for #910: inventory Landman underwriting data roots

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-07-10
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/910
> **Client:** N/A
> **Lane:** lane:claude
> **Execution mode:** parallel-readonly planning; single implementation lane after approval
> **Review artifacts:** scripts/review/results/2026-07-10-plan-910-codex.md | scripts/review/results/2026-07-10-plan-910-claude-unavailable.md | scripts/review/results/2026-07-10-plan-910-gemini-unavailable.md

## Resource Intelligence Summary

### Existing code and standards

- `scripts/generate_metadata.py` accepts `/mnt/ace/worldenergydata/data` as an external data root, but does not produce a Landman root inventory or quarantine classification.
- `scripts/generate_catalog.py` writes a module catalog, not a bounded root inventory.
- `config/landman.yml` declares BLM, state-GIS, county-reference, and federal-lease concepts, but does not report materialized roots or private/legacy status.
- `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` defines freshness/completeness vocabulary and distinguishes source-data dates from local refresh metadata.

### Documents and related issues

- [#910](https://github.com/vamseeachanta/worldenergydata/issues/910) requires bounded discovery, root ownership, status, representative evidence, and Landman relevance tags.
- Parent [#909](https://github.com/vamseeachanta/worldenergydata/issues/909) frames this as the source-readiness foundation.
- [#911](https://github.com/vamseeachanta/worldenergydata/issues/911) consumes this inventory; [#913](https://github.com/vamseeachanta/worldenergydata/issues/913) and [#914](https://github.com/vamseeachanta/worldenergydata/issues/914) remain downstream.
- [#462](https://github.com/vamseeachanta/worldenergydata/issues/462) is the source-refresh contract precedent.
- No relevant drive-file index result was available; the plan will rely on repo metadata and bounded live-root probes.

### Evidence

Verified 2026-07-10:

```text
#910 OPEN, status:needs-plan, lane:claude
#909 OPEN, status:needs-plan, epic
#911 OPEN, status:needs-plan, blocked by #910
#913 OPEN, status:needs-plan, blocked by #911
#914 OPEN, status:needs-plan, blocked by #911
/mnt/ace                         exists
/mnt/ace/worldenergydata         exists
/mnt/ace/Production              exists
```

The live probe establishes presence only. It does not authorize reading private/legacy contents or claim completeness. Implementation will use bounded `find -maxdepth`, `du`, manifest reads, and representative samples with explicit time/entry limits.

Reproduction proofs: N/A — this is a documentation/inventory issue, not a runtime failure.

### Gaps identified

- No repo-tracked Landman inventory schema exists.
- No bounded scanner records ownership, source authority, representative files, and status consistently.
- No machine-readable quarantine flag separates public downloaded data from private/legacy roots.
- No tests protect traversal bounds or prevent raw-data copying into the repository.
- The issue-required evidence set is not yet enumerated in the deliverable: Texas RRC, Kansas KGS, Oklahoma OCC, Colorado ECMC, pressure_screen, HSE, BSEE, Spain CORES, Kaggle ROGII, frontierdeepwater, tiny placeholders, and private/legacy roots.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-10-issue-910-landman-data-root-inventory.md` |
| Human inventory | `docs/data/landman-data-root-inventory.md` |
| Machine inventory | `data/landman-data-root-inventory.json` |
| Bounded scanner | `scripts/audit/inventory_landman_data_roots.py` |
| Tests | `tests/unit/audit/test_landman_data_root_inventory.py` |
| Plan index | `docs/plans/README.md` |

## Deliverable

A bounded, tested inventory of Landman-relevant data roots that records provenance and quarantine status without copying or recursively crawling raw/private data.

## Pseudocode

```text
scan_root(root, policy):
    validate the root against allowed probe roots
    enumerate only bounded first-level/module entries
    inspect manifests and a bounded representative sample
    collect size, owner, source authority, and evidence paths
    classify status and Landman relevance; quarantine private/legacy roots
    return rows plus probe limits and incomplete-scan warnings

write_inventory(rows, output):
    validate the closed schema and stable enums
    sort rows by canonical path and write JSON/Markdown atomically
    never copy raw data into the repository
```

Each machine-readable row will contain `root_path`, `root_owner`, `status`,
`quarantined`, `geography`, `source_authority`, `source_url`,
`representative_evidence`, `size_bytes`, `observed_at`, `landman_relevance`,
and `limitations`. The top-level document will contain `schema_version`,
`scan_policy` (`max_depth`, `max_entries`, `timeout_seconds`), `observed_at`,
`coverage_warnings`, and `rows`. A row will never contain raw record contents.

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/audit/inventory_landman_data_roots.py` | bounded policy-driven scanner |
| Create | `tests/unit/audit/test_landman_data_root_inventory.py` | TDD coverage for bounds and classification |
| Create | `data/landman-data-root-inventory.json` | machine-readable evidence snapshot |
| Create | `docs/data/landman-data-root-inventory.md` | human-readable report and limitations |
| Update | `docs/plans/README.md` | plan index row |

## TDD Test List

| Test | Verification | Expected result |
|---|---|---|
| `test_inventory_schema_and_required_tags` | representative fixtures | closed schema and required tags |
| `test_scan_is_bounded` | deep synthetic tree | depth/entry/time limits are enforced |
| `test_private_legacy_root_is_quarantined` | legacy fixture | `private/legacy`, `quarantined: true` |
| `test_public_root_records_manifest_provenance` | manifest fixture | URL, timestamp, size, hash, authority captured |
| `test_status_classes_are_distinct` | absent/configured/partial fixtures | stable status classification |
| `test_inventory_does_not_copy_raw_files` | output inspection | only report artifacts are written |
| `test_output_is_deterministic` | repeated fixture scan | byte-identical JSON/Markdown |

## Acceptance Criteria

- [ ] Tests will be written before implementation and run against synthetic fixtures.
- [ ] Inventory covers `/mnt/ace/*/data`, `/mnt/ace/worldenergydata/data`, and explicitly named legacy/private roots without recursive bulk crawling.
- [ ] Inventory explicitly accounts for Texas RRC, Kansas KGS, Oklahoma OCC, Colorado ECMC, pressure_screen, HSE, BSEE, Spain CORES, Kaggle ROGII, frontierdeepwater, tiny placeholder roots, and private/legacy roots, marking unavailable items rather than silently omitting them.
- [ ] Each row records path, size, owner/root owner, geography, source authority, status, representative evidence, and Landman relevance tags.
- [ ] Status enum includes `downloaded`, `derived`, `configured-only`, `partial/error`, `missing`, and `private/legacy`.
- [ ] Private/client/legacy rows are quarantined and cannot be promoted by the scanner.
- [ ] Outputs are deterministic, public-safe, and contain no copied raw data or client identifiers.
- [ ] #911 can consume this inventory; #913/#914 remain downstream.
- [ ] Focused tests, legal scan, diff check, and bounded live-root smoke pass.
- [ ] Adversarial plan review artifacts exist before `status:plan-review`.

## Risks and Open Questions

- `/mnt/ace` may contain private or legacy material; the scanner must fail closed and record only metadata for quarantined roots.
- Mount availability and ownership may differ by machine; observed state must not be generalized to every machine.
- File modification time is not source-data vintage; source dates will be reported only when a manifest or dataset field provides them.
- The inventory will not decide which source to acquire; #911 owns the readiness matrix and #913/#914 own acquisition/feasibility plans.

## Complexity: T2

T2: one bounded scanner, two report formats, fixture-based tests, and live metadata smoke with no raw-data mutation.
