"""Reproduce the security findings addressed before enabling enforcement."""

import hashlib
from urllib.request import Request

import pytest

from worldenergydata.field_development.dexpi import dexpi_to_graph
from worldenergydata.modules.state_regulators.fetch import http
from worldenergydata.testing.cleanup.test_analyzer import TestAnalyzer as Analyzer


@pytest.mark.parametrize("declaration", ["", '<!ENTITY sample "expanded">'])
def test_xml_document_types_are_rejected(declaration):
    xml = f"<!DOCTYPE PlantModel [{declaration}]><PlantModel/>"
    with pytest.raises(ValueError, match="DOCTYPE"):
        dexpi_to_graph(xml)


@pytest.mark.parametrize(
    "url", ["file:///sample", "ftp://example.test/sample", "sample"]
)
def test_download_rejects_non_http_before_opening(url, monkeypatch):
    def unexpected_open(*args):
        pytest.fail("the opener must not be constructed for rejected URLs")

    monkeypatch.setattr(http, "build_opener", unexpected_open)
    with pytest.raises(ValueError, match="HTTP"):
        http.urlopen(url)


@pytest.mark.parametrize("scheme", ["file", "ftp", "data"])
def test_redirect_rejects_non_http(scheme):
    with pytest.raises(ValueError, match="HTTP"):
        http._HTTPRedirects().redirect_request(
            Request("https://example.test/source"),
            None,
            302,
            "Found",
            {},
            f"{scheme}://example.test/target",
        )


def test_https_redirect_is_preserved():
    target = "https://example.test/target"
    redirected = http._HTTPRedirects().redirect_request(
        Request("http://example.test/source"), None, 302, "Found", {}, target
    )
    assert redirected.full_url == target


def test_duplicate_hash_is_marked_nonsecurity(tmp_path, monkeypatch):
    real_md5 = hashlib.md5
    calls = []

    def restricted_md5(data, *, usedforsecurity=True):
        calls.append(usedforsecurity)
        if usedforsecurity:
            raise ValueError("security MD5 is disabled")
        return real_md5(data, usedforsecurity=False)

    monkeypatch.setattr(hashlib, "md5", restricted_md5)
    (tmp_path / "test_sample.py").write_text(
        "def test_first():\n    assert True\ndef test_second():\n    assert True\n",
        encoding="utf-8",
    )
    report = Analyzer(tmp_path).analyze()
    assert calls == [False, False]
    assert report["summary"]["duplicate_tests"] == 1


def test_http_open_preserves_url_timeout_and_response(monkeypatch):
    response = object()

    class Opener:
        def open(self, url, timeout):
            assert url == "https://example.test/source"
            assert timeout == 17
            return response

    def build(handler):
        assert isinstance(handler, http._HTTPRedirects)
        return Opener()

    monkeypatch.setattr(http, "build_opener", build)
    assert http.urlopen("https://example.test/source", timeout=17) is response
