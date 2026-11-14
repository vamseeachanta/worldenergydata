"""Offline archive-integrity regressions using synthetic survey records.

The schema comes from WellData._get_column_names_for_dsptsdelimit_file in
packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/well_data.py.
All numbers below are literal test inputs, not engineering acceptance limits.
Expected records are independently transcribed from ROW; SHA-256 is computed
with the standard library, independently of the demo's verification function.
"""

import hashlib
import importlib.util
import io
import pickle
import runpy
import shutil
import socket
import zipfile
from pathlib import Path
from unittest.mock import Mock

import httpx
import pandas as pd
import pytest

DEMO_PATH = Path(__file__).resolve().parents[4] / "scripts/bsee/demo_well_path_julia.py"
ROW = "000000000001,10,0,100,N,20,0,E,99,1,2,-90,28\n"
DESERIALIZATION_EVENTS = []


def record_deserialization():
    """Record a harmless canary decode, including through unpatched aliases."""
    DESERIALIZATION_EVENTS.append("decoded")


class DeserializationCanary:
    def __reduce__(self):
        return record_deserialization, ()


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch, request):
    """Reject network calls, including attempts whose errors are swallowed."""
    guards = {}
    for target, attribute in (
        (httpx, "stream"),
        (httpx.Client, "send"),
        (httpx.AsyncClient, "send"),
        (socket, "create_connection"),
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
    ):
        guard = Mock(side_effect=AssertionError(f"Forbidden call: {attribute}"))
        monkeypatch.setattr(target, attribute, guard)
        guards[target, attribute] = guard
    expected = getattr(request, "param", {})
    assert set(expected).issubset(guards)
    yield guards
    for key, guard in guards.items():
        assert guard.call_count == expected.get(key, 0), key


@pytest.fixture
def forbid_deserialization(monkeypatch, forbid_network):
    """Reject deserialization and extraction; retain the decode canary."""
    DESERIALIZATION_EVENTS.clear()
    guards = []
    for target, attribute in (
        (pickle, "load"),
        (pickle, "loads"),
        (pickle, "Unpickler"),
        (pd, "read_pickle"),
        (zipfile.ZipFile, "extract"),
        (zipfile.ZipFile, "extractall"),
        (shutil, "unpack_archive"),
    ):
        guard = Mock(side_effect=AssertionError(f"Forbidden call: {attribute}"))
        monkeypatch.setattr(target, attribute, guard)
        guards.append(guard)
    yield
    assert DESERIALIZATION_EVENTS == []
    for guard in guards:
        guard.assert_not_called()


