"""Synthetic, disk-backed inventory checks for OSHA CSV fragments.

Fixture headers are the catalogued fragment schemas in
data/catalog/data-catalog.yml (osha_violation0..13, osha_violation_event0..11
and osha_violation_gen_duty_std0..2). DOL files are written as latin-1, the
encoding the repository's OSHA acquirer and importer read them with.
"""

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
VIOLATION_FIELDS = [
    "activity_nr",
    "citation_id",
    "delete_flag",
    "standard",
    "viol_type",
    "issuance_date",
    "abate_date",
    "abate_complete",
    "current_penalty",
    "initial_penalty",
    "contest_date",
    "final_order_date",
    "nr_instances",
    "nr_exposed",
    "rec",
    "gravity",
    "emphasis",
    "hazcat",
    "fta_insp_nr",
    "fta_issuance_date",
    "fta_penalty",
    "fta_contest_date",
    "fta_final_order_date",
    "hazsub1",
    "hazsub2",
    "hazsub3",
    "hazsub4",
    "hazsub5",
    "load_dt",
]
EVENT_FIELDS = [
    "activity_nr",
    "citation_id",
    "pen_fta",
    "hist_event",
    "hist_date",
    "hist_penalty",
    "hist_abate_date",
    "hist_vtype",
    "hist_insp_nr",
    "load_dt",
]
GEN_DUTY_FIELDS = ["activity_nr", "citation_id", "line_nr", "line_text", "load_dt"]
KEY = ["activity_nr", "citation_id"]


def violation(activity="0317000001", citation="01001A", issued="2024-01-02", **values):
    row = dict.fromkeys(VIOLATION_FIELDS, "")
    row.update(
        activity_nr=activity,
        citation_id=citation,
        issuance_date=issued,
        standard="19100147",
        viol_type="S",
        current_penalty="5000",
    )
    row.update(values)
    return [row[column] for column in VIOLATION_FIELDS]


ROW = violation()


