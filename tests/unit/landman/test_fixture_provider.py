"""Focused fixture schema, secure file, and county-record search contracts."""

import json
import os
import select
import socket
import subprocess
import sys
from copy import deepcopy

import pytest

from worldenergydata.landman.exceptions import FixtureValidationError
from worldenergydata.landman.fixture_schema import (
    MAX_FIXTURE_BYTES,
    parse_fixture_bytes,
    read_custom_fixture,
)
from worldenergydata.landman.landman import Landman
from worldenergydata.landman.providers.county_records import CountyRecordsProvider
from worldenergydata.landman.routing import SourceConfig


def _record(record_id="REC-002", **overrides):
    record = {
        "record_id": record_id,
        "state": "TX",
        "county": "Midland County",
        "legal_description": "Section 12, Block 42, T-1-S",
        "owner_name": "Smith Minerals LLC",
        "interest_type": "mineral",
        "mineral_interest_percent": 50.0,
        "net_mineral_acres": 80.0,
        "gross_acres": 160.0,
        "effective_date": "2024-01-02",
        "recorded_date": "2024-02-03",
    }
    record.update(overrides)
    return record


def _payload(records=None, **overrides):
    payload = {
        "schema_version": 1,
        "dataset_id": "public-test-fixture",
        "mode": "fixture-only",
        "records": records if records is not None else [_record()],
    }
    payload.update(overrides)
    return payload


def _encoded(payload):
    return json.dumps(payload, allow_nan=True).encode("utf-8")


def _write_fixture(path, records):
    path.write_text(json.dumps(_payload(records)), encoding="utf-8")


def test_fixture_schema_valid_and_closed():
    fixture = parse_fixture_bytes(_encoded(_payload()), "sample")
    record = fixture.records[0]
    assert fixture.dataset_id == "public-test-fixture"
    assert record.interest_type.value == "mineral"
    assert record.effective_date.isoformat() == "2024-01-02"

    for payload in (
        _payload(extra=True),
        _payload(schema_version=2),
        _payload(records=[_record(unexpected="value")]),
        _payload(records=[_record(interest_type="invalid")]),
        _payload(records=[_record(effective_date="01/02/2024")]),
    ):
        with pytest.raises(FixtureValidationError):
            parse_fixture_bytes(_encoded(payload), "records.json")


@pytest.mark.parametrize(
    "field,value",
    [
        ("mineral_interest_percent", True),
        ("mineral_interest_percent", -1),
        ("mineral_interest_percent", 101),
        ("net_mineral_acres", False),
        ("net_mineral_acres", 0),
        ("gross_acres", float("inf")),
        ("gross_acres", float("nan")),
    ],
)
def test_fixture_numeric_values_fail_closed(field, value):
    with pytest.raises(FixtureValidationError):
        parse_fixture_bytes(
            _encoded(_payload(records=[_record(**{field: value})])), "x.json"
        )


def test_fixture_limits_duplicates_and_json_constants():
    duplicate = _payload(records=[_record("A"), _record("A")])
    with pytest.raises(FixtureValidationError):
        parse_fixture_bytes(_encoded(duplicate), "x.json")
    with pytest.raises(FixtureValidationError):
        parse_fixture_bytes(
            _encoded(_payload(records=[_record(str(i)) for i in range(1001)])), "x.json"
        )
    with pytest.raises(FixtureValidationError):
        parse_fixture_bytes(
            b'{"schema_version":1,"dataset_id":"x","mode":"fixture-only","records":[NaN]}',
            "x.json",
        )
    with pytest.raises(FixtureValidationError):
        parse_fixture_bytes(b" " * (MAX_FIXTURE_BYTES + 1), "x.json")


def test_huge_json_integer_becomes_fixture_validation_error():
    payload = _payload(records=[_record(gross_acres=10**400)])
    with pytest.raises(FixtureValidationError) as caught:
        parse_fixture_bytes(_encoded(payload), "huge.json")
    assert caught.value.code == "LANDMAN_FIXTURE_SCHEMA_INVALID"


