# Repository Structure Standard

Issue: [worldenergydata#394](https://github.com/vamseeachanta/worldenergydata/issues/394)

This standard defines the Phase 1 folder/file structure contract for `worldenergydata`.
It is intentionally conservative: the current pass adds documentation, a machine-readable
contract, tests, and enforcement. It does **not** authorize broad package moves or docs tree
moves. Generated artifact deletion or tracked evidence relocation under a generated root
requires the retirement rule below.

## Canonical source of truth

- Human-readable standard: `docs/standards/repo-structure.md`
- Machine-readable contract: `config/repo_structure.yml`
- Checker: `scripts/maintenance/verify_repo_structure.py`
- Tests: `tests/repo_structure/test_repo_structure_contract.py`

Run the checker from the repository root:

```bash
PYTHONPATH='src:../assetutilities/src' uv run python scripts/maintenance/verify_repo_structure.py
```

Run the targeted tests:

```bash
PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest tests/repo_structure/test_repo_structure_contract.py -q
```

## Root contract

New tracked or non-ignored working-tree root entries must be intentionally classified in
`config/repo_structure.yml`. The checker reads `git ls-files` plus `git status --short
--untracked-files=all` by default, so it catches committed state and visible pre-commit
drift without scanning ignored caches or generated local outputs.

Root entries are classified as:

1. `allowed_roots` — canonical source, tests, docs, config, scripts, tool metadata, and
   approved root files.
2. `generated_artifact_roots` — generated-output-style roots that require explicit
   temporary-exception metadata before they are tolerated.
3. `ignored_roots` — local caches, virtualenvs, build outputs, or untracked operational
   roots that are not part of the tracked Phase 1 contract.
4. `temporary_exceptions` — tracked generated-looking artifacts preserved as durable
   evidence until follow-up classification decides whether to retain, relocate, or delete.
   Each temporary exception must list explicit `allowed_paths`; new generated-root paths are
   rejected until classified.

## Generated-output policy

Retire tracked generated-looking artifacts only under the retirement rule below. Each such
root must be classified as one of:

- unauthorized generated artifact,
- durable evidence, or
- temporary durable exception with owner, review date, follow-up URL, and justification.

For this Phase 1 pass, existing tracked `logs/` and `reports/` content is preserved as
`durable-evidence` temporary exceptions. Generated-file retirement follows the rule below.

## Retiring a generated file

`config/generated_retirements.yml` records one entry per retired generated path.
Each entry contains the repository-relative `path`, the `sha256` of its last
committed content, a valid calendar `date` in `YYYY-MM-DD` form, a substantive
`reason` of at least 30 characters, a `disposition`, and a `follow_up` issue or
pull request URL in this repository. Unknown fields, duplicate YAML mapping
keys, duplicate paths and placeholder metadata are rejected. The register is a
mapping with a `retirements` list; a missing register is treated as an empty list.

The disposition is either `cold-store`, with a relative `dataset_path` inside
the store and a relative `digest_list` name there, or `reproducible`, with the
`command` that regenerates the file. Both store fields reject absolute paths,
drive/URL syntax and traversal. Dataset paths additionally reject host references.
Qualified-domain and IPv4 prefixes, including a terminal DNS root dot, are treated
as host references; versioned relative dataset directories are permitted. The
checker validates reference form and does not access a store or execute a
regeneration command.

A deletion under a generated root is accepted only when the same change adds a
valid entry for that exact path and its digest matches the file at `HEAD`.
The checker reads the committed blob as bytes and computes SHA-256 itself.
An unreadable committed blob or a different digest prevents retirement.
Staged and unstaged deletions are checked alike. A rename is a retirement of the
old path plus a new file; the old path needs a matching entry and the new path
must be classified under the existing rules. Without an entry, deletion and
rename remain refused under the original violation code.

A path with a valid retirement entry no longer needs an `allowed_paths` row.
The same change must remove its row: a leftover row is an error. An entry for a
path that is still tracked is also an error; paths being deleted and old paths
being renamed in the current change are excluded from that tracked-path check.
A retired path shall not be used again for a new tracked file.

On every default run, including a clean checkout, the checker validates register
form, duplicate paths, tracked-path conflicts and leftover classification rows.
For historical entries whose path is already absent from `HEAD`, the digest is
checked for form only: 64 lowercase hexadecimal characters. Its content cannot
be recomputed from `HEAD`. Independent errors are reported together; malformed
entries do not exempt paths from the existing classification or refusal checks.
Explicit `--path` mode keeps its path-only meaning and reads no Git status; it
checks register form and leftover rows without inferring retirement status.

The maintainer approves a retirement through the pull request carrying its entry.
For `cold-store`, the digest list must exist in the store before the entry is
merged. The maintainer confirms that existence because the checker cannot.
Building this rule approves no individual retirement.

The following is a synthetic example, not an entry or a retirement approval.
Its digest and dataset are illustrative and shall be replaced with verified
values in a retirement pull request:

```yaml
retirements:
  - path: reports/example.txt
    sha256: '0000000000000000000000000000000000000000000000000000000000000000'
    date: '2026-10-13'
    reason: This synthetic file is retained in an example cold-store dataset.
    disposition:
      kind: cold-store
      dataset_path: synthetic/generated-example
      digest_list: sha256.txt
    follow_up: https://github.com/vamseeachanta/worldenergydata/issues/394
```

## Change rules

- Add new source code under `src/worldenergydata/`.
- Add tests under `tests/`, mirroring the relevant behavior/domain where practical.
- Add operational repo checks under `scripts/maintenance/`.
- Add shared repo policy and standards under `docs/standards/`.
- Add machine-readable policy under `config/`.
- Do not add new root files or directories unless the contract is updated in the same
  transaction and the checker remains green.
- Do not move source/docs/generated artifacts without reference-scan proof, rollback notes,
  and explicit scope approval.

## Enforcement

The pre-commit configuration includes the local `repo-structure-contract` hook. CI or
manual validation should run the same checker before closeout. The checker emits stable
violation codes such as `unknown-root`, `generated-root-missing-exception`, and
`invalid-exception-metadata` to support deterministic follow-up.

The existing generated-output checks also emit `generated-path-not-classified`
and `generated-artifact-deletion-or-relocation`. Retirement-specific codes are:

| Code | Criterion violated |
|---|---|
| `invalid-retirement-entry` | Register or entry schema, field form or unique YAML keys. |
| `duplicate-retirement-entry` | More than one entry names the same path. |
| `retirement-digest-mismatch` | Entry SHA-256 differs from the committed blob at `HEAD`. |
| `retirement-entry-for-tracked-path` | Entry names a path still tracked in this change. |
| `retired-path-still-allowed` | Entry path remains in an `allowed_paths` row. |
