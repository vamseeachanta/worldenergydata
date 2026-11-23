"""Hand-written source examples for the print migration."""

import ast
import importlib.util
import runpy
from pathlib import Path, PureWindowsPath

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/migrate_print_to_logging.py"
spec = importlib.util.spec_from_file_location("migrate_print_to_logging", SCRIPT)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_parenthesised_import_stays_parseable(tmp_path):
    """Independent expected output (written by hand):

    from pathlib import (
        Path,
    )

    from worldenergydata.common.logging import get_logger

    logger = get_logger(__name__)
    logger.info("ready")

    The closing parenthesis belongs to the original import; both added
    statements follow it. Exactly one print expression is replaced.
    """
    source = 'from pathlib import (\n    Path,\n)\nprint("ready")\n'
    expected = (
        "from pathlib import (\n    Path,\n)\n\n"
        "from worldenergydata.common.logging import get_logger\n\n"
        'logger = get_logger(__name__)\nlogger.info("ready")\n'
    )
    path = tmp_path / "example.py"
    path.write_text(source, encoding="utf-8", newline="\n")
    assert migration.process_file(path, write=True) == 1
    ast.parse(path.read_text(encoding="utf-8"))
    assert path.read_text(encoding="utf-8") == expected


# Expected blocks below are literal, independently written Python statements.
BLOCK = (
    "\nfrom worldenergydata.common.logging import get_logger\n\n"
    "logger = get_logger(__name__)\n"
)


def test_import_and_docstring_boundaries():
    """Each prefix is complete; append setup, then the hand-replaced call.

    Independent count: each input has exactly one eligible print expression.
    Python 3.11 ast.AST documents end_lineno as the final statement line:
    https://docs.python.org/3.11/library/ast.html#ast.AST
    """
    prefixes = [
        "import os\n",
        "from pathlib import (\n    Path,\n)\n",
        "from pathlib import \\\n    Path\n",
        '"""Module notes."""\n',
        '"""Module notes."""\nfrom __future__ import annotations\n',
        "#!/usr/bin/env python3\n# coding: utf-8\n",
        "",
    ]
    for prefix in prefixes:
        expected = prefix + BLOCK + 'logger.info("ready")\n'
        actual, count = migration.migrate_source(prefix + 'print("ready")\n')
        assert count == 1
        assert actual == expected
        assert ast.get_docstring(ast.parse(actual)) == ast.get_docstring(
            ast.parse(prefix)
        )


def test_type_checking_imports_remain_conditional():
    """Only the typing import anchors setup; the nested import stays in its if."""
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    from pathlib import Path\n"
        'print("ready")\n'
    )
    expected = (
        "from typing import TYPE_CHECKING\n"
        + BLOCK
        + "if TYPE_CHECKING:\n    from pathlib import Path\n"
        + 'logger.info("ready")\n'
    )
    assert migration.migrate_source(source) == (expected, 1)


def test_unchanged_sources():
    """Zero eligible replacements follows by inspection of each literal input."""
    sources = [
        '"""Only a docstring."""',
        "",
        '# print("comment")\ntext = \'print("string")\'\n',
        'logger = object()\nprint("ready")\n',
        'import logging\nlogger = logging.getLogger(__name__)\nprint("ready")\n',
        'from helper import logger\nprint("ready")\n',
        'from helper import *\nprint("ready")\n',
        'match value:\n    case {"item": print}:\n        print("ready")\n',
        'def f(print):\n    print("ready")\n',
        'print("a", "b")\nprint("x", end="")\n',
        "print(*values)\n",
        'result = print("ready")\n',
        'print("early")\nimport os\n',
        'get_logger = object()\nprint("ready")\n',
    ]
    for source in sources:
        assert migration.migrate_source(source) == (source, 0)


def test_existing_import_and_second_run(tmp_path):
    """Reuse the sole logger import; the second pass has no eligible call."""
    source = migration.LOGGER_IMPORT + '\nprint("ready")\n'
    expected = (
        migration.LOGGER_IMPORT
        + "\n\nlogger = get_logger(__name__)\n"
        + 'logger.info("ready")\n'
    )
    actual, count = migration.migrate_source(source)
    assert (actual, count) == (expected, 1)
    path = tmp_path / "example.py"
    path.write_text(actual, encoding="utf-8", newline="\n")
    runpy.run_path(str(path))
    assert migration.migrate_source(actual) == (actual, 0)


@pytest.mark.parametrize(
    "binding",
    [
        "get_logger = None",
        "get_logger: object = None",
        "(get_logger := None)",
        "import math as get_logger",
        "from math import pi as get_logger",
        "def get_logger():\n    return None",
        "async def get_logger():\n    return None",
        "class get_logger:\n    pass",
        "del get_logger",
        "for get_logger in (None,):\n    pass",
        "from contextlib import nullcontext\nwith nullcontext() as get_logger:\n    pass",
        "try:\n    raise ValueError\nexcept ValueError as get_logger:\n    pass",
        "match None:\n    case get_logger:\n        pass",
        'match {"item": None}:\n    case {"item": get_logger}:\n        pass',
        "match {}:\n    case {**get_logger}:\n        pass",
        "def helper(get_logger):\n    pass",
    ],
)
def test_competing_factory_bindings_preserve_execution(binding, tmp_path, capsys):
    """A permitted import cannot hide another binding; no call may change."""
    source = (
        "from worldenergydata.common.logging import get_logger\n"
        + binding
        + '\nimport os\nprint("ready")\n'
    )
    path = tmp_path / "example.py"
    path.write_text(source, encoding="utf-8", newline="\n")
    runpy.run_path(str(path))
    assert capsys.readouterr().out == "ready\n"

    actual, count = migration.migrate_source(source)
    path.write_text(actual, encoding="utf-8", newline="\n")
    runpy.run_path(str(path))
    assert capsys.readouterr().out == "ready\n"
    assert (actual, count) == (source, 0)