def test_custom_file_is_direct_child_descriptor_opened_and_bounded(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _write_fixture(tmp_path / "records.json", [_record()])
    assert read_custom_fixture("records.json").dataset_id == "public-test-fixture"

    outside = tmp_path.parent / "outside.json"
    _write_fixture(outside, [_record()])
    (tmp_path / "linked.json").symlink_to(outside)
    (tmp_path / "nested").mkdir()
    for invalid in (
        "",
        ".",
        "..",
        "../outside.json",
        "nested/records.json",
        str(outside),
        "linked.json",
        "records.txt",
        r"C:\private\records.json",
    ):
        with pytest.raises(FixtureValidationError) as caught:
            read_custom_fixture(invalid)
        assert str(outside) not in str(caught.value)
        assert "C:\\private" not in str(caught.value)

    (tmp_path / "large.json").write_bytes(b"x" * (MAX_FIXTURE_BYTES + 1))
    with pytest.raises(FixtureValidationError):
        read_custom_fixture("large.json")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO unavailable")
def test_custom_fifo_is_rejected_without_blocking(tmp_path):
    fifo = tmp_path / "records.json"
    os.mkfifo(fifo)
    script = "\n".join(
        [
            "from worldenergydata.landman.exceptions import FixtureValidationError",
            "from worldenergydata.landman.fixture_schema import read_custom_fixture",
            "print('READY', flush=True)",
            "try:",
            "    read_custom_fixture('records.json')",
            "except FixtureValidationError as error:",
            "    print(error.code)",
            "else:",
            "    raise SystemExit(2)",
        ]
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ready, _, _ = select.select([process.stdout], [], [], 30)
    assert ready and process.stdout.readline().strip() == "READY"
    try:
        stdout, stderr = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    assert process.returncode == 0, stderr
    assert "LANDMAN_FIXTURE_PATH_INVALID" in stdout


def test_fixture_search_filter_contract_and_record_order():
    records = [
        _record("REC-020", owner_name="Smith Minerals LLC"),
        _record("REC-003", owner_name="JONES FAMILY TRUST"),
        _record(
            "REC-010", county="  MIDLAND  ", legal_description="Section 99, Block 1"
        ),
    ]
    provider = CountyRecordsProvider.from_payload(_payload(records=records))

    result = provider.search_ownership(
        {
            "state": " tx ",
            "county": " midland county ",
            "owner_name": " minerals ",
            "legal_description": " block 42 ",
        }
    )
    assert [record.record_id for record in result] == ["REC-020"]
    assert provider.search_ownership({"state": "TX", "county": "REEVES"}) == []
    ordered = provider.search_ownership({"state": "TX", "county": "MIDLAND"})
    assert [record.record_id for record in ordered] == ["REC-003", "REC-010", "REC-020"]
    assert all(record.provider == "county_records" for record in ordered)


def test_two_sequential_sources_do_not_share_provider_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_fixture(tmp_path / "first.json", [_record("FIRST")])
    _write_fixture(tmp_path / "second.json", [_record("SECOND")])
    landman = Landman()

    first = landman.search_ownership("TX", "MIDLAND", records_file="first.json")
    second = landman.search_ownership("TX", "MIDLAND", records_file="second.json")

    assert [record.record_id for record in first.ownership_records] == ["FIRST"]
    assert [record.record_id for record in second.ownership_records] == ["SECOND"]
    assert landman._providers == {}


def test_fixture_search_never_opens_network(monkeypatch):
    attempts = []

    def reject_network(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    provider = CountyRecordsProvider(SourceConfig(sample=True))
    records = provider.search_ownership({"state": "TX", "county": "MIDLAND"})

    assert records
    assert attempts == []


def test_source_payload_is_not_mutated():
    payload = _payload()
    original = deepcopy(payload)
    CountyRecordsProvider.from_payload(payload)
    assert payload == original
