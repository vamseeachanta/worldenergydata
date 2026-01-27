# Regression Prevention Guide

> Prevent breaking changes during refactoring through systematic validation.

## Core Principle

**STOP on ANY error.** Never proceed with refactoring if tests fail or static analysis reports issues.

---

## Pre-Refactoring Checklist

### 1. Establish Baseline

```bash
# Verify all tests pass BEFORE any changes
uv run pytest --tb=short

# Record current test count and coverage
uv run pytest --cov=src --cov-report=term-missing

# Run static analysis baseline
uv run ruff check src/
uv run mypy src/
```

### 2. Document Golden Outputs

For critical functions, capture expected outputs:

```python
# Create snapshot tests for complex transformations
def test_golden_output_snapshot():
    result = complex_calculation(test_input)
    assert result == GOLDEN_OUTPUT  # Captured before refactor
```

### 3. Identify Test Coverage Gaps

```bash
# Generate coverage report
uv run pytest --cov=src --cov-report=html

# Review uncovered lines - these are risk areas
# Add tests for uncovered critical paths BEFORE refactoring
```

---

## Validation After Every Change

### The Validation Loop

```
┌─────────────────────────────────────────┐
│  1. Make ONE atomic change              │
│  2. Run static analysis (ruff, mypy)    │
│  3. Run tests                           │
│  4. If ANY failure → REVERT immediately │
│  5. Commit if green                     │
│  6. Repeat                              │
└─────────────────────────────────────────┘
```

### Validation Commands

```bash
# Quick validation (after each small change)
uv run ruff check src/ && uv run pytest -x --tb=short

# Full validation (before commits)
uv run ruff check src/ && uv run mypy src/ && uv run pytest --tb=short
```

---

## Static Analysis Before Tests

**Order matters.** Run static analysis FIRST:

1. **Syntax errors** - Caught by ruff/mypy before runtime
2. **Type errors** - Caught by mypy before tests run
3. **Style issues** - Caught by ruff before tests run
4. **Logic errors** - Caught by tests

```bash
# Correct order
uv run ruff check src/           # Step 1: Lint
uv run mypy src/                 # Step 2: Type check
uv run pytest                    # Step 3: Test
```

---

## Migration Checklist Requirements

Before starting ANY refactoring:

- [ ] All existing tests pass
- [ ] Test coverage is documented (target: 80%+)
- [ ] Static analysis passes (zero errors)
- [ ] Golden outputs captured for critical functions
- [ ] Backup/commit of current working state
- [ ] Refactoring scope clearly defined
- [ ] Rollback plan documented

---

## Atomic Commits for Rollback

### Commit Strategy

Each commit should be:
- **Single-purpose**: One refactoring action per commit
- **Complete**: Tests pass after the commit
- **Reversible**: Can be reverted without breaking other changes

### Commit Message Format

```
refactor(<scope>): <action>

- What was changed
- Why it was changed
- Any caveats

Tests: all passing
Coverage: maintained at X%
```

### Example Commit Sequence

```bash
# Good: Atomic commits
git commit -m "refactor(auth): extract validate_token to separate function"
git commit -m "refactor(auth): add type hints to auth module"
git commit -m "refactor(auth): replace if/elif with dictionary dispatch"

# Bad: Monolithic commit
git commit -m "refactor: rewrite entire auth module"
```

---

## Stop on Any Error Rule

### What Constitutes an Error

| Category | Stop Condition |
|----------|----------------|
| Tests | Any test failure |
| Ruff | Any error (not warning) |
| Mypy | Any type error |
| Runtime | Any exception during manual testing |
| Import | Any circular import detected |

### Error Response Protocol

```
Error Detected
     │
     ▼
┌────────────────┐
│ STOP IMMEDIATELY │
└────────────────┘
     │
     ▼
┌────────────────┐
│ Identify cause │
└────────────────┘
     │
     ├── Simple fix? ──▶ Fix and re-validate
     │
     └── Complex? ──▶ REVERT to last green commit
                      │
                      ▼
                 Re-plan approach
```

### Revert Commands

```bash
# Revert uncommitted changes
git checkout -- .

# Revert last commit (keep changes staged)
git reset --soft HEAD~1

# Revert last commit (discard changes)
git reset --hard HEAD~1

# Revert specific commit
git revert <commit-hash>
```

---

## Continuous Validation Script

Create a validation script for consistent checks:

```bash
#!/bin/bash
# validate.sh - Run before each commit

set -e  # Exit on any error

echo "=== Running Ruff ==="
uv run ruff check src/

echo "=== Running Mypy ==="
uv run mypy src/

echo "=== Running Tests ==="
uv run pytest --tb=short

echo "=== All checks passed ==="
```

---

## Risk Mitigation by Refactoring Type

| Refactoring Type | Risk Level | Extra Precautions |
|------------------|------------|-------------------|
| Rename | Low | Search for all usages |
| Extract Method | Low | Verify call sites |
| Inline Method | Medium | Check all callers |
| Change Signature | Medium | Update all call sites |
| Move to Class | High | Integration tests |
| Restructure Module | High | Full test suite + manual testing |

---

## Summary

1. **Baseline first**: All tests green, coverage documented
2. **Atomic changes**: One refactoring action at a time
3. **Validate always**: Static analysis, then tests
4. **Stop on error**: Never proceed with failing tests
5. **Commit often**: Each green state gets committed
6. **Revert fast**: Don't debug failed refactoring, revert and retry
