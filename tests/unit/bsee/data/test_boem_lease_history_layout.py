"""Offline source-byte contract for the BOEM lease-history first slice."""

import csv
import hashlib
import io
import json
import re
import shutil
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
LAYOUT = ROOT / "data/modules/bsee/boem_lease_history_layout.json"
FIXTURES = ROOT / "tests/fixtures/bsee/boem_raw"


def records(raw):
    """Split original bytes only at CRLF outside quoted fields."""
    quoted, start, spans = False, 0, []
    for offset, byte in enumerate(raw):
        if byte == 34:
            quoted = not quoted
        elif byte == 13 and not quoted:
            assert raw[offset : offset + 2] == b"\r\n", "record terminator"
        elif byte == 10 and not quoted:
            assert offset and raw[offset - 1] == 13, "record terminator"
            spans.append(raw[start : offset + 1])
            start = offset + 1
    assert not quoted and start == len(raw), "incomplete record"
    return spans


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("layout tests must remain offline")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def validate(layout, directory):
    members = layout["members"]
    names = [m["name"] for m in members]
    assert len(names) == len(set(names)) == 15, "member inventory"
    serial = (
        "companies descriptions high_bids leases lease_owners lease_owner_assigns "
        "lease_owner_groups lease_owner_remarks portion_aliquots rates remarks xys"
    ).split()
    assert set(names) == {
        "LeaseOwnerRawData/mv_lease_owners_main.txt",
        "LABRawData/mv_lease_area_block.txt",
        "DeepQualRawData/mv_deep_water_field_leases.txt",
        *(f"SerialRegRawData/mv_serreg_{name}.txt" for name in serial),
    }, "member identities"
    assert {
        a: sum(n.startswith(a + "/") for n in names) for a in layout["archives"]
    } == {
        "LeaseOwnerRawData": 1,
        "LABRawData": 1,
        "DeepQualRawData": 1,
        "SerialRegRawData": 12,
    }, "archive inventory"
    provenance = json.loads((directory / "provenance.json").read_text())
    assert set(provenance["members"]) <= set(names)
    assert {
        p.relative_to(directory).as_posix() for p in directory.rglob("*.txt")
    } == set(provenance["members"]), "fixture inventory"
    row_count, tables = 0, {}
    for member in members:
        encoding = member["encoding"]
        assert encoding["decoding"] == "cp1252"
        assert encoding["record_terminator"] == "CRLF"
        assert encoding["utf8_valid"] == (not encoding["non_ascii_bytes"])
        assert member["size_bytes"] > 0 and len(member["sha256"]) == 64
        if member["name"] not in provenance["members"]:
            continue
        raw = (directory / member["name"]).read_bytes()
        text = raw.decode(encoding["decoding"], errors="strict")
        assert text.encode(encoding["decoding"]) == raw, "encoding round trip"
        assert {f"0x{b:02X}" for b in raw if b > 127} <= set(
            encoding["non_ascii_bytes"]
        ), "unrecorded non-ASCII byte"
        spans = records(raw)
        assert spans[0] == member["header"].encode("cp1252"), "header mismatch"
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
        assert len(rows) == len(spans), "record count"
        assert all(len(row) == len(rows[0]) for row in rows), "field count"
        assert set(member["field_roles"].values()) <= set(rows[0]), "field roles"
        source = provenance["members"][member["name"]]
        assert len(source["selected_records"]) == len(rows) - 1
        assert all(
            r["ordinal"] > 0 and r["byte_offset"] >= len(spans[0])
            for r in source["selected_records"]
        )
        assert [r["size_bytes"] for r in source["selected_records"]] == [
            len(span) for span in spans[1:]
        ], "source span sizes"
        archive = layout["archives"][member["name"].split("/")[0]]
        for key in (
            "source_url",
            "retrieved_utc",
            "archive_sha256",
            "archive_size_bytes",
        ):
            assert source[key] == archive[key], "archive provenance"
        assert source["member_sha256"] == member["sha256"]
        assert source["member_size_bytes"] == member["size_bytes"]
        assert source["terms_urls"] == layout["terms_urls"]
        assert source["fixture_size_bytes"] == len(raw), "fixture size"
        assert (
            source["fixture_sha256"] == hashlib.sha256(raw).hexdigest()
        ), "fixture digest"
        row_count += len(rows) - 1
        tables[member["name"]] = [dict(zip(rows[0], row)) for row in rows[1:]]
    assert len(tables) == 8, "fixture count"
    assert row_count <= 62, "data row budget"
    size = LAYOUT.stat().st_size + (directory / "provenance.json").stat().st_size
    assert size + sum(p.stat().st_size for p in directory.rglob("*.txt")) <= 48 * 1024
    return tables


