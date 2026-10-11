"""Offline download policy and provenance checks."""

import hashlib
from io import BytesIO
from urllib.error import HTTPError

import pytest

from worldenergydata.bsee.lease_fetch import discover_archives, download

URL = "https://www.data.bsee.gov/Leasing/Files/lseowndelimit.zip"


class Response(BytesIO):
    def geturl(self):
        return URL


def test_download_records_readback_provenance(tmp_path, monkeypatch):
    calls = []

    def opened(request, timeout):
        calls.append((request, timeout))
        return Response(b"public bytes")

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", opened)
    target = tmp_path / "source.zip"
    record = download(URL, target)
    assert record["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert record["size_bytes"] == 12
    assert record["source_url"] == URL
    assert record["retrieved_at_utc"].endswith("Z")
    assert len(calls) == 1
    assert calls[0][1] == 45
    assert "WorldEnergyData" in calls[0][0].get_header("User-agent")
    assert record["terms"]["source_url"].endswith("page=Disclaimer")


@pytest.mark.parametrize("status", [401, 403, 429])
def test_access_refusal_never_retries(tmp_path, monkeypatch, status):
    calls = []

    def refused(*args, **kwargs):
        calls.append(1)
        raise HTTPError(URL, status, "Refused", {}, None)

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", refused)
    with pytest.raises(PermissionError):
        download(URL, tmp_path / "source.zip")
    assert calls == [1]
    assert not (tmp_path / "source.zip").exists()


def test_transient_failure_has_only_one_retry(tmp_path, monkeypatch):
    calls = []

    def timed_out(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("timeout")

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", timed_out)
    monkeypatch.setattr(
        "worldenergydata.bsee.lease_fetch.time.sleep", lambda delay: None
    )
    with pytest.raises(TimeoutError):
        download(URL, tmp_path / "source.zip")
    assert len(calls) == 2


def test_discovers_only_source_published_archive_links():
    links = discover_archives('<a href="/Leasing/Files/lseowndelimit.zip">Delimit</a>')
    assert links == {"lseowndelimit.zip": URL}


def test_refuses_existing_download_and_external_url(tmp_path):
    path = tmp_path / "kept.zip"
    path.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        download(URL, path)
    with pytest.raises(ValueError):
        download("https://example.org/file.zip", tmp_path / "new.zip")
    assert path.read_bytes() == b"keep"


def test_partial_fetch_preserves_provenance_and_refusal(tmp_path, monkeypatch):
    import json

    from worldenergydata.bsee.lease_fetch import PAGE, fetch_bundle

    def read(url):
        if url == PAGE:
            return b'<a href="/Leasing/Files/lseowndelimit.zip">Owner</a>'
        if url == URL:
            raise PermissionError("BSEE automated access refused: HTTP 403")
        return b"public layout or terms"

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch._read", read)
    schema = {
        "tables": {
            "owner": {
                "archive": "lseowndelimit.zip",
                "layout_url": "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=leaseOwner",
            }
        }
    }
    with pytest.raises(PermissionError):
        fetch_bundle(schema, tmp_path)
    saved = json.loads((tmp_path / "leasing-page.html.provenance.json").read_text())
    assert (
        saved["sha256"]
        == hashlib.sha256((tmp_path / "leasing-page.html").read_bytes()).hexdigest()
    )
    assert json.loads((tmp_path / "interruption.json").read_text())["reason"].endswith(
        "HTTP 403"
    )
    assert not (tmp_path / "lseowndelimit.zip").exists()