def load_module():
    assert SCRIPT.is_file(), "The planned inventory script does not exist"
    spec = importlib.util.spec_from_file_location("hse_bulk_ingest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile(raw_dir, index_db, **options):
    return load_module().profile_fragments(raw_dir, index_db, **options)


def write_csv(root, name, rows, fields=VIOLATION_FIELDS, encoding="latin-1"):
    path = root / name
    with path.open("w", encoding=encoding, newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)
    return path


def test_exact_overlap_and_key_conflicts_are_distinct(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    changed = violation(current_penalty="900")
    other = violation("0317000002", "01001A", "2024-02-03")
    write_csv(raw, "osha_violation2.csv", [ROW, ROW, other])
    write_csv(raw, "osha_violation3.csv", [ROW, changed])
    result = profile(raw, tmp_path / "index.sqlite")
    assert result["table"] == "violation"
    assert result["rows"] == 5
    assert result["unique_rows"] == 3
    assert result["duplicate_rows"] == 2
    assert result["keyed_rows"] == 5
    assert result["unique_candidate_keys"] == 2
    assert result["duplicate_candidate_keys"] == 3
    assert result["candidate_key"] == KEY
    assert result["date_column"] == "issuance_date"
    assert result["files_missing_key_columns"] == []
    assert result["files_missing_date_column"] == []
    first, second = result["files"]
    assert first["duplicate_rows"] == 1
    assert first["overlap_rows"] == 0
    assert second["duplicate_rows"] == second["overlap_rows"] == 1
    assert second["overlap_candidate_keys"] == 2
    assert first["date_min"] == "2024-01-02"
    assert first["date_max"] == "2024-02-03"
    assert first["columns"] == VIOLATION_FIELDS
    assert first["bytes"] == (raw / "osha_violation2.csv").stat().st_size
    assert (
        first["sha256"]
        == hashlib.sha256((raw / "osha_violation2.csv").read_bytes()).hexdigest()
    )


def test_catalogued_schemas_give_meaningful_key_and_date_metrics(tmp_path):
    # The probe from review: catalogued headers for all three tables in one
    # directory, with one exact violation repeat across two fragments.
    write_csv(tmp_path, "osha_violation0.csv", [ROW, violation(citation="01002")])
    write_csv(tmp_path, "osha_violation1.csv", [ROW])
    write_csv(
        tmp_path,
        "osha_violation_event0.csv",
        [["0317000001", "01001A", "P", "Z", "2024-03-01", "0", "", "S", "", ""]] * 2,
        EVENT_FIELDS,
    )
    write_csv(
        tmp_path,
        "osha_violation_gen_duty_std0.csv",
        [["0317000001", "01001A", "1", "Employees were exposed", ""]],
        GEN_DUTY_FIELDS,
    )
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert [item["name"] for item in result["files"]] == [
        "osha_violation0.csv",
        "osha_violation1.csv",
    ]
    assert result["rows"] == result["keyed_rows"] == 3
    assert result["unkeyed_rows"] == 0
    assert result["unique_rows"] == result["unique_candidate_keys"] == 2
    assert result["duplicate_candidate_keys"] == 1
    assert result["files_missing_key_columns"] == []
    second = result["files"][1]
    assert second["overlap_rows"] == second["overlap_candidate_keys"] == 1
    for item in result["files"]:
        assert item["missing_key_columns"] == []
        assert item["missing_dates"] == item["invalid_dates"] == 0
        assert item["date_min"] == item["date_max"] == "2024-01-02"


@pytest.mark.parametrize(
    "table, name, fields, date_column",
    [
        ("violation", "osha_violation0.csv", VIOLATION_FIELDS, "issuance_date"),
        ("violation_event", "osha_violation_event0.csv", EVENT_FIELDS, "hist_date"),
        (
            "violation_gen_duty_std",
            "osha_violation_gen_duty_std0.csv",
            GEN_DUTY_FIELDS,
            None,
        ),
    ],
)
def test_table_selection_is_exact(tmp_path, table, name, fields, date_column):
    write_csv(tmp_path, "osha_violation0.csv", [ROW, violation(citation="01002")])
    write_csv(
        tmp_path,
        "osha_violation_event0.csv",
        [["0317000001", "01001A", "P", "Z", "2024-03-01", "0", "", "S", "", ""]],
        EVENT_FIELDS,
    )
    write_csv(
        tmp_path,
        "osha_violation_gen_duty_std0.csv",
        [["0317000001", "01001A", str(n), "text", ""] for n in (1, 2, 3)],
        GEN_DUTY_FIELDS,
    )
    # Names that a prefix glob would take but that are not table fragments.
    for stray in ("osha_violation_old.csv", "osha_violation0.csv.bak"):
        write_csv(tmp_path, stray, [ROW])
    result = profile(tmp_path, tmp_path / "index.sqlite", table=table)
    rows = {"violation": 2, "violation_event": 1, "violation_gen_duty_std": 3}
    assert result["table"] == table
    assert [item["name"] for item in result["files"]] == [name]
    assert result["files"][0]["columns"] == fields
    assert result["rows"] == result["keyed_rows"] == rows[table]
    assert result["date_column"] == date_column
    assert result["files_missing_date_column"] == []
    if date_column is None:
        item = result["files"][0]
        assert item["missing_dates"] is item["invalid_dates"] is None
        assert item["date_min"] is item["date_max"] is None


def test_unknown_table_is_rejected(tmp_path):
    write_csv(tmp_path, "osha_violation0.csv", [ROW])
    with pytest.raises(ValueError, match="Unknown OSHA table"):
        profile(tmp_path, tmp_path / "index.sqlite", table="inspection")
    assert not (tmp_path / "index.sqlite").exists()


def test_fragments_are_ordered_by_numeric_suffix(tmp_path):
    for number in (10, 2, 1):
        write_csv(tmp_path, f"osha_violation{number}.csv", [ROW])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    names = [item["name"] for item in result["files"]]
    assert names == [
        "osha_violation1.csv",
        "osha_violation2.csv",
        "osha_violation10.csv",
    ]
    assert [item["overlap_rows"] for item in result["files"]] == [0, 1, 1]


def test_column_order_and_file_creation_order_do_not_change_counts(tmp_path):
    write_csv(
        tmp_path, "osha_violation3.csv", [list(reversed(ROW))], VIOLATION_FIELDS[::-1]
    )
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
    assert json.loads(key) == ["0317000001", "01001A"]


def test_missing_keys_and_invalid_dates_are_reported(tmp_path):
    rows = [
        ROW,
        violation(activity="", issued="2024-02-30"),
        violation(activity="0317000003", citation="", issued=""),
        violation(activity="0317000004", issued="01/03/2024"),
        violation(activity="0317000005", issued="20240104"),
    ]
    write_csv(tmp_path, "osha_violation2.csv", rows)
    result = profile(tmp_path, tmp_path / "index.sqlite")
    item = result["files"][0]
    assert result["unkeyed_rows"] == item["unkeyed_rows"] == 2
    assert item["invalid_dates"] == 3
    assert item["missing_dates"] == 1
    assert item["date_min"] == item["date_max"] == "2024-01-02"


def test_unknown_schema_is_inventoried_without_guessing_keys(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [["0001", "raw value"]], ["id", "extra"])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    item = result["files"][0]
    # Absent key or date columns are reported as absent, never as zero repeats.
    assert result["files_missing_key_columns"] == ["osha_violation2.csv"]
    assert result["files_missing_date_column"] == ["osha_violation2.csv"]
    for name in (
        "keyed_rows",
        "unkeyed_rows",
        "duplicate_candidate_keys",
        "unique_candidate_keys",
    ):
        assert result[name] is None
        assert item.get(name) is None
    assert result["rows"] == result["unique_rows"] == 1
    assert item["missing_key_columns"] == KEY
    assert item["missing_dates"] is item["invalid_dates"] is None
    assert item["date_min"] is item["date_max"] is None
    assert item["columns"] == ["id", "extra"]


def test_one_fragment_without_key_columns_nulls_the_key_totals(tmp_path):
    write_csv(tmp_path, "osha_violation1.csv", [ROW])
    write_csv(
        tmp_path,
        "osha_violation2.csv",
        [["0317000001", "2024-01-02"]],
        ["activity_nr", "issuance_date"],
    )
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["files_missing_key_columns"] == ["osha_violation2.csv"]
    assert result["files_missing_date_column"] == []
    assert result["keyed_rows"] is result["unique_candidate_keys"] is None
    assert result["rows"] == 2
    first, second = result["files"]
    assert first["keyed_rows"] == 1
    assert second["missing_key_columns"] == ["citation_id"]
    assert second["keyed_rows"] is None
    assert second["date_min"] == "2024-01-02"


def test_all_columns_participate_in_exact_row_identity(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [ROW, violation(current_penalty="1")])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["unique_rows"] == 2
    assert result["unique_candidate_keys"] == 1


def test_empty_fragment_has_explicit_zero_counts(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["rows"] == result["unique_rows"] == 0
    assert result["keyed_rows"] == result["unique_candidate_keys"] == 0
    assert result["files"][0]["date_min"] is None


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
    "content, encoding, error",
    [
        (b"id,extra\na\n", "latin-1", ValueError),
        (b"", "latin-1", ValueError),
        (b"id,extra\na,\xff\n", "utf-8", UnicodeDecodeError),
    ],
)
def test_failed_later_fragment_leaves_index_incomplete(
    tmp_path, content, encoding, error
):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    (tmp_path / "osha_violation3.csv").write_bytes(content)
    index_db = tmp_path / "index.sqlite"
    with pytest.raises(error):
        profile(tmp_path, index_db, encoding=encoding)
    with sqlite3.connect(index_db) as index:
        assert index.execute("SELECT complete FROM meta").fetchall() == [(0,)]
        assert index.execute("SELECT COUNT(*) FROM exact_rows").fetchone() == (1,)


def test_dol_latin1_bytes_decode_by_default(tmp_path):
    header = ",".join(VIOLATION_FIELDS).encode("ascii")
    record = ",".join(violation(hazsub1="café", load_dt="°")).encode("latin-1")
    (tmp_path / "osha_violation0.csv").write_bytes(header + b"\r\n" + record + b"\r\n")
    index_db = tmp_path / "index.sqlite"
    result = profile(tmp_path, index_db)
    assert result["encoding"] == "latin-1"
    assert result["rows"] == result["keyed_rows"] == 1
    with sqlite3.connect(index_db) as index:
        stored = json.loads(
            index.execute("SELECT signature FROM exact_rows").fetchone()[0]
        )
    assert stored["hazsub1"] == "café"
    assert stored["load_dt"] == "°"


def test_utf8_byte_order_mark_needs_an_explicit_encoding(tmp_path):
    write_csv(tmp_path, "osha_violation0.csv", [ROW], encoding="utf-8-sig")
    with pytest.raises(ValueError, match="byte-order mark"):
        profile(tmp_path, tmp_path / "latin.sqlite")
    result = profile(tmp_path, tmp_path / "utf8.sqlite", encoding="utf-8-sig")
    assert result["encoding"] == "utf-8-sig"
    assert result["files"][0]["columns"] == VIOLATION_FIELDS
    assert result["keyed_rows"] == 1


def test_unsupported_encoding_is_rejected(tmp_path):
    write_csv(tmp_path, "osha_violation0.csv", [ROW])
    with pytest.raises(ValueError, match="Unsupported encoding"):
        profile(tmp_path, tmp_path / "index.sqlite", encoding="cp1252")
    assert not (tmp_path / "index.sqlite").exists()


@pytest.mark.parametrize("value", ["２０２４-０１-０２", "٢٠٢٤-٠١-٠٢"])
def test_non_ascii_dates_are_rejected_before_calendar_parsing(monkeypatch, value):
    module = load_module()

    class AsciiCalendar:
        @staticmethod
        def fromisoformat(value):
            pytest.fail("Non-ASCII dates must fail the format gate")

    monkeypatch.setattr(module, "date", AsciiCalendar)
    item = {"invalid_dates": 0}
    module._observe_date(item, value)
    assert item["invalid_dates"] == 1


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


def run_cli(tmp_path, *options):
    assert SCRIPT.is_file(), "The planned inventory script does not exist"
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--raw-dir",
            str(tmp_path),
            "--index-db",
            str(tmp_path / "index.sqlite"),
            *options,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_outputs_json_without_absolute_paths(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    completed = run_cli(tmp_path)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["rows"] == 1
    assert result["index_complete"] is True
    assert result["index_db"] == "index.sqlite"
    assert str(tmp_path) not in completed.stdout


def test_cli_selects_table_and_encoding(tmp_path):
    write_csv(tmp_path, "osha_violation2.csv", [ROW])
    write_csv(
        tmp_path,
        "osha_violation_event2.csv",
        [["0317000001", "01001A", "P", "Z", "2024-03-01", "0", "", "S", "", ""]],
        EVENT_FIELDS,
        encoding="utf-8-sig",
    )
    completed = run_cli(
        tmp_path, "--table", "violation_event", "--encoding", "utf-8-sig"
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["table"] == "violation_event"
    assert result["encoding"] == "utf-8-sig"
    assert [item["name"] for item in result["files"]] == ["osha_violation_event2.csv"]
    assert result["files"][0]["date_min"] == "2024-03-01"


def test_cli_missing_inputs_cannot_report_success(tmp_path):
    completed = run_cli(tmp_path)
    assert completed.returncode != 0
    assert not completed.stdout
    assert "No OSHA violation fragments" in completed.stderr


def test_multiline_values_and_leading_zero_ids_are_preserved(tmp_path):
    row = violation(hazsub1='comma, quote " and\nlatin-1: café')
    write_csv(tmp_path, "osha_violation2.csv", [row])
    result = profile(tmp_path, tmp_path / "index.sqlite")
    assert result["rows"] == 1
    with sqlite3.connect(tmp_path / "index.sqlite") as index:
        record = index.execute("SELECT signature FROM exact_rows").fetchone()[0]
        key = index.execute("SELECT signature FROM candidate_keys").fetchone()[0]
    assert json.loads(record) == dict(zip(VIOLATION_FIELDS, row))
    assert json.loads(key) == ["0317000001", "01001A"]


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
