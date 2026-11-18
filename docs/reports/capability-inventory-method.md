# Capability inventory method

The collector records repository presence without evaluating execution readiness.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| 1 | 2026-11-16 | Define the bounded collector for reproducible presence evidence. |
| 2 | 2026-11-17 | Exclude hidden/private package roots and reject output aliases to text inputs to preserve inventory evidence. |
| 3 | 2026-11-18 | Record the expanded regression coverage so the documented test scope includes package exclusions and input preservation. |

Run `python scripts/audit/check_capability_inventory.py --project-root . --json-output <output.json>` with PyYAML installed. Both arguments are required; the output parent must already exist.

An output destination that aliases a text input is rejected before writing, including normalized paths, symbolic links and hard links. Required text inputs and the optional scheduler configuration are protected; concurrent filesystem changes during collection are outside this check.

Rows union module identifiers from Module-column index tables, manifest IDs, catalog keys and immediate Python domains in both source layouts. Namespace directories with Python descendants count; compatibility copies retain every owner path. Names remain literal, without alias inference.

README, index, manifest and catalog are required. Missing optional tests or docs produce null evidence; an inspected directory without matches produces an empty list. Scheduler configuration is fingerprinted when present, without checking wiring. Missing source layouts contribute no domains. Symlinks, hidden/private directories, non-Python domains and package-root support files have explicit exclusions.

Test filenames follow `test_*.py` or `*_test.py`. Test and documentation associations use module tokens in relative paths; README mentions give line locations. These are discovery hints, with possible false matches, not proof of coverage. Collectability always remains `not_evaluated`; catalog status is empty, nonempty or absent, without data-file validation.

JSON has schema version 1.0, sorted rows, ownership paths, presence flags, findings and exclusions. Input digests fingerprint the bytes of text inputs only; source, test and documentation contents are not fingerprinted. Unchanged inputs and path inventories yield identical bytes, without a timestamp or absolute root. Malformed YAML, duplicate keys/IDs and invalid input shapes fail with bounded diagnostics before output is written. Filesystem failures return a nonzero status.

## Regression coverage

`tests/unit/audit/test_capability_inventory.py` contains 39 collected cases: 12 original presence, determinism, malformed-input and symlink cases; two hidden/private package-root cases; and 25 output-alias cases. The alias matrix covers five alias forms against five protected text inputs, including the optional scheduler configuration, and checks that input bytes remain unchanged after rejection.

These offline fixtures check the collector contract. Domain execution readiness and concurrent filesystem changes remain outside their scope.

The historical readiness report remains unchanged. Runtime collection, readiness ranking, CLI/API and scheduler checks, comprehensive claim corrections and final report companions remain follow-up work for #349. No downloads, imports of discovered domains, GitHub writes or index rewrites occur.
