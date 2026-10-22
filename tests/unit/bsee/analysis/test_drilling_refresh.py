"""Offline tests using synthetic rows; identifiers do not describe real wells."""

import copy
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.error import URLError

import pytest

from worldenergydata.bsee.analysis.drilling_refresh import (
    NetworkBlocked,
    QualityError,
    analyse,
    fetch,
    record_download,
    write_data_quality,
)

FIXTURE = Path(__file__).parent / "fixtures" / "drilling_refresh"
CONFIG = Path("config/analysis/bsee/drilling_refresh.json")


@pytest.fixture
def setup_run(tmp_path):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["data_dir"] = str(tmp_path / "data")
    config["output_dir"] = str(tmp_path / "outputs")
    config["population_csv"] = str(FIXTURE / "boreholes.csv")
    config["synthetic"] = True
    config["sources"] = config["sources"][:1]
    config["sources"][0]["url"] = "https://example.org/synthetic.zip"
    data = Path(config["data_dir"])
    data.mkdir()
    source = config["sources"][0]
    path = data / source["file"]
    with zipfile.ZipFile(path, "w") as archive:
        for table, spec in config["tables"].items():
            archive.writestr(
                spec["member"] + ".txt", (FIXTURE / f"{table}.csv").read_bytes()
            )
    record_download(config, source, path, "2026-01-01T00:00:00Z", 200)
    return config


def rewrite_table(config, table, change):
    spec = config["tables"][table]
    source = config["sources"][0]
    path = Path(config["data_dir"]) / source["file"]
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    name = spec["member"] + ".txt"
    rows = list(csv.DictReader(io.StringIO(members[name].decode("utf-8"))))
    change(rows)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    members[name] = stream.getvalue().encode("utf-8")
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    record_download(config, source, path, "2026-01-01T00:00:00Z", 200)


def test_synthetic_headlines_and_overlap_basis(setup_run):
    result = analyse(setup_run)
    assert result["synthetic"] is True
    assert result["headlines"]["calendar_median_days"] == 9.5
    assert result["headlines"]["bore_drilling_days_sum"] == 21
    assert result["headlines"]["well_drilling_days_union"] == 14
    assert result["headlines"]["completion_days_sum"] == 7
    assert result["sources"][0]["downloaded_at"] == "2026-01-01T00:00:00Z"
    output = Path(setup_run["output_dir"])
    for chart in ("calendar", "completion", "drilldown", "rig_day_basis", "activity"):
        assert (output / f"{chart}.csv").is_file()
        headline = json.loads((output / f"{chart}.json").read_text(encoding="utf-8"))
        assert headline["sources"][0]["sha256"]
        assert headline["qa_status"] == "pass"
    assert "calendar_days [day]" in (output / "calendar.csv").read_text(
        encoding="utf-8"
    )


def test_bsee_timestamps_keep_calendar_year_and_inclusive_days(setup_run):
    rewrite_table(
        setup_run,
        "war",
        lambda rows: rows[0].update(
            WAR_START_DT="1/1/2020 12:01:00 AM", WAR_END_DT="1/7/2020 11:59:00 AM"
        ),
    )
    result = analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 21
    output = Path(setup_run["output_dir"])
    rows = list(csv.DictReader((output / "activity.csv").open(encoding="utf-8")))
    assert {row["year [year]"] for row in rows} == {"2020"}


