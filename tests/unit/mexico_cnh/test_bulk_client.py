"""HTTP boundaries use synthetic responses; no test contacts a public server."""

from io import BytesIO

import pytest

from worldenergydata.mexico_cnh.bulk_client import BulkProductionClient

from .test_bulk_production import workbook


class Response(BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


def test_discover_download_and_receipt(tmp_path):
    """Workbook bytes are retained exactly; receipt digest matches those bytes."""
    source = workbook(tmp_path / "source.xlsx").read_bytes()
    calls = []

    def get(url, *, timeout):
        calls.append(url)
        data = (
            source
            if url.endswith(".xlsx")
            else (
                b'<a href="/media/99/producci&#243;n-nacional-de-petr&#243;leo-y-gas.xlsx">'
                b'Excel</a><a href="/media/10/unrelated.xlsx">Other</a>'
            )
        )
        return Response(data, url)

    client = BulkProductionClient(timeout=5, max_bytes=len(source) + 1000, opener=get)
    download = client.download(tmp_path / "retained")
    assert download.path.read_bytes() == source
    assert download.receipt["sha256"] == download.workbook.sha256
    assert download.receipt["vintage"] == "2024-02"
    assert download.receipt["source_url"].endswith(".xlsx")
    assert "%C3%B3" in calls[1]
    assert len(calls) == 2


@pytest.mark.parametrize(
    "html",
    [
        b"<html>Mantenimiento</html>",
        b'<a href="https://elsewhere.invalid/produccion-nacional.xlsx">Excel</a>',
        (
            b'<a href="/media/1/produccion-nacional.xlsx">One</a>'
            b'<a href="/media/2/produccion-nacional.xlsx">Two</a>'
        ),
    ],
)
def test_no_guessing_when_listing_is_missing_or_ambiguous(html):
    client = BulkProductionClient(
        timeout=5, max_bytes=10000, opener=lambda url, **kw: Response(html, url)
    )
    with pytest.raises(ValueError):
        client.discover()


def test_rejects_html_download_and_oversize(tmp_path):
    client = BulkProductionClient(
        timeout=5, max_bytes=10, opener=lambda url, **kw: Response(b"x" * 11, url)
    )
    with pytest.raises(ValueError, match="size"):
        client.download(
            tmp_path, url="https://hidrocarburos.energia.gob.mx/media/a.xlsx"
        )


@pytest.mark.parametrize(
    "url",
    [
        "file:///input.xlsx",
        "http://example.invalid/a.xlsx",
        "https://elsewhere.invalid/a.xlsx",
    ],
)
def test_rejects_untrusted_download_url(tmp_path, url):
    client = BulkProductionClient(timeout=5, max_bytes=10000)
    with pytest.raises(ValueError, match="source"):
        client.download(tmp_path, url=url)


def test_html_export_is_not_a_workbook(tmp_path):
    client = BulkProductionClient(
        timeout=5,
        max_bytes=10000,
        opener=lambda url, **kw: Response(b"<html>Maintenance</html>", url),
    )
    with pytest.raises(ValueError, match="XLSX"):
        client.download(
            tmp_path, url="https://hidrocarburos.energia.gob.mx/media/a.xlsx"
        )


def test_redirect_cannot_leave_source_origin():
    from urllib.request import Request

    from worldenergydata.mexico_cnh.bulk_client import SourceRedirectHandler

    handler = SourceRedirectHandler()
    with pytest.raises(ValueError, match="source"):
        handler.redirect_request(
            Request("https://hidrocarburos.energia.gob.mx/"),
            None,
            302,
            "Moved",
            {},
            "https://elsewhere.invalid/",
        )


@pytest.mark.parametrize("redirect", [True, False])
def test_default_opener_checks_redirect_and_response_origin(monkeypatch, redirect):
    """Exercise the actual opener chain without opening a network connection."""
    import urllib.request
    from email.message import Message
    from urllib.response import addinfourl

    calls = []

    class FakeHTTPSHandler(urllib.request.HTTPSHandler):
        def https_open(self, request):
            calls.append(request.full_url)
            assert len(calls) == 1, "untrusted redirect was followed"
            headers = Message()
            headers["Location"] = "https://elsewhere.invalid/input.xlsx"
            response = addinfourl(
                BytesIO(b"unused"),
                headers,
                request.full_url if redirect else headers["Location"],
                302 if redirect else 200,
            )
            response.msg = "Moved" if redirect else "OK"
            return response

    monkeypatch.setattr(urllib.request, "HTTPSHandler", FakeHTTPSHandler)
    client = BulkProductionClient(timeout=5, max_bytes=10000)
    with pytest.raises(ValueError, match="source"):
        client.discover()
    assert len(calls) == 1


@pytest.mark.parametrize("explicit_budget", [False, True])
def test_archive_expansion_budget_is_checked_before_parsing(
    tmp_path, monkeypatch, explicit_budget
):
    from zipfile import ZIP_DEFLATED, ZipFile

    from worldenergydata.mexico_cnh import bulk_client

    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
        zipped.writestr("first.xml", b"x" * 6000)
        zipped.writestr("second.xml", b"x" * 6000)
    payload = archive.getvalue()

    def unexpected_parse(path):
        pytest.fail("oversized archive reached workbook parser")

    monkeypatch.setattr(bulk_client, "load_production_workbook", unexpected_parse)
    budget = {"max_uncompressed_bytes": 10000} if explicit_budget else {}
    client = BulkProductionClient(
        timeout=5,
        max_bytes=1000,
        opener=lambda url, **kw: Response(payload, url),
        **budget,
    )
    with pytest.raises(ValueError, match="uncompressed.*budget"):
        client.download(tmp_path / "retained", url=bulk_client.LISTING_URL + "a.xlsx")
    assert not (tmp_path / "retained").exists()


def test_discovery_accepts_cp1252_listing():
    html = '<p>Información</p><a href="/producción-nacional.xlsx">Excel</a>'
    client = BulkProductionClient(
        timeout=5,
        max_bytes=10000,
        opener=lambda url, **kw: Response(html.encode("cp1252"), url),
    )
    assert client.discover().endswith("/producci%C3%B3n-nacional.xlsx")


def test_total_transfer_deadline_rejects_slow_chunks(monkeypatch):
    from worldenergydata.mexico_cnh import bulk_client

    elapsed = [0.0]

    class SlowResponse(Response):
        def read(self, size):
            return self.read1(size)

        def read1(self, size):
            elapsed[0] += 3
            return b"x"

    monkeypatch.setattr(bulk_client, "monotonic", lambda: elapsed[0], raising=False)
    client = BulkProductionClient(
        timeout=5,
        max_bytes=100,
        opener=lambda url, **kw: SlowResponse(b"", url),
    )
    with pytest.raises(TimeoutError, match="transfer.*budget"):
        client.discover()


def test_repeated_digest_retains_each_retrieval_receipt(tmp_path):
    import json

    source = workbook(tmp_path / "source.xlsx").read_bytes()
    client = BulkProductionClient(
        timeout=5,
        max_bytes=10000,
        opener=lambda url, **kw: Response(source, url),
    )
    directory = tmp_path / "retained"
    first = client.download(
        directory, url="https://hidrocarburos.energia.gob.mx/media/a.xlsx"
    )
    before = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    second = client.download(
        directory, url="https://hidrocarburos.energia.gob.mx/media/b.xlsx"
    )
    assert first.path == second.path
    assert all((directory / name).read_bytes() == data for name, data in before.items())
    receipts = [json.loads(path.read_text()) for path in directory.glob("*.json")]
    assert len(receipts) == 2
    assert first.receipt in receipts and second.receipt in receipts
