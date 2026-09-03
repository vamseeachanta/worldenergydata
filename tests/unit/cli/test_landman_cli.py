"""Focused command and JSON-envelope coverage for the Landman module CLI."""

import csv
import io
import json

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.landman import app


runner = CliRunner()


def _invoke(*args):
    return runner.invoke(app, list(args))


def _json_output(result):
    return json.loads(result.stdout)


def test_search_default_is_ownership_and_reports_resolved_provider():
    result = _invoke(
        "search", "--state", "TX", "--county", "MIDLAND", "--sample", "--format", "json"
    )
    payload = _json_output(result)
    assert result.exit_code == 0
    assert payload["status"] == "ok"
    assert payload["operation"] == "ownership"
    assert payload["requested_provider"] == "auto"
    assert payload["resolved_provider"] == "county_records"
    assert payload["source_mode"] == "sample"
    assert payload["records"]
    assert payload["failures"] == []


@pytest.mark.parametrize(
    "operation", ["leases", "title", "deeds", "mortgages", "assignments", "all"]
)
def test_each_unsupported_operation_and_all_exit_one(operation):
    result = _invoke(
        "search",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--type",
        operation,
        "--sample",
        "--format",
        "json",
    )
    payload = _json_output(result)
    assert result.exit_code == 1
    assert payload["status"] == "error"
    assert payload["requested_provider"] == "auto"
    assert payload["resolved_provider"] is None
    assert payload["failures"]
    assert all(
        row["code"] == "LANDMAN_CAPABILITY_UNAVAILABLE" for row in payload["failures"]
    )


def test_json_stdout_is_single_parseable_success_or_error_envelope():
    success = _invoke(
        "search", "--state", "TX", "--county", "MIDLAND", "--sample", "--format", "json"
    )
    failure = _invoke(
        "search",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--type",
        "title",
        "--sample",
        "--format",
        "json",
    )
    assert success.stdout.count("\n{") == 0
    assert failure.stdout.count("\n{") == 0
    assert _json_output(success)["status"] == "ok"
    assert _json_output(failure)["status"] == "error"


def test_status_and_providers_json_contract():
    for command in ("providers", "status"):
        without = _invoke(command, "--format", "json")
        with_sample = _invoke(command, "--sample", "--format", "json")
        assert without.exit_code == 0
        payload = _json_output(without)
        ready_payload = _json_output(with_sample)
        assert payload["route_modes"] == ["auto"]
        assert payload["counts"]["total"] == 7
        assert len(payload["providers"]) == 7
        county = next(
            row for row in payload["providers"] if row["name"] == "county_records"
        )
        ready = next(
            row for row in ready_payload["providers"] if row["name"] == "county_records"
        )
        assert county["implementation_status"] == "implemented"
        assert county["requirements_satisfied"] is False
        assert county["routable_now"] is False
        assert ready["routable_now"] is True


def test_source_flags_are_mutually_exclusive_and_required_for_search(tmp_path):
    no_source = _invoke(
        "search", "--state", "TX", "--county", "MIDLAND", "--format", "json"
    )
    both = _invoke(
        "search",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--sample",
        "--records-file",
        "records.json",
        "--format",
        "json",
    )
    assert no_source.exit_code == 1
    assert both.exit_code == 1
    assert _json_output(no_source)["status"] == "error"
    assert _json_output(both)["status"] == "error"


def test_provider_status_rejects_invalid_custom_file_syntax():
    result = _invoke(
        "providers",
        "--operation",
        "ownership",
        "--records-file",
        ".",
        "--format",
        "json",
    )
    payload = _json_output(result)
    assert result.exit_code == 1
    assert payload["failures"][0]["code"] == "LANDMAN_FIXTURE_PATH_INVALID"


def test_lookup_missing_selector_json_is_one_error_object():
    result = _invoke(
        "lookup",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--format",
        "json",
    )
    payload = _json_output(result)
    assert result.exit_code == 1
    assert payload["status"] == "error"
    assert payload["failures"][0]["code"] == "LANDMAN_LOOKUP_SELECTOR_REQUIRED"