@pytest.mark.parametrize(
    "table,change,reason",
    [
        ("war", lambda r: r.append(copy.deepcopy(r[0])), "duplicate_keys"),
        ("war", lambda r: r[0].update(SN_WAR=""), "missing_keys"),
        ("war", lambda r: r[0].update(API_WELL_NUMBER="bad"), "invalid_api"),
        ("war", lambda r: r[0].update(WAR_START_DT=""), "missing_dates"),
        ("war", lambda r: r[0].update(WAR_START_DT="02/30/2020"), "invalid_dates"),
        ("war", lambda r: r[0].update(WAR_END_DT="12/31/2019"), "reversed_dates"),
        ("war", lambda r: r[0].update(WAR_END_DT="12/31/2020"), "implausible_span"),
        ("activity", lambda r: r[0].update(SN_WAR="999"), "orphan_keys"),
        ("activity", lambda r: r.pop(), "unattributed_reports"),
        ("boreholes", lambda r: r.pop(), "population_coverage"),
    ],
)
def test_fail_closed(setup_run, table, change, reason):
    rewrite_table(setup_run, table, change)
    with pytest.raises(QualityError):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "not-evaluated"
    assert reason in str(qa["failures"])
    assert {path.name for path in output.glob("*.csv")} == {"data_quality.csv"}
    quality = json.loads((output / "data_quality.json").read_text(encoding="utf-8"))
    assert any(reason in row["defect"] for row in quality["rows"])
    assert all(row["rule"] == "excluded" for row in quality["rows"])
    assert not (output / "activity.json").exists()
    assert not (output / "headlines.json").exists()


@pytest.mark.parametrize(
    "setting,value,reason",
    [("unit", "hour", "unit_check"), ("min_rows", 999, "row_count")],
)
def test_contract_failure(setup_run, setting, value, reason):
    setup_run["tables"]["war"][setting] = value
    with pytest.raises(QualityError):
        analyse(setup_run)
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert reason in str(qa["failures"])


def test_digest_mismatch_cannot_publish(setup_run):
    path = Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(QualityError, match="digest"):
        analyse(setup_run)
    assert not (Path(setup_run["output_dir"]) / "headlines.json").exists()


def test_existing_outputs_are_never_overwritten(setup_run):
    analyse(setup_run)
    with pytest.raises(FileExistsError):
        analyse(setup_run)


def test_fetch_records_exact_bytes(setup_run):
    original = Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    payload = original.read_bytes()
    setup_run["data_dir"] = str(Path(setup_run["data_dir"]).parent / "fresh")

    class Response(io.BytesIO):
        status = 200

    manifest = fetch(setup_run, opener=lambda url, timeout: Response(payload))
    entry = manifest["files"][0]
    assert entry["size_bytes"] == len(payload)
    assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
    assert entry["downloaded_at"].endswith("Z")


def test_fetch_resume_does_not_repeat_completed_download(setup_run):
    def unavailable(*args, **kwargs):
        pytest.fail("completed source was fetched again")

    fetch(setup_run, opener=unavailable)


def test_network_failure_is_explicit(setup_run):
    setup_run["data_dir"] += "-unreachable"

    def unavailable(*args, **kwargs):
        raise URLError("offline")

    with pytest.raises(NetworkBlocked, match="BLOCKED-NETWORK"):
        fetch(setup_run, opener=unavailable)


def test_html_response_is_not_data(setup_run):
    path = Path(setup_run["data_dir"]) / "error.zip"
    path.write_bytes(b"<html>unavailable</html>")
    with pytest.raises(QualityError, match="ZIP"):
        record_download(
            setup_run, setup_run["sources"][0], path, "2026-01-01T00:00:00Z", 200
        )


def test_missing_source_column_is_not_evaluated(setup_run):
    rewrite_table(
        setup_run, "war", lambda rows: [row.pop("WAR_END_DT") for row in rows]
    )
    with pytest.raises(QualityError, match="columns"):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    assert (
        json.loads((output / "qa.json").read_text(encoding="utf-8"))["status"]
        == "not-evaluated"
    )
    assert not list(output.glob("*.csv"))


def test_missing_phase_is_null_and_pnd_stays_separate(setup_run):
    rewrite_table(
        setup_run, "activity", lambda rows: rows[2].update(WELL_ACTIVITY_CD="PND")
    )
    result = analyse(setup_run)
    assert result["headlines"]["completion_days_sum"] is None
    rows = list(
        csv.DictReader(
            (Path(setup_run["output_dir"]) / "drilldown.csv").open(encoding="utf-8")
        )
    )
    assert rows[0]["completion_days [day]"] == ""
    assert float(rows[0]["pnd_days [day]"]) == 7


