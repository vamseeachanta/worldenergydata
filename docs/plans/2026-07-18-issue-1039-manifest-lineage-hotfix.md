# Plan for [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039): Repair Big Foot manifest lineage after squash merge

> **Status:** plan-review
> **Complexity:** T3
> **Date:** 2026-07-18
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1039
> **Parent:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Design:** `docs/superpowers/specs/2026-07-18-big-foot-manifest-lineage-hotfix-design.html`
> **Lane:** lane:codex
> **Plan review:** `scripts/review/results/2026-07-18-plan-1039-hotfix-synthesis.md`

## Goal

The hotfix will restore deterministic Big Foot evidence-pack regeneration from a clean depth-one `main` checkout after squash merge, without weakening producer ancestry or executable-blob validation.

## Architecture

The existing test-only history hydrator and production validator will remain unchanged. Existing coverage will retain two-parent PR merge behavior, while a focused local-Git regression will cover a one-parent squash commit after feature-branch deletion plus hostile producer identities. Manifest v1 will then be republished with durable producer commit `66ce9d6808492a01f6a7cac60415304bcc6e6ef5`, whose executable blobs match the published pack and which will remain on the `main` ancestry.

## Tech stack

Python 3.10–3.12, pytest, Git CLI subprocesses with argument lists, canonical JSON, SHA-256, and the existing deterministic Big Foot evidence-pack builder.

## Resource Intelligence and captured reproduction

| Evidence | Captured result |
|---|---|
| `main` push CI | Run `29615395015`, commit `66ce9d6808492a01f6a7cac60415304bcc6e6ef5`, 2026-07-17 21:52–21:53 UTC |
| Python 3.10 / 3.11 / 3.12 | `test_checked_in_outputs_regenerate_from_manifest_producer` fails with `ValueError: producer commit remains unavailable` in all three jobs |
| Previous `main` CI | Run `29453422566` contains the other capability-index, logging, repository-structure, workflow-API, and Python 3.10 failures but no Big Foot producer-lineage failure |
| `git merge-base --is-ancestor 80b6560... 66ce9d6...` | Exit 1: the published feature producer is not on durable `main` ancestry |
| `git show 66ce9d6:scripts/cost/build_big_foot_cost_map.py` | SHA-256 `1c97155bca9a57aadc0e1dd51feb8ba4986340df286fc69cd3aff014e92dc2fa`, equal to manifest `producer.builder_sha256` |

Implementation will preserve the CI URLs and exact failing node in the issue closeout evidence.

## Hard stop: hotfix-plan approval

Implementation will not begin from the original 2026-07-16 approval marker. After T3 plan review, the user will explicitly approve this exact hotfix plan. Only then will the operator apply `status:plan-approved` on the user's explicit behalf and add `.planning/plan-approved/1039-hotfix.md` containing the approval quote, date, issue URL, and this plan path. No agent will self-authorize this gate.

## Global constraints

- TDD will use the existing post-merge checked-output failure as RED evidence before manifest mutation.
- Production code and validation semantics will not change.
- The only implementation paths will be new `tests/unit/cost/test_big_foot_cost_lineage.py` and `data/modules/cost/curated/cost_map_contract_manifest.v1.json`.
- `reports/cost/big_foot_cost_map.html` and `reports/cost/big_foot_cost_map_reconciliation.csv` will remain byte-identical; any byte drift will stop implementation and return the issue to plan review.
- The FDAS workbooks will remain read-only and retain their current SHA-256 values.
- No email, external circulation, accounting-data rewrite, or unrelated full-suite repair will occur.
- Every commit will use a pathspec to prevent sweep contamination.

---

### Task 1: Reproduce the durable-lineage failure and add focused real-Git attacks

**Files:**
- Create: `tests/unit/cost/test_big_foot_cost_lineage.py`
- Verify: `tests/unit/cost/test_big_foot_cost_outputs.py:381`

**Interfaces:**
- Consumes: the existing test-only Git/build helpers from `test_big_foot_cost_output_hardening.py` without modifying that 400-line file.
- Produces: a local squash repository fixture plus durable-producer, missing-origin, orphaned-feature, fabricated-commit, and existing-non-ancestor tests.

- [ ] **Step 1: Create an isolated hotfix worktree from current `origin/main`**

```bash
BASE_SHA=66ce9d6808492a01f6a7cac60415304bcc6e6ef5
git fetch origin main --prune
test "$(git rev-parse origin/main)" = "$BASE_SHA" || {
  echo "origin/main advanced; return #1039 to plan review" >&2
  exit 2
}
git worktree add ../wed-1039-lineage-hotfix -b bugfix/1039-manifest-lineage "$BASE_SHA"
cd ../wed-1039-lineage-hotfix
test "$(git rev-parse HEAD)" = "$BASE_SHA"
uv sync --all-extras
uv run black --version
git status --short --branch
```

Expected: a clean `bugfix/1039-manifest-lineage` worktree at the reviewed merge commit, a complete `uv` environment, and Black 25.9.0. Any advanced `main` will stop execution for renewed inspection.

- [ ] **Step 2: Run the existing checked-output test to capture RED**

