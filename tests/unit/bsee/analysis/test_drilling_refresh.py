"""Offline tests using synthetic rows; identifiers do not describe real wells."""

import copy
import csv
import hashlib
import io
import json
import zipfile
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import URLError

import pytest

from worldenergydata.bsee.analysis import drilling_refresh as refresh
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
    config["data_dir"] = (tmp_path / "data").as_posix()
    config["output_dir"] = (tmp_path / "outputs").as_posix()
    config["population_csv"] = (FIXTURE / "boreholes.csv").as_posix()
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
    # Calendar: (13 + 6) / 2 = 9.5 d. DRL bore sums: 14 + 7 = 21 d.
    # The second bore overlaps the first by 7 d: the API10 union is 14 d.
    # COM spans Jan 15 through Jan 21 inclusive: 7 d.
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
        assert "qa_status" not in headline
        assert headline["receipt"] == "qa.json"
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
        ("activity", lambda r: r[0].update(SN_WAR="999"), "orphan_keys"),
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
    if table == "war" and reason == "missing_keys":
        assert "public record key" in str(qa["failures"])
        assert {path.name for path in output.iterdir()} == {"qa.json"}
        return
    assert {path.name for path in output.glob("*.csv")} == {"data_quality.csv"}
    quality = json.loads((output / "data_quality.json").read_text(encoding="utf-8"))
    assert any(reason in row["defect"] for row in quality["rows"])
    assert all(row["rule"] == "reported" for row in quality["rows"])
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
    setup_run["data_dir"] = (Path(setup_run["data_dir"]).parent / "fresh").as_posix()

    class Response(io.BytesIO):
        status = 200

        def geturl(self):
            return setup_run["sources"][0]["url"]

    manifest = fetch(setup_run, opener=lambda url, timeout: Response(payload))
    entry = manifest["files"][0]
    assert entry["size_bytes"] == len(payload)
    assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
    assert entry["downloaded_at"].endswith("Z")
    assert entry["resolved_url"] == setup_run["sources"][0]["url"]


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


def test_missing_activity_code_retains_unattributed_coverage(setup_run):
    rewrite_table(
        setup_run, "activity", lambda rows: rows[0].update(WELL_ACTIVITY_CD="")
    )
    result = analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 14
    assert result["per_bore"]["990000000100"]["reports_without_code"] == 1


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
    result = analyse(setup_run)
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
        assert account["reported"] == row["count"]
    assert result["headlines"]["calendar_median_days"] is None
    assert result["headlines"]["bore_drilling_days_sum"] is None
    assert result["coverage"]["status"] == "partial"


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
    assert qa["workflow_sha256"] == refresh._workflow_digest(workflow)
    assert qa["failures"] == []
    assert qa["headlines"] == result["headlines"]
    assert qa["coverage"] == result["coverage"]
    assert quality["rows"] == []
    assert "No source defects were detected" in result["public_data_quality"]
    assert result["qa_status"] == "pass"


def test_synthetic_exclusion_prevents_statistics_computation(setup_run, monkeypatch):
    from worldenergydata.bsee.analysis import drilling_refresh

    def forbidden(*args, **kwargs):
        pytest.fail("excluded source records reached statistics")

    monkeypatch.setattr(drilling_refresh, "_products", forbidden)
    rewrite_table(setup_run, "war", lambda rows: rows.append(copy.deepcopy(rows[0])))
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
    assert qa["workflow_sha256"] == refresh._workflow_digest(workflow), (
        "Rebuild with python -m worldenergydata.bsee.analysis.drilling_refresh "
        "config/analysis/bsee/drilling_refresh.json using new data and output directories"
    )
    assert qa["sources"] == manifest["files"]
    assert qa["data_quality"] == quality
    assert quality["synthetic"] is False
    assert qa["status"] == "pass"
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
        assert quality["accounting"][row["defect"]] == {"reported": row["count"]}
        assert row["example_id"].lstrip("-").isdigit()
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


def test_unselected_row_defects_do_not_block_population(setup_run):
    rewrite_table(
        setup_run,
        "war",
        lambda rows: rows.append(
            dict(
                SN_WAR="5",
                API_WELL_NUMBER="990000000200",
                WAR_START_DT="01/07/2020",
                WAR_END_DT="01/01/2020",
            )
        ),
    )
    result = refresh.analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 21
    assert result["headlines"]["activity_code_records"] == 4
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["tables"]["war"]["checks"]["reversed_dates"] == 1
    assert qa["population_tables"]["war"]["checks"]["reversed_dates"] == 0
    assert qa["status"] == "pass"