def test_missing_activity_code_is_rejected(setup_run):
    rewrite_table(
        setup_run, "activity", lambda rows: rows[0].update(WELL_ACTIVITY_CD="")
    )
    with pytest.raises(QualityError):
        analyse(setup_run)


def test_ambiguous_archive_member_is_rejected(setup_run):
    path = Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr(
            "duplicate/mv_war_main.txt", (FIXTURE / "war.csv").read_bytes()
        )
    record_download(
        setup_run, setup_run["sources"][0], path, "2026-01-01T00:00:00Z", 200
    )
    with pytest.raises(QualityError, match="ambiguous"):
        analyse(setup_run)


def test_retained_qa_receipt_matches_manifest_and_workflow():
    directory = Path("docs/modules/bsee/analysis/drilling_refresh")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    qa = json.loads((directory / "qa.json").read_text(encoding="utf-8"))
    assert qa["sources"] == manifest["files"]
    assert qa["status"] == "not-evaluated"
    assert qa["failures"]
    # This immutable receipt identifies the implementation used for that vintage.
    assert len(qa["workflow_sha256"]) == 64


def test_synthetic_quality_table_covers_retained_defect_types(setup_run):
    rewrite_table(
        setup_run,
        "war",
        lambda rows: (
            rows[0].update(WAR_END_DT="12/31/2019"),
            rows[1].update(WAR_END_DT="12/31/2020"),
        ),
    )
    rewrite_table(
        setup_run,
        "activity",
        lambda rows: (rows[0].update(WELL_ACTIVITY_CD=""), rows.pop()),
    )
    rewrite_table(
        setup_run,
        "boreholes",
        lambda rows: (
            rows[0].update(WELL_SPUD_DATE="", TOTAL_DEPTH_DATE=""),
            rows.pop(),
        ),
    )
    with pytest.raises(QualityError):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    quality = json.loads((output / "data_quality.json").read_text(encoding="utf-8"))
    assert quality["synthetic"] is True
    counts = {row["defect"]: row["count"] for row in quality["rows"]}
    assert counts == {
        "war.reversed_dates": 1,
        "war.implausible_span": 1,
        "activity.missing_keys": 1,
        "boreholes.missing_dates": 2,
        "unattributed_reports": 1,
        "population_coverage": 1,
    }
    with (output / "data_quality.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["defect", "count", "example_id", "rule", "reason"]
        rows = list(reader)
    assert len(rows) == len(counts)
    assert all(row["example_id"].isdigit() for row in rows)
    text = (output / "public_data_quality.txt").read_text(encoding="utf-8")
    assert text.startswith("Public data quality\n")
    for row in quality["rows"]:
        assert f"{row['defect']}: {row['count']}" in text
        account = quality["accounting"][row["defect"]]
        assert account["excluded"] + account["corrected"] == row["count"]
    assert not (output / "headlines.json").exists()
    assert not (output / "calendar.csv").exists()


@pytest.mark.parametrize(
    "outcomes",
    [[], ["2"], ["1", "1"]],
)
def test_synthetic_accounting_fails_closed(tmp_path, outcomes):
    defects = {"war.reversed_dates": ["1"]}
    with pytest.raises(QualityError, match="accounting"):
        write_data_quality(
            tmp_path, defects, {"war.reversed_dates": outcomes}, synthetic=True
        )
    assert not list(tmp_path.iterdir())


def test_synthetic_accounting_rejects_free_text_identifier(tmp_path):
    defects = {"war.reversed_dates": ["untrusted source text"]}
    with pytest.raises(QualityError, match="public record key"):
        write_data_quality(tmp_path, defects, defects, synthetic=True)
    assert not list(tmp_path.iterdir())


def test_passing_rows_are_the_only_statistics_input(setup_run):
    result = analyse(setup_run)
    output = Path(setup_run["output_dir"])
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    quality = json.loads((output / "data_quality.json").read_text(encoding="utf-8"))
    workflow = Path(
        "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/drilling_refresh.py"
    )
    assert qa["workflow_sha256"] == hashlib.sha256(workflow.read_bytes()).hexdigest()
    assert qa["failures"] == []
    assert quality["rows"] == []
    assert "No source defects were detected" in result["public_data_quality"]
    assert result["qa_status"] == "pass"


def test_synthetic_exclusion_prevents_statistics_computation(setup_run, monkeypatch):
    from worldenergydata.bsee.analysis import drilling_refresh

    def forbidden(*args, **kwargs):
        pytest.fail("excluded source records reached statistics")

    monkeypatch.setattr(drilling_refresh, "_products", forbidden)
    rewrite_table(setup_run, "war", lambda rows: rows[0].update(WAR_START_DT=""))
    with pytest.raises(QualityError):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    assert {path.name for path in output.iterdir()} == {
        "qa.json",
        "data_quality.csv",
        "data_quality.json",
        "public_data_quality.txt",
    }


def test_statistics_reject_quality_defects_before_importing_dependencies():
    from worldenergydata.bsee.analysis.drilling_refresh import _products

    with pytest.raises(QualityError, match="exclude all statistics"):
        _products({}, {}, set(), [], {"rows": [{"defect": "war.reversed_dates"}]})


@pytest.mark.parametrize(
    "excluded", [{}, {"war.reversed_dates": ["1"], "extra": ["2"]}]
)
def test_synthetic_accounting_requires_matching_classes(tmp_path, excluded):
    with pytest.raises(QualityError, match="accounting"):
        write_data_quality(
            tmp_path, {"war.reversed_dates": ["1"]}, excluded, synthetic=True
        )
    assert not list(tmp_path.iterdir())


def test_retained_public_quality_accounting_and_provenance():
    directory = Path("docs/modules/bsee/analysis/drilling_refresh/quality")
    qa = json.loads((directory / "qa.json").read_text(encoding="utf-8"))
    quality = json.loads((directory / "data_quality.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    workflow = Path(
        "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/drilling_refresh.py"
    )
    assert qa["workflow_sha256"] == hashlib.sha256(workflow.read_bytes()).hexdigest()
    assert qa["sources"] == manifest["files"]
    assert qa["data_quality"] == quality
    assert quality["synthetic"] is False
    assert qa["status"] == "not-evaluated"
    expected = {
        f"{name}.{check}": count
        for name, table in qa["tables"].items()
        for check, count in table["checks"].items()
        if count
    }
    expected.update({key: count for key, count in qa["joins"].items() if count})
    assert {row["defect"]: row["count"] for row in quality["rows"]} == expected
    with (directory / "data_quality.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [
        {key: str(value) for key, value in row.items()} for row in quality["rows"]
    ]
    for row in quality["rows"]:
        assert quality["accounting"][row["defect"]] == {
            "excluded": row["count"],
            "corrected": 0,
        }
        assert row["example_id"].isdigit()
    assert (directory / "public_data_quality.txt").read_text(
        encoding="utf-8"
    ) == quality["public_data_quality"]


def test_synthetic_qa_count_disagreement_withholds_statistics(setup_run, monkeypatch):
    from worldenergydata.bsee.analysis import drilling_refresh

    original = drilling_refresh._quality

    def inconsistent(*args):
        qa = original(*args)
        qa["tables"]["war"]["checks"]["missing_dates"] = 1
        return qa

    monkeypatch.setattr(drilling_refresh, "_quality", inconsistent)
    with pytest.raises(QualityError, match="accounting"):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    assert {path.name for path in output.iterdir()} == {"qa.json"}
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "not-evaluated"
    assert "accounting" in str(qa["failures"])
    assert qa["criterion"]
    assert qa["basis"] == "DRL+COM"


def test_synthetic_missing_public_example_is_not_invented(setup_run):
    rewrite_table(
        setup_run, "boreholes", lambda rows: rows[0].update(API_WELL_NUMBER="bad")
    )
    with pytest.raises(QualityError, match="public record key"):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    assert {path.name for path in output.iterdir()} == {"qa.json"}
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    assert "public record key" in str(qa["failures"])
