# Python Code Refactor Skill

---
name: python-code-refactor
version: 1.0.0
description: Systematic Python code quality improvements
triggers: /python-code-refactor
---

## Overview

A comprehensive skill for systematic Python code refactoring with safety-first methodology. Transforms script-like code into clean, maintainable OOP architecture while preserving functionality through rigorous validation.

## 4-Phase Workflow

### Phase 1: ANALYSIS (Read-Only)

**Objective:** Comprehensive codebase assessment without modifications.

1. **Read Entire Codebase**
   - Scan all Python files in target directory
   - Build dependency graph
   - Identify entry points and module relationships

2. **Identify Anti-Patterns**
   - Script-like/procedural code patterns
   - God Objects (classes with too many responsibilities)
   - Complex nesting (>3 levels deep)
   - Long functions (>30 lines)
   - Magic numbers and strings
   - Cryptic variable/function names
   - Missing type hints
   - Missing or inadequate docstrings

3. **Assess OOP Architecture**
   - Global state usage and dependencies
   - SOLID principle compliance audit
   - Dependency injection opportunities
   - Class cohesion and coupling analysis

4. **Measure Metrics**
   - Run `measure_complexity.py` for baseline metrics
   - Execute flake8 with 16 plugins for comprehensive linting
   - Check test coverage with pytest-cov
   - Document all findings

5. **Generate Analysis Report**
   - Summary of findings by severity
   - Prioritized list of refactoring targets
   - Risk assessment for each change

### Phase 2: PLANNING

**Objective:** Create safe, sequenced refactoring plan.

1. **Categorize by Risk Level**
   | Risk | Change Type | Examples |
   |------|-------------|----------|
   | LOW | Non-breaking | Renames (with IDE support), documentation, formatting |
   | MEDIUM | Localized impact | Extract functions, add type hints, simplify conditionals |
   | HIGH | Breaking changes | Remove globals, delete code, restructure APIs |

2. **For DESTRUCTIVE Changes (MANDATORY)**
   - Grep ALL usages across codebase
   - Create migration checklist with exact file:line locations
   - Document all dependent code paths
   - Plan backward compatibility layer if needed

3. **Sequence Changes**
   - Order: Safest -> Riskiest
   - Group related changes
   - Identify natural breakpoints for commits

4. **Define Rollback Plan**
   - Git checkpoint strategy
   - Verification steps at each stage
   - Criteria for aborting refactor

### Phase 3: EXECUTION

#### For NON-DESTRUCTIVE Changes

Apply directly with validation:
- Rename variables/functions (with usage update)
- Extract constants from magic numbers
- Add documentation and type hints
- Convert to guard clauses
- Simplify boolean expressions

#### For DESTRUCTIVE Changes (STRICT PROTOCOL)

**Step 1: CREATE** - Build new structure alongside old
```python
# Create new class/function WITHOUT removing old
class NewRefactoredClass:
    """New implementation with better design."""
    pass

# Old code still exists and works
```

**Step 2: SEARCH** - Find ALL usages
```bash
# Grep for every reference
grep -rn "old_function_name" --include="*.py"
grep -rn "OldClassName" --include="*.py"
```

**Step 3: CREATE MIGRATION CHECKLIST**
```markdown
## Migration: old_function -> new_function
- [ ] src/module_a.py:45
- [ ] src/module_b.py:123
- [ ] tests/test_module_a.py:67
- [ ] tests/test_module_b.py:89
```

**Step 4: MIGRATE** - One location at a time
1. Update single usage
2. Run `flake8 --select=F821,E0602` (undefined names)
3. Run `pytest` for affected module
4. Check off from migration list
5. Commit if all pass

**Step 5: VERIFY** - Confirm 100% migration
```bash
# Re-grep MUST return ZERO matches
grep -rn "old_function_name" --include="*.py"
# Expected: No output
```

**Step 6: REMOVE** - Delete old code
Only after verification shows zero remaining usages.

### Phase 4: VALIDATION

**Objective:** Ensure refactoring improved code without breaking functionality.

1. **Static Analysis FIRST**
   ```bash
   # MUST return ZERO errors
   flake8 --select=F821,E0602 src/
   ruff check src/
   ```

2. **Run Full Test Suite**
   ```bash
   pytest --cov=src --cov-fail-under=80
   # Requirement: 100% tests pass
   ```

3. **Compare Before/After Metrics**
   - Cyclomatic complexity delta
   - Cognitive complexity delta
   - Lines of code delta
   - Function/class count changes

4. **Compare Flake8 Reports**
   - Violations reduced or eliminated
   - No new violations introduced
   - Plugin-specific improvements

