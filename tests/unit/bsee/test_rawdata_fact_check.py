"""Offline, hand-counted cases for the standalone BSEE raw-data example."""

import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "examples/bsee/rawdata_fact_check/count_rawdata.py"
)
SPEC = importlib.util.spec_from_file_location("count_rawdata_example", SCRIPT)
rawdata = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rawdata)


def apd(sn, api="A", **overrides):
    return {
        "SN_APD": str(sn),
        "API_WELL_NUMBER": api,
        "PERMIT_TYPE": "New Well",
        "REGION_CODE": "G",
        "REQ_SPUD_DATE": "1/1/2005",
        "RIG_TYPE_CODE": "JACKUP",
        "WATER_DEPTH": "90",
        **overrides,
    }


def write_zip(path, member, rows, fields):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member, "\ufeff" + text.getvalue())


@pytest.mark.parametrize("with_output", [False, True])
def test_reversed_years_rejected_before_fetch(
    monkeypatch, capsys, tmp_path, with_output
):
    def no_fetch(_):
        pytest.fail("invalid years reached the download step")

    monkeypatch.setattr(rawdata, "fetch", no_fetch)
    monkeypatch.setattr(sys.stdout, "reconfigure", lambda **_: None, raising=False)
    args = ["--first-year", "2006", "--last-year", "2005"]
    if with_output:
        args += ["--out", str(tmp_path / "output")]
    with pytest.raises(SystemExit) as error:
        rawdata.main(args)
    assert error.value.code == 2
    assert "--first-year must not exceed --last-year" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()


def test_blank_api_numbers_are_excluded_before_grouping():
    rows = [apd(1, ""), apd(2, "  "), apd(3)]
    assert rawdata.first_new_well_permits(rows) == [rows[2]]


def test_lowest_numeric_permit_follows_region_and_type_filters():
    rows = [
        apd(10, WATER_DEPTH="100"),
        apd(9),
        apd(1, PERMIT_TYPE="Revised New Well"),
        apd(2, REGION_CODE="P"),
        apd(3, "B", REQ_SPUD_DATE=""),
        apd(4, "B", REQ_SPUD_DATE="2/1/2005"),
    ]
    permits = rawdata.first_new_well_permits(rows)
    assert permits == [rows[1], rows[4]]
    result = rawdata.count_permits(permits, 2005, 2005)
    assert result["all"] == 1
    assert result["no_spud_date"] == 1
    assert result["water_depth"]["Jack-up"] == {
        "n": 1,
        "median_ft": 90.0,
        "min_ft": 90.0,
        "max_ft": 90.0,
    }


@pytest.mark.parametrize(
    "code,label",
    [
        ("JACKUP", "Jack-up"),
        (" drillship ", "Drillship"),
        ("SEMISUBMERSIBLE", "Semisubmersible"),
        ("DP SEMISUBMERSIBLE", "DP semisubmersible"),
        ("PLATFORM", "Platform rig"),
        ("SUBMERSIBLE", "Submersible"),
        ("BARGE RIG", "Other"),
        ("", "Other"),
        ("UNRECOGNIZED", "Other"),
    ],
)
def test_rig_labels_use_fixed_mapping(code, label):
    assert rawdata.rig_label(code) == label


def test_inclusive_year_bounds_and_unreadable_dates():
    rows = [
        apd(1, REQ_SPUD_DATE="12/31/2004"),
        apd(2, REQ_SPUD_DATE="1/1/2005", RIG_TYPE_CODE=""),
        apd(3, REQ_SPUD_DATE="12/31/2006", RIG_TYPE_CODE="BARGE RIG"),
        apd(4, REQ_SPUD_DATE="1/1/2007"),
        apd(5, REQ_SPUD_DATE="not a date"),
        apd(6, REQ_SPUD_DATE=""),
    ]
    result = rawdata.count_permits(rows, 2005, 2006)
    assert [row["total"] for row in result["by_year"]] == [1, 1]
    assert result["all"] == 2
    assert result["other_grouped"] == {"(blank)": 1, "BARGE RIG": 1}
    assert result["no_spud_date"] == 2


