# ABOUTME: Exercise monthly public HSE collection with synthetic offline responses.
# ABOUTME: Check provenance, access rules, retained files and strict configuration.

from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZIP_LZMA, ZipFile, ZipInfo

import httpx
import pytest
import yaml

from worldenergydata.hse.monthly_refresh import load_config, main, run_refresh

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)
UA = "synthetic-hse-refresh/1 (+https://example.org/project)"


def source(**changes: Any) -> dict[str, Any]:
    return {
        "id": "synthetic",
        "authority": "Synthetic public authority",
        "description": "Synthetic test records",
        "licence": "Synthetic fixture",
        "terms_url": "https://example.org/terms",
        "kind": "bulk_file",
        "expect": "zip",
        "required": True,
        "enabled": True,
        "urls": ["https://example.org/data.zip"],
    } | changes


def config_file(tmp_path: Path, *rows: dict[str, Any]) -> Path:
    path = tmp_path / "sources.yml"
    payload = {
        "schema_version": 1,
        "user_agent": UA,
        "sources": list(rows or [source()]),
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def archive(name: str = "records.csv") -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w") as zipped:
        zipped.writestr(ZipInfo(name), "id,value\n1,alpha\n2,beta\n")
        zipped.writestr(ZipInfo("readme.bin"), b"synthetic")
    return stream.getvalue()


def corrupt_archive(compression: int = ZIP_DEFLATED) -> bytes:
    stream = io.BytesIO()
    member = ZipInfo("records.csv", date_time=(1980, 1, 1, 0, 0, 0))
    member.compress_type = compression
    member.external_attr = 0o600 << 16
    with ZipFile(stream, "w") as zipped:
        zipped.writestr(member, "id,value\n1,synthetic\n")
    payload = bytearray(stream.getvalue())
    payload[30 + len("records.csv") + (4 if compression == ZIP_LZMA else 0)] = 255
    return bytes(payload)


def refresh(tmp_path: Path, handler: Any, *rows: dict[str, Any], **kwargs: Any) -> dict:
    config = load_config(config_file(tmp_path, *rows))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return run_refresh(
            config,
            tmp_path / "output",
            client=client,
            now=NOW,
            sleep=lambda _: None,
            **kwargs,
        )


def response_handler(
    payload: bytes, requests: list | None = None, content_type: str = "application/zip"
) -> Any:
    def handle(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            content=payload,
            headers={
                "Content-Type": content_type,
                "ETag": '"fixture-1"',
                "Last-Modified": "Thu, 12 Nov 2026 08:00:00 GMT",
            },
        )

    return handle


def test_valid_and_shipped_config(tmp_path: Path) -> None:
    config = load_config(config_file(tmp_path))
    assert config.user_agent == UA and config.sources[0].id == "synthetic"
    assert len(load_config(ROOT / "config/hse/monthly_sources.yml").sources) >= 5


@pytest.mark.parametrize("field", list(source()))
def test_missing_source_fields(tmp_path: Path, field: str) -> None:
    row = source()
    del row[field]
    with pytest.raises(ValueError, match=field):
        load_config(config_file(tmp_path, row))


@pytest.mark.parametrize(
    "changes",
    [
        {"unknown": 1},
        {"id": "Bad-ID"},
        {"id": "../escape"},
        {"authority": " "},
        {"description": None},
        {"licence": ""},
        {"kind": "api"},
        {"expect": "txt"},
        {"expect": ["zip"]},
        {"required": "true"},
        {"enabled": 1},
        {"urls": []},
        {"urls": "https://example.org/data.zip"},
        {"urls": ["http://example.org/data.zip"]},
        {"urls": ["https://account:secret@example.org/data.zip"]},
        {"urls": ["https://example.org:bad/data.zip"]},
        {"urls": ["https://example.org/bad path.zip"]},
        {"terms_url": "file:terms"},
        {"kind": "manual"},
        {"kind": "manual", "manual_drop_dir": "../escape"},
        {"kind": "manual", "manual_drop_dir": "C:\\escape"},
        {"kind": "manual", "manual_drop_dir": "/escape"},
        {"urls": ["https://example.org/a.zip", "https://example.org/other/a.zip"]},
        {"urls": ["https://example.org/manifest.json"]},
        {"urls": ["https://example.org/links.json"]},
        {"urls": ["https://example.org/%2e%2e"]},
    ],
)
def test_invalid_source(tmp_path: Path, changes: dict) -> None:
    with pytest.raises(ValueError):
        load_config(config_file(tmp_path, source(**changes)))


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"schema_version": "1"},
        {"schema_version": 2},
        {"sources": []},
        {"sources": {}},
        {"user_agent": ""},
        {"user_agent": "agent\r\nInjected: yes"},
        {"unknown": True},
    ],
)
def test_invalid_root(tmp_path: Path, change: dict) -> None:
    path = config_file(tmp_path)
    path.write_text(yaml.safe_dump(yaml.safe_load(path.read_text()) | change))
    with pytest.raises(ValueError):
        load_config(path)


