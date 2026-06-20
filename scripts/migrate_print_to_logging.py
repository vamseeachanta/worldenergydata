"""Migrate print() statements to logging calls.

Usage: python scripts/migrate_print_to_logging.py src/worldenergydata/
"""
import ast
import sys
from pathlib import Path


def _logging_insert_line(content: str, new_lines: list[str]) -> int:
    """Return the 0-based line index AFTER the top-level import block.

    Uses ``ast`` to locate the last top-level ``import``/``from`` statement so
    the insertion point is the line *after* the full (possibly multi-line)
    import block — never inside an unclosed ``(`` of a multi-line import.

    Falls back to a paren-depth-aware line scan if the source does not parse.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _logging_insert_line_fallback(new_lines)

    last_import_end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # end_lineno is 1-based and points at the statement's last line
            # (the line containing the closing paren for multi-line imports).
            end = getattr(node, "end_lineno", node.lineno)
            last_import_end = max(last_import_end, end)
        else:
            # Imports must be contiguous at module top for our insertion to be
            # safe; stop at the first non-import top-level statement.
            break
    return last_import_end  # 0-based index of line *after* the import block


def _logging_insert_line_fallback(new_lines: list[str]) -> int:
    """Paren-depth-aware scan: insert only when bracket depth is 0.

    Tracks ``()[]{}`` depth so a multi-line import/call body does not register
    as an import boundary. Returns the line index after the last top-level
    ``import``/``from`` statement.
    """
    import_idx = 0
    depth = 0
    in_import = False
    for i, line in enumerate(new_lines):
        # A new top-level statement begins only when no bracket is open.
        if depth == 0 and (
            line.startswith("import ") or line.startswith("from ")
        ):
            in_import = True
        depth += line.count("(") - line.count(")")
        depth += line.count("[") - line.count("]")
        depth += line.count("{") - line.count("}")
        if depth < 0:
            depth = 0
        # When brackets close (depth 0) on a line belonging to an import
        # statement, the import block extends through this line.
        if in_import and depth == 0:
            import_idx = i + 1
            in_import = False
    return import_idx


def process_file(filepath: Path) -> int:
    """Replace print() with logger calls. Returns count of replacements."""
    content = filepath.read_text()
    if "print(" not in content:
        return 0

    lines = content.split("\n")
    replacements = 0
    has_logger = "get_logger" in content or "logger" in content

    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("print(f\"ERROR") or stripped.startswith("print(f\"Error"):
            new_lines.append(line.replace("print(", "logger.error(", 1))
            replacements += 1
        elif stripped.startswith("print(f\"Warning") or stripped.startswith("print(f\"WARN"):
            new_lines.append(line.replace("print(", "logger.warning(", 1))
            replacements += 1
        elif stripped.startswith("print("):
            new_lines.append(line.replace("print(", "logger.info(", 1))
            replacements += 1
        else:
            new_lines.append(line)

    if replacements > 0 and not has_logger:
        # Find the line AFTER the top-level import block (depth 0) so the
        # logging setup is never injected inside a multi-line import/call.
        import_idx = _logging_insert_line("\n".join(new_lines), new_lines)
        new_lines.insert(import_idx, "")
        new_lines.insert(import_idx + 1, "from worldenergydata.common.logging import get_logger")
        new_lines.insert(import_idx + 2, "")
        new_lines.insert(import_idx + 3, "logger = get_logger(__name__)")

        filepath.write_text("\n".join(new_lines))
    elif replacements > 0:
        filepath.write_text("\n".join(new_lines))

    return replacements


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("src/worldenergydata")
    total = 0
    for py_file in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        count = process_file(py_file)
        if count > 0:
            print(f"  {py_file}: {count} replacements")
            total += count
    print(f"\nTotal: {total} print() -> logger replacements")
