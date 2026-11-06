"""Offline CLI search contract for issue #924.

All records and identifiers below are synthetic. Legal-description components
come from the search command's NM example (Section 12, T24S, R36E). Expected
JSON is specified explicitly, without using model serialization as the oracle.
One supplied ownership record and no lease/title records give a total of one;
a fixed clock gives zero elapsed milliseconds. Exit zero means success;
nonzero means failure, as required by the command contract in issue #924.
"""

import builtins
import importlib
import json
import socket
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.landman import app
from worldenergydata.landman.exceptions import ProviderError
from worldenergydata.landman.landman import Landman
from worldenergydata.landman.models import MineralOwnershipRecord


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail on HTTP transport, DNS, or socket transport, even if caught by CLI."""

    def blocked(*args, **kwargs):
        pytest.fail("Network transport is forbidden in offline CLI tests")

    for name in ("connect", "connect_ex", "sendto", "sendmsg"):
        if hasattr(socket.socket, name):
            monkeypatch.setattr(socket.socket, name, blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(httpx.Client, "send", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)


@pytest.mark.parametrize("provider_args", [[], ["--provider", "county_records"]])
def test_cli_search_serializes_fixture_result(monkeypatch, tmp_path, provider_args):
    """Real validation, result construction, and serialization retain CLI inputs."""
    search_module = importlib.import_module("worldenergydata.landman.landman")
    models_module = importlib.import_module("worldenergydata.landman.models")
    instant = datetime.fromisoformat("2024-01-01T00:00:00")

    class FixedClock:
        @staticmethod
        def now():
            return instant

        @staticmethod
        def utcnow():
            return instant

    monkeypatch.setattr(search_module, "datetime", FixedClock)
    monkeypatch.setattr(models_module, "datetime", FixedClock)
    monkeypatch.setattr(search_module.uuid, "uuid4", lambda: "synthetic-search")

    criteria = {
        "state": "NM",
        "county": "LEA",
        "legal_description": "Section 12, T24S, R36E",
        "owner_name": "SYNTHETIC MINERAL TRUST",
    }
    record = MineralOwnershipRecord(
        record_id="synthetic-record",
        state="NM",
        county="LEA",
        legal_description="Section 12, T24S, R36E",
        owner_name="SYNTHETIC MINERAL TRUST",
        provider="synthetic",
    )
    acquisitions = []
    searches = []

    def provider_search(search_criteria):
        searches.append(search_criteria)
        return [record]

    def get_provider(self, provider_name, cfg):
        acquisitions.append((provider_name, cfg))
        return SimpleNamespace(search_ownership=provider_search)

    monkeypatch.setattr(Landman, "_get_provider", get_provider)
    output = tmp_path / "result.json"
    result = CliRunner().invoke(
        app,
        [
            "search",
            "--state",
            "nm",
            "--county",
            "lea",
            "--section",
            "12",
            "--township",
            "24S",
            "--range",
            "36E",
            "--owner",
            "SYNTHETIC MINERAL TRUST",
            "--format",
            "json",
            "--output",
            str(output),
            *provider_args,
        ],
    )

    assert result.exit_code == 0, result.output
    provider_name = "county_records" if provider_args else "auto"
    assert acquisitions == [
        (
            provider_name,
            {
                "state": "NM",
                "county": "LEA",
                "provider": provider_name,
                "search": criteria,
            },
        )
    ]
    assert searches == [criteria]
    assert json.loads(output.read_text()) == {
        "search_id": "synthetic-search",
        "search_criteria": criteria,
        "state": "NM",
        "county": "LEA",
        "owner_name": "SYNTHETIC MINERAL TRUST",
        "legal_description": "Section 12, T24S, R36E",
        "ownership_records": [
            {
                "record_id": "synthetic-record",
                "state": "NM",
                "county": "LEA",
                "legal_description": "Section 12, T24S, R36E",
                "owner_name": "SYNTHETIC MINERAL TRUST",
                "owner_address": None,
                "interest_type": "mineral",
                "mineral_interest_percent": None,
                "net_mineral_acres": None,
                "gross_acres": None,
                "effective_date": None,
                "source_document": None,
                "grantor": None,
                "recorded_date": None,
                "book": None,
                "page": None,
                "volume": None,
                "instrument_number": None,
                "notes": None,
                "provider": "synthetic",
                "retrieved_at": None,
            }
        ],
        "lease_records": [],
        "title_records": [],
        "total_records": 1,
        "search_timestamp": "2024-01-01T00:00:00",
        "provider": provider_name,
        "search_duration_ms": 0,
        "has_more_results": False,
        "warnings": [],
        "errors": [],
    }
    assert "Results saved to" in result.output
    assert "Total records found: 1" in result.output


@pytest.mark.parametrize("output_format", ["table", "json"])
def test_cli_error_result_fails(monkeypatch, output_format):
    """A generic provider failure becomes result.errors through the real search."""
    searches = []

    def fail(search_criteria):
        searches.append(search_criteria)
        raise RuntimeError("synthetic provider failure")

    monkeypatch.setattr(
        Landman,
        "_get_provider",
        lambda *args: SimpleNamespace(search_ownership=fail),
    )
    result = CliRunner().invoke(
        app,
        ["search", "--state", "NM", "--county", "LEA", "--format", output_format],
    )

    assert searches == [{"state": "NM", "county": "LEA"}]
    assert "Search failed: synthetic provider failure" in result.output
    assert result.exit_code != 0, result.output
    assert "Total records found:" not in result.output


def test_cli_unavailable_provider_fails(monkeypatch):
    """A structured provider capability failure retains its existing error exit."""

    def unavailable(self, provider_name, cfg):
        assert provider_name == "county_records"
        raise ProviderError(
            "synthetic capability unavailable",
            error_code="PROVIDER_UNAVAILABLE",
            details={"provider": provider_name},
        )

    monkeypatch.setattr(Landman, "_get_provider", unavailable)
    result = CliRunner().invoke(
        app,
        ["search", "--state", "NM", "--county", "LEA", "--provider", "county_records"],
    )

    assert result.exit_code != 0, result.output
    assert "synthetic capability unavailable" in result.output
    assert "Total records found:" not in result.output


def test_cli_import_failure_fails(monkeypatch):
    """An unavailable Landman import fails before acquiring any provider."""
    original_import = builtins.__import__

    def fail_import(name, *args, **kwargs):
        if name == "worldenergydata.landman.landman":
            raise ImportError("synthetic missing dependency")
        return original_import(name, *args, **kwargs)

    def unexpected_provider(*args):
        pytest.fail("Import failure reached provider acquisition")

    monkeypatch.setattr(builtins, "__import__", fail_import)
    monkeypatch.setattr(Landman, "_get_provider", unexpected_provider)
    result = CliRunner().invoke(app, ["search", "--state", "NM", "--county", "LEA"])

    assert result.exit_code != 0, result.output
    assert "Could not import Landman module:" in result.output
    assert "synthetic missing dependency" in result.output
    assert "Total records found:" not in result.output
