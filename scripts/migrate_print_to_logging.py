"""Preview conservative print-to-logging migrations; use --write to save.

Only standalone, unshadowed print calls with one argument and no keywords
are eligible. Existing logger bindings and unsupported calls are left alone.
See docs/development/print-to-logging.md for examples and limitations.
"""

import argparse
import ast
import difflib
import io
import tokenize
from pathlib import Path

LOGGER_IMPORT = "from worldenergydata.common.logging import get_logger"


def _bound_names(tree: ast.Module) -> set[str]:
    """Conservatively collect bindings, including nested scopes."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.split(".")[0])
        elif (
            isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar))
            and node.name
        ):
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names


def _insertion_line(tree: ast.Module, content: str) -> int:
    """Return a complete physical line after the docstring and module imports.

    Python 3.11 ast docs, Abstract Grammar / node positions: lineno is
    one-indexed and end_lineno includes the statement's final source line.
    https://docs.python.org/3.11/library/ast.html#ast.AST
    """
    anchors = [
        node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    if tree.body and isinstance(tree.body[0], ast.Expr):
        value = tree.body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            anchors.append(tree.body[0])
    if anchors:
        return max(node.end_lineno for node in anchors)

    # Keep the shebang, encoding cookie and leading comments before the block.
    for token in tokenize.generate_tokens(io.StringIO(content).readline):
        if token.type not in (tokenize.COMMENT, tokenize.NL, tokenize.ENDMARKER):
            return token.start[0] - 1
    return len(content.splitlines())


def migrate_source(content: str) -> tuple[str, int]:
    """Build a candidate without changing the input file; syntax errors propagate."""
    tree = ast.parse(content)
    bindings = _bound_names(tree)
    if "logger" in bindings or "print" in bindings or "*" in bindings:
        return content, 0

    insertion = _insertion_line(tree, content)
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if (
            isinstance(call.func, ast.Name)
            and call.func.id == "print"
            and len(call.args) == 1
            and not isinstance(call.args[0], ast.Starred)
            and not call.keywords
        ):
            # A call before a later module import would precede logger setup.
            # Leave such unusual modules unchanged rather than move execution.
            if call.lineno <= insertion:
                return content, 0
            calls.append(call)
    if not calls:
        return content, 0

    # AST column offsets are UTF-8 byte offsets (Python 3.11 ast.AST docs).
    # Replace only the function token, preserving strings, comments and layout.
    lines = content.encode("utf-8").splitlines(keepends=True)
    for call in sorted(
        calls, key=lambda item: (item.lineno, item.col_offset), reverse=True
    ):
        level = "info"
        argument = call.args[0]
        if isinstance(argument, ast.JoinedStr) and argument.values:
            prefix = argument.values[0]
            if isinstance(prefix, ast.Constant) and isinstance(prefix.value, str):
                if prefix.value.startswith(("ERROR", "Error")):
                    level = "error"
                elif prefix.value.startswith(("Warning", "WARN")):
                    level = "warning"
        index = call.func.lineno - 1
        column = call.func.col_offset
        line = lines[index]
        lines[index] = (
            line[:column] + f"logger.{level}".encode() + line[column + len("print") :]
        )

    newline = "\r\n" if "\r\n" in content else "\n"
    # Reuse only an unconditional, correctly bound get_logger import.
    imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "worldenergydata.common.logging"
        and not node.level
        and any(
            alias.name == "get_logger" and alias.asname in (None, "get_logger")
            for alias in node.names
        )
        for node in tree.body
    )
    if "get_logger" in bindings and not imported:
        return content, 0
    block = newline
    if not imported:
        block += LOGGER_IMPORT + newline + newline
    block += "logger = get_logger(__name__)" + newline
    if insertion and not lines[insertion - 1].endswith(b"\n"):
        block = newline + block
    lines.insert(insertion, block.encode("utf-8"))
    return b"".join(lines).decode("utf-8"), len(calls)


def process_file(filepath: Path, *, write: bool = False) -> int:
    """Preview a unified diff, or save a validated candidate with explicit opt-in.

    Invalid input or output is skipped. Validation happens before opening the
    file for writing, so a failed parse leaves the original bytes intact.
    """
    original = filepath.read_bytes()
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(original).readline)
        content = original.decode(encoding)
        rewritten, count = migrate_source(content)
        if not count:
            return 0
        ast.parse(rewritten)
        encoded = rewritten.encode(encoding)
    except (SyntaxError, UnicodeError, LookupError) as error:
        print(f"Skipped {filepath.name}: {type(error).__name__}")
        return 0

    if write:
        try:
            filepath.write_bytes(encoded)
        except OSError:
            filepath.write_bytes(original)
            raise
    else:
        print(
            "".join(
                difflib.unified_diff(
                    content.splitlines(keepends=True),
                    rewritten.splitlines(keepends=True),
                    fromfile=str(filepath),
                    tofile=str(filepath),
                )
            ),
            end="",
        )
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", nargs="?", type=Path, default=Path("src/worldenergydata")
    )
    parser.add_argument("--write", action="store_true", help="Save validated rewrites")
    args = parser.parse_args(argv)
    paths = [args.root] if args.root.is_file() else sorted(args.root.rglob("*.py"))
    total = sum(process_file(path, write=args.write) for path in paths)
    print(
        f"\nTotal: {total} print() -> logger replacements ({'written' if args.write else 'preview'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