def test_levels_and_multiline_calls():
    """Three literal calls map respectively to error, warning and info."""
    source = (
        'print(f"ERROR: {value}")\nprint(f"Warning: {value}")\nprint(\n    "ready"\n)\n'
    )
    expected = (
        BLOCK
        + 'logger.error(f"ERROR: {value}")\n'
        + 'logger.warning(f"Warning: {value}")\nlogger.info(\n    "ready"\n)\n'
    )
    assert migration.migrate_source(source) == (expected, 3)


def test_utf8_columns_and_semicolon():
    """The accented character occupies two UTF-8 bytes; only print changes."""
    source = 'text = "é"; print("ready")\n'
    expected = BLOCK + 'text = "é"; logger.info("ready")\n'
    assert migration.migrate_source(source) == (expected, 1)


def test_dry_run_preserves_bytes_and_prints_diff(tmp_path, capsys):
    """One call yields one replacement in the preview, with no saved change."""
    path = tmp_path / "example.py"
    original = b'print("ready")\n'
    path.write_bytes(original)
    assert migration.process_file(path) == 1
    assert path.read_bytes() == original
    diff = capsys.readouterr().out
    assert "--- " in diff and "+++ " in diff and "@@ " in diff
    assert '-print("ready")' in diff
    assert '+logger.info("ready")' in diff


def test_preview_uses_portable_relative_paths(capsys):
    """Windows preview headers use forward slashes without filesystem access."""

    class PreviewPath(PureWindowsPath):
        def read_bytes(self):
            return b'print("ready")\n'

    assert migration.process_file(PreviewPath("examples/example.py")) == 1
    assert capsys.readouterr().out.splitlines()[:2] == [
        "--- examples/example.py",
        "+++ examples/example.py",
    ]


def test_syntax_error_is_skipped(tmp_path, capsys):
    """An unclosed call is invalid before migration, so its bytes stay intact."""
    path = tmp_path / "broken.py"
    original = b"print(\n"
    path.write_bytes(original)
    assert migration.process_file(path, write=True) == 0
    assert path.read_bytes() == original
    assert "Skipped broken.py: SyntaxError" in capsys.readouterr().out


def test_invalid_candidate_is_not_saved(tmp_path, monkeypatch, capsys):
    """A simulated faulty transform cannot replace the valid original file."""
    path = tmp_path / "example.py"
    original = b'print("ready")\n'
    path.write_bytes(original)
    monkeypatch.setattr(migration, "migrate_source", lambda text: ("logger.info(\n", 1))
    assert migration.process_file(path, write=True) == 0
    assert path.read_bytes() == original
    assert "Skipped example.py: SyntaxError" in capsys.readouterr().out


def test_save_failure_restores_original(tmp_path, monkeypatch):
    """Simulate a partial first write; a subsequent restoration uses input bytes."""
    import pytest

    path = tmp_path / "example.py"
    original = b'print("ready")\n'
    path.write_bytes(original)
    write = Path.write_bytes
    attempts = []

    def partial_write(self, data):
        attempts.append(data)
        if len(attempts) == 1:
            write(self, b"partial")
            raise OSError("simulated write failure")
        return write(self, data)

    monkeypatch.setattr(Path, "write_bytes", partial_write)
    with pytest.raises(OSError, match="simulated write failure"):
        migration.process_file(path, write=True)
    assert path.read_bytes() == original


def test_encoding_crlf_and_no_final_newline(tmp_path):
    """The cookie selects Latin-1; existing CRLF and the missing EOF newline stay."""
    path = tmp_path / "example.py"
    source = '# coding: latin-1\r\nprint("café")'
    expected = (
        "# coding: latin-1\r\n" + BLOCK.replace("\n", "\r\n") + 'logger.info("café")'
    )
    path.write_bytes(source.encode("latin-1"))
    assert migration.process_file(path, write=True) == 1
    assert path.read_bytes() == expected.encode("latin-1")
    assert migration.process_file(path, write=True) == 0


def test_cli_requires_write_flag(tmp_path, capsys):
    """The same one-call file is unchanged by preview and changed by --write."""
    path = tmp_path / "example.py"
    source = 'print("ready")\n'
    path.write_text(source, encoding="utf-8", newline="\n")
    assert migration.main([str(path)]) == 0
    assert path.read_text(encoding="utf-8") == source
    assert "(preview)" in capsys.readouterr().out
    assert migration.main([str(path), "--write"]) == 0
    assert path.read_text(encoding="utf-8") == BLOCK + 'logger.info("ready")\n'
    assert "(written)" in capsys.readouterr().out