5. **Performance Regression Check**
   - Run benchmarks if available
   - Maximum allowed degradation: <10%
   - Flag significant changes for review

6. **Generate Summary Report**
   ```markdown
   ## Refactoring Summary
   - Files modified: X
   - Anti-patterns fixed: Y
   - Test coverage: before% -> after%
   - Complexity: before -> after
   ```

7. **Flag for Human Review**
   - Any HIGH risk changes
   - Test coverage decreased
   - Performance degradation >5%
   - Unresolved edge cases

## Anti-Pattern Catalog

### Priority: CRITICAL

| Pattern | Description | Detection | Resolution |
|---------|-------------|-----------|------------|
| Script-like Code | Procedural code without classes, global functions | Functions at module level, no classes | Extract to classes with clear responsibilities |
| God Object | Class with too many responsibilities | >10 methods, >500 lines, multiple concerns | Split by Single Responsibility Principle |

### Priority: HIGH

| Pattern | Description | Detection | Resolution |
|---------|-------------|-----------|------------|
| Complex Nesting | Deeply nested conditionals/loops | >3 levels deep | Extract methods, guard clauses, early returns |
| Long Functions | Functions doing too much | >30 lines | Extract helper functions, decompose |
| Magic Numbers | Unexplained literal values | Numeric/string literals in logic | Extract to named constants |
| Cryptic Names | Unclear variable/function names | Single letters, abbreviations | Rename to descriptive names |
| Missing Type Hints | No type annotations | Functions without annotations | Add comprehensive type hints |
| Missing Docstrings | No documentation | Public APIs without docstrings | Add Google/NumPy style docstrings |

### Priority: MEDIUM

| Pattern | Description | Detection | Resolution |
|---------|-------------|-----------|------------|
| Duplicate Code | Copy-pasted logic | Similar code blocks | Extract to shared function |
| Primitive Obsession | Overuse of primitives | Dicts instead of classes | Create domain objects |
| Long Parameter Lists | Too many function params | >5 parameters | Introduce parameter object |
| Mixed Abstraction | High/low level code mixed | API calls next to string parsing | Separate abstraction layers |

### Priority: LOW

| Pattern | Description | Detection | Resolution |
|---------|-------------|-----------|------------|
| Inconsistent Naming | Mixed naming conventions | camelCase + snake_case | Standardize to PEP 8 |
| Redundant Comments | Comments stating the obvious | `# increment i` above `i += 1` | Remove or improve |
| Unused Imports | Imported but not used | flake8 F401 | Remove unused imports |

## Metric Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Cyclomatic Complexity | <10 | >15 | >20 |
| Cognitive Complexity | <15 | >20 | >30 |
| Function Length | <30 lines | >50 lines | >100 lines |
| Nesting Depth | <=3 levels | >4 levels | >5 levels |
| Docstring Coverage | >80% | <60% | <40% |
| Type Hint Coverage | >90% | <70% | <50% |
| Test Coverage | >=80% | <70% | <60% |
| Lines per File | <400 | >500 | >800 |
| Methods per Class | <10 | >15 | >20 |

## Safety Rules (Non-Negotiable)

### Pre-Refactoring Checklist

- [ ] Test coverage >= 80% (or document gaps)
- [ ] All tests passing
- [ ] Golden outputs captured for integration tests
- [ ] Git working directory clean
- [ ] Baseline metrics documented

### During Refactoring

1. **Static Analysis BEFORE Tests**
   - Run flake8/ruff after every change
   - Catch undefined names immediately
   - Faster feedback than full test suite

2. **Validate After EVERY Micro-Change**
   - One logical change at a time
   - Run relevant tests
   - Commit on success

3. **Migration Checklists for Destructive Changes**
   - Document every usage location
   - Check off as migrated
   - Verify zero remaining usages before deletion

4. **Atomic Commits**
   - Each commit is a working state
   - Clear commit message describing change
   - Easy to bisect if issues arise

5. **STOP on ANY Error**
   - Do not proceed past failures
   - Investigate immediately
   - Fix or rollback before continuing

### Never Do

- Delete code without verifying zero usages
- Combine multiple unrelated changes
- Skip tests "just this once"
- Ignore flake8 warnings
- Force push over broken commits

## Usage

