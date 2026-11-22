"""Ordered CSV identity uses the shared stdlib catalog fingerprint."""

import csv
import hashlib
import importlib
import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

# This file's third ancestor is the repository root.
ROOT = Path(__file__).resolve().parents[2]
CATALOG_SOURCE = ROOT / "src/worldenergydata/field_development"
CSV_TEXT = 'Z,A,M\n," \t ","\u00e9""\\\n"\n'
VALUES = ["", " \t ", '\u00e9"\\\n']
# Hand-encoded compact JSON list, independent of either fingerprint function:
# empty text, preserved spaces/tab, UTF-8 e-acute, escaped quote/backslash/LF.
JSON_BYTES = b'[""," \\t ","\xc3\xa9\\"\\\\\\n"]'


def load_atlas(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/field_atlas"))
    return importlib.import_module("build_atlas_feed")


def test_atlas_delegates_to_shared_fingerprint(monkeypatch):
    atlas = load_atlas(monkeypatch)
    monkeypatch.syspath_prepend(str(CATALOG_SOURCE))
    common = importlib.import_module("catalog_build_common")
    row = next(csv.DictReader(io.StringIO(CSV_TEXT)))
    expected = hashlib.sha256(JSON_BYTES).hexdigest()

    with patch.object(common, "row_fingerprint", wraps=common.row_fingerprint) as spy:
        assert atlas._row_fingerprint(row) == expected
        spy.assert_called_once_with(VALUES)


def test_atlas_fingerprint_preserves_csv_bytes(monkeypatch):
    atlas = load_atlas(monkeypatch)
    row = next(csv.DictReader(io.StringIO(CSV_TEXT)))
    expected = hashlib.sha256(JSON_BYTES).hexdigest()

    assert list(row.values()) == VALUES
    assert atlas._row_fingerprint(row) == expected
    assert atlas._row_fingerprint(dict(row, A=" ")) != expected
    reordered = {"A": row["A"], "Z": row["Z"], "M": row["M"]}
    assert atlas._row_fingerprint(reordered) != expected


def test_atlas_fingerprint_runs_without_site_packages():
    # Isolated Python excludes site packages and ignores the inherited path.
    # A direct script load must avoid importing the analysis package entirely.
    program = """
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("atlas", sys.argv[1])
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)
print(atlas._row_fingerprint({"Z": "", "A": " "}))
assert not any(
    name == "worldenergydata" or name.startswith("worldenergydata.")
    for name in sys.modules
)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            program,
            str(ROOT / "scripts/field_atlas/build_atlas_feed.py"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # Hand-encoded compact JSON for the separate minimal subprocess example.
    assert result.stdout.strip() == hashlib.sha256(b'[""," "]').hexdigest()
