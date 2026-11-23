# Plan: Issue #275 — Make migrate_print_to_logging.py AST-aware

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/275
**Status:** plan-review
**Tier:** T2 (script rewrite with AST tracking)

## Root Cause
`scripts/migrate_print_to_logging.py` inserts `get_logger` at a fixed line offset without
tracking open-parenthesis depth. This broke 19 files by injecting imports mid-import-block.

## Plan

### Task 1 — Read current script
`scripts/migrate_print_to_logging.py` — understand current insertion logic.

### Task 2 — Add bracket-depth tracking
Replace fixed-offset insertion with a scan-then-insert approach:
```python
def find_safe_insertion_line(lines: list[str]) -> int:
    """Return first line index after all top-level import statements."""
    depth = 0
    last_import_end = 0
    for i, line in enumerate(lines):
        depth += line.count("(") - line.count(")")
        if line.strip().startswith(("import ", "from ")) and depth == 0:
            last_import_end = i
    return last_import_end + 1
```

### Task 3 — Test on the 19 broken files
Run the fixed script against a copy of one broken file from `hse/` or `canada/`.
Assert no mid-block injection occurs.

### Task 4 — Regression tests
`tests/unit/scripts/test_migrate_print_to_logging.py`:
- Multi-line import block: assert get_logger inserted AFTER closing `)` 
- Single-line imports: assert inserted after last import
- No imports: assert inserted at top

## Acceptance Criteria
- `scripts/migrate_print_to_logging.py` tracks bracket depth before inserting
- Running on a file with multi-line import blocks does not inject mid-block
- Unit tests cover the three fixture cases above
