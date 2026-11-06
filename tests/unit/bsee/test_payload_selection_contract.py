"""In-memory selection contracts for the extraction slice of issue #365.

The quoted CSV and CRLF shape follows test_bsee_payload.py's fixture.
All cells below are synthetic; the expected table is transcribed by hand
from QUOTED_CSV, without using a parser to construct the oracle.
"""

import io
import socket
import zipfile
from itertools import permutations

import pytest

from worldenergydata.bsee.data.refresh.payload import (
    PayloadKind,
    classify_payload,
    extract_primary_table,
    list_data_members,
    select_primary_member,
)

QUOTED_CSV = (
    '"CATEGORY","LABEL","STATUS"\r\n'
    '"north","upper, lower","ready"\r\n'
    '"south","plain","hold"\r\n'
)
EXPECTED_COLUMNS = ["CATEGORY", "LABEL", "STATUS"]
# Hand transcription: each CRLF-terminated data record contributes one row;
# the comma inside the quoted LABEL contributes no additional column.
EXPECTED_RECORDS = [
    ["north", "upper, lower", "ready"],
    ["south", "plain", "hold"],
]
SMALL_CSV = '"CATEGORY","LABEL","STATUS"\r\n"other","short","hold"\r\n'
PREFERRED_MEMBER = "Archive/Deep/Mv_Preferred_Table.TxT"
SECONDARY_MEMBER = "Archive/MV_SECONDARY_TABLE.txt"
# Priority is fixed across every member-order and size permutation.
PATTERNS = ["MV_PREFERRED_*.TXT", "mv_*.txt"]


@pytest.fixture(autouse=True)
def forbid_network_and_filesystem_extraction(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Payload contract tests require in-memory archives")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "_extract_member", forbidden)


def _archive(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Archive/", "")
        for name, content in members:
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "member_order", list(permutations((PREFERRED_MEMBER, SECONDARY_MEMBER)))
)
@pytest.mark.parametrize("preferred_larger", [False, True])
def test_pattern_priority_survives_member_permutation(member_order, preferred_larger):
    # Size ordering follows directly from the literal byte lengths, independent
    # of ZIP compression: QUOTED_CSV has an additional, longer data record.
    contents = {
        PREFERRED_MEMBER: QUOTED_CSV if preferred_larger else SMALL_CSV,
        SECONDARY_MEMBER: SMALL_CSV if preferred_larger else QUOTED_CSV,
    }
    data = _archive([(name, contents[name]) for name in member_order])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = list_data_members(archive)
        assert [member.filename for member in members] == list(member_order)
        preferred = archive.getinfo(PREFERRED_MEMBER)
        secondary = archive.getinfo(SECONDARY_MEMBER)
        assert (preferred.file_size > secondary.file_size) is preferred_larger
        assert select_primary_member(members, PATTERNS) is preferred

    _, selected_name = extract_primary_table(data, PATTERNS)
    assert selected_name == PREFERRED_MEMBER


@pytest.mark.parametrize("extension", ["TxT", "CsV"])
def test_nested_mixed_case_member_roundtrip(extension):
    selected_name = f"Archive/Deep/Nested/Mv_PrEfErReD_TaBlE.{extension}"
    data = _archive(
        [
            (SECONDARY_MEMBER, SMALL_CSV),
            (selected_name, QUOTED_CSV),
        ]
    )
    assert classify_payload(data) is PayloadKind.ZIP
    table, member = extract_primary_table(
        data, [f"MV_PREFERRED_*.{extension.upper()}", "mv_*"]
    )
    assert member == selected_name
    assert list(table.columns) == EXPECTED_COLUMNS
    assert table.to_numpy().tolist() == EXPECTED_RECORDS
    assert len(table) == len(EXPECTED_RECORDS)


def test_unmatched_patterns_never_fall_back():
    data = _archive(
        [
            ("Archive/mv_small.txt", SMALL_CSV),
            ("Archive/Deep/MV_LARGE_TABLE.CSV", QUOTED_CSV),
        ]
    )
    missing_patterns = ["mv_missing_*.txt", "mv_absent_*.csv"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.getinfo("Archive/Deep/MV_LARGE_TABLE.CSV").file_size > len(
            SMALL_CSV.encode("utf-8")
        )
        with pytest.raises(LookupError, match="primary_member_patterns"):
            select_primary_member(list_data_members(archive), missing_patterns)

    with pytest.raises(LookupError, match="primary_member_patterns"):
        extract_primary_table(data, missing_patterns)
