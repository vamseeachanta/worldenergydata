# Plan for #1039: Repair Big Foot manifest lineage after squash merge

> **Status:** plan-review
> **Complexity:** T3
> **Date:** 2026-07-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1039
> **Parent:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Design:** `docs/superpowers/specs/2026-07-18-big-foot-manifest-lineage-hotfix-design.html`
> **Lane:** lane:codex

## Goal

The hotfix will restore deterministic Big Foot evidence-pack regeneration from a clean depth-one `main` checkout after squash merge, without weakening producer ancestry or executable-blob validation.

## Architecture

The existing test-only history hydrator and production validator will remain unchanged. A parametrized local-Git regression will cover both two-parent PR merge commits and one-parent squash commits after feature-branch deletion. Manifest v1 will then be republished with durable producer commit `66ce9d6808492a01f6a7cac60415304bcc6e6ef5`, whose executable blobs match the published pack and which will remain on the `main` ancestry.

## Tech stack

Python 3.10–3.12, pytest, Git CLI subprocesses with argument lists, canonical JSON, SHA-256, and the existing deterministic Big Foot evidence-pack builder.

## Global constraints

- TDD will use the existing post-merge checked-output failure as RED evidence before manifest mutation.
- Production code and validation semantics will not change.
- The only implementation paths will be `tests/unit/cost/test_big_foot_cost_output_hardening.py` and `data/modules/cost/curated/cost_map_contract_manifest.v1.json`.
- `reports/cost/big_foot_cost_map.html` and `reports/cost/big_foot_cost_map_reconciliation.csv` will remain byte-identical; any byte drift will stop implementation and return the issue to plan review.
- The FDAS workbooks will remain read-only and retain their current SHA-256 values.
- No email, external circulation, accounting-data rewrite, or unrelated full-suite repair will occur.
- Every commit will use a pathspec to prevent sweep contamination.

---

### Task 1: Reproduce the durable-lineage failure and extend the Git fixture

**Files:**
- Modify: `tests/unit/cost/test_big_foot_cost_output_hardening.py:167`
- Verify: `tests/unit/cost/test_big_foot_cost_outputs.py:381`

**Interfaces:**
- Consumes: `hydrate_trusted_producer_history(root: Path, producer: str) -> None` and `trusted_artifact_commit(root: Path) -> str` from the hardening test harness.
- Produces: `test_trusted_hydration_from_shallow_integration`, parametrized for `merge_commit` and `squash`, with the feature branch deleted before depth-one cloning.

- [ ] **Step 1: Create an isolated hotfix worktree from current `origin/main`**

```bash
git fetch origin main --prune
git worktree add ../wed-1039-lineage-hotfix -b bugfix/1039-manifest-lineage origin/main
cd ../wed-1039-lineage-hotfix
git status --short --branch
```

Expected: a clean `bugfix/1039-manifest-lineage` worktree at merge commit `66ce9d6808492a01f6a7cac60415304bcc6e6ef5`.

- [ ] **Step 2: Run the existing checked-output test to capture RED**

```bash
.venv/bin/pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_outputs.py::test_checked_in_outputs_regenerate_from_manifest_producer
```

Expected: FAIL with `ValueError: producer commit remains unavailable` or `ValueError: trusted producer history unavailable`; the manifest producer will be `80b6560a947af49057dd4bbc7364b88ad8867db3`, which will not be an ancestor of `origin/main`.

- [ ] **Step 3: Replace the merge-only fixture with a branch-deleting merge/squash fixture**

Replace `test_trusted_hydration_from_shallow_pr_merge` with:

```python
@pytest.mark.parametrize("strategy", ("merge_commit", "squash"))
def test_trusted_hydration_from_shallow_integration(
    source_repo, tmp_path: Path, strategy: str
) -> None:
    origin, producer = source_repo
    main = _git(origin, "branch", "--show-current")
    _git(origin, "checkout", "-qb", "feature")
    (origin / "artifact.txt").write_text("artifact\n", encoding="utf-8")
    _git(origin, "add", "artifact.txt")
    _git(origin, "commit", "-qm", "artifact")
    artifact = _git(origin, "rev-parse", "HEAD")
    _git(origin, "checkout", "-q", main)
    trusted = artifact
    if strategy == "merge_commit":
        _git(origin, "merge", "--no-ff", "-qm", "synthetic PR", "feature")
    else:
        _git(origin, "merge", "--squash", "feature")
        _git(origin, "commit", "-qm", "synthetic squash")
        trusted = _git(origin, "rev-parse", "HEAD")
    _git(origin, "branch", "-D", "feature")
    baseline = tmp_path / f"baseline-{strategy}"
    _generate(origin, baseline, producer)

    root = tmp_path / f"shallow-{strategy}"
    _git(tmp_path, "clone", "-q", "--depth", "1", origin.as_uri(), str(root))
    assert not _has_commit(root, producer)
    _git(root, "remote", "remove", "origin")
    with pytest.raises(ValueError, match="trusted producer history"):
        hydrate_trusted_producer_history(root, producer)
    _git(root, "remote", "add", "origin", origin.as_uri())
    assert trusted_artifact_commit(root) == trusted
    hydrate_trusted_producer_history(root, producer)
    hydrated = tmp_path / f"hydrated-{strategy}"
    _generate(root, hydrated, producer)
    assert all(
        (baseline / item).read_bytes() == (hydrated / item).read_bytes()
        for item in (HTML, CSV, MANIFEST)
    )
```

