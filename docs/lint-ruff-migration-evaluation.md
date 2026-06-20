# Ruff Migration Evaluation (issue #315)

**Status:** Trial config added (additive). `black` + `isort` + `flake8` are NOT yet
removed. Ruff `0.15.18` was installed and run against this repo — the statistics
below are **real**, not paper estimates.

## 1. Current linting stack

| Tool   | Config location        | Key settings |
|--------|------------------------|--------------|
| black  | `pyproject.toml [tool.black]` | `line-length = 88`, `target-version = ['py310','py311','py312']`, `include = '\.pyi?$'` |
| isort  | `pyproject.toml [tool.isort]` | `profile = "black"`, `line_length = 88` |
| flake8 | `.flake8`              | `max-line-length = 100`, `extend-ignore = E203, W503`, `exclude = .git,__pycache__,build,dist,.venv,venv`, `per-file-ignores = __init__.py:F401` |

Note the **line-length mismatch**: black/isort wrap at 88, but flake8 only flags
lines over 100. This is one source of the cross-tool disagreement #311 hit.

## 2. Settings mapping → `[tool.ruff]`

| Current setting | Ruff equivalent | Notes |
|---|---|---|
| black `line-length = 88` | `[tool.ruff] line-length = 88` | Single knob drives formatter + E501. |
| black `target-version py310/11/12` | `target-version = "py310"` | Ruff takes the lowest; matches `[tool.mypy] python_version = "3.10"`. |
| isort `profile = "black"` | `[tool.ruff.lint] select = ["I"]` + black-compatible isort defaults | Ruff's isort is black-compatible out of the box. |
| flake8 pyflakes/pycodestyle (F, E, W) | `select = ["E","F","W"]` | Full flake8 rule coverage. |
| flake8 `extend-ignore = E203, W503` | `ignore = ["E203"]` | **W503 has no ruff rule** — ruff/black never emit it, so no mapping needed. |
| flake8 `max-line-length = 100` | (see E501 decision below) | Mismatch with black's 88. |
| flake8 `exclude = ...` | `[tool.ruff] exclude = [...]` | Same six paths. |
| flake8 `per-file-ignores = __init__.py:F401` | `[tool.ruff.lint.per-file-ignores] "__init__.py" = ["F401"]` | Preserved. |

### E501 (line-too-long) decision
With `select = ["E"]` the **full** pycodestyle E category is on, including E501 at
88 cols. Because flake8 historically allowed 100, the repo has ~1840 lines in the
88–100 range. To keep the trial low-noise, **E501 is ignored in the lint** while the
**formatter still wraps new code at 88**. Re-enable E501 after the codebase is
`ruff format`-ted (the formatter resolves most of them).

### Proposed config block (as added to `pyproject.toml`)
```toml
[tool.ruff]
line-length = 88
target-version = "py310"
exclude = [".git", "__pycache__", "build", "dist", ".venv", "venv"]

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E203", "E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]

[tool.ruff.lint.isort]
known-first-party = ["worldenergydata"]

[tool.ruff.format]
quote-style = "double"
```

## 3. Trial results (real — ruff 0.15.18, 2033 .py files in src/ + tests/)

`ruff check src/ tests/ --statistics` with the proposed config (E,F,W,I, E203/E501 ignored):

| Count | Rule | Fixable | Description |
|------:|------|:--:|---|
| 1310 | F401 | yes | unused-import |
| 258  | F841 | yes | unused-variable |
| 181  | F541 | yes | f-string-missing-placeholders |
| 138  | E712 | no | true-false-comparison |
| 133  | E402 | no | module-import-not-at-top-of-file |
| 54   | W293 | no | blank-line-with-whitespace |
| 31   | E722 | no | bare-except |
| 20   | E741 | no | ambiguous-variable-name |
| 18   | I001 | yes | unsorted-imports (isort) |
| 10   | F811 | yes | redefined-while-unused |
| 7    | E731 | no | lambda-assignment |
| 4    | W291 | no | trailing-whitespace |
| 2    | F402 | no | import-shadowed-by-loop-var |
| 1 each | E713/E721/F823/W605 | mixed | misc |

**Total: 2170 errors; 1489 auto-fixable** (457 more behind `--unsafe-fixes`).
If E501 is left ON it adds ~1841 line-too-long findings (≈4011 total) — hence the
decision to defer E501.

### Speed (acceptance criterion: < 30s)
- `ruff check src/ tests/`  → **~3.8s wall**
- `ruff format --check src/ tests/` → **~1.0s wall** (309 files would reformat, 1724 already clean)

Both comfortably under the 30s target; this replaces multi-minute black+isort+flake8 runs.

## 4. Pros / cons

**Pros**
- One tool, one config table — eliminates the black/isort/flake8 disagreement that
  forced 5 retries in PR #311 (line-length 88 vs 100 was a direct cause).
- 10–100× faster (≈3.8s vs minutes); satisfies the <30s CI criterion easily.
- Full flake8 F/E/W coverage plus isort, with room to add bugbear/comprehensions/simplify.
- 1489 of 2170 findings auto-fixable (`ruff check --fix`) without `--unsafe-fixes`.

**Cons / gaps**
- W503 has no ruff equivalent — harmless (it was already disabled), just note it.
- The 88-vs-100 line-length history means E501 must be deferred or the codebase
  reformatted first, or CI floods with ~1840 findings.
- A one-time `ruff format` reformat will produce a large diff (309 files) — land it
  as a single isolated commit so review noise is contained.
- `disallow_untyped_defs`/mypy stay separate; ruff does not replace the type checker.

## 5. Migration plan (incremental, low-risk)

1. **Add trial config** (this commit) — `[tool.ruff]` alongside black/isort/flake8. ✅
2. **Trial in CI as non-blocking** — add a `ruff check`/`ruff format --check`
   informational step; keep black/isort/flake8 as the gate.
3. **Auto-fix the safe set** — `ruff check src/ tests/ --fix` (the 1489 fixable),
   reviewed in a dedicated PR.
4. **Reformat** — `ruff format src/ tests/` in one isolated commit; then re-enable E501.
5. **Flip the gate** — make `ruff check` + `ruff format --check` the blocking CI step;
   remove the Black / isort / flake8 steps from `.github/workflows/ci.yml`.
6. **Remove old tooling** — drop `black`, `isort`, `flake8` from dev deps; add
   `ruff>=0.6`; delete `.flake8` and `[tool.black]`/`[tool.isort]` tables.
7. **Update pre-commit** config (if used) and the contributor docs.

Each step is independently revertible; the trial config in step 1 changes no
behaviour for existing black/isort/flake8 users.