```bash
uv run pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_outputs.py::test_checked_in_outputs_regenerate_from_manifest_producer
```

Expected: FAIL with `ValueError: producer commit remains unavailable` or `ValueError: trusted producer history unavailable`; the manifest producer will be `80b6560a947af49057dd4bbc7364b88ad8867db3`, which will not be an ancestor of `origin/main`.

- [ ] **Step 3: Create the focused squash-lineage fixture and real-Git tests**

Create `tests/unit/cost/test_big_foot_cost_lineage.py` with:

```python
import shutil
from pathlib import Path

import pytest

from tests.unit.cost import test_big_foot_cost_output_hardening as hardening


@pytest.fixture()
def squashed_repo(tmp_path: Path) -> tuple[Path, Path, Path, str, str, str]:
    origin = tmp_path / "origin"
    for relative in hardening._builder().INPUT_PATHS:
        target = origin / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(hardening.ROOT / relative, target)
    hardening._git(origin, "init", "-q")
    hardening._git(origin, "config", "user.email", "test@example.com")
    hardening._git(origin, "config", "user.name", "Test")
    hardening._git(origin, "add", ".")
    hardening._git(origin, "commit", "-qm", "durable producer")
    producer = hardening._git(origin, "rev-parse", "HEAD")
    main = hardening._git(origin, "branch", "--show-current")

    hardening._git(origin, "checkout", "-qb", "unrelated")
    (origin / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
    hardening._git(origin, "add", "unrelated.txt")
    hardening._git(origin, "commit", "-qm", "unrelated")
    nonancestor = hardening._git(origin, "rev-parse", "HEAD")
    hardening._git(origin, "checkout", "-q", main)

    hardening._git(origin, "checkout", "-qb", "feature")
    (origin / "artifact.txt").write_text("artifact\n", encoding="utf-8")
    hardening._git(origin, "add", "artifact.txt")
    hardening._git(origin, "commit", "-qm", "feature artifact")
    orphan = hardening._git(origin, "rev-parse", "HEAD")
    hardening._git(origin, "checkout", "-q", main)
    hardening._git(origin, "merge", "--squash", "feature")
    hardening._git(origin, "commit", "-qm", "synthetic squash")
    hardening._git(origin, "branch", "-D", "feature")
    baseline = tmp_path / "baseline"
    hardening._generate(origin, baseline, producer)
    root = tmp_path / "shallow"
    hardening._git(tmp_path, "clone", "-q", "--depth", "1", origin.as_uri(), str(root))
    return origin, root, baseline, producer, orphan, nonancestor


def test_durable_producer_survives_squash_and_missing_origin(
    squashed_repo, tmp_path: Path
) -> None:
    origin, root, baseline, producer, _, _ = squashed_repo
    hardening._git(root, "remote", "remove", "origin")
    with pytest.raises(ValueError, match="trusted producer history"):
        hardening.hydrate_trusted_producer_history(root, producer)
    hardening._git(root, "remote", "add", "origin", origin.as_uri())
    hardening.hydrate_trusted_producer_history(root, producer)
    hydrated = tmp_path / "hydrated"
    hardening._generate(root, hydrated, producer)
    assert all(
        (baseline / item).read_bytes() == (hydrated / item).read_bytes()
        for item in (hardening.HTML, hardening.CSV, hardening.MANIFEST)
    )


def test_orphaned_and_fabricated_producers_reject(squashed_repo) -> None:
    _, root, _, _, orphan, _ = squashed_repo
    for producer in (orphan, "f" * 40):
        with pytest.raises(ValueError):
            hardening.hydrate_trusted_producer_history(root, producer)


def test_existing_nonancestor_producer_rejects(squashed_repo) -> None:
    _, root, _, _, _, nonancestor = squashed_repo
    hardening._git(root, "fetch", "--depth", "2", "origin", "unrelated")
    assert hardening._has_commit(root, nonancestor)
    with pytest.raises(ValueError, match="trusted producer history"):
        hardening.hydrate_trusted_producer_history(root, nonancestor)
```

The existing merge-commit, dirty-executable, malformed-SHA, and Git-error-normalization tests will remain unchanged in their current files. Every new function will remain below 50 lines and the new file will remain below 400 lines.

- [ ] **Step 4: Run the integration fixture**

```bash
uv run pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_lineage.py
```

Expected: all new lineage tests PASS. They will prove durable squash lineage and real-Git rejection for missing origin, a deleted feature producer, a fabricated 40-hex commit, and an existing non-ancestor; the checked-output test from Step 2 will remain RED until Task 2.

- [ ] **Step 5: Verify structural limits and commit the test-first change**

```bash
wc -l tests/unit/cost/test_big_foot_cost_lineage.py
uv run black --check tests/unit/cost/test_big_foot_cost_lineage.py
uv run isort --check-only --diff tests/unit/cost/test_big_foot_cost_lineage.py
uv run ruff check tests/unit/cost/test_big_foot_cost_lineage.py
bash scripts/legal/legal-sanity-scan.sh --diff-only
git diff --check
git commit -m "test(cost): cover squash-stable producer lineage" -- \
  tests/unit/cost/test_big_foot_cost_lineage.py
```