The parametrized fixture will retain missing-origin rejection. Fabricated-producer rejection will remain in `test_big_foot_cost_outputs.py::test_production_has_no_attestation_bypass_and_normalizes_git_errors`, and dirty/non-ancestor rejection will remain in the neighboring producer-validation tests. The old duplicate fabricated-producer assertions will be removed with the replaced function, so the hardening file will remain at most 400 lines and the parametrized function will remain below 50 lines.

- [ ] **Step 4: Run the integration fixture**

```bash
.venv/bin/pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_output_hardening.py::test_trusted_hydration_from_shallow_integration
```

Expected: two parametrized cases PASS. This fixture will prove that strict ancestry works for a durable pre-squash producer and rejects dependence on the deleted feature lineage; the checked-output test from Step 2 will remain RED until Task 2.

- [ ] **Step 5: Verify structural limits and commit the test-first change**

```bash
wc -l tests/unit/cost/test_big_foot_cost_output_hardening.py
black --check tests/unit/cost/test_big_foot_cost_output_hardening.py
isort --check-only --diff tests/unit/cost/test_big_foot_cost_output_hardening.py
git diff --check
git commit -m "test(cost): cover squash-stable producer lineage" -- \
  tests/unit/cost/test_big_foot_cost_output_hardening.py
```

Expected: the file will be at most 400 lines, every function will be at most 50 lines, formatting checks will pass, and only the hardening test will enter the commit.

---

### Task 2: Republish manifest v1 with the durable main producer

**Files:**
- Modify: `data/modules/cost/curated/cost_map_contract_manifest.v1.json`
- Verify unchanged: `reports/cost/big_foot_cost_map.html`
- Verify unchanged: `reports/cost/big_foot_cost_map_reconciliation.csv`
- Verify unchanged: `scripts/cost/build_big_foot_cost_map.py`
- Verify unchanged: `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack.py`

**Interfaces:**
- Consumes: `build_outputs(repo_root, output_root, source_date_epoch, producer_commit)` through the existing CLI environment contract.
- Produces: manifest producer commit `66ce9d6808492a01f6a7cac60415304bcc6e6ef5` with unchanged builder SHA-256 `1c97155bca9a57aadc0e1dd51feb8ba4986340df286fc69cd3aff014e92dc2fa`.

- [ ] **Step 1: Record immutable pre-build fingerprints**

```bash
sha256sum \
  reports/cost/big_foot_cost_map.html \
  reports/cost/big_foot_cost_map_reconciliation.csv \
  docs/modules/bsee/analysis/production/FDAS_V30/lease_assumptions.xlsx \
  docs/modules/bsee/analysis/production/FDAS_V30/financial_project_summary.xlsx \
  docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx \
  > /tmp/issue-1039-lineage-before.sha256
```

Expected workbook hashes:

```text
a1193f669db49ac33b87481733fb13af409844fed890e763b4e8726e329a1407  lease_assumptions.xlsx
00f200def283d307293bb93033f070718722618b9a8ace2bbbe11bfbffeddf04  financial_project_summary.xlsx
3ecfa1128b33edf73db3a793f8839c98c50bc27184487a8af579c5ef22795e7f  drilling_and_completion_days.xlsx
```

- [ ] **Step 2: Regenerate through the production builder**

```bash
SOURCE_DATE_EPOCH=1700000000 \
PRODUCER_COMMIT=66ce9d6808492a01f6a7cac60415304bcc6e6ef5 \
  .venv/bin/python scripts/cost/build_big_foot_cost_map.py
```

Expected: exit 0. The manifest will change only in `producer.commit`; HTML and CSV will remain byte-identical.

- [ ] **Step 3: Prove the change boundary**

```bash
git diff --exit-code -- \
  reports/cost/big_foot_cost_map.html \
  reports/cost/big_foot_cost_map_reconciliation.csv \
  scripts/cost/build_big_foot_cost_map.py \
  packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/evidence_pack.py
git diff -- data/modules/cost/curated/cost_map_contract_manifest.v1.json
sha256sum -c /tmp/issue-1039-lineage-before.sha256
```

