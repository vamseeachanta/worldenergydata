"""Tests for scripts/migrate_print_to_logging.py (issue #275).

Regression coverage for the AST/depth-aware logging-setup injection: the
``get_logger`` block must be inserted at top-level (statement depth 0), AFTER
the full import block, and must NEVER land inside an unclosed ``(`` of a
multi-line import/call.
"""

import ast
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "migrate_print_to_logging.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("migrate_print_to_logging", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


migrate = _load_module()


def test_multiline_import_injection_is_valid_python(tmp_path: Path):
    """The classic broken case from issue #275: a multi-line import."""
    src = (
        "from worldenergydata.modules.hse.importers.bsee_incidents_importer import (\n"
        "    BSEEIncidentsImporter,\n"
        "    OtherThing,\n"
        ")\n"
        "\n"
        "\n"
        "def run():\n"
        '    print(f"Loaded {BSEEIncidentsImporter}")\n'
    )
    f = tmp_path / "mod.py"
    f.write_text(src)

    count = migrate.process_file(f)
    out = f.read_text()

    # Replacement happened.
    assert count == 1
    # File still parses -> injection did NOT land mid-import.
    ast.parse(out)

    out_lines = out.split("\n")
    import_close = next(i for i, ln in enumerate(out_lines) if ln.strip() == ")")
    logger_setup = next(
        i for i, ln in enumerate(out_lines) if ln == "logger = get_logger(__name__)"
    )
    get_logger_import = next(
        i
        for i, ln in enumerate(out_lines)
        if ln == "from worldenergydata.common.logging import get_logger"
    )
    # The logging setup is inserted AFTER the import block closes.
    assert get_logger_import > import_close
    assert logger_setup > import_close
    # print() was rewritten to logger.info(.
    assert "logger.info(" in out
    assert "print(" not in out


def test_single_line_import_injection_is_valid_python(tmp_path: Path):
    src = (
        "import os\n"
        "from pathlib import Path\n"
        "\n"
        "\n"
        "def run():\n"
        "    print(f\"cwd={os.getcwd()} {Path('.')}\")\n"
    )
    f = tmp_path / "mod.py"
    f.write_text(src)

    count = migrate.process_file(f)
    out = f.read_text()

    assert count == 1
    ast.parse(out)
    out_lines = out.split("\n")
    last_import = max(
        i
        for i, ln in enumerate(out_lines)
        if ln.startswith("import os") or ln.startswith("from pathlib")
    )
    get_logger_import = next(
        i
        for i, ln in enumerate(out_lines)
        if ln == "from worldenergydata.common.logging import get_logger"
    )
    assert get_logger_import > last_import
    assert "logger.info(" in out


def test_error_and_warning_print_routing(tmp_path: Path):
    src = (
        "import sys\n"
        "\n"
        "\n"
        "def run():\n"
        '    print(f"ERROR bad: {sys.argv}")\n'
        '    print(f"Warning slow")\n'
        '    print(f"ok")\n'
    )
    f = tmp_path / "mod.py"
    f.write_text(src)

    count = migrate.process_file(f)
    out = f.read_text()

    assert count == 3
    ast.parse(out)
    assert "logger.error(" in out
    assert "logger.warning(" in out
    assert "logger.info(" in out


def test_no_print_is_noop(tmp_path: Path):
    src = "import os\n\n\nx = os.getcwd()\n"
    f = tmp_path / "mod.py"
    f.write_text(src)
    assert migrate.process_file(f) == 0
    assert f.read_text() == src


def test_existing_logger_not_reinjected(tmp_path: Path):
    src = (
        "from worldenergydata.common.logging import get_logger\n"
        "\n"
        "logger = get_logger(__name__)\n"
        "\n"
        "\n"
        "def run():\n"
        '    print(f"hello")\n'
    )
    f = tmp_path / "mod.py"
    f.write_text(src)
    count = migrate.process_file(f)
    out = f.read_text()
    assert count == 1
    ast.parse(out)
    # get_logger import appears exactly once (not re-injected).
    assert out.count("from worldenergydata.common.logging import get_logger") == 1


def test_fallback_handles_multiline_import_when_source_unparsable():
    """Depth-aware fallback used when ast.parse fails on the input."""
    # Source with a genuine syntax error elsewhere so ast.parse raises,
    # forcing the fallback path; the multi-line import must still be skipped.
    lines = [
        "from x import (",
        "    a,",
        "    b,",
        ")",
        "def broken(:",  # syntax error -> ast.parse fails
    ]
    idx = migrate._logging_insert_line("\n".join(lines), lines)
    # Insertion index must be AFTER the closing paren (line index 3), i.e. 4,
    # never inside the multi-line import (indices 0-3).
    assert idx == 4


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
