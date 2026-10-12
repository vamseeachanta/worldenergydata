"""Offline network policy and provenance tests."""

import hashlib
import io
import zipfile
from urllib.error import HTTPError

import pytest

from worldenergydata.bsee.borehole_status_fetch import fetch_file, load_archive


def test_fetch_records_readback_provenance(tmp_path):
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(b"public source")

    record = fetch_file(
        "https://www.data.bsee.gov/Main/Well.aspx",
        tmp_path / "index.html",
        opener=opener,
    )
    assert len(calls) == 1
    assert calls[0][1] == 60
    assert "worldenergydata" in calls[0][0].get_header("User-agent")
    assert record["sha256"] == hashlib.sha256(b"public source").hexdigest()
    assert record["size_bytes"] == 13
    assert record["retrieved_at_utc"].endswith("+00:00")
    assert "terms" in record
    with pytest.raises(FileExistsError):
        fetch_file(record["source_url"], tmp_path / "index.html", opener=opener)
    assert len(calls) == 1


@pytest.mark.parametrize("status", [401, 403, 429])
def test_refusal_never_retried(tmp_path, status):
    calls = []

    def opener(request, timeout):
        calls.append(1)
        raise HTTPError(request.full_url, status, "refused", {}, None)

    with pytest.raises(HTTPError):
        fetch_file(
            "https://www.data.bsee.gov/Main/Well.aspx",
            tmp_path / "refused.html",
            opener=opener,
        )
    assert len(calls) == 1
    assert not (tmp_path / "refused.html").exists()


def test_timeout_one_retry_only(tmp_path):
    calls = []
    sleeps = []

    def opener(request, timeout):
        calls.append(1)
        raise TimeoutError("timeout")

    with pytest.raises(TimeoutError):
        fetch_file(
            "https://www.data.bsee.gov/Main/Well.aspx",
            tmp_path / "timeout.html",
            opener=opener,
            sleep=sleeps.append,
        )
    assert len(calls) == 2
    assert sleeps == [2]


def test_archive_requires_expected_member(tmp_path):
    path = tmp_path / "wrong.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("wrong.txt", "wrong")
    with pytest.raises(ValueError, match="5010.txt"):
        load_archive(path)


def test_invalid_archive_encoding_names_member_and_offset():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("5010.txt", b"abc\xff")
    buffer.seek(0)
    with pytest.raises(ValueError, match="5010.txt.*utf-8-sig.*byte offset 3") as error:
        load_archive(buffer)
    assert isinstance(error.value.__cause__, UnicodeDecodeError)
