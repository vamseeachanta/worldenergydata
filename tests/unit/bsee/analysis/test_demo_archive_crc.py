"""Offline CRC regressions for the data-only survey loader.

Column order: WellData._get_column_names_for_dsptsdelimit_file in
packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/well_data.py.
Every survey number is a synthetic input; expected cells are hand-transcribed
from SURVEY_TEXT, independently of the loader and its schema constants.

Local-header layout and ZipExtFile._update_crc behavior (BadZipFile at EOF):
https://github.com/python/cpython/blob/v3.12.7/Lib/zipfile/__init__.py#L148-L165
https://github.com/python/cpython/blob/v3.12.7/Lib/zipfile/__init__.py#L999-L1007
"""

import hashlib
import importlib.util
import io
import pickle
import shutil
import socket
import struct
import zipfile
from pathlib import Path
from unittest.mock import Mock

import httpx
import pandas as pd
import pytest

# Four ancestors ascend analysis -> bsee -> unit -> tests -> repository root.
DEMO_PATH = Path(__file__).resolve().parents[4] / "scripts/bsee/demo_well_path_julia.py"
SURVEY_TEXT = (
    b"000000000001,10,0,100,N,20,0,E,99,1,2,-90,28\n"
    b"000000000002,30,0,200,S,40,0,W,198,3,4,-91,29\n"
)
# CPython's cited local file header, ending in filename and extra-field lengths.
LOCAL_HEADER = struct.Struct("<4s2B4HL2L2H")


@pytest.fixture
def forbidden_calls(monkeypatch):
    """Fail immediately on deserialization, extraction, or network access."""
    guards = []
    for target, attribute in (
        (pickle, "load"),
        (pickle, "loads"),
        (pd, "read_pickle"),
        (zipfile.ZipFile, "extract"),
        (zipfile.ZipFile, "extractall"),
        (shutil, "unpack_archive"),
        (httpx, "stream"),
        (httpx.Client, "send"),
        (httpx.AsyncClient, "send"),
        (socket, "create_connection"),
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
    ):
        guard = Mock(side_effect=AssertionError(f"Forbidden call: {attribute}"))
        monkeypatch.setattr(target, attribute, guard)
        guards.append(guard)
    yield
    for guard in guards:
        guard.assert_not_called()


@pytest.fixture
def demo(tmp_path, monkeypatch, forbidden_calls):
    spec = importlib.util.spec_from_file_location("survey_crc_demo", DEMO_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DSPTS_DIR", str(tmp_path))
    monkeypatch.setattr(module, "DSPTS_ZIP", str(tmp_path / "dsptsdelimit.ZIP"))
    return module


def survey_archive():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("dsptsdelimit.txt", SURVEY_TEXT)
    return output.getvalue()


def test_corrupt_crc_with_matching_digest_is_rejected(demo, tmp_path, monkeypatch):
    valid = survey_archive()
    with zipfile.ZipFile(io.BytesIO(valid)) as archive:
        member = archive.getinfo("dsptsdelimit.txt")
        assert member.compress_type == zipfile.ZIP_STORED
        header = LOCAL_HEADER.unpack_from(valid, member.header_offset)
    *_, filename_length, extra_length = header
    payload_start = (
        member.header_offset + LOCAL_HEADER.size + filename_length + extra_length
    )
    payload_end = payload_start + member.file_size
    assert valid[payload_start:payload_end] == SURVEY_TEXT

    # Replace the leading ASCII digit with another digit: CSV remains valid.
    # The local header and central directory (including both CRCs) stay intact.
    damaged = bytearray(valid)
    damaged[payload_start : payload_start + len(b"9")] = b"9"
    damaged = bytes(damaged)
    assert damaged != valid
    assert damaged[:payload_start] == valid[:payload_start]
    assert damaged[payload_end:] == valid[payload_end:]
    archive_path = Path(demo.DSPTS_ZIP)
    archive_path.write_bytes(damaged)
    sentinel = tmp_path / "dsptsdelimit.txt"
    sentinel_bytes = b"Existing output must remain unchanged.\n"
    sentinel.write_bytes(sentinel_bytes)
    before = set(tmp_path.iterdir())

    # Approve the final damaged bytes with stdlib hashing, without the loader.
    approved_digest = hashlib.sha256(damaged).hexdigest()
    dataframe = Mock(side_effect=AssertionError("Constructed a DataFrame"))
    monkeypatch.setattr(pd, "DataFrame", dataframe)
    with pytest.raises(zipfile.BadZipFile, match="Bad CRC-32"):
        demo.load_surveys(approved_digest)
    dataframe.assert_not_called()
    assert archive_path.read_bytes() == damaged
    assert sentinel.read_bytes() == sentinel_bytes
    assert set(tmp_path.iterdir()) == before


def test_valid_crc_returns_literal_records(demo):
    data = survey_archive()
    Path(demo.DSPTS_ZIP).write_bytes(data)
    result = demo.load_surveys(hashlib.sha256(data).hexdigest())
    expected = pd.DataFrame(
        [
            ["000000000001", 10, 0, 100, "N", 20, 0, "E", 99, 1, 2, -90, 28],
            ["000000000002", 30, 0, 200, "S", 40, 0, "W", 198, 3, 4, -91, 29],
        ],
        columns=[
            "API_WELL_NUMBER",
            "INCL_ANG_DEG_VAL",
            "INCL_ANG_MIN_VAL",
            "SURVEY_POINT_MD",
            "WELL_N_S_CODE",
            "DIR_DEG_VAL",
            "DIR_MINS_VAL",
            "WELL_E_W_CODE",
            "SURVEY_POINT_TVD",
            "DELTA_X",
            "DELTA_Y",
            "SURF_LONGITUDE",
            "SURF_LATITUDE",
        ],
    )
    pd.testing.assert_frame_equal(result, expected, check_exact=True)
    assert Path(demo.DSPTS_ZIP).read_bytes() == data