Expected: the new file will be at most 400 lines, every function will be at most 50 lines, the legal scan will report `PASS`, and only the focused lineage test will enter the commit.

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
  uv run python scripts/cost/build_big_foot_cost_map.py
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
uv run pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_outputs.py::test_checked_in_outputs_regenerate_from_manifest_producer
```

Expected: PASS.

- [ ] **Step 5: Run the complete focused cost evidence-pack suite**

```bash
uv run pytest -q -o addopts='' \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py \
  tests/unit/cost/test_big_foot_cost_lineage.py
uv run black --check \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py \
  tests/unit/cost/test_big_foot_cost_lineage.py
uv run isort --check-only --diff \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py \
  tests/unit/cost/test_big_foot_cost_lineage.py
uv run ruff check \
  tests/unit/cost/test_big_foot_cost_outputs.py \
  tests/unit/cost/test_big_foot_cost_output_hardening.py \
  tests/unit/cost/test_big_foot_cost_lineage.py
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
- Report: GitHub issue [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039) comment and hotfix PR body

**Interfaces:**
- Consumes: Task 1 regression evidence, Task 2 fingerprint evidence, and both implementation commits.
- Produces: T3 code/artifact review verdicts, a hotfix PR using `Refs #1039`, and a verified post-merge issue closure.

- [ ] **Step 1: Run T3 adversarial code/artifact review**

Claude, Codex, and Gemini code-review artifacts will be recorded at `scripts/review/results/2026-07-18-issue-1039-hotfix-code-{claude,codex,gemini}.md`, with `UNAVAILABLE` and the provider error recorded if quota or CLI failure degrades T3 to T2. Every prompt will default to non-approval and will attempt to prove that the hotfix weakens ancestry, accepts an orphaned producer, changes executable inputs, mutates HTML/CSV/workbooks, exceeds structural limits, or fails in a genuine depth-one squash checkout. Critical and Important findings will be remediated and re-reviewed before push.

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

Expected: an open PR whose changed paths are limited to the focused lineage test and manifest.

- [ ] **Step 3: Verify PR CI and the full-matrix cost node**

The PR domain cost lane will pass. After owner-authorized squash merge, the following commands will capture the exact push run and fail closed if any Python 3.10–3.12 failed log retains the cost regression:

```bash
MERGE_SHA=$(gh pr view "$PR" --repo vamseeachanta/worldenergydata --json mergeCommit --jq .mergeCommit.oid)
RUN_ID=$(gh run list --repo vamseeachanta/worldenergydata --commit "$MERGE_SHA" \
  --workflow CI --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --repo vamseeachanta/worldenergydata || true
gh run view "$RUN_ID" --repo vamseeachanta/worldenergydata --log-failed \
  > /tmp/issue-1039-main-failed.log
! rg 'test_checked_in_outputs_regenerate_from_manifest_producer|producer commit remains unavailable' \
  /tmp/issue-1039-main-failed.log
```

The `main` full matrix may remain red only for the documented pre-existing debt; the saved failed log will be attached or linked in the issue closeout.

- [ ] **Step 4: Comment and close [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039) only after merge verification**

The issue comment will include the hotfix PR, merge SHA, focused test counts, three workbook hashes, review verdicts, CI evidence, unchanged email/circulation state, and the separate pre-existing full-suite failures. Issue [#1039](https://github.com/vamseeachanta/worldenergydata/issues/1039) will close only after the durable producer is verified on `origin/main`.

- [ ] **Step 5: Run the cleanup audit**

The audit will classify worktrees, branches, stashes, ignored review ledgers, `/tmp/issue-1039-lineage-before.sha256`, and test scratch repositories as CLEAN, EXPECTED, or UNEXPECTED. UNEXPECTED residue will be removed or resolved before closeout; host-owned worktrees will not be deleted.

## Acceptance criteria

- [ ] Manifest v1 will name `66ce9d6808492a01f6a7cac60415304bcc6e6ef5` as producer.
- [ ] The producer will be a real ancestor of durable `main` and will contain every exact executable blob.
- [ ] Existing merge-commit coverage and the new squash-commit depth-one fixture will regenerate byte-identically after source-branch deletion.
- [ ] Real Git will reject missing-origin, orphaned-feature, fabricated-40-hex, and existing-non-ancestor producer cases.
- [ ] The existing checked-output test will move from the recorded RED failure to GREEN without a production-code change.
- [ ] HTML, CSV, production helpers, accounting data, and all three workbooks will remain byte-identical.
- [ ] T3 adversarial review and the PR cost lane will pass.
- [ ] Post-merge Python 3.10–3.12 logs will contain no Big Foot producer-lineage failure.
- [ ] Issue [#1048](https://github.com/vamseeachanta/worldenergydata/issues/1048) will retain the generalized manifest producer redesign.
- [ ] No email or external circulation will occur.

## Out of scope

The hotfix will not repair capability-index drift, logging capture, repository-structure classifications, workflow-API imports, Python 3.10 `datetime.UTC` compatibility, portfolio cost mapping, estimator training, workbook formulas, or generalized manifest identity semantics.