Expected: the first command will emit no diff; the manifest diff will replace only the 40-hex producer commit; every recorded HTML, CSV, and workbook fingerprint will report `OK`.

- [ ] **Step 4: Run the RED command unchanged to prove GREEN**

```bash
.venv/bin/pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_outputs.py::test_checked_in_outputs_regenerate_from_manifest_producer
```

Expected: PASS.

- [ ] **Step 5: Run the complete focused cost evidence-pack suite**

```bash
.venv/bin/pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py
black --check \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py
isort --check-only --diff \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py
ruff check \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py
bash scripts/legal/legal-sanity-scan.sh --diff-only
```

Expected: all focused tests and static checks will pass. The legal scan will report `PASS` for changed/untracked eligible files.

- [ ] **Step 6: Commit the minimal manifest repair**

```bash
git diff --check
git commit -m "fix(cost): pin evidence pack to durable main producer" -- \
  data/modules/cost/curated/cost_map_contract_manifest.v1.json
```

Expected: only manifest v1 will enter the commit.

---

### Task 3: Adversarial review, PR verification, and issue closeout

**Files:**
- Review: the two implementation commits and their exact diff from `66ce9d6808492a01f6a7cac60415304bcc6e6ef5`
- Report: GitHub issue #1039 comment and hotfix PR body

**Interfaces:**
- Consumes: Task 1 regression evidence, Task 2 fingerprint evidence, and both implementation commits.
- Produces: T3 code/artifact review verdicts, a hotfix PR using `Refs #1039`, and a verified post-merge issue closure.

- [ ] **Step 1: Run T3 adversarial code/artifact review**

Every reviewer prompt will default to non-approval and will attempt to prove that the hotfix weakens ancestry, accepts an orphaned producer, changes executable inputs, mutates HTML/CSV/workbooks, exceeds structural limits, or fails in a genuine depth-one squash checkout. Critical and Important findings will be remediated and re-reviewed before push.

- [ ] **Step 2: Push and open the hotfix PR**

```bash
git push -u origin bugfix/1039-manifest-lineage
gh pr create \
  --repo vamseeachanta/worldenergydata \
  --base main \
  --head bugfix/1039-manifest-lineage \
  --title "fix(cost): preserve evidence-pack lineage after squash merge" \
  --body "Refs #1039. Repairs the checked manifest producer after squash merge; production validation, reports, workbooks, email, and circulation remain unchanged."
```

Expected: an open PR whose changed paths are limited to the hardening test and manifest.

- [ ] **Step 3: Verify PR CI and the full-matrix cost node**

The PR domain cost lane will pass. After owner-authorized squash merge, the `main` full matrix may remain red for documented pre-existing debt, but none of its Python 3.10–3.12 logs will contain `test_checked_in_outputs_regenerate_from_manifest_producer` or `producer commit remains unavailable`.

- [ ] **Step 4: Comment and close #1039 only after merge verification**

The issue comment will include the hotfix PR, merge SHA, focused test counts, three workbook hashes, review verdicts, CI evidence, unchanged email/circulation state, and the separate pre-existing full-suite failures. Issue #1039 will close only after the durable producer is verified on `origin/main`.

- [ ] **Step 5: Run the cleanup audit**

The audit will classify worktrees, branches, stashes, ignored review ledgers, `/tmp/issue-1039-lineage-before.sha256`, and test scratch repositories as CLEAN, EXPECTED, or UNEXPECTED. UNEXPECTED residue will be removed or resolved before closeout; host-owned worktrees will not be deleted.

## Acceptance criteria

- [ ] Manifest v1 will name `66ce9d6808492a01f6a7cac60415304bcc6e6ef5` as producer.
- [ ] The producer will be a real ancestor of durable `main` and will contain every exact executable blob.
- [ ] Merge-commit and squash-commit depth-one fixtures will regenerate byte-identically after source-branch deletion.
- [ ] The existing checked-output test will move from the recorded RED failure to GREEN without a production-code change.
- [ ] HTML, CSV, production helpers, accounting data, and all three workbooks will remain byte-identical.
- [ ] T3 adversarial review and the PR cost lane will pass.
- [ ] Post-merge Python 3.10–3.12 logs will contain no Big Foot producer-lineage failure.
- [ ] Issue #1048 will retain the generalized manifest producer redesign.
- [ ] No email or external circulation will occur.

## Out of scope

The hotfix will not repair capability-index drift, logging capture, repository-structure classifications, workflow-API imports, Python 3.10 `datetime.UTC` compatibility, portfolio cost mapping, estimator training, workbook formulas, or generalized manifest identity semantics.
