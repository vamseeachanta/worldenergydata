# Plan for [#274](https://github.com/vamseeachanta/worldenergydata/issues/274): fix(ci): remove || true from bandit security scan step

> **Status:** plan-review
> **Complexity:** T2
> **Date:** 2026-05-04
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/274
> **Review artifacts:** scripts/review/results/2026-05-04-plan-274-claude.md | ...-codex.md | ...-gemini.md

---

## Resource Intelligence Summary

### Existing repo code

- Found: `.github/workflows/ci.yml` line 158 — `uv run bandit -r src/ -ll -ii -x tests/ || true` — security scan currently silently passes regardless of findings
- Found: `src/worldenergydata/west_africa/nigeria/nuprc_client.py:83` — `hashlib.md5(url.encode()).hexdigest()` — High-severity B324 (MD5 used as cache key, not for security; fixable via `usedforsecurity=False`)
- Found: `pyproject.toml` lines 234–237 — `[tool.bandit]` section exists with `exclude_dirs = ["tests", "docs"]` and `skips = []` — no global skips configured
- Found: 9 existing `# nosec B301` annotations on `pickle.load()` calls across `src/worldenergydata/bsee/` — pattern established for intentional suppressions
- Gap: No bandit baseline file (`.bandit` or `bandit.yaml`) exists — all triage will use inline `# nosec` annotations

### Standards

| Standard | Status | Source |
|---|---|---|
| CWE-327 (Use of Broken Algorithm) | not applicable — bandit B324 is a linter rule, not a standard citation | n/a |
| PEP 456 / Python 3.9+ `usedforsecurity=False` | applicable — stdlib `hashlib` API allows marking non-security hash use | Python docs |

### LLM Wiki pages consulted

- No relevant wiki pages for CI enforcement patterns in worldenergydata wiki.

### Documents consulted

