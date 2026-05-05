# Plan: Issue #315 — Ruff migration (replace black + isort + flake8)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/315
**Status:** plan-review
**Tier:** T2 (tooling migration with CI update)

## Plan

### Task 1 — Add ruff to dev dependencies
```bash
uv add --dev ruff
```

### Task 2 — Configure ruff in pyproject.toml
```toml
[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "W", "I", "N"]  # pep8, pyflakes, warnings, isort, pep8-naming
ignore = ["E501"]  # line length handled separately

[tool.ruff.format]
quote-style = "double"  # Match black

[tool.ruff.isort]
known-first-party = ["worldenergydata"]
```

### Task 3 — Run ruff and fix auto-fixable issues
```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
```
Review remaining non-auto-fixable issues. Fix or add `# noqa` with reason.

### Task 4 — Update CI / pre-commit
In `.github/workflows/ci.yml` or equivalent:
- Remove `black`, `isort`, `flake8` steps
- Add: `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/`

In `.pre-commit-config.yaml` (if present):
- Replace black/isort/flake8 hooks with ruff equivalents

### Task 5 — Remove old tools from dev deps (optional)
`uv remove black isort flake8` — only if CI fully migrated and team agrees.

## Acceptance Criteria
- `uv run ruff check src/ tests/` exits 0
- `uv run ruff format --check src/ tests/` exits 0
- CI uses ruff instead of black/isort/flake8
- No regression in caught errors vs. prior flake8 runs
