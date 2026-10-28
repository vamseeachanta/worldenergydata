"""Independent fixtures for the repository syntax check."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/check_python_syntax.py"
spec = importlib.util.spec_from_file_location("check_python_syntax", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_lists_all_failures_and_counts_files(tmp_path, capsys):
    """Hand count: one valid module plus two unclosed calls gives three files.

    Both unclosed calls fail at their only line; a text file is excluded.
    """
    (tmp_path / "good.py").write_text('value = "ready"\n')
    (tmp_path / "bad.py").write_text("print(\n")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "bad.py").write_text("print(\n")
    (tmp_path / "ignored.txt").write_text("print(\n")
    count, failures = checker.check_sources([tmp_path])
    assert count == 3
    assert failures == [
        f'{tmp_path / "bad.py"}:1: SyntaxError',
        f'{nested / "bad.py"}:1: SyntaxError',
    ]
    assert checker.main([str(tmp_path)]) == 1
    assert "Parsed 3 Python files; 2 failures" in capsys.readouterr().out


def test_valid_encoded_source_passes(tmp_path, capsys):
    """One valid Latin-1 source gives one parsed file and no failures."""
    (tmp_path / "good.py").write_bytes(b'# coding: latin-1\ntext = "caf\xe9"\n')
    assert checker.check_sources([tmp_path]) == (1, [])
    assert checker.main([str(tmp_path)]) == 0
    assert "Parsed 1 Python files; 0 failures" in capsys.readouterr().out


def test_missing_source_root_fails(tmp_path, capsys):
    """A missing directory is a scan failure, not evidence of valid syntax."""
    missing = tmp_path / "missing"
    assert checker.check_sources([missing]) == (0, [f"{missing}: missing source root"])
    assert checker.main([str(missing)]) == 1
    assert "missing source root" in capsys.readouterr().out