def test_pending_investigations_count_dates_and_undated_records():
    rows = [
        {"DATE_OCCURRED": date, "PANEL_DISTRICT": kind, "STATUS": status}
        for date, kind, status in [
            ("1/4/1995", "DISTRICT", "Complete"),
            ("7/26/2020", "PANEL", "Pending"),
            ("3/9/2024", "DISTRICT", "Pending"),
            ("4/9/2024", "DISTRICT", "Pending"),
            ("", "PANEL", "Pending"),
            ("unreadable", "DISTRICT", "Pending"),
        ]
    ]
    result = rawdata.count_investigations(rows)
    assert result["records"] == 6
    assert result["first_incident"] == (1995, 1, 4)
    assert result["last_incident"] == (2024, 4, 9)
    assert result["by_kind_and_status"] == {
        "DISTRICT Complete": 1,
        "DISTRICT Pending": 3,
        "PANEL Pending": 2,
    }
    assert result["pending_panel_incidents"] == [(2020, 7, 26)]
    assert result["pending_district_by_year"] == {2024: 2}
    assert result["pending_without_date"] == 2


def test_existing_self_test_runs_under_pytest(capsys):
    rawdata.self_test()
    assert capsys.readouterr().out == "self-test passed\n"


@pytest.mark.parametrize("members", [[], ["first/data.txt", "second/data.txt"]])
def test_archive_member_must_occur_once(tmp_path, members):
    path = tmp_path / "fixture.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, "value\n1\n")
    with pytest.raises(SystemExit, match="not found once"):
        rawdata.read_member(path, "data.txt")


@pytest.fixture
def cached_inputs(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = [
        apd(1),
        apd(2, ""),
        apd(3, "  "),
        apd(4, "", PERMIT_TYPE="Revised New Well"),
        apd(5, "", REGION_CODE="P"),
    ]
    write_zip(data_dir / "APDRawData.zip", rawdata.APD_MEMBER, rows, list(rows[0]))
    write_zip(
        data_dir / "IncInvRawData.zip",
        rawdata.INV_MEMBER,
        [],
        ["DATE_OCCURRED", "PANEL_DISTRICT", "STATUS"],
    )
    before = {path.name: path.read_bytes() for path in data_dir.iterdir()}
    return data_dir, before


def test_cached_cli_writes_matching_csv_json_and_missing_api_count(
    tmp_path, cached_inputs
):
    data_dir, before = cached_inputs
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--data-dir",
            "data",
            "--out",
            "output",
            "--first-year",
            "2005",
            "--last-year",
            "2005",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    printed = json.loads(result.stdout)
    saved = json.loads((tmp_path / "output/counts.json").read_text())
    assert saved == printed
    assert saved["permits"]["no_api_well_number"] == 2
    assert saved["permits"]["all"] == 1
    assert saved["investigations"]["records"] == 0
    with (tmp_path / "output/new-well-permits-by-rig-type.csv").open(newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == 1
    assert csv_rows[0]["year"] == "2005"
    assert csv_rows[0]["total"] == "1"
    assert csv_rows[0]["Jack-up"] == "1"
    for name, original in before.items():
        assert (data_dir / name).read_bytes() == original
        assert saved["files"][name]["sha256"] == hashlib.sha256(original).hexdigest()
        assert saved["files"][name]["retrieved_utc"] == "already in data dir"


def test_fetch_downloads_missing_files_and_reuses_cache(tmp_path, monkeypatch):
    calls = []
    payload = b"synthetic download bytes; not a source snapshot"

    def download(url, timeout):
        calls.append((url, timeout))
        return io.BytesIO(payload)

    monkeypatch.setattr(rawdata.urllib.request, "urlopen", download)
    first = rawdata.fetch(tmp_path)
    assert calls == [
        ("https://www.data.bsee.gov/Well/Files/APDRawData.zip", 300),
        ("https://www.data.bsee.gov/Other/Files/IncInvRawData.zip", 300),
    ]
    second = rawdata.fetch(tmp_path)
    assert len(calls) == 2
    for name in first:
        assert (tmp_path / name).read_bytes() == payload
        assert first[name]["sha256"] == hashlib.sha256(payload).hexdigest()
        assert first[name]["retrieved_utc"].endswith("Z")
        assert second[name]["retrieved_utc"] == "already in data dir"