@pytest.fixture
def demo(tmp_path, monkeypatch, forbid_network):
    spec = importlib.util.spec_from_file_location("survey_demo", DEMO_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DSPTS_DIR", str(tmp_path))
    monkeypatch.setattr(module, "DSPTS_ZIP", str(tmp_path / "dsptsdelimit.ZIP"))
    return module


def archive_bytes(text=ROW, member="dsptsdelimit.txt", pickle_payload=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(member, text)
        if pickle_payload is not None:
            archive.writestr("dsptsdelimit.bin", pickle_payload)
    return output.getvalue()


def local_archive(demo, data):
    Path(demo.DSPTS_ZIP).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def mock_download(demo, monkeypatch, data, status=200):
    response = httpx.Response(
        status,
        content=data,
        headers={"Location": "https://example.com/other.zip"},
        request=httpx.Request("GET", demo.DSPTS_URL),
    )
    stream = Mock()
    stream.return_value.__enter__ = Mock(return_value=response)
    stream.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(httpx, "stream", stream)
    return stream


@pytest.mark.parametrize(
    "forbid_network", [{(httpx.Client, "send"): 1}], indirect=True, ids=["send-probe"]
)
@pytest.mark.parametrize("route", ["top-level", "client"])
def test_alternate_http_routes_are_rejected_before_transport(
    demo, monkeypatch, forbid_network, route
):
    """Probe the network boundary without allowing transport dispatch."""
    transport = Mock(side_effect=AssertionError("Transport backstop reached"))
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", transport)
    with pytest.raises(AssertionError, match="Forbidden call: send"):
        if route == "top-level":
            httpx.get("https://example.invalid/survey.zip", trust_env=False)
        else:
            with httpx.Client(trust_env=False) as client:
                client.get("https://example.invalid/survey.zip")
    transport.assert_not_called()


@pytest.mark.parametrize("protocol", [0, 4])
def test_deserialization_canary_records_an_unpatched_decode(protocol):
    """Establish the canary signal separately from the guarded loader calls."""
    DESERIALIZATION_EVENTS.clear()
    payload = pickle.dumps(DeserializationCanary(), protocol=protocol)
    assert pickle.loads(payload) is None
    assert DESERIALIZATION_EVENTS == ["decoded"]
    DESERIALIZATION_EVENTS.clear()


def test_verified_text_preserves_first_record_and_string_identifiers(demo):
    """Two copies of ROW give two records, API '000000000001', MD 100 each."""
    digest = local_archive(demo, archive_bytes(ROW + ROW))
    result = demo.load_surveys(digest)
    assert list(result.columns) == demo.DSPTS_COLS
    assert result["API_WELL_NUMBER"].tolist() == ["000000000001"] * 2
    assert result["SURVEY_POINT_MD"].tolist() == [100, 100]
    assert result["SURVEY_POINT_TVD"].tolist() == [99, 99]
    assert pd.api.types.is_numeric_dtype(result["INCL_ANG_DEG_VAL"])


def test_whitespace_is_normalized(demo):
    text = ROW.replace("000000000001", " 000000000001 ").replace(",N,", ", N ,")
    digest = local_archive(demo, archive_bytes(text))
    result = demo.load_surveys(digest)
    assert result["API_WELL_NUMBER"].tolist() == ["000000000001"]
    assert result["WELL_N_S_CODE"].tolist() == ["N"]


def test_uppercase_digest_is_accepted(demo):
    digest = local_archive(demo, archive_bytes())
    assert len(demo.load_surveys(digest.upper())) == 1


@pytest.mark.parametrize("digest", [None, "", "abc", "z" * 64, "a " * 32])
def test_invalid_pin_fails_before_network_or_parsing(demo, digest, monkeypatch):
    monkeypatch.setattr(pd, "read_csv", Mock(side_effect=AssertionError("Parsed")))
    with pytest.raises(ValueError, match="SHA-256"):
        demo.load_surveys(digest)


def test_mismatch_is_rejected_before_zip_or_csv_parsing(demo, monkeypatch):
    local_archive(demo, b"untrusted bytes")
    monkeypatch.setattr(zipfile, "ZipFile", Mock(side_effect=AssertionError("Opened")))
    monkeypatch.setattr(pd, "read_csv", Mock(side_effect=AssertionError("Parsed")))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        demo.load_surveys(hashlib.sha256(b"approved bytes").hexdigest())
    assert Path(demo.DSPTS_ZIP).read_bytes() == b"untrusted bytes"


def test_cached_archive_is_verified_on_every_load(demo):
    digest = local_archive(demo, archive_bytes())
    demo.load_surveys(digest)
    with open(demo.DSPTS_ZIP, "ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        demo.load_surveys(digest)


def test_legacy_pickle_is_never_read_or_replaced(demo, monkeypatch, tmp_path):
    legacy = tmp_path / "dsptsdelimit.bin"
    legacy.write_bytes(b"legacy pickle must remain untouched")
    monkeypatch.setattr(pickle, "load", Mock(side_effect=AssertionError("Unpickled")))
    monkeypatch.setattr(
        pd, "read_pickle", Mock(side_effect=AssertionError("Unpickled"))
    )
    digest = local_archive(demo, archive_bytes())
    demo.load_surveys(digest)
    assert legacy.read_bytes() == b"legacy pickle must remain untouched"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "dsptsdelimit.ZIP",
        "dsptsdelimit.bin",
    ]


@pytest.mark.parametrize("legacy_cache", [False, True])
def test_missing_archive_is_downloaded_and_verified(
    demo, monkeypatch, tmp_path, forbid_deserialization, legacy_cache
):
    payload = pickle.dumps(DeserializationCanary(), protocol=4)
    legacy = tmp_path / "dsptsdelimit.bin"
    if legacy_cache:
        legacy.write_bytes(payload)
    data = archive_bytes(pickle_payload=payload)
    stream = mock_download(demo, monkeypatch, data)
    result = demo.load_surveys(hashlib.sha256(data).hexdigest())
    assert result["API_WELL_NUMBER"].tolist() == ["000000000001"]
    assert result["SURVEY_POINT_MD"].tolist() == [100]
    assert result["SURVEY_POINT_TVD"].tolist() == [99]
    assert Path(demo.DSPTS_ZIP).read_bytes() == data
    stream.assert_called_once_with("GET", demo.DSPTS_URL, follow_redirects=False)
    expected_paths = ["dsptsdelimit.ZIP"]
    if legacy_cache:
        assert legacy.read_bytes() == payload
        expected_paths.append("dsptsdelimit.bin")
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(expected_paths)


@pytest.mark.parametrize("protocol", [0, 4])
@pytest.mark.parametrize("layout", ["raw", "pickle-only-zip", "pickle-as-text"])
def test_downloaded_pickle_is_rejected_without_deserialization(
    demo, monkeypatch, tmp_path, forbid_deserialization, protocol, layout
):
    payload = pickle.dumps(DeserializationCanary(), protocol=protocol)
    data = payload
    error_type, message = zipfile.BadZipFile, "File is not a zip file"
    if layout == "pickle-only-zip":
        data = archive_bytes(payload, member="dsptsdelimit.bin")
        error_type, message = ValueError, "exactly one dsptsdelimit.txt"
    elif layout == "pickle-as-text":
        data = archive_bytes(payload)
        error_type, message = ValueError, "survey schema"
    stream = mock_download(demo, monkeypatch, data)
    with pytest.raises(error_type, match=message) as error:
        demo.load_surveys(hashlib.sha256(data).hexdigest())
    if layout == "pickle-as-text":
        if protocol == 4:
            assert isinstance(error.value.__cause__, UnicodeDecodeError)
        else:
            assert "field count in record 1" in str(error.value.__cause__)
    assert Path(demo.DSPTS_ZIP).read_bytes() == data
    assert [path.name for path in tmp_path.iterdir()] == ["dsptsdelimit.ZIP"]
    stream.assert_called_once_with("GET", demo.DSPTS_URL, follow_redirects=False)


def test_download_redirect_creates_no_archive(
    demo, monkeypatch, forbid_deserialization
):
    stream = mock_download(demo, monkeypatch, b"", status=302)
    with pytest.raises(httpx.HTTPStatusError, match="302"):
        demo.load_surveys(hashlib.sha256(b"approved").hexdigest())
    assert not Path(demo.DSPTS_ZIP).exists()
    stream.assert_called_once_with("GET", demo.DSPTS_URL, follow_redirects=False)


def test_http_failure_does_not_create_archive(demo, monkeypatch):
    response = httpx.Response(503, request=httpx.Request("GET", demo.DSPTS_URL))
    stream = Mock()
    stream.return_value.__enter__ = Mock(return_value=response)
    stream.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(httpx, "stream", stream)
    with pytest.raises(httpx.HTTPStatusError):
        demo.load_surveys(hashlib.sha256(b"approved").hexdigest())
    assert not Path(demo.DSPTS_ZIP).exists()


def test_download_mismatch_is_rejected(demo, monkeypatch, forbid_deserialization):
    data = archive_bytes(
        pickle_payload=pickle.dumps(DeserializationCanary(), protocol=4)
    )
    stream = mock_download(demo, monkeypatch, data)
    parser = Mock(side_effect=AssertionError("ZIP parsed before verification"))
    monkeypatch.setattr(zipfile, "ZipFile", parser)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        demo.load_surveys(hashlib.sha256(b"different archive").hexdigest())
    parser.assert_not_called()
    assert Path(demo.DSPTS_ZIP).read_bytes() == data
    stream.assert_called_once_with("GET", demo.DSPTS_URL, follow_redirects=False)


@pytest.mark.parametrize(
    "text",
    [
        ROW.rstrip().rsplit(",", 1)[0] + "\n",
        ROW.rstrip() + ",extra\n",
        ROW.replace(",100,", ",invalid,"),
        ROW.replace("000000000001", "not-an-api"),
        ROW.replace(",N,", ",invalid,"),
        ROW.replace(",E,", ",invalid,"),
        "",
    ],
)
def test_pinned_schema_rejects_malformed_text(demo, text):
    digest = local_archive(demo, archive_bytes(text))
    with pytest.raises(ValueError, match="survey schema"):
        demo.load_surveys(digest)


@pytest.mark.parametrize("first", [False, True], ids=["last", "first"])
@pytest.mark.parametrize("width", ["short", "long"])
def test_mixed_record_widths_are_rejected_before_dataframe(
    demo, monkeypatch, first, width
):
    malformed = (
        ROW.rstrip().rsplit(",", 1)[0] + "\n"
        if width == "short"
        else ROW.rstrip() + ",extra\n"
    )
    text = malformed + ROW if first else ROW + malformed
    digest = local_archive(demo, archive_bytes(text))
    monkeypatch.setattr(
        pd, "DataFrame", Mock(side_effect=AssertionError("Constructed"))
    )
    with pytest.raises(ValueError, match="survey schema") as error:
        demo.load_surveys(digest)
    record = 1 if first else 2
    assert f"record {record}" in str(error.value.__cause__)


def test_explicitly_empty_optional_coordinate_is_accepted(demo):
    """The trailing comma supplies field 13; an absent field must be rejected."""
    empty_latitude = ROW.rstrip().rsplit(",", 1)[0] + ",\n"
    digest = local_archive(demo, archive_bytes(ROW + empty_latitude))
    result = demo.load_surveys(digest)
    assert len(result) == 2
    assert result["SURF_LATITUDE"].iloc[0] == 28
    assert pd.isna(result["SURF_LATITUDE"].iloc[1])


def test_quoted_fields_are_counted_as_csv_records(demo):
    text = ROW.replace("000000000001", '"000000000001"').replace(",N,", ',"N\n",')
    digest = local_archive(demo, archive_bytes(text))
    result = demo.load_surveys(digest)
    assert len(result) == 1
    assert result["API_WELL_NUMBER"].tolist() == ["000000000001"]
    assert result["WELL_N_S_CODE"].tolist() == ["N"]


def test_missing_text_member_is_rejected(demo):
    digest = local_archive(demo, archive_bytes(member="unexpected.txt"))
    with pytest.raises(ValueError, match="dsptsdelimit.txt"):
        demo.load_surveys(digest)


def test_verified_non_zip_is_rejected(demo):
    digest = local_archive(demo, b"not a ZIP")
    with pytest.raises(zipfile.BadZipFile):
        demo.load_surveys(digest)


def test_cli_requires_digest_before_importing_pipeline(demo):
    with pytest.raises(SystemExit) as error:
        demo.main([])
    assert error.value.code == 2


def test_cli_passes_digest_to_loader(demo, monkeypatch):
    digest = hashlib.sha256(b"synthetic pin").hexdigest()
    loader = Mock(side_effect=RuntimeError("loader reached"))
    monkeypatch.setattr(demo, "load_surveys", loader)
    with pytest.raises(RuntimeError, match="loader reached"):
        demo.main(["--survey-sha256", digest])
    loader.assert_called_once_with(digest)


def test_duplicate_text_member_is_rejected(demo):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("dsptsdelimit.txt", ROW)
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("dsptsdelimit.txt", ROW)
    digest = local_archive(demo, output.getvalue())
    with pytest.raises(ValueError, match="exactly one"):
        demo.load_surveys(digest)


def test_unrelated_archive_members_are_never_unpickled(demo, monkeypatch):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("dsptsdelimit.txt", ROW)
        archive.writestr("dsptsdelimit.bin", b"untrusted serialized object")
    monkeypatch.setattr(pickle, "load", Mock(side_effect=AssertionError("Unpickled")))
    monkeypatch.setattr(
        pd, "read_pickle", Mock(side_effect=AssertionError("Unpickled"))
    )
    digest = local_archive(demo, output.getvalue())
    assert len(demo.load_surveys(digest)) == 1


def test_hashing_and_parsing_share_one_file_handle(demo, monkeypatch):
    digest = local_archive(demo, archive_bytes())
    original = zipfile.ZipFile
    opened = []

    def checked_zip(file):
        assert hasattr(file, "read")
        assert file.tell() == 0
        opened.append(file)
        return original(file)

    monkeypatch.setattr(zipfile, "ZipFile", checked_zip)
    assert len(demo.load_surveys(digest)) == 1
    assert len(opened) == 1
    assert opened[0].closed


def test_download_disconnect_never_reaches_parser(demo, monkeypatch):
    monkeypatch.setattr(
        httpx, "stream", Mock(side_effect=httpx.ConnectError("Disconnected"))
    )
    monkeypatch.setattr(pd, "read_csv", Mock(side_effect=AssertionError("Parsed")))
    with pytest.raises(httpx.ConnectError):
        demo.load_surveys(hashlib.sha256(b"approved").hexdigest())
    assert not Path(demo.DSPTS_ZIP).exists()


def test_documented_worked_example(tmp_path, monkeypatch, capsys):
    """The documented answer is two literal API fields and fourth-field depths."""
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    root = DEMO_PATH.parents[2]
    monkeypatch.chdir(root)
    document = (root / "docs/modules/bsee/survey-archive-integrity.md").read_text()
    example = document.split("```python\n", 1)[1].split("```", 1)[0]
    example_path = tmp_path / "documented_example.py"
    example_path.write_text(example)
    runpy.run_path(str(example_path))
    output = capsys.readouterr().out
    assert "['000000000001', '000000000001']" in output
    assert "[100, 100]" in output
