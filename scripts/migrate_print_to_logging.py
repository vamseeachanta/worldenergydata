"""Migrate print() statements to logging calls.

Usage: python scripts/migrate_print_to_logging.py src/worldenergydata/
"""
import re
import sys
from pathlib import Path


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
        import_idx = 0
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                import_idx = i + 1
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