```bash
# Full refactoring workflow (all phases)
/python-code-refactor --all

# Analysis phase only (generates report)
/python-code-refactor --analyze

# Reduce cyclomatic/cognitive complexity
/python-code-refactor --complexity

# Transform procedural to OOP
/python-code-refactor --oop

# Organize and clean imports
/python-code-refactor --imports

# Add comprehensive type hints
/python-code-refactor --type-hints

# Standardize docstrings (Google style)
/python-code-refactor --docstrings

# Upgrade to modern Python syntax
/python-code-refactor --modernize

# Target specific file or directory
/python-code-refactor --path src/module.py

# Dry run (plan without execution)
/python-code-refactor --dry-run
```

### Option Combinations

```bash
# Analysis with complexity focus
/python-code-refactor --analyze --complexity

# Type hints and docstrings together
/python-code-refactor --type-hints --docstrings

# Full refactor on specific module
/python-code-refactor --all --path src/data_processing/
```

## Tool Integration

### Primary Tools

| Tool | Purpose | Speed | Configuration |
|------|---------|-------|---------------|
| **Ruff** | Linting + formatting | 10-100x faster than flake8 | `ruff.toml` or `pyproject.toml` |
| **Flake8** | Comprehensive linting | Standard | `.flake8` |
| **pytest** | Test execution | - | `pytest.ini` or `pyproject.toml` |
| **coverage** | Code coverage | - | `.coveragerc` |

### Flake8 Plugin Stack (16 Plugins)

```ini
# .flake8 configuration
[flake8]
max-line-length = 100
max-complexity = 10
extend-select =
    # Code quality
    C90,    # mccabe complexity
    E,W,    # pycodestyle
    F,      # pyflakes
    # Docstrings
    D,      # pydocstyle
    DAR,    # darglint
    # Bugs
    B,      # bugbear
    S,      # bandit security
    # Imports
    I,      # isort
    # Type hints
    ANN,    # flake8-annotations
    # Clean code
    SIM,    # simplify
    PIE,    # pie
    # Comprehensions
    C4,     # comprehensions
    # Print statements
    T20,    # print
```

### Complexity Analysis

| Tool | Metric | Usage |
|------|--------|-------|
| **complexipy** | Cognitive complexity | `complexipy src/` |
| **radon** | Cyclomatic complexity | `radon cc src/ -a` |
| **mccabe** | McCabe complexity | Via flake8 C90 |

### Type Checking

| Tool | Purpose | Command |
|------|---------|---------|
| **mypy** | Static type checking | `mypy src/ --strict` |
| **pyright** | Fast type checking | `pyright src/` |

### Recommended Workflow Integration

```bash
# Pre-commit hook
ruff check --fix src/
ruff format src/
mypy src/
pytest --cov=src

# CI Pipeline
ruff check src/
flake8 src/
mypy src/ --strict
pytest --cov=src --cov-fail-under=80
```

## Output Artifacts

After running the skill, these artifacts are generated:

```
specs/refactoring/
├── analysis-report.md      # Phase 1 findings
├── refactoring-plan.md     # Phase 2 plan
├── migration-checklists/   # Phase 3 checklists
│   └── {change-name}.md
├── validation-report.md    # Phase 4 results
└── metrics-comparison.md   # Before/after metrics
```

## Integration with Other Skills

- **TDD Skill**: Ensures test coverage before refactoring
- **Documentation Skill**: Updates docs after API changes
- **Code Review Skill**: Reviews refactoring PRs
- **Performance Skill**: Validates no regression

## Examples

### Example 1: Reduce Complexity

```bash
/python-code-refactor --complexity --path src/data_processor.py
```

Output:
```markdown
## Complexity Reduction: src/data_processor.py

### Before
- Cyclomatic: 25 (CRITICAL)
- Cognitive: 45 (CRITICAL)
- Deepest nesting: 6 levels

### Changes Made
1. Extracted `validate_input()` from `process()`
2. Converted nested ifs to guard clauses
3. Split `transform_data()` into 3 focused functions

### After
- Cyclomatic: 8 (PASS)
- Cognitive: 12 (PASS)
- Deepest nesting: 2 levels

### Validation
- All 47 tests passing
- Coverage: 85% (unchanged)
- Performance: +2% faster
```

### Example 2: OOP Transformation

```bash
/python-code-refactor --oop --path src/utils/
```

Output:
```markdown
## OOP Transformation: src/utils/

### Script-like Code Identified
- `helpers.py`: 15 module-level functions
- `processors.py`: 8 functions with shared state

### Transformation Plan
1. Create `DataHelper` class from helpers.py
2. Create `Processor` class with dependency injection
3. Remove global variables

### Migration Checklist
- [x] src/main.py:23 - Updated to use DataHelper
- [x] src/main.py:45 - Updated to use Processor
- [x] tests/test_helpers.py - Updated fixtures

### Verification
- grep "helper_function" -> 0 matches
- All tests passing
```
