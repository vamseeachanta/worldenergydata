# Repository Structure Standard

Issue: [worldenergydata#394](https://github.com/vamseeachanta/worldenergydata/issues/394)

This standard defines the Phase 1 folder/file structure contract for `worldenergydata`.
It is intentionally conservative: the current pass adds documentation, a machine-readable
contract, tests, and enforcement. It does **not** authorize broad package moves, docs tree
moves, generated artifact deletion, or tracked evidence relocation.

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

Do not delete or relocate tracked generated-looking artifacts during Phase 1. Each such
root must be classified as one of:

- unauthorized generated artifact,
- durable evidence, or
- temporary durable exception with owner, review date, follow-up URL, and justification.

For this Phase 1 pass, existing tracked `logs/` and `reports/` content is preserved as
`durable-evidence` temporary exceptions. Broad cleanup belongs in a separately approved
follow-up issue.

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
