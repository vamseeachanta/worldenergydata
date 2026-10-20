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
