# python-code-refactor Skill (v1.0.0)

> Systematic Python code quality improvements with safety-first design

## Key Principles

1. **Safety-First**: Regression prevention is mandatory - tests must pass before AND after
2. **Static Analysis BEFORE Tests**: Run linters/type checkers to catch issues early
3. **Migration Checklists**: Destructive changes require documented rollback plans
4. **Multi-Dimensional Metrics**: Track complexity, coverage, type hints, documentation
5. **Class-Based Architecture**: Transform spaghetti code into maintainable OOP structures

## Quick Start

```bash
/python-code-refactor --analyze      # Analyze code quality first
/python-code-refactor --all          # Full refactor workflow
/python-code-refactor --complexity   # Target high-complexity functions
/python-code-refactor --types        # Add missing type hints
```

## File Structure

```
python-code-refactor/
├── SKILL.md                    # Core skill definition and workflow
├── README.md                   # This file
├── assets/
│   ├── pyproject.toml          # Ruff, mypy, radon configurations
│   └── templates/              # Code templates for refactoring
├── scripts/                    # Validation and analysis scripts
└── references/                 # Detailed guides and examples
    └── examples/               # Before/after refactoring samples
```

## Gap This Skill Fills

Existing skills handle **repository structure**:
- `module-based-refactor` - Move files, reorganize directories
- `discipline-refactor` - Enforce naming conventions
- `repo-cleanup` - Remove dead code, fix imports

**Missing**: Python **code-level** refactoring for:
- Reducing cyclomatic/cognitive complexity
- Transforming procedural code to OOP
- Adding type hints systematically
- Standardizing docstrings
- Detecting and fixing anti-patterns

## What This Skill Does

| Category | Actions |
|----------|---------|
| **Complexity Reduction** | Split long functions, extract methods, simplify conditionals |
| **OOP Transformation** | Convert procedural to class-based, apply SOLID principles |
| **Type Hint Coverage** | Add return types, parameter types, `TypedDict` for dicts |
| **Documentation** | Standardize to Google/NumPy docstring format |
| **Anti-Pattern Detection** | Find god classes, long parameter lists, deep nesting |

## Safety Workflow

```
1. Baseline Tests    -> Must pass (exit if fail)
2. Static Analysis   -> Capture current warnings
3. Refactor Code     -> Apply targeted improvements
4. Verify Tests      -> Must still pass
5. Compare Metrics   -> Document improvements
6. Commit Changes    -> With detailed message
```

## Integration

This skill integrates with:
- **pytest** - Test verification
- **ruff** - Linting and formatting
- **mypy** - Type checking
- **radon** - Complexity metrics

## Related Files

- **[SKILL.md](./SKILL.md)** - Complete workflow definition and decision trees
- **[assets/pyproject.toml](./assets/pyproject.toml)** - Tool configuration
- **[references/](./references/)** - Anti-pattern guides, complexity thresholds

---

*Internal meta-skill for Python code quality improvements*