def test_provider_filters_are_visible_in_table_and_csv():
    table = _invoke("providers", "--state", "TX")
    online = _invoke("providers", "--state", "TX", "--online-only")
    csv_result = _invoke("providers", "--state", "TX", "--format", "csv")
    assert table.exit_code == online.exit_code == csv_result.exit_code == 0
    assert "MIDLAND" in table.stdout and "GRADY" not in table.stdout
    assert "LOVING" in table.stdout and "LOVING" not in online.stdout
    rows = list(csv.DictReader(io.StringIO(csv_result.stdout)))
    counties = {row["county"] for row in rows if row["kind"] == "county_reference"}
    assert "MIDLAND" in counties and "GRADY" not in counties


<<<<<<< HEAD
def test_status_csv_is_machine_parseable():
    result = _invoke("status", "--format", "csv")
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert result.exit_code == 0
    assert rows and {row["kind"] for row in rows} == {"provider"}
=======
def test_status_csv_preserves_module_and_data_status(tmp_path):
    result = _invoke("status", "--data-path", str(tmp_path), "--format", "csv")
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert result.exit_code == 0
    status_rows = [row for row in rows if row["kind"] == "status"]
    assert status_rows and status_rows[0]["module_loaded"] == "True"
    assert status_rows[0]["data_path"] == str(tmp_path)
    assert status_rows[0]["file_count"] == "0"
>>>>>>> b803c579f6e48cb4198d76b08e111e88a2fe700e


def test_cli_command_option_and_output_compatibility(tmp_path):
    help_result = _invoke("--help")
    assert help_result.exit_code == 0
    for command in ("search", "lookup", "county-info", "providers", "status"):
        assert command in help_result.stdout
        assert _invoke(command, "--help").exit_code == 0

    search_help = _invoke("search", "--help").stdout
    for option in (
        "--state",
        "--county",
        "--section",
        "--township",
        "--range",
        "--owner",
        "--type",
        "--provider",
        "--format",
        "--output",
        "--verbose",
        "--sample",
        "--records-file",
    ):
        assert option in search_help

    output_file = tmp_path / "records.csv"
    csv_result = _invoke(
        "search",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--sample",
        "--format",
        "csv",
        "--output",
        str(output_file),
    )
    assert csv_result.exit_code == 0
    with output_file.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows and rows[0]["record_id"]


def test_county_info_reference_command_still_works():
    result = _invoke(
        "county-info", "--state", "TX", "--county", "MIDLAND", "--format", "json"
    )
    payload = _json_output(result)
    assert result.exit_code == 0
    assert payload["state"] == "TX"
    assert payload["county"] == "MIDLAND"


def test_county_info_json_instructions_are_in_one_object():
    result = _invoke(
        "county-info",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--format",
        "json",
        "--instructions",
    )
    payload = _json_output(result)
    assert result.exit_code == 0
    assert payload["state"] == "TX"
    assert payload["instructions"]


def test_huge_numeric_fixture_returns_stable_json_envelope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    record = {
        "record_id": "HUGE",
        "state": "TX",
        "county": "MIDLAND",
        "legal_description": "Section 12, Block 42",
        "owner_name": "Public Fixture Owner",
        "gross_acres": 10**400,
    }
    payload = {
        "schema_version": 1,
        "dataset_id": "huge-number",
        "mode": "fixture-only",
        "records": [record],
    }
    (tmp_path / "huge.json").write_text(json.dumps(payload), encoding="utf-8")
    result = _invoke(
        "search",
        "--state",
        "TX",
        "--county",
        "MIDLAND",
        "--records-file",
        "huge.json",
        "--format",
        "json",
    )
    error = _json_output(result)
    assert result.exit_code == 1
    assert error["failures"][0]["code"] == "LANDMAN_FIXTURE_SCHEMA_INVALID"
