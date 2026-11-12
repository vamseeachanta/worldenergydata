"""Synthetic, disk-backed inventory checks for OSHA CSV fragments."""

import csv
import hashlib
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/ingest/hse_bulk_ingest.py"
FIELDS = ["violation_id", "establishment_id", "citation_date", "naics", "detail"]
ROW = ["0001", "0010", "2024-01-02", "213112", "synthetic detail"]


def load_module():
    assert SCRIPT.is_file(), "The planned inventory script does not exist"
    spec = importlib.util.spec_from_file_location("hse_bulk_ingest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile(raw_dir, index_db):
    return load_module().profile_fragments(raw_dir, index_db)


def write_csv(root, name, rows, fields=FIELDS):
    path = root / name
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)
    return path


def test_exact_overlap_and_key_conflicts_are_distinct(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    changed = [*ROW[:-1], "changed detail"]
    other = ["0002", "0010", "2024-02-03", "211111", "another detail"]
    write_csv(raw, "osha_violation2.csv", [ROW, ROW, other])
    write_csv(raw, "osha_violation3.csv", [ROW, changed])
    result = profile(raw, tmp_path / "index.sqlite")
    assert result["rows"] == 5
    assert result["unique_rows"] == 3
    assert result["duplicate_rows"] == 2
    assert result["keyed_rows"] == 5
    assert result["unique_candidate_keys"] == 2
    assert result["duplicate_candidate_keys"] == 3
    assert result["candidate_key"] == FIELDS[:3]
    first, second = result["files"]
    assert first["duplicate_rows"] == 1
    assert first["overlap_rows"] == 0
    assert second["duplicate_rows"] == second["overlap_rows"] == 1
    assert second["overlap_candidate_keys"] == 2
    assert first["citation_date_min"] == "2024-01-02"
    assert first["citation_date_max"] == "2024-02-03"
    assert first["columns"] == FIELDS
    assert first["bytes"] == (raw / "osha_violation2.csv").stat().st_size
    assert (
        first["sha256"]
        == hashlib.sha256((raw / "osha_violation2.csv").read_bytes()).hexdigest()
    )


def test_column_order_and_file_creation_order_do_not_change_counts(tmp_path):
    write_csv(tmp_path, "osha_violation3.csv", [list(reversed(ROW))], FIELDS[::-1])
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    first = profile(tmp_path, tmp_path / "first.sqlite")
    second = profile(tmp_path, tmp_path / "second.sqlite")
    assert first.pop("index_db") == "first.sqlite"
    assert second.pop("index_db") == "second.sqlite"
    assert first == second
    assert first["unique_rows"] == first["unique_candidate_keys"] == 1
    assert [item["name"] for item in first["files"]] == [
        "osha_violation2.csv",
        "osha_violation3.csv",
    ]
    # The index is retained on disk, with exact strings rather than numeric IDs.
    with sqlite3.connect(tmp_path / "first.sqlite") as index:
        key = index.execute("SELECT signature FROM candidate_keys").fetchone()[0]
    assert json.loads(key) == ROW[:3]


def test_missing_keys_and_invalid_dates_are_reported(tmp_path):
    rows = [
        ROW,
        ["", "0010", "2024-02-30", "213112", "invalid date"],
        ["0003", "", "", "213112", "missing fields"],
        ["0004", "0010", "01/03/2024", "213112", "ambiguous date"],
        ["0005", "0010", "20240104", "213112", "compact date"],
    ]
    write_csv(tmp_path, "osha_violation2.csv", rows)
    result = profile(tmp_path, tmp_path / "index.sqlite")
    item = result["files"][0]
    assert result["unkeyed_rows"] == item["unkeyed_rows"] == 2
    assert item["invalid_citation_dates"] == 3
    assert item["missing_citation_dates"] == 1
    assert item["citation_date_min"] == item["citation_date_max"] == "2024-01-02"


def test_unknown_schema_is_inventoried_without_guessing_keys(tmp_path):
    write_csv(
        tmp_path, "osha_violation_event2.csv", [["0001", "raw value"]], ["id", "extra"]
    )
    result = profile(tmp_path, tmp_path / "index.sqlite")
    item = result["files"][0]
    assert result["keyed_rows"] == result["unique_candidate_keys"] == 0
    assert result["unkeyed_rows"] == 1
    assert item["missing_key_columns"] == FIELDS[:3]
    assert item["missing_citation_dates"] == 1
    assert item["citation_date_min"] is item["citation_date_max"] is None
    assert item["columns"] == ["id", "extra"]


def test_all_columns_participate_in_exact_row_identity(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [ROW, [*ROW[:-1], "other"]])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["unique_rows"] == 2
    assert result["unique_candidate_keys"] == 1


def test_empty_fragment_has_explicit_zero_counts(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["rows"] == result["unique_rows"] == 0
    assert result["files"][0]["citation_date_min"] is None


@pytest.mark.parametrize("rows", [[], [ROW]])
def test_successful_index_is_marked_complete(tmp_path, rows):
    write_csv(tmp_path, "osha_violation2.csv", rows)
    index_db = tmp_path / "index.sqlite"
    result = profile(tmp_path, index_db)
    assert result["index_complete"] is True
    assert result["index_db"] == index_db.name
    with sqlite3.connect(index_db) as index:
        assert index.execute("SELECT complete FROM meta").fetchall() == [(1,)]


@pytest.mark.parametrize(
    "content, error",
    [
        (b"id,extra\na\n", ValueError),
        (b"", ValueError),
        (b"id,extra\na,\xff\n", UnicodeDecodeError),
    ],
)
def test_failed_later_fragment_leaves_index_incomplete(tmp_path, content, error):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    (tmp_path / "osha_violation3.csv").write_bytes(content)
    index_db = tmp_path / "index.sqlite"
    with pytest.raises(error):
        profile(tmp_path, index_db)
    with sqlite3.connect(index_db) as index:
        assert index.execute("SELECT complete FROM meta").fetchall() == [(0,)]
        assert index.execute("SELECT COUNT(*) FROM exact_rows").fetchone() == (1,)


@pytest.mark.parametrize("value", ["２０２４-０１-０２", "٢٠٢٤-٠١-٠٢"])
def test_non_ascii_dates_are_rejected_before_calendar_parsing(monkeypatch, value):
    module = load_module()

    class AsciiCalendar:
        @staticmethod
        def fromisoformat(value):
            pytest.fail("Non-ASCII dates must fail the format gate")

    monkeypatch.setattr(module, "date", AsciiCalendar)
    item = {"invalid_citation_dates": 0}
    module._observe_date(item, value)
    assert item["invalid_citation_dates"] == 1


@pytest.mark.parametrize("missing_dir", [False, True])
def test_absent_inputs_fail_without_creating_index(tmp_path, missing_dir):
    raw = tmp_path / "missing" if missing_dir else tmp_path
    with pytest.raises(FileNotFoundError, match="No OSHA violation fragments"):
        profile(raw, tmp_path / "index.sqlite")
    assert not (tmp_path / "index.sqlite").exists()


def test_existing_index_is_never_overwritten(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    index = tmp_path / "existing.sqlite"
    index.write_bytes(b"existing data")
    with pytest.raises(FileExistsError):
        profile(tmp_path, index)
    assert index.read_bytes() == b"existing data"


def test_incomplete_index_is_never_reused(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    broken = tmp_path / "osha_violation3.csv"
    broken.write_bytes(b"id,extra\na\n")
    index_db = tmp_path / "index.sqlite"
    with pytest.raises(ValueError, match="Malformed record"):
        profile(tmp_path, index_db)
    before = index_db.read_bytes()
    # Repairing the input still requires a new index path.
    write_csv(tmp_path, broken.name, [ROW])
    with pytest.raises(FileExistsError):
        profile(tmp_path, index_db)
    assert index_db.read_bytes() == before
    with sqlite3.connect(index_db) as index:
        assert index.execute("SELECT complete FROM meta").fetchall() == [(0,)]
        assert index.execute("SELECT COUNT(*) FROM exact_rows").fetchone() == (1,)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "id,id\na,b\n",
        "id,\na,b\n",
        "id,extra\na\n",
        "id,extra\na,b,c\n",
        'id,extra\na,"unfinished\n',
    ],
)
def test_malformed_csv_fails_instead_of_dropping_records(tmp_path, content):
    (tmp_path / "osha_violation2.csv").write_text(content)
    with pytest.raises(ValueError, match="header|record"):
        profile(tmp_path, tmp_path / "index.sqlite")


def test_raw_inputs_are_unchanged_and_unrelated_csv_is_excluded(tmp_path):
    path = write_csv(tmp_path, "osha_violation2.csv", [ROW])
    write_csv(tmp_path, "unrelated.csv", [["ignore"]], ["id"])
    before = path.read_bytes()
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert path.read_bytes() == before
    assert len(result["files"]) == 1


def test_cli_outputs_json_without_absolute_paths(tmp_path):
    assert SCRIPT.is_file(), "The planned inventory script does not exist"
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--raw-dir",
            str(tmp_path),
            "--index-db",
            str(tmp_path / "index.sqlite"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["rows"] == 1
    assert result["index_complete"] is True
    assert result["index_db"] == "index.sqlite"
    assert str(tmp_path) not in completed.stdout


def test_cli_missing_inputs_cannot_report_success(tmp_path):
    assert SCRIPT.is_file(), "The planned inventory script does not exist"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--raw-dir",
            str(tmp_path),
            "--index-db",
            str(tmp_path / "index.sqlite"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert not completed.stdout
    assert "No OSHA violation fragments" in completed.stderr


def test_multiline_values_and_leading_zero_ids_are_preserved(tmp_path):
    row = [*ROW[:-1], 'comma, quote " and\nUnicode: café']
    write_csv(tmp_path, "osha_violation2.csv", [row])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["rows"] == 1
    with sqlite3.connect(tmp_path / "index.sqlite") as index:
        record = index.execute("SELECT signature FROM exact_rows").fetchone()[0]
    assert json.loads(record) == dict(zip(FIELDS, row))


def test_storage_failure_propagates(tmp_path, monkeypatch):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    module = load_module()

    def fail_write(*args):
        raise sqlite3.OperationalError("synthetic storage failure")

    monkeypatch.setattr(module, "_observe_signature", fail_write)
    with pytest.raises(sqlite3.OperationalError, match="synthetic storage failure"):
        module.profile_fragments(tmp_path, tmp_path / "index.sqlite")
    with sqlite3.connect(tmp_path / "index.sqlite") as index:
        assert index.execute("SELECT complete FROM meta").fetchall() == [(0,)]


def test_changed_source_is_rejected(tmp_path, monkeypatch):
    path = write_csv(tmp_path, "osha_violation2.csv", [ROW])
    module = load_module()
    original = module._observe_signature

    def change_source(*args):
        with path.open("r+b") as source:
            source.write(b"X")
        return original(*args)

    monkeypatch.setattr(module, "_observe_signature", change_source)
    with pytest.raises(RuntimeError, match="changed during profiling"):
        module.profile_fragments(tmp_path, tmp_path / "index.sqlite")