def test_duplicate_sources_and_yaml_keys(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        load_config(config_file(tmp_path, source(), source()))
    path = config_file(tmp_path)
    path.write_text(path.read_text() + "schema_version: 1\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_config(path)


def test_zip_success_provenance_and_unchanged(tmp_path: Path) -> None:
    payload, requests = archive(), []
    handler = response_handler(payload, requests)
    first = refresh(tmp_path, handler)
    manifest = first["sources"][0]
    assert manifest["status"] == "success"
    assert manifest["source_id"] == "synthetic"
    assert manifest["month"] == "2026-11"
    record = manifest["files"][0]
    assert record["sha256"] == hashlib.sha256(payload).hexdigest()
    assert record["bytes"] == len(payload)
    assert record["http_status"] == 200
    assert record["url"] == record["effective_url"] == "https://example.org/data.zip"
    assert record["content_type"] == "application/zip"
    assert record["etag"] == '"fixture-1"'
    assert record["last_modified"].endswith("GMT")
    assert record["retrieved_at_utc"] == "2026-11-12T09:00:00Z"
    assert record["members"][0] == {"name": "records.csv", "bytes": 24, "rows": 2}
    output = tmp_path / "output"
    assert (output / record["path"]).read_bytes() == payload
    latest_path = output / "synthetic/latest.json"
    assert json.loads(latest_path.read_text()) == manifest
    assert (
        first["config_sha256"]
        == hashlib.sha256((tmp_path / "sources.yml").read_bytes()).hexdigest()
    )
    assert json.loads((output / "refresh-summary.json").read_text()) == first
    second = refresh(tmp_path, handler, month="2026-12")
    assert second["sources"][0]["status"] == "unchanged"
    assert second["sources"][0]["files"][0]["path"] == record["path"]
    assert not (output / "synthetic/2026-12/data.zip").exists()
    assert json.loads(latest_path.read_text())["month"] == "2026-12"
    assert all(request.headers["User-Agent"] == UA for request in requests)


@pytest.mark.parametrize(
    "kind,status",
    [
        ("html", "unexpected_content"),
        (403, "blocked"),
        (401, "blocked"),
        (429, "blocked"),
        (500, "failed"),
    ],
)
def test_data_failure_not_retried(tmp_path: Path, kind: Any, status: str) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200 if kind == "html" else kind, text="<html>denied</html>"
        )

    summary = refresh(tmp_path, handler)
    assert summary["sources"][0]["status"] == status
    assert summary["sources"][0]["files"][0]["reason"]
    assert summary["required_failures"] == ["synthetic"]
    assert requests.count("https://example.org/data.zip") == 1
    assert not list((tmp_path / "output").rglob("*.zip"))


@pytest.mark.parametrize(
    "code,status",
    [(403, "blocked"), (401, "blocked"), (500, "robots_unavailable"), (429, "blocked")],
)
def test_robots_responses(tmp_path: Path, code: int, status: str) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return (
            httpx.Response(code)
            if request.url.path == "/robots.txt"
            else httpx.Response(200, content=archive())
        )

    assert refresh(tmp_path, handler)["sources"][0]["status"] == status
    assert len(requests) == (2 if status == "success" else 1)
    assert "https://example.org/data.zip" not in requests


def test_robots_disallow_and_timeout(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        return httpx.Response(
            200, text="User-agent: synthetic-hse-refresh\nDisallow: /\n"
        )

    assert refresh(tmp_path, handler)["sources"][0]["status"] == "disallowed_by_robots"

    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("synthetic offline error", request=request)

    assert (
        refresh(tmp_path, unavailable)["sources"][0]["status"] == "robots_unavailable"
    )


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
def test_listing_links_and_reuse(tmp_path: Path, encoding: str) -> None:
    html = """<html><a href="/reports/a.pdf">A café <b>report</b></a>
    <a href="/reports/a.pdf">Duplicate</a><a href="/sites/file">Site</a>
    <a href="https://example.org/media/item">Media</a><a href="https://[">Broken</a></html>"""
    listing = source(
        kind="listing_page", expect="html", urls=["https://example.org/listing"]
    )
    handler = response_handler(
        html.encode(encoding), content_type=f"text/html; charset={encoding}"
    )
    summary = refresh(tmp_path, handler, listing)
    assert summary["sources"][0]["status"] == "success"
    path = tmp_path / "output/synthetic/2026-11/links.json"
    assert json.loads(path.read_text()) == [
        {"url": "https://example.org/media/item", "text": "Media"},
        {"url": "https://example.org/reports/a.pdf", "text": "A café report"},
        {"url": "https://example.org/sites/file", "text": "Site"},
    ]
    refresh(tmp_path, handler, listing, month="2026-12")
    assert (path.parent.parent / "2026-12/links.json").read_bytes() == path.read_bytes()


def test_manual_pending_and_present(tmp_path: Path) -> None:
    row = source(kind="manual", manual_drop_dir="synthetic/manual")

    def no_network(request: httpx.Request) -> httpx.Response:
        pytest.fail("manual source attempted a request")

    summary = refresh(tmp_path, no_network, row)
    assert summary["sources"][0]["status"] == "manual_pending"
    assert "https://example.org/data.zip" in summary["sources"][0]["reason"]
    assert summary["required_failures"] == ["synthetic"]
    drop = tmp_path / "output/synthetic/manual"
    drop.mkdir()
    (drop / "manual.zip").write_bytes(archive())
    summary = refresh(tmp_path, no_network, row)
    assert summary["sources"][0]["status"] == "manual_present"
    record = summary["sources"][0]["files"][0]
    assert record["name"] == "manual.zip"
    assert record["sha256"] == hashlib.sha256(archive()).hexdigest()
    assert record["mtime"].endswith("Z")
    assert summary["required_failures"] == []


def test_archive_member_traversal_never_extracted(tmp_path: Path) -> None:
    summary = refresh(tmp_path, response_handler(archive("../../escaped.csv")))
    assert summary["sources"][0]["files"][0]["members"][0]["rows"] == 2
    assert not list(tmp_path.rglob("escaped.csv"))


def test_cli_failure_and_configuration_error(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    import worldenergydata.hse.monthly_refresh as module

    real_client = httpx.Client
    monkeypatch.setattr(
        module.httpx,
        "Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(lambda req: httpx.Response(403))
        ),
    )
    args = [
        "--config",
        str(config_file(tmp_path)),
        "--output-root",
        str(tmp_path / "output"),
    ]
    assert main(args + ["--json"]) == 1
    assert json.loads(capsys.readouterr().out)["required_failures"] == ["synthetic"]
    assert main(args + ["--source", "unknown"]) == 2
    assert main(args + ["--month", "2026-13"]) == 2


def test_dry_run_disabled_and_environment_root(
    tmp_path: Path, monkeypatch: Any
) -> None:
    config = load_config(
        config_file(tmp_path, source(), source(id="disabled", enabled=False))
    )
    monkeypatch.delenv("WED_HSE_SOURCES_ROOT", raising=False)
    with pytest.raises(ValueError, match="output"):
        run_refresh(config, None)
    monkeypatch.setenv("WED_HSE_SOURCES_ROOT", str(tmp_path / "output"))
    result = run_refresh(config, None, dry_run=True, now=NOW)
    assert result["counts"] == {"dry_run": 1, "skipped_disabled": 1}
    assert not (tmp_path / "output").exists()


def test_same_month_reuse_and_older_month_does_not_replace_latest(
    tmp_path: Path,
) -> None:
    handler = response_handler(archive())
    refresh(tmp_path, handler)
    assert refresh(tmp_path, handler)["sources"][0]["status"] == "unchanged"
    assert (tmp_path / "output/synthetic/2026-11/data.zip").exists()
    refresh(tmp_path, handler, month="2026-10")
    latest = json.loads((tmp_path / "output/synthetic/latest.json").read_text())
    assert latest["month"] == "2026-11"
    (tmp_path / "output/synthetic/2026-11/data.zip").unlink()
    result = refresh(tmp_path, handler, month="2026-12")
    assert result["sources"][0]["status"] == "success"
    assert (tmp_path / "output/synthetic/2026-12/data.zip").is_file()


def test_redirects_checked_and_paced(tmp_path: Path) -> None:
    requests, sleeps = [], []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "example.org":
            return httpx.Response(
                302, headers={"Location": "https://example.net/data.zip"}
            )
        return httpx.Response(200, content=archive())

    config = load_config(config_file(tmp_path))
    with httpx.Client(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        result = run_refresh(
            config,
            tmp_path / "output",
            client=client,
            now=NOW,
            sleep=sleeps.append,
            clock=lambda: 0.0,
        )
    assert result["sources"][0]["status"] == "success"
    assert requests == [
        "https://example.org/robots.txt",
        "https://example.org/data.zip",
        "https://example.net/robots.txt",
        "https://example.net/data.zip",
    ]
    assert sleeps == [1.0, 1.0]


def test_insecure_redirect_never_requested(tmp_path: Path) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return (
            httpx.Response(404)
            if request.url.path == "/robots.txt"
            else httpx.Response(
                302, headers={"Location": "http://example.org/plain.zip"}
            )
        )

    assert refresh(tmp_path, handler)["sources"][0]["status"] == "failed"
    assert len(requests) == 2


@pytest.mark.parametrize("failure", ["network", "payload", "manifest"])
def test_partial_same_month_failure_preserves_latest_bytes(
    tmp_path: Path, monkeypatch: Any, failure: str
) -> None:
    row = source(
        urls=["https://example.org/first.zip", "https://example.org/second.zip"]
    )
    initial = refresh(tmp_path, response_handler(archive()), row)
    output = tmp_path / "output"
    latest_bytes = (output / "synthetic/latest.json").read_bytes()
    retained = {
        r["path"]: (output / r["path"]).read_bytes()
        for r in initial["sources"][0]["files"]
    }

    def partial(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if failure == "network" and request.url.path == "/second.zip":
            return httpx.Response(403)
        return httpx.Response(200, content=archive("changed.csv"))

    if failure != "network":
        import worldenergydata.hse.monthly_refresh as module

        original = module._write

        def fail_write(path: Path, payload: bytes) -> None:
            target = "second.zip" if failure == "payload" else "manifest.json"
            if path.name.endswith(target) and b'"status": "failed"' not in payload:
                raise OSError("synthetic storage failure")
            original(path, payload)

        monkeypatch.setattr(module, "_write", fail_write)
    result = refresh(tmp_path, partial, row)
    assert result["required_failures"] == ["synthetic"]
    assert (output / "synthetic/latest.json").read_bytes() == latest_bytes
    assert all(
        (output / path).read_bytes() == content for path, content in retained.items()
    )


def test_multiple_listing_pages_share_sorted_index(tmp_path: Path) -> None:
    row = source(
        kind="listing_page",
        expect="html",
        urls=["https://example.org/first", "https://example.org/second"],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        link = "a" if request.url.path == "/first" else "b"
        return httpx.Response(
            200, text=f'<html><a href="/{link}.pdf">{link}</a></html>'
        )

    refresh(tmp_path, handler, row)
    links = json.loads((tmp_path / "output/synthetic/2026-11/links.json").read_text())
    assert [r["url"] for r in links] == [
        "https://example.org/a.pdf",
        "https://example.org/b.pdf",
    ]


def test_manual_symlink_escape_is_not_consumed(tmp_path: Path) -> None:
    (output := tmp_path / "output").mkdir()
    try:
        (output / "escape").symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable")
    row = source(kind="manual", manual_drop_dir="escape")
    result = refresh(tmp_path, response_handler(archive()), row)
    assert result["sources"][0]["status"] == "failed"
    assert result["sources"][0]["files"] == []


@pytest.mark.parametrize("location", ["/robots-next.txt", "http://example.org/plain"])
def test_redirected_robots_failure_blocks_data(tmp_path: Path, location: str) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(302, headers={"Location": location})
        return httpx.Response(503)

    assert refresh(tmp_path, handler)["sources"][0]["status"] == "robots_unavailable"
    assert "https://example.org/data.zip" not in requests


@pytest.mark.parametrize(
    "expect,payload,valid",
    [
        ("json", b'{"synthetic": true}', True),
        ("json", b"<html>error</html>", False),
        ("csv", b"id,value\n1,synthetic\n", True),
        ("csv", b"<html>error</html>", False),
        ("pdf", b"%PDF-1.7\nsynthetic", True),
        ("pdf", b"plain text", False),
        ("html", b"<html>synthetic</html>", True),
        ("html", b"plain text", False),
        ("zip", b"PKinvalid archive", False),
        ("xlsx", archive(), False),
        ("zip", corrupt_archive(), False),
        ("csv", b"plain text", False),
        ("zip", corrupt_archive(ZIP_LZMA), False),
    ],
    ids=[
        "json-valid",
        "json-html",
        "csv-valid",
        "csv-html",
        "pdf-valid",
        "pdf-plain-text",
        "html-valid",
        "html-plain-text",
        "zip-invalid",
        "xlsx-missing-workbook",
        "zip-corrupt-deflate",
        "csv-plain-text",
        "zip-corrupt-lzma",
    ],
)
def test_content_sniffs(
    tmp_path: Path, expect: str, payload: bytes, valid: bool
) -> None:
    row = source(expect=expect, urls=[f"https://example.org/file.{expect}"])
    handler = response_handler(payload)
    control = source(id="control", urls=["https://example.org/control.zip"])

    def responses(request: httpx.Request) -> httpx.Response:
        return (
            httpx.Response(200, content=archive())
            if request.url.path == "/control.zip"
            else handler(request)
        )

    result = refresh(tmp_path, responses, row, control)
    assert result["sources"][0]["status"] == (
        "success" if valid else "unexpected_content"
    )
    assert result["sources"][1]["status"] == "success"


def test_backfill_preserves_every_manifest_payload(tmp_path: Path) -> None:
    first, second, backfill = archive("a.csv"), archive("b.csv"), archive("c.csv")
    for month, payload in [
        ("2026-09", first),
        ("2026-10", first),
        ("2026-11", second),
        ("2026-09", backfill),
    ]:
        result = refresh(tmp_path, response_handler(payload), month=month)
        assert result["sources"][0]["status"] == (
            "unchanged" if month == "2026-10" else "success"
        )
    output = tmp_path / "output"
    manifests = list(output.rglob("manifest.json")) + list(output.rglob("latest.json"))
    assert len(manifests) == 4
    for path in manifests:
        for record in json.loads(path.read_text())["files"]:
            retained = output / record["path"]
            assert retained.is_file()
            assert hashlib.sha256(retained.read_bytes()).hexdigest() == record["sha256"]
    assert (output / "synthetic/2026-09/data.zip").read_bytes() == first
    assert (
        json.loads((output / "synthetic/latest.json").read_text())["month"] == "2026-11"
    )


def test_changed_same_month_payload_is_write_once(tmp_path: Path) -> None:
    original, changed = archive(), archive("changed.csv")
    first = refresh(tmp_path, response_handler(original))["sources"][0]
    second = refresh(tmp_path, response_handler(changed))["sources"][0]
    output = tmp_path / "output"
    assert (output / first["files"][0]["path"]).read_bytes() == original
    record = second["files"][0]
    assert record["path"] == f"synthetic/2026-11/{record['sha256'][:12]}-data.zip"
    assert (output / record["path"]).read_bytes() == changed
    third = refresh(tmp_path, response_handler(changed))["sources"][0]
    assert third["status"] == "unchanged"
    assert third["files"][0]["path"] == record["path"]
    assert len(list(output.rglob("*.zip"))) == 2


@pytest.mark.parametrize(
    "source_id,html,expected",
    [
        (
            "havtil_investigations_listing",
            '<a href="/en/supervision/investigation-reports/2026/'
            'investigation-of-an-incident/">Investigation of an incident</a>'
            '<a href="/en/about-us/contact/">Contact</a>',
            {
                "/en/supervision/investigation-reports/2026/"
                "investigation-of-an-incident/": "Investigation of an incident"
            },
        ),
        (
            "havtil_rnnp_listing",
            '<a href="/en/explore-technical-subjects2/rnnp/2026/">RNNP 2026</a>'
            '<a href="/reports/rnnp.pdf">Annual report</a>'
            '<a href="/en/about-us/contact/">Contact</a>',
            {
                "/en/explore-technical-subjects2/rnnp/2026/": "RNNP 2026",
                "/reports/rnnp.pdf": "Annual report",
            },
        ),
        (
            "csb_investigations_listing",
            '<a href="/example-plant-explosion-/" id="x" tt="inv" '
            'class="linkHd" TID="1"><span>Example Plant Explosion</span></a>'
            '<a href="/career-opportunities/" style="">Career Opportunities</a>'
            '<a href="/example-plant-explosion-/" class="rmore">'
            "full Investigation details</a>",
            {"/example-plant-explosion-/": "Example Plant Explosion"},
        ),
        (
            "imca_safety_flashes_listing",
            '<a href="/resources/safety/safety-flashes/'
            '1926-dropped-bulk-bag-during-loading-operations/">Dropped bulk bag</a>'
            '<a href="/resources/safety/safety-flashes/rss-feed/">RSS</a>'
            '<a href="/login/?redirectUrl=...">Login</a>',
            {
                "/resources/safety/safety-flashes/"
                "1926-dropped-bulk-bag-during-loading-operations/": "Dropped bulk bag"
            },
        ),
        (
            "emsa_emcip_listing",
            '<a href="/emcip/items.html?cid=141&amp;id=5844">Annual overview</a>'
            '<a href="/about.html">About</a>',
            {"/emcip/items.html?cid=141&id=5844": "Annual overview"},
        ),
        (
            "bsee_safety_alerts_listing",
            '<a href="/safety-alerts/safety-alert-526">Safety alert 526</a>'
            '<a href="/reports/alert.pdf">Alert PDF</a>'
            '<a href="/about-bsee">About</a>',
            {
                "/safety-alerts/safety-alert-526": "Safety alert 526",
                "/reports/alert.pdf": "Alert PDF",
            },
        ),
    ],
)
def test_configured_listing_shapes(
    tmp_path: Path, source_id: str, html: str, expected: dict[str, str]
) -> None:
    rows = yaml.safe_load((ROOT / "config/hse/monthly_sources.yml").read_text())[
        "sources"
    ]
    row = next(row for row in rows if row["id"] == source_id)
    # Synthetic origin retains the supplied official path and anchor shapes.
    row["urls"] = ["https://example.org/listing"]
    result = refresh(tmp_path, response_handler(html.encode()), row)
    assert result["sources"][0]["status"] == "success"
    links = tmp_path / f"output/{source_id}/2026-11/links.json"
    assert json.loads(links.read_text()) == [
        {"url": "https://example.org" + url, "text": text}
        for url, text in sorted(expected.items())
    ]


@pytest.mark.parametrize(
    "selectors",
    [
        {"link_patterns": "report"},
        {"link_classes": "title"},
        {"link_patterns": None},
        {"link_classes": {}},
        {"link_patterns": [5]},
        {"link_classes": [None]},
        {"link_patterns": ["["]},
        {"link_patterns": [""]},
        {"link_classes": [""]},
        {"link_classes": ["two tokens"]},
    ],
)
def test_invalid_listing_selectors(tmp_path: Path, selectors: dict) -> None:
    row = source(kind="listing_page", expect="html", **selectors)
    with pytest.raises(ValueError, match="link_"):
        load_config(config_file(tmp_path, row))


@pytest.mark.parametrize("kind", ["bulk_file", "manual"])
@pytest.mark.parametrize("field", ["link_patterns", "link_classes"])
def test_selectors_require_listing_kind(tmp_path: Path, kind: str, field: str) -> None:
    row = source(kind=kind, manual_drop_dir="manual", **{field: ["report"]})
    with pytest.raises(ValueError, match="listing_page"):
        load_config(config_file(tmp_path, row))


@pytest.mark.parametrize("required", [False, True])
@pytest.mark.parametrize("selectors", [{}, {"link_patterns": []}, {"link_classes": []}])
def test_listing_without_links_is_failure(
    tmp_path: Path, required: bool, selectors: dict
) -> None:
    row = source(kind="listing_page", expect="html", required=required, **selectors)
    # Explicit empty selectors must not fall back to the default PDF rule.
    html = b'<html><a href="/report.pdf">Report</a></html>' if selectors else b"<html/>"
    handler = response_handler(html)
    for _ in range(2):
        result = refresh(tmp_path, handler, row)
        manifest = result["sources"][0]
        assert manifest["status"] == "no_links"
        assert manifest["reason"]
        assert result["required_failures"] == (["synthetic"] if required else [])
    assert not (tmp_path / "output/synthetic/latest.json").exists()
    assert not (tmp_path / "output/synthetic/2026-11/links.json").exists()


def test_listing_selectors_or_and_first_nonempty_title(tmp_path: Path) -> None:
    row = source(
        kind="listing_page",
        expect="html",
        link_patterns=[r"https://example\.org/reports/"],
        link_classes=["linkHd"],
        urls=["https://example.org/first", "https://example.org/second"],
    )
    pages = {
        "/first": '<a href="/class" class="other linkHd"> </a>'
        '<a href="/reports/a"> </a><a href="/reports/a">Title</a>'
        '<a href="/reports/a">Duplicate</a><a href="/default.pdf">Dropped</a>'
        '<a href="/substring" class="linkHdOther">Dropped</a>',
        "/second": '<a href="/class" class="linkHd">Class title</a>'
        '<a href="/reports/a">Later title</a>',
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=pages[request.url.path])

    result = refresh(tmp_path, handler, row)
    assert result["sources"][0]["status"] == "success"
    index = tmp_path / "output/synthetic/2026-11/links.json"
    assert json.loads(index.read_text()) == [
        {"url": "https://example.org/class", "text": "Class title"},
        {"url": "https://example.org/reports/a", "text": "Title"},
    ]


def test_listing_retains_links_only_and_compares_page_digests(tmp_path: Path) -> None:
    row = source(
        kind="listing_page", expect="html", urls=["https://example.org/listing.html"]
    )
    original = b'<html><a href="/report.pdf">Report</a><nav>Navigation</nav></html>'
    for month, payload, status in [
        ("2026-09", original, "success"),
        ("2026-10", original, "unchanged"),
        ("2026-10", original + b"<!-- changed -->", "success"),
    ]:
        result = refresh(tmp_path, response_handler(payload), row, month=month)
        manifest = result["sources"][0]
        assert manifest["status"] == status
        record = manifest["files"][0]
        assert "path" not in record
        assert record["retained"] == "links_only"
        assert record["url"] == row["urls"][0]
        assert record["http_status"] == 200
        assert record["bytes"] == len(payload)
        assert record["sha256"] == hashlib.sha256(payload).hexdigest()
        assert record["retrieved_at_utc"] == "2026-11-12T09:00:00Z"
        directory = tmp_path / f"output/synthetic/{month}"
        assert json.loads((directory / "manifest.json").read_text()) == manifest
        assert json.loads((directory / "links.json").read_text()) == [
            {"url": "https://example.org/report.pdf", "text": "Report"}
        ]
        assert not list((tmp_path / "output").rglob("*.html"))
    assert {p.name for p in directory.iterdir()} == {"links.json", "manifest.json"}


def test_pending_payload_filename_collision_preserves_both_records(
    tmp_path: Path,
) -> None:
    original, changed, other = archive(), archive("changed.csv"), archive("other.csv")
    refresh(tmp_path, response_handler(original))
    prefix = hashlib.sha256(changed).hexdigest()[:12]
    row = source(
        urls=[
            "https://example.org/data.zip",
            f"https://example.org/{prefix}-data.zip",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        payload = changed if request.url.path == "/data.zip" else other
        return httpx.Response(200, content=payload)

    result = refresh(tmp_path, handler, row)
    assert result["sources"][0]["status"] == "success"
    records = result["sources"][0]["files"]
    assert len({record["path"] for record in records}) == 2
    output = tmp_path / "output"
    assert (output / "synthetic/2026-11/data.zip").read_bytes() == original
    for record in records:
        payload = (output / record["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]


@pytest.mark.parametrize("preceding_payload", [False, True])
def test_existing_digest_path_collision_fails_without_replacing_bytes(
    tmp_path: Path, preceding_payload: bool
) -> None:
    original, changed = archive(), archive("changed.csv")
    urls = ["https://example.org/data.zip"]
    if preceding_payload:
        urls.insert(0, "https://example.org/first.zip")
    row = source(urls=urls)
    refresh(tmp_path, response_handler(original), row)
    output = tmp_path / "output/synthetic"
    latest = (output / "latest.json").read_bytes()
    prefix = hashlib.sha256(changed).hexdigest()[:12]
    collision = output / f"2026-11/{prefix}-data.zip"
    collision.write_bytes(original)
    result = refresh(tmp_path, response_handler(changed), row)
    assert result["sources"][0]["status"] == "failed"
    assert result["required_failures"] == ["synthetic"]
    assert collision.read_bytes() == original
    assert (output / "2026-11/data.zip").read_bytes() == original
    assert (output / "latest.json").read_bytes() == latest
    manifest = json.loads((output / "2026-11/manifest.json").read_text())
    for record in manifest["files"]:
        if "path" in record:
            payload = (tmp_path / "output" / record["path"]).read_bytes()
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]


def test_empty_selection_overrides_unchanged_page(tmp_path: Path) -> None:
    row = source(kind="listing_page", expect="html")
    handler = response_handler(b'<html><a href="/report.pdf">Report</a></html>')
    refresh(tmp_path, handler, row)
    latest = (tmp_path / "output/synthetic/latest.json").read_bytes()
    result = refresh(tmp_path, handler, row | {"link_classes": ["missing"]})
    assert result["sources"][0]["status"] == "no_links"
    assert result["required_failures"] == ["synthetic"]
    assert (tmp_path / "output/synthetic/latest.json").read_bytes() == latest


def test_rerun_without_links_keeps_the_successful_index(tmp_path: Path) -> None:
    row = source(kind="listing_page", expect="html")
    good = response_handler(b'<html><a href="/report.pdf">Report</a></html>')
    assert refresh(tmp_path, good, row)["sources"][0]["status"] == "success"
    output = tmp_path / "output/synthetic"
    index = (output / "2026-11/links.json").read_bytes()
    latest = (output / "latest.json").read_bytes()
    assert json.loads(index) == [
        {"url": "https://example.org/report.pdf", "text": "Report"}
    ]
    # Same month, changed page with no kept link.
    empty = response_handler(b"<html><p>Maintenance</p></html>")
    result = refresh(tmp_path, empty, row)
    assert result["sources"][0]["status"] == "no_links"
    assert (output / "2026-11/links.json").read_bytes() == index
    assert (output / "latest.json").read_bytes() == latest
    assert json.loads(latest)["status"] == "success"


def test_robots_429_blocks_all_urls_on_origin(tmp_path: Path) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(429)

    row = source(urls=["https://example.org/a.zip", "https://example.org/b.zip"])
    result = refresh(tmp_path, handler, row)
    assert result["sources"][0]["status"] == "blocked"
    assert requests == ["https://example.org/robots.txt"]
    assert all(
        record["status"] == "blocked" for record in result["sources"][0]["files"]
    )