- `docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md` — prior CI fix plan; no bandit overlap
- GitHub issue [#274](https://github.com/vamseeachanta/worldenergydata/issues/274) — problem statement: `|| true` silences security scan; action: triage first, then remove suppression
- Commit `18d7f643` — `chore(deps): replace assetutilities git dep with PyPI release` — removed `|| true` from mypy step; bandit step was missed in the same pass

### Gaps identified

- No bandit run has produced a categorized findings list yet — must run locally to confirm the 97 Low / 58 Medium / 18 High counts and identify which High findings require code fixes vs. `# nosec` annotations
- High-severity files beyond nuprc_client.py are unknown until the triage run completes

### Evidence (embedded verification)

**Issue statuses** (verified 2026-05-04 via `gh issue view 274`):
- `#274` — OPEN — fix(ci): remove || true from bandit security scan step

**File existence** (`ls` 2026-05-04):
- EXISTS: `.github/workflows/ci.yml`
- EXISTS: `src/worldenergydata/west_africa/nigeria/nuprc_client.py`
- EXISTS: `pyproject.toml` (contains `[tool.bandit]` at line 234)
- MISSING (new — this plan creates): none

**Line excerpts** (`ci.yml` lines 155–158):
```yaml
      - name: Run bandit security scan
        run: |
          uv pip install bandit
          uv run bandit -r src/ -ll -ii -x tests/ || true
```

**nuprc_client.py line 83:**
```python
    def _cache_key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
```

**Existing nosec pattern** (`grep -rn "nosec" src/`):
```
src/worldenergydata/bsee/data/field_names.py:69:                obj = pickle.load(f)  # nosec B301
src/worldenergydata/bsee/data/loaders/company/company_loader.py:57:            obj = pickle.load(f)  # nosec B301
... (9 total B301 suppressions across bsee/)
```

**Gap proof** (bandit config has no skips):
```toml
[tool.bandit]
exclude_dirs = ["tests", "docs"]
skips = []
```

**Bandit finding counts** (from issue context, pre-verified externally):
- 97 Low, 58 Medium, 18 High — total 173 findings at `-ll -ii` severity thresholds

**Phase 2B precedent** (commit 18d7f643 message excerpt):
```
- Remove `|| true` from mypy step so type errors now fail CI properly
```

<!-- Verification: distinct sources = 5 (issue body, ci.yml, nuprc_client.py, pyproject.toml, commit 18d7f643) -->

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `worldenergydata/docs/plans/2026-05-04-issue-274-bandit-remove-or-true.md` |
| CI workflow | `.github/workflows/ci.yml` |
| High-severity fix | `src/worldenergydata/west_africa/nigeria/nuprc_client.py` |
| Other triage targets | TBD after local bandit run (High findings only require fixes or nosec) |
| Plan review — Claude | `scripts/review/results/2026-05-04-plan-274-claude.md` |
| Plan review — Codex | `scripts/review/results/2026-05-04-plan-274-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-05-04-plan-274-gemini.md` |

---

## Deliverable

The bandit CI step enforces without `|| true`; any real High-severity security issues are fixed in source and CI fails on genuine findings rather than silently passing.

---

## Pseudocode

```
STEP 1 — triage:
  run: uv run bandit -r src/ -ll -ii -x tests/ -f json -o /tmp/bandit-report.json
  for each finding in report:
    if severity == HIGH:
      if finding is a real security risk (not a non-security use-case):
        fix the code (e.g., usedforsecurity=False for MD5 cache keys)
      else if finding is an intentional false-positive (trusted input, internal-only, etc.):
        add: # nosec B<NNN> -- <one-line justification> on the offending line
    if severity == MEDIUM or LOW:
      review in bulk; add # nosec only when clearly intentional (e.g., pickle on trusted internal files)
      leave unfixed findings as failing (force developer to address them)

STEP 2 — remove suppression:
  edit .github/workflows/ci.yml line 158:
    before: uv run bandit -r src/ -ll -ii -x tests/ || true
    after:  uv run bandit -r src/ -ll -ii -x tests/

STEP 3 — verify:
  run bandit locally with the same flags — confirm exit code 0
  confirm CI passes on a test push / act run
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify | `.github/workflows/ci.yml` | Remove `|| true` from bandit step (line 158) |
| Modify | `src/worldenergydata/west_africa/nigeria/nuprc_client.py` | Add `usedforsecurity=False` to `hashlib.md5()` call at line 83 (fixes B324 High) |
| Modify (conditional) | Any other High-severity src files identified in triage | Either code fix or `# nosec B<NNN>` with justification |
| Update | `docs/plans/README.md` | Add this plan to index (if README maintained) |

---

## TDD Test List

This is a CI-enforcement issue. No new runtime logic is introduced; verification is via CI green/red behaviour.

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| bandit_scan_passes_clean | bandit exits 0 after all fixes/nosec applied | `uv run bandit -r src/ -ll -ii -x tests/` | exit code 0 |
| ci_bandit_step_has_no_or_true | ci.yml bandit step does not contain `\|\| true` | grep of ci.yml line | zero matches |
| md5_cache_key_uses_usedforsecurity | nuprc_client.py cache key uses `usedforsecurity=False` | grep of nuprc_client.py | `usedforsecurity=False` present |
| nosec_annotations_have_justification | all `# nosec` lines include a B-code and comment | grep pattern `# nosec B[0-9]+ --` | all nosec lines match pattern |

---

## Acceptance Criteria

- [ ] `uv run bandit -r src/ -ll -ii -x tests/` exits 0 locally
- [ ] `.github/workflows/ci.yml` bandit step contains no `|| true`
- [ ] `src/worldenergydata/west_africa/nigeria/nuprc_client.py:83` uses `hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()`
- [ ] All `# nosec` annotations added by this issue include a Bandit rule ID and a one-line justification comment
- [ ] CI pipeline passes end-to-end (bandit step green, no regression in other steps)
- [ ] Review artifacts posted to `scripts/review/results/`

---

## Adversarial Review Summary

<!-- Filled in after Step 4 completes. Do not post to GitHub until this section is populated. -->

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | APPROVE / MINOR / MAJOR | summary of findings |
| Codex | APPROVE / MINOR / MAJOR | summary of findings |
| Gemini | APPROVE / MINOR / MAJOR | summary of findings |

**Overall result:** PASS / FAIL (re-draft required)

Revisions made based on review:
- (list any changes made to the plan after adversarial review)

---

## Risks and Open Questions

- **Risk:** The 18 High findings may include issues beyond nuprc_client.py that require non-trivial code changes — triage must complete before the `|| true` removal commit is made; do not remove the suppression until bandit exits 0 locally
- **Risk:** Bulk `# nosec` on all Medium/Low findings without review would defeat the purpose of removing `|| true` — only annotate findings that are genuinely intentional (e.g., pickle on BSEE-trusted internal files); leave legitimate findings as CI-failing to force developer attention
- **Open:** Should Medium-severity findings also be fixed in this issue, or deferred to a follow-up? The issue body scopes to "fix real issues or add nosec for known false-positives" — recommend addressing all High in this issue and filing a follow-up for remaining Medium findings

---

## Complexity: T2

**T2** — multiple source files require triage and targeted edits; one CI config change; no new modules, but triage step requires a local bandit run and judgment calls on 173 findings before the enforcement gate can be activated.
