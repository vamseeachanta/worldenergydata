"""Offline fetch policy probes; transport payloads are explicitly synthetic."""

import io
import json
import zipfile
from urllib.error import HTTPError

import pytest

from scripts.bsee.fetch_sands_atlas import verify_retained_files
from worldenergydata.bsee import atlas_fetch

from .test_atlas import FIXTURES, SCHEMA


def test_fetch_preserves_existing_disclaimer(tmp_path):
    path = tmp_path / "disclaimer.html"
    path.write_text("retained evidence")
    with pytest.raises(FileExistsError):
        atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert path.read_text() == "retained evidence"


def test_refusal_stops_after_one_request(tmp_path, monkeypatch):
    calls = []

    def refuse(url):
        calls.append(url)
        raise HTTPError(url, 403, "refused", {}, None)

    monkeypatch.setattr(atlas_fetch, "_request_bytes", refuse)
    with pytest.raises(HTTPError):
        atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert calls == [atlas_fetch.SOURCE_PAGE]
    assert json.loads((tmp_path / "refusal.json").read_text())["http_status"] == 403
    assert (
        json.loads((tmp_path / "handmade-fixture.json").read_text())["synthetic"]
        is True
    )


def test_sequential_fetch_manifest_and_real_fixture_export(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("synthetic.accdb", b"synthetic transport fixture")
    link = "https://www.data.bsee.gov/GGStudies/Files/2023%20Atlas%20Update.zip"
    calls = []

    def retrieve(url):
        calls.append(url)
        payload = {
            atlas_fetch.SOURCE_PAGE: f'<a href="{link}">Download</a>'.encode(),
            atlas_fetch.TERMS_URL: b"synthetic disclaimer transport fixture",
            link: archive.getvalue(),
        }[url]
        return payload

    def export(command, stdout, check):
        assert check
        stdout.write((FIXTURES / f"{command[-1]}.csv").read_text())

    monkeypatch.setattr(atlas_fetch, "_request_bytes", retrieve)
    monkeypatch.setattr(atlas_fetch.subprocess, "run", export)
    manifest = atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert calls == [atlas_fetch.SOURCE_PAGE, atlas_fetch.TERMS_URL, link]
    assert manifest["row_counts"]["2023sands"] == 5
    for record in manifest["files"]:
        assert record["sha256"] and record["size_bytes"] > 0
        assert record["retrieved_at_utc"] and record["terms"]


def test_incomplete_manifest_cannot_validate_consumed_tables(tmp_path):
    with pytest.raises(ValueError, match="manifest"):
        verify_retained_files(tmp_path, {"files": []})


def test_transport_pins_host_headers_closes_and_rejects_redirect(monkeypatch):
    calls = []
    closed = []
    status = [200]

    class Connection:
        def __init__(self, host, timeout):
            assert host == "www.data.bsee.gov"
            assert timeout == 120

        def request(self, method, target, headers):
            calls.append((method, target, headers))

        def getresponse(self):
            class Response:
                reason = "synthetic transport response"
                headers = {}

                def read(self):
                    return b"synthetic transport payload"

            response = Response()
            response.status = status[0]
            return response

        def close(self):
            closed.append(True)

    monkeypatch.setattr(atlas_fetch, "HTTPSConnection", Connection)
    assert (
        atlas_fetch._request_bytes(atlas_fetch.SOURCE_PAGE)
        == b"synthetic transport payload"
    )
    assert calls[0] == (
        "GET",
        "/Main/GandG.aspx",
        {"User-Agent": atlas_fetch.USER_AGENT},
    )
    status[0] = 302
    with pytest.raises(HTTPError):
        atlas_fetch._request_bytes(atlas_fetch.SOURCE_PAGE)
    assert len(calls) == len(closed) == 2
