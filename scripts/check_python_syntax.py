"""Parse every Python source under src/ and packages/ without importing it."""

import argparse
import ast
from pathlib import Path


def check_sources(roots: list[Path]) -> tuple[int, list[str]]:
    """Return the file count and every parse/read failure, in path order."""
    paths = sorted({path for root in roots for path in root.rglob("*.py")})
    failures = [f"{root}: missing source root" for root in roots if not root.is_dir()]
    for path in paths:
        try:
            ast.parse(path.read_bytes(), filename=str(path))
        except (SyntaxError, UnicodeError, OSError) as error:
            line = getattr(error, "lineno", None)
            failures.append(f"{path}:{line}: {type(error).__name__}")
    return len(paths), failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots", nargs="*", type=Path, default=[Path("src"), Path("packages")]
    )
    args = parser.parse_args(argv)
    count, failures = check_sources(args.roots)
    print(f"Parsed {count} Python files; {len(failures)} failures")
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