def test_undated_bore_has_null_calendar_result(setup_run):
    rewrite_table(
        setup_run, "boreholes", lambda rows: rows[0].update(WELL_SPUD_DATE="")
    )
    result = refresh.analyse(setup_run)
    assert result["headlines"]["calendar_median_days"] == 6
    assert result["headlines"]["bore_drilling_days_sum"] == 21
    assert result["coverage"]["selected_bores"] == 2
    assert result["coverage"]["calendar_evaluated_bores"] == 1
    assert result["coverage"]["status"] == "partial"
    with (Path(setup_run["output_dir"]) / "calendar.csv").open(
        encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["calendar_days [day]"] == ""
    assert "missing_dates" in rows[0]["status [category]"]


@pytest.mark.parametrize(
    "change",
    [
        dict(WAR_START_DT=""),
        dict(WAR_START_DT="02/30/2020"),
        dict(WAR_END_DT="12/31/2019"),
        dict(WAR_END_DT="12/31/2020"),
    ],
)
def test_invalid_population_interval_is_not_evaluated_per_bore(setup_run, change):
    rewrite_table(setup_run, "war", lambda rows: rows[0].update(**change))
    result = refresh.analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 7
    assert result["headlines"]["well_drilling_days_union"] is None
    assert result["headlines"]["activity_code_records"] == 1
    assert result["coverage"]["drilling_evaluated_bores"] == 1
    assert result["coverage"]["status"] == "partial"
    with (Path(setup_run["output_dir"]) / "drilldown.csv").open(
        encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["drilling_days [day]"] == ""
    assert "not-evaluated" in rows[0]["days_status [category]"]


def test_unattributed_week_preserves_bore_coverage(setup_run):
    rewrite_table(setup_run, "activity", lambda rows: rows.pop())
    result = refresh.analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 14
    with (Path(setup_run["output_dir"]) / "drilldown.csv").open(
        encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[1]["reports_without_code [record]"] == "1"
    assert rows[1]["drilling_days [day]"] == ""


def test_negative_war_key_is_reported_without_bore_substitution(setup_run):
    rewrite_table(setup_run, "war", lambda rows: rows[0].update(SN_WAR="-1"))
    rewrite_table(setup_run, "activity", lambda rows: rows.pop(0))
    refresh.analyse(setup_run)
    quality = json.loads(
        (Path(setup_run["output_dir"]) / "data_quality.json").read_text(
            encoding="utf-8"
        )
    )
    row = next(
        row for row in quality["rows"] if row["defect"] == "unattributed_reports"
    )
    assert row["example_id"] == "-1"
    assert row["rule"] == "reported"
    assert quality["accounting"]["unattributed_reports"] == {"reported": 1}


def test_invalid_war_key_cannot_fall_back_to_bore_key():
    with pytest.raises(refresh.QualityError, match="public record key"):
        refresh._public_key(dict(SN_WAR="invalid", API_WELL_NUMBER="990000000100"))


def test_exclusive_ninety_day_span_matches_canonical_boundary(setup_run):
    rewrite_table(
        setup_run, "war", lambda rows: rows[0].update(WAR_END_DT="03/31/2020")
    )
    result = refresh.analyse(setup_run)
    # Leap-year Jan 1 to Mar 31 is 90 exclusive days; inclusive union is 91.
    # The second bore contributes seven days: 91 + 7 = 98.
    assert result["headlines"]["bore_drilling_days_sum"] == 98


def test_configured_date_range_is_enforced(setup_run):
    setup_run["tables"]["war"].update(date_min="1900-01-01", date_max="2026-12-31")
    rewrite_table(
        setup_run,
        "war",
        lambda rows: rows[0].update(WAR_START_DT="01/01/2099", WAR_END_DT="01/07/2099"),
    )
    result = refresh.analyse(setup_run)
    assert result["headlines"]["bore_drilling_days_sum"] == 7
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["tables"]["war"]["checks"]["out_of_range_dates"] == 2
    with (Path(setup_run["output_dir"]) / "drilldown.csv").open(
        encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["drilling_days [day]"] == ""
    assert "out_of_range_dates" in rows[0]["days_status [category]"]


@pytest.mark.parametrize(
    "table, source_date, expected",
    [
        ("war", "04/06/1988", 1),
        ("war", "04/07/1988", 0),
        ("war", "04/08/1988", 0),
        ("war", "10/16/2026", 0),
        ("war", "10/17/2026", 0),
        ("war", "10/18/2026", 1),
        ("boreholes", "05/09/1947", 1),
        ("boreholes", "05/10/1947", 0),
        ("boreholes", "05/11/1947", 0),
        ("boreholes", "06/09/2026", 0),
        ("boreholes", "06/10/2026", 0),
        ("boreholes", "06/11/2026", 1),
    ],
)
def test_date_bounds_include_each_endpoint_independently(
    setup_run, table, source_date, expected
):
    spec = setup_run["tables"][table]
    assert (
        spec["dates"]
        == {
            "war": ["WAR_START_DT", "WAR_END_DT"],
            "boreholes": ["WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"],
        }[table]
    )
    # Vary one date field at a time; every other required date stays in range.
    for column in spec["dates"]:
        row = {
            key: "1" if key == "SN_WAR" else "990000000100"
            for key in spec["keys"] + spec["required"]
        }
        row.update({key: "01/01/2020" for key in spec["dates"]})
        row[column] = source_date
        qa = refresh._table_qa([row], spec, "day")
        assert qa["checks"]["out_of_range_dates"] == expected, column


@pytest.mark.parametrize("table", ["war", "boreholes"])
def test_date_bounds_record_a_basis_beside_each_criterion(table):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    spec = config["tables"][table]
    manifest = json.loads(
        Path(
            "docs/modules/bsee/analysis/drilling_refresh/quality/manifest.json"
        ).read_text(encoding="utf-8")
    )
    for endpoint in ("date_min", "date_max"):
        basis = spec[f"{endpoint}_basis"]
        reference, pointer = basis["reference"].split("#", 1)
        evidence = json.loads(Path(reference).read_text(encoding="utf-8"))
        assert evidence["sources"] == manifest["files"]
        assert basis["archive_sha256"] == manifest["files"][0]["sha256"]
        for key in pointer.strip("/").split("/"):
            evidence = evidence[key]
        assert evidence == spec[endpoint]
        assert spec[endpoint] in basis["derivation"]


def test_workflow_digest_ignores_checkout_line_endings(tmp_path):
    lf, crlf = tmp_path / "lf.py", tmp_path / "crlf.py"
    lf.write_text("value = 1\n", encoding="utf-8", newline="\n")
    crlf.write_bytes(b"value = 1\r\n")
    assert refresh._workflow_digest(lf) == hashlib.sha256(lf.read_bytes()).hexdigest()
    assert refresh._workflow_digest(crlf) == refresh._workflow_digest(lf)
    assert refresh._digest(crlf) != refresh._digest(lf)


def test_http_incomplete_read_is_a_controlled_failure(setup_run):
    setup_run["data_dir"] += "-incomplete"

    class Response(io.BytesIO):
        status = 200

        def geturl(self):
            return setup_run["sources"][0]["url"]

        def read(self, *args):
            raise IncompleteRead(b"", 100)

    with pytest.raises(refresh.NetworkBlocked):
        refresh.fetch(setup_run, opener=lambda *args, **kwargs: Response())
    assert not (Path(setup_run["data_dir"]) / "manifest.json").exists()
    assert (Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]).exists()


def test_raw_archive_digest_keeps_crlf_bytes(setup_run):
    path = Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("line_endings.txt", b"first\r\nsecond\r\n")
    manifest = refresh.record_download(
        setup_run, setup_run["sources"][0], path, "2026-01-01T00:00:00Z", 200
    )
    assert (
        manifest["files"][0]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("offset", [-10, 10])
def test_content_length_mismatch_keeps_partial_file_without_provenance(
    setup_run, offset
):
    payload = (
        Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    ).read_bytes()
    setup_run["data_dir"] += "-mismatch"

    class Response(io.BytesIO):
        status = 200
        headers = {"content-length": str(len(payload) + offset)}

        def geturl(self):
            return setup_run["sources"][0]["url"]

    with pytest.raises(refresh.NetworkBlocked, match="Content-Length"):
        refresh.fetch(setup_run, opener=lambda *args, **kwargs: Response(payload))
    assert not (Path(setup_run["data_dir"]) / "manifest.json").exists()
    assert (Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]).exists()


def test_short_valid_zip_is_rejected_by_content_length(setup_run):
    payload = (
        Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    ).read_bytes()
    setup_run["data_dir"] += "-short"

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Length": str(len(payload) + 10)}

        def geturl(self):
            return setup_run["sources"][0]["url"]

    with pytest.raises(refresh.NetworkBlocked, match="Content-Length"):
        refresh.fetch(setup_run, opener=lambda *args, **kwargs: Response(payload))
    assert not (Path(setup_run["data_dir"]) / "manifest.json").exists()


def test_missing_configuration_is_reported_without_a_local_path(tmp_path, capsys):
    path = tmp_path / "missing.json"
    assert refresh.main([path.as_posix()]) == 1
    text = capsys.readouterr().out
    assert "configuration" in text
    assert path.as_posix() not in text


def test_missing_population_file_does_not_export_a_local_path(setup_run):
    setup_run["population_csv"] = (
        Path(setup_run["data_dir"]) / "missing.csv"
    ).as_posix()
    with pytest.raises(QualityError):
        analyse(setup_run)
    text = (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    assert setup_run["population_csv"] not in text


@pytest.mark.parametrize("timestamp", [None, "invalid", "2026-01-01T01:00:00+01:00"])
def test_invalid_source_retrieval_time_withholds_statistics(setup_run, timestamp):
    path = Path(setup_run["data_dir"]) / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if timestamp is None:
        manifest["files"][0].pop("downloaded_at")
    else:
        manifest["files"][0]["downloaded_at"] = timestamp
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(QualityError, match="retrieval time"):
        analyse(setup_run)
    assert not (Path(setup_run["output_dir"]) / "headlines.json").exists()


@pytest.mark.parametrize("error_type", [RuntimeError, KeyError, MemoryError])
def test_product_failure_never_leaves_a_passing_receipt(
    setup_run, monkeypatch, error_type
):
    output = Path(setup_run["output_dir"])
    observed = []

    def broken(*args, **kwargs):
        observed.append(
            json.loads((output / "qa.json").read_text(encoding="utf-8"))["status"]
        )
        raise error_type("synthetic product failure")

    monkeypatch.setattr(refresh, "_products", broken)
    with pytest.raises(QualityError, match="product generation"):
        analyse(setup_run)
    assert observed == ["pending-products"]
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "not-evaluated"
    assert error_type.__name__ in str(qa["failures"])


def test_retained_phase_reasons_and_overlap_are_generated(setup_run):
    result = analyse(setup_run)
    assert (
        result["per_bore"]["990000000101"]["completion_status"] == "no_activity_coded"
    )
    assert result["phase_status_counts"]["completion"]["no_activity_coded"] == 1
    # A 21-day API12 DRL sum minus the 14-day API10 union is 7 days of overlap.
    assert result["overlap"]["drilling_days"] == 7
    assert result["overlap"]["all_war_days"] == 7
    assert result["overlap"]["wells_with_multiple_bores"] == 1
    output = Path(setup_run["output_dir"])
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    quality = json.loads((output / "data_quality.json").read_text(encoding="utf-8"))
    assert qa["phase_status_counts"] == result["phase_status_counts"]
    assert qa["overlap"] == result["overlap"]
    assert qa["data_quality"] == quality


@pytest.mark.parametrize("field", ["size_bytes", "sha256", "http_status", "file"])
def test_malformed_resume_metadata_is_a_quality_failure(setup_run, field):
    path = Path(setup_run["data_dir"]) / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["files"][0].pop(field)
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(QualityError, match="provenance|manifest"):
        fetch(setup_run)


@pytest.mark.parametrize("change", ["scheme", "host"])
def test_redirect_target_must_preserve_public_https_origin(setup_run, change):
    payload = (
        Path(setup_run["data_dir"]) / setup_run["sources"][0]["file"]
    ).read_bytes()
    setup_run["data_dir"] += "-redirect"
    url = setup_run["sources"][0]["url"]

    class Response(io.BytesIO):
        status = 200

        def geturl(self):
            return (
                url.replace("https:", "http:")
                if change == "scheme"
                else url.replace("//", "//alternate-")
            )

    with pytest.raises(NetworkBlocked, match="redirect"):
        fetch(setup_run, opener=lambda *args, **kwargs: Response(payload))
    assert not (Path(setup_run["data_dir"]) / "manifest.json").exists()


def test_blank_activity_report_key_is_a_structural_failure(setup_run):
    rewrite_table(setup_run, "activity", lambda rows: rows[0].update(SN_WAR=""))
    with pytest.raises(QualityError):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "not-evaluated"
    assert qa["tables"]["activity"]["checks"]["invalid_war"] == 1
    assert {path.name for path in output.iterdir()} == {"qa.json"}


def test_span_boundary_preserves_source_time_precision(setup_run):
    rewrite_table(
        setup_run,
        "war",
        lambda rows: rows[0].update(
            WAR_START_DT="01/01/2020 11:59:00 PM", WAR_END_DT="04/01/2020 12:01:00 AM"
        ),
    )
    result = analyse(setup_run)
    # The timestamp difference floors to 90 days, matching the canonical check.
    # Calendar-inclusive union: Jan 1 through Apr 1 = 92 days, plus 7 = 99.
    assert result["headlines"]["bore_drilling_days_sum"] == 99


def test_partial_product_write_carries_no_passing_verdict(setup_run, monkeypatch):
    original = refresh._json

    def interrupted(path, value):
        if path.name == "activity.json":
            raise OSError("synthetic write failure")
        original(path, value)

    monkeypatch.setattr(refresh, "_json", interrupted)
    with pytest.raises(QualityError, match="product generation"):
        analyse(setup_run)
    output = Path(setup_run["output_dir"])
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    chart = json.loads((output / "calendar.json").read_text(encoding="utf-8"))
    assert qa["status"] == "not-evaluated"
    assert "qa_status" not in chart
    assert chart["receipt"] == "qa.json"


def test_csv_phase_gaps_have_reasons(setup_run):
    analyse(setup_run)
    with (Path(setup_run["output_dir"]) / "drilldown.csv").open(
        encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[1]["completion_days [day]"] == ""
    assert rows[1]["completion_status [category]"] == "no_activity_coded"


def test_absent_war_marks_the_bore_and_sibling_union_not_evaluated(setup_run):
    rewrite_table(
        setup_run, "war", lambda rows: rows.__setitem__(slice(None), rows[-1:])
    )
    rewrite_table(
        setup_run, "activity", lambda rows: rows.__setitem__(slice(None), rows[-1:])
    )
    result = analyse(setup_run)
    assert result["per_bore"]["990000000100"]["rig"] == ["missing_war"]
    assert result["headlines"]["bore_drilling_days_sum"] == 7
    assert result["headlines"]["well_drilling_days_union"] is None
    output = Path(setup_run["output_dir"])
    with (output / "rig_day_basis.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["drilling_days_union [day]"] == ""
    assert "missing_war" in rows[0]["drilling_status [category]"]
    assert result["overlap"]["evaluated_wells"] == 0


@pytest.mark.parametrize("code", ["NONE", "nan"])
def test_missing_code_sentinels_share_the_canonical_rule(setup_run, code):
    rewrite_table(
        setup_run, "activity", lambda rows: rows[-1].update(WELL_ACTIVITY_CD=code)
    )
    result = analyse(setup_run)
    assert result["headlines"]["activity_code_records"] == 3
    bore = result["per_bore"]["990000000101"]
    assert bore["reports_without_code"] == 1
    assert bore["drilling_status"] == "no_activity_coded"


def test_activity_tokens_use_the_canonical_case(setup_run):
    rewrite_table(
        setup_run, "activity", lambda rows: rows[0].update(WELL_ACTIVITY_CD="drl")
    )
    analyse(setup_run)
    with (Path(setup_run["output_dir"]) / "activity.csv").open(
        encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert {row["activity_code [token]"] for row in rows} == {"DRL", "COM"}


@pytest.mark.parametrize("failure", ["date_bound", "csv_field"])
def test_source_stage_failures_always_leave_a_receipt(setup_run, failure):
    limit = csv.field_size_limit()
    try:
        if failure == "date_bound":
            setup_run["tables"]["war"]["date_min"] = None
        else:
            rewrite_table(
                setup_run, "war", lambda rows: rows[0].update(EXTRA="x" * 129)
            )
            csv.field_size_limit(128)
        with pytest.raises(QualityError, match="source evaluation"):
            analyse(setup_run)
    finally:
        csv.field_size_limit(limit)
    qa = json.loads(
        (Path(setup_run["output_dir"]) / "qa.json").read_text(encoding="utf-8")
    )
    assert qa["status"] == "not-evaluated"


def test_unsupported_basis_has_blocking_quality_text(setup_run):
    setup_run["basis"] = "unsupported"
    with pytest.raises(QualityError):
        analyse(setup_run)
    text = (Path(setup_run["output_dir"]) / "public_data_quality.txt").read_text(
        encoding="utf-8"
    )
    assert "not evaluated" in text
    assert "withheld" in text
