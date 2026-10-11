"""Offline download policy and provenance checks."""

import hashlib
import json
import runpy
from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from worldenergydata.bsee.lease_fetch import discover_archives, download

URL = "https://www.data.bsee.gov/Leasing/Files/lseowndelimit.zip"


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.time.sleep", lambda _: None)


class Response(BytesIO):
    def geturl(self) -> str:
        return URL


def test_download_records_readback_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []

    def opened(request: Request, timeout: int) -> Response:
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
    assert "(+https://github.com/vamseeachanta/worldenergydata;" in calls[0][
        0
    ].get_header("User-agent")
    assert record["terms"]["source_url"].endswith("page=Disclaimer")


@pytest.mark.parametrize("status", [401, 403, 429])
def test_access_refusal_never_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    calls: list[Any] = []

    def refused(*args: Any, **kwargs: Any) -> None:
        calls.append(1)
        raise HTTPError(URL, status, "Refused", Message(), None)

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", refused)
    with pytest.raises(PermissionError):
        download(URL, tmp_path / "source.zip")
    assert calls == [1]
    assert not (tmp_path / "source.zip").exists()


def test_transient_failure_has_only_one_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []

    def timed_out(*args: Any, **kwargs: Any) -> None:
        calls.append(1)
        raise TimeoutError("timeout")

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", timed_out)
    monkeypatch.setattr(
        "worldenergydata.bsee.lease_fetch.time.sleep", lambda delay: None
    )
    with pytest.raises(TimeoutError):
        download(URL, tmp_path / "source.zip")
    assert len(calls) == 2


def test_discovers_only_source_published_archive_links() -> None:
    links = discover_archives('<a href="/Leasing/Files/lseowndelimit.zip">Delimit</a>')
    assert links == {"lseowndelimit.zip": URL}


def test_refuses_existing_download_and_external_url(tmp_path: Path) -> None:
    path = tmp_path / "kept.zip"
    path.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        download(URL, path)
    with pytest.raises(ValueError):
        download("https://example.org/file.zip", tmp_path / "new.zip")
    assert path.read_bytes() == b"keep"


def test_partial_fetch_preserves_provenance_and_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    from worldenergydata.bsee.lease_fetch import PAGE, fetch_bundle

    def read(url: str, **kwargs: Any) -> bytes:
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


def test_bundle_paces_every_request_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from worldenergydata.bsee.lease_fetch import PAGE, REQUEST_INTERVAL, fetch_bundle

    events: list[Any] = []

    def opened(request: Request, timeout: int) -> Response:
        events.append(("request", request.full_url))
        body = (
            b'<a href="/Leasing/Files/lseowndelimit.zip">Owner</a>'
            if request.full_url == PAGE
            else b"fixture bytes"
        )
        return Response(body)

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", opened)
    schema = {
        "tables": {
            "owner": {
                "archive": "lseowndelimit.zip",
                "layout_url": "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=leaseOwner",
            }
        }
    }
    records = fetch_bundle(
        schema, tmp_path, sleep=lambda n: events.append(("sleep", n))
    )
    assert REQUEST_INTERVAL >= 2
    assert len(records) == 4
    assert events[::2] == [("sleep", REQUEST_INTERVAL)] * len(records)
    assert events[1::2] == [("request", record["source_url"]) for record in records]


def test_retry_is_also_paced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from worldenergydata.bsee.lease_fetch import REQUEST_INTERVAL

    events: list[Any] = []

    def opened(request: Request, timeout: int) -> Response:
        events.append("request")
        if events.count("request") == 1:
            raise TimeoutError("fixture timeout")
        return Response(b"fixture bytes")

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", opened)
    download(URL, tmp_path / "source.zip", sleep=lambda n: events.append(n))
    assert events == [REQUEST_INTERVAL, "request", REQUEST_INTERVAL, "request"]


def test_challenge_body_stops_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []

    def challenged(request: Request, timeout: int) -> Response:
        calls.append(request.full_url)
        return Response(b"<html>Verify you are human</html>")

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", challenged)
    with pytest.raises(PermissionError, match="challenge"):
        download(URL, tmp_path / "archive.zip")
    assert calls == [URL]
    assert not (tmp_path / "archive.zip").exists()


def fixture_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], Path, Path, list[dict[str, Any]], bytes]:
    from worldenergydata.bsee.lease_fetch import PAGE, fetch_bundle

    root = Path(__file__).resolve().parents[4]
    directory = root / "data/modules/bsee/leases"
    schema = json.loads((directory / "source_schema.json").read_text())
    anchors = "".join(
        f'<a href="/Leasing/Files/{spec["archive"]}">Archive</a>'
        for spec in schema["tables"].values()
    ).encode()

    def opened(request: Request, timeout: int) -> Response:
        return Response(anchors if request.full_url == PAGE else b"fixture bytes")

    monkeypatch.setattr("worldenergydata.bsee.lease_fetch.urlopen", opened)
    raw = tmp_path / "raw"
    records = fetch_bundle(schema, raw)
    script = runpy.run_path(str(root / "scripts/bsee/fetch_leases.py"))
    output = tmp_path / "output"
    output.mkdir()
    committed = (directory / "source_manifest.json").read_bytes()
    (output / "source_manifest.json").write_bytes(committed)
    return script, raw, output, records, committed


def test_fixture_manifest_has_committed_shape_and_reports_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script, raw, output, records, committed = fixture_manifest(tmp_path, monkeypatch)
    script["publish_manifest"](records, raw, output, update=True)
    emitted = json.loads((raw / "source_manifest.json").read_text())
    reference = json.loads(committed)
    assert emitted.keys() == reference.keys()
    assert len(emitted["files"]) == len(reference["files"])
    for actual, expected in zip(emitted["files"], reference["files"]):
        assert actual.keys() == expected.keys()
        assert actual["terms"].keys() == expected["terms"].keys()
    assert (raw / "source_manifest.json").read_bytes() == (
        output / "source_manifest.json"
    ).read_bytes()
    records[0]["sha256"] = "0" * 64
    script["publish_manifest"](records, raw, output, update=False)
    assert "sha256" in capsys.readouterr().out


def test_script_without_update_flag_preserves_committed_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script, raw, output, records, committed = fixture_manifest(tmp_path, monkeypatch)
    globals_ = script["main"].__globals__
    monkeypatch.setitem(globals_, "fetch_bundle", lambda schema, destination: records)
    monkeypatch.setattr(
        "sys.argv",
        [
            "fetch_leases.py",
            "--raw-dir",
            str(raw),
            "--output-dir",
            str(output),
        ],
    )
    script["main"]()
    assert (output / "source_manifest.json").read_bytes() == committed
    assert (raw / "source_manifest.json").is_file()
