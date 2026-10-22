"""Local-cache downloader tests; all response bytes are synthetic.

Expected byte counts are len(payload); expected digests are independently
calculated by hashlib.sha256. No engineering conversion is performed.
"""

import hashlib
import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from worldenergydata.canada.production import cnloer_client

# ISO 32000-1:2008, section 7.5.2: PDF file header. This is a test payload,
# not a valid production PDF and not a regulator document.
PDF = b"%PDF-1.7\nsynthetic download test\n"


@pytest.fixture
def remote(monkeypatch):
    def response(*args, **kwargs):
        return io.BytesIO(PDF)

    fetch = Mock(side_effect=response)
    opener = Mock()
    opener.open = fetch
    monkeypatch.setattr(cnloer_client, "build_opener", Mock(return_value=opener))
    return fetch


def client(tmp_path):
    return cnloer_client.CnloerPdfClient(cache_dir=tmp_path, timeout=10, max_bytes=1024)


def test_download_records_source_identity_and_digest(tmp_path, remote):
    """One payload produces one PDF with its independently calculated digest."""
    result = client(tmp_path).download(year=2026, field_code="h")
    assert result.read_bytes() == PDF
    assert result.name == f"2026hpro-{hashlib.sha256(PDF).hexdigest()}.pdf"
    manifest = json.loads((tmp_path / "2026hpro.json").read_text())
    assert manifest["source_url"] == (
        "https://www.cnloer.ca/wp-content/uploads/2026hpro.pdf"
    )
    assert manifest["source_id"] == "canada-cnloer"
    assert manifest["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert manifest["size_bytes"] == len(PDF)
    assert manifest["publication_status"] == "restricted_pending_licence_review"
    assert manifest["retrieved_at"]
    assert (tmp_path / ".gitignore").read_text() == "*\n"


def test_cache_reuse_verifies_bytes_without_network(tmp_path, remote):
    first = client(tmp_path).download(year=2026, field_code="he")
    remote.reset_mock()
    assert client(tmp_path).download(year=2026, field_code="he") == first
    remote.assert_not_called()


def test_tampered_cache_is_rejected_without_overwriting(tmp_path, remote):
    path = client(tmp_path).download(year=2026, field_code="n")
    path.write_bytes(b"tampered")
    remote.reset_mock()
    with pytest.raises(ValueError, match="digest"):
        client(tmp_path).download(year=2026, field_code="n")
    assert path.read_bytes() == b"tampered"
    remote.assert_not_called()


def test_refresh_preserves_previous_snapshot(tmp_path, remote):
    first = client(tmp_path).download(year=2026, field_code="t")
    updated = PDF + b"changed"
    remote.side_effect = lambda *args, **kwargs: io.BytesIO(updated)
    second = client(tmp_path).download(year=2026, field_code="t", force_refresh=True)
    assert first.read_bytes() == PDF
    assert second.read_bytes() == updated
    assert first != second


@pytest.mark.parametrize(
    "payload", [b"<html>error</html>", b"", b"%PDF-" + b"x" * 1024]
)
def test_bad_response_does_not_replace_cached_snapshot(tmp_path, remote, payload):
    path = client(tmp_path).download(year=2026, field_code="w")
    before = (tmp_path / "2026wpro.json").read_bytes()
    remote.side_effect = lambda *args, **kwargs: io.BytesIO(payload)
    with pytest.raises(ValueError):
        client(tmp_path).download(year=2026, field_code="w", force_refresh=True)
    assert path.read_bytes() == PDF
    assert (tmp_path / "2026wpro.json").read_bytes() == before


@pytest.mark.parametrize(
    "year,code", [(2026, "m"), (2026, "../h"), ("../2026", "h"), (True, "h")]
)
def test_invalid_report_identity_rejected_before_network(tmp_path, remote, year, code):
    with pytest.raises(ValueError):
        client(tmp_path).download(year=year, field_code=code)
    remote.assert_not_called()


def test_http_failure_does_not_create_manifest(tmp_path, remote):
    remote.side_effect = HTTPError("https://example.org", 404, "missing", {}, None)
    with pytest.raises(HTTPError):
        client(tmp_path).download(year=2026, field_code="h")
    assert not list(tmp_path.glob("*.json"))
    assert not list(tmp_path.glob("*.pdf"))


@pytest.mark.parametrize(
    "timeout,max_bytes", [(0, 1024), (float("nan"), 1024), (10, 0), (10, True)]
)
def test_limits_are_required_positive_inputs(tmp_path, timeout, max_bytes):
    with pytest.raises(ValueError):
        cnloer_client.CnloerPdfClient(
            cache_dir=tmp_path, timeout=timeout, max_bytes=max_bytes
        )


def test_manifest_cannot_redirect_cache_read_outside_directory(tmp_path, remote):
    client(tmp_path).download(year=2026, field_code="h")
    path = tmp_path / "2026hpro.json"
    manifest = json.loads(path.read_text())
    manifest["file"] = "../outside.pdf"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest"):
        client(tmp_path).download(year=2026, field_code="h")


@pytest.mark.parametrize("code", ["h", "he", "n", "t", "w"])
def test_each_published_field_code_uses_annual_report_url(tmp_path, remote, code):
    """C-NLOER statistics page links annual reports using these field stems."""
    client(tmp_path).download(year=2026, field_code=code)
    assert remote.call_args.args[0] == (
        f"https://www.cnloer.ca/wp-content/uploads/2026{code}pro.pdf"
    )


def test_cache_hit_refuses_missing_ignore_protection(tmp_path, remote):
    client(tmp_path).download(year=2026, field_code="h")
    (tmp_path / ".gitignore").write_text("*.unrelated\n")
    with pytest.raises(ValueError, match="gitignore"):
        client(tmp_path).download(year=2026, field_code="h")


def test_existing_ignore_rules_are_preserved(tmp_path, remote):
    original = "*.unrelated\n"
    (tmp_path / ".gitignore").write_text(original)
    with pytest.raises(ValueError, match="gitignore"):
        client(tmp_path).download(year=2026, field_code="h")
    assert (tmp_path / ".gitignore").read_text() == original
    assert not list(tmp_path.glob("*.pdf"))


def test_cache_hit_obeys_current_size_limit(tmp_path, remote):
    client(tmp_path).download(year=2026, field_code="h")
    smaller = cnloer_client.CnloerPdfClient(
        cache_dir=tmp_path, timeout=10, max_bytes=len(PDF) - 1
    )
    with pytest.raises(ValueError, match="size"):
        smaller.download(year=2026, field_code="h")


@pytest.mark.parametrize("enlarge_cache", [False, True])
def test_cache_hit_bounds_payload_read(tmp_path, remote, monkeypatch, enlarge_cache):
    path = client(tmp_path).download(year=2026, field_code="h")
    if enlarge_cache:
        path.write_bytes(PDF + b"x" * 8192)
    smaller = cnloer_client.CnloerPdfClient(
        cache_dir=tmp_path, timeout=10, max_bytes=16
    )
    original_open = type(path).open
    read_sizes = []
    read_lengths = []

    def tracked_open(cache_path, *args, **kwargs):
        stream = original_open(cache_path, *args, **kwargs)
        if cache_path == path:
            original_read = stream.read

            def tracked_read(size=-1):
                read_sizes.append(size)
                payload = original_read(size)
                read_lengths.append(len(payload))
                return payload

            monkeypatch.setattr(stream, "read", tracked_read)
        return stream

    monkeypatch.setattr(type(path), "open", tracked_open)
    remote.reset_mock()
    with pytest.raises(ValueError, match="size"):
        smaller.download(year=2026, field_code="h")
    assert read_sizes == [17]
    assert read_lengths == [17]
    remote.assert_not_called()


def test_negated_ignore_pattern_is_rejected(tmp_path, remote):
    (tmp_path / ".gitignore").write_text("*\n!*.pdf\n")
    with pytest.raises(ValueError, match="gitignore"):
        client(tmp_path).download(year=2026, field_code="h")
    assert not list(tmp_path.glob("*.pdf"))


@pytest.mark.parametrize(
    "destination",
    [
        "http://www.cnloer.ca/report.pdf",
        "https://example.org/report.pdf",
        "file:///report.pdf",
        "https://www.cnloer.ca:443/report.pdf",
    ],
)
def test_redirects_outside_fixed_https_origin_are_refused(destination):
    from urllib.request import Request

    handler = cnloer_client.CnloerRedirectHandler()
    with pytest.raises(HTTPError, match="redirect"):
        handler.redirect_request(
            Request("https://www.cnloer.ca/report.pdf"),
            None,
            302,
            "found",
            {},
            destination,
        )


def test_same_origin_https_redirect_is_permitted():
    from urllib.request import Request

    destination = "https://www.cnloer.ca/wp-content/uploads/2026hpro.pdf"
    redirected = cnloer_client.CnloerRedirectHandler().redirect_request(
        Request("https://www.cnloer.ca/report.pdf"), None, 302, "found", {}, destination
    )
    assert redirected.full_url == destination