def test_source_layout_and_provenance():
    assert LAYOUT.is_file(), "BOEM source-layout descriptor is absent"
    validate(json.loads(LAYOUT.read_text()), FIXTURES)


def test_acceptance_examples_and_source_limitations():
    tables = validate(json.loads(LAYOUT.read_text()), FIXTURES)
    lab = tables["LABRawData/mv_lease_area_block.txt"]
    assert {r["LEASE_NUMBER"] for r in lab} == {
        "G08487",
        "G18207",
        "G32306",
        "G35491",
        "G28148",
    }
    remarks = tables["SerialRegRawData/mv_serreg_remarks.txt"]
    assert any(
        r["LEASE_NUMBER"] == "G37022"
        and r["REMARK_DATE"] == "9/22/2021"
        and "segregated lease" in r["REMARK"]
        for r in remarks
    )
    values = [v for rows in tables.values() for row in rows for v in row.values()]
    assert any(re.fullmatch(r"0\d+", v) for v in values), "leading-zero identifier"
    assert any("," in v for v in values), "quoted comma coverage"
    assert any("\n" in v for v in values), "embedded newline coverage"


@pytest.mark.parametrize(
    "name, byte",
    [
        ("mv_serreg_remarks", 0xA0),
        ("mv_serreg_lease_owner_groups", 0xBF),
    ],
)
def test_non_ascii_source_regressions(name, byte):
    raw = (FIXTURES / "SerialRegRawData" / (name + ".txt")).read_bytes()
    assert byte in raw
    for encoding in ("ascii", "utf-8"):
        with pytest.raises(UnicodeDecodeError):
            raw.decode(encoding)
    assert chr(byte) in raw.decode("cp1252")
    rows = list(csv.reader(io.StringIO(raw.decode("cp1252"), newline=""), strict=True))
    assert all(len(row) == len(rows[0]) for row in rows)


@pytest.mark.parametrize(
    "damage, message",
    [
        ("undefined", "charmap"),
        ("unrecorded", "unrecorded non-ASCII"),
        ("missing_header", "header mismatch"),
        ("reordered_header", "header mismatch"),
        ("duplicate", "member inventory"),
        ("tampered", "fixture digest"),
        ("bare_lf", "record terminator"),
    ],
)
def test_rejects_damaged_copies(tmp_path, damage, message):
    layout = json.loads(LAYOUT.read_text())
    directory = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, directory)
    path = directory / "LABRawData/mv_lease_area_block.txt"
    raw = path.read_bytes()
    header, body = raw.split(b"\r\n", 1)
    if damage == "duplicate":
        layout["members"][-1] = layout["members"][0]
    elif damage == "missing_header":
        path.write_bytes(body)
    elif damage == "reordered_header":
        path.write_bytes(b",".join(reversed(header.split(b","))) + b"\r\n" + body)
    elif damage == "bare_lf":
        path.write_bytes(raw.replace(b"\r\n", b"\n", 1))
    else:
        replacement = {"undefined": b"\x81", "unrecorded": b"\xe9", "tampered": b"X"}[
            damage
        ]
        path.write_bytes(header + b"\r\n" + body.replace(b"G", replacement, 1))
    with pytest.raises((AssertionError, UnicodeDecodeError), match=message):
        validate(layout, directory)
