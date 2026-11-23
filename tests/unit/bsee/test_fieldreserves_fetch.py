"""Offline tests; all response bodies in this module are synthetic."""

import io
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from worldenergydata.bsee import fieldreserves_fetch as fetch


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("live network forbidden in tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", denied)


class Response(io.BytesIO):
    def __init__(
        self, body: bytes, url: str = fetch.VINTAGE_LISTING, status: int = 200
    ) -> None:
        super().__init__(body)
        self.url = url
        self.status = status

    def geturl(self) -> str:
        return self.url


def test_fetch_caps_stream_and_uses_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[tuple[urllib.request.Request, int]] = []

    def transport(request: urllib.request.Request, timeout: int) -> Response:
        observed.append((request, timeout))
        return Response(b"synthetic payload")

    monkeypatch.setattr(fetch, "_open", transport)
    client = fetch.Client(max_bytes=4)
    with pytest.raises(ValueError, match="limit"):
        client.get(fetch.VINTAGE_LISTING)
    assert observed[0][1] == 30
    assert (
        "https://github.com/vamseeachanta/worldenergydata"
        in observed[0][0].headers["User-agent"]
    )


def test_fetch_pauses_and_stops_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    pauses: list[int] = []
    monkeypatch.setattr(fetch.time, "sleep", pauses.append)
    monkeypatch.setattr(fetch, "_open", lambda *a, **k: Response(b"ok"))
    client = fetch.Client()
    client.get(fetch.VINTAGE_LISTING)
    client.get(fetch.VINTAGE_LISTING)
    assert pauses and pauses[0] >= 2

    def refused(*args: Any, **kwargs: Any) -> None:
        raise urllib.error.HTTPError(
            fetch.VINTAGE_LISTING, 403, "refused", Message(), None
        )

    monkeypatch.setattr(fetch, "_open", refused)
    with pytest.raises(urllib.error.HTTPError):
        client.get(fetch.VINTAGE_LISTING)


def test_listing_renamed_member_fails() -> None:
    with pytest.raises(ValueError, match="missing"):
        fetch.validate_listing(
            "<a href='/FieldReserves/Files/renamed.zip'>x</a>", ["2023 Hist.zip"]
        )


def test_manifest_deterministic_and_has_source_digest() -> None:
    record = fetch.record(
        "https://example.gov/synthetic", b"synthetic", "2026-10-11T00:00:00Z"
    )
    manifest = fetch.emit_manifest([record], terms="not stated by the source")
    assert manifest == fetch.emit_manifest([record], terms="not stated by the source")
    assert '"size_bytes": 9' in manifest
    assert '"sha256":' in manifest


def test_fixture_manifest_reproduced_from_fixed_fixture_bytes() -> None:
    root = Path(__file__).parents[2] / "fixtures/bsee/fieldreserves"
    assert (
        fetch.fixture_manifest(root) == (root / "synthetic_manifest.json").read_text()
    )


def test_committed_live_manifest_reproduced_from_retrieval_metadata_fixture() -> None:
    import json

    root = Path(__file__).parents[3]
    inputs = json.loads(
        (
            root / "tests/fixtures/bsee/fieldreserves/live_provenance_inputs.json"
        ).read_text()
    )
    expected = (root / "data/modules/bsee/fieldreserves/manifest.json").read_bytes()
    assert inputs["data_kind"] == "live-retrieval-metadata"
    assert (
        fetch.manifest_from_inputs(inputs["retrievals"], terms=inputs["terms"]).encode(
            "utf-8"
        )
        == expected
    )
    records = json.loads(expected)["records"]
    assert len(records) == 10
    assert {r["source_url"] for r in records} == set(fetch.source_urls())


def test_redirect_refused_before_followup_request() -> None:
    handler = fetch._NoRedirect()
    with pytest.raises(urllib.error.HTTPError):
        handler.redirect_request(None, None, 302, "redirect", {}, "https://other.gov/")


def test_family_preflight_and_fetch_are_offline_and_reproducible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import json

    from tests.unit.bsee.fieldreserves_helpers import archive

    responses = {
        fetch.BASE + "/robots.txt": b"User-agent: *\nAllow: /\n",
        fetch.TERMS_URL: fetch.DISCLAIMER.encode(),
        fetch.VINTAGE_LISTING: "".join(
            f"<a href='/FieldReserves/Files/{n}'>x</a>" for n in fetch.FILES[:2]
        ).encode(),
        fetch.FAMILY_LISTING: "".join(
            f"<a href='/FieldReserves/Files/{n}'>x</a>" for n in fetch.FILES[2:]
        ).encode(),
    }
    responses[fetch.MASTER_DEFINITION] = b"synthetic master definition"
    responses[fetch.APPENDIX_DEFINITION] = b"synthetic index definition"
    import hashlib

    monkeypatch.setattr(
        fetch, "TERMS_SHA256", hashlib.sha256(responses[fetch.TERMS_URL]).hexdigest()
    )
    for name in fetch.FILES:
        responses[fetch.BASE + "/FieldReserves/Files/" + name.replace(" ", "%20")] = (
            archive("synthetic.txt", b"synthetic")
        )

    def transport(request: urllib.request.Request, timeout: int) -> Response:
        response = Response(responses[request.full_url], request.full_url, 203)
        return response

    monkeypatch.setattr(fetch, "_open", transport)
    monkeypatch.setattr(fetch.time, "sleep", lambda seconds: None)
    path = fetch.fetch_family(tmp_path)
    data = json.loads(path.read_text())
    assert len(data["records"]) == 10
    assert {r["source_url"] for r in data["records"]} == set(fetch.source_urls())
    assert all(r["http_status"] == 203 for r in data["records"])
    inputs = json.loads((tmp_path / "recorded_inputs.json").read_text())
    assert (
        fetch.manifest_from_inputs(inputs["retrievals"], terms=inputs["terms"])
        == path.read_text()
    )
    assert (
        fetch.emit_manifest(data["records"], terms=fetch.DISCLAIMER) == path.read_text()
    )
    with pytest.raises(FileExistsError):
        fetch.fetch_family(tmp_path)


def test_changed_terms_fail_even_when_original_sentence_is_retained() -> None:
    with pytest.raises(ValueError, match="Terms page changed"):
        fetch.verify_terms(
            (fetch.DISCLAIMER + " Automated access is forbidden.").encode()
        )


def test_existing_manifest_preserved_without_network(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("preserved synthetic manifest")
    with pytest.raises(FileExistsError):
        fetch.fetch_family(tmp_path)
    assert path.read_text() == "preserved synthetic manifest"


def test_old_recorded_inputs_omit_unknown_status() -> None:
    item = fetch.retrieval_input("synthetic://old", b"old", "2026-10-11T00:00:00Z")
    assert "http_status" not in fetch.record_from_input(item)
    assert (
        fetch.record("synthetic://new", b"new", "2026-10-11T00:00:00Z", 202)[
            "http_status"
        ]
        == 202
    )


def test_definition_pages_are_checked_against_robots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    requested: list[str] = []

    def transport(request: urllib.request.Request, timeout: int) -> Response:
        requested.append(request.full_url)
        response = Response(
            b"User-agent: *\nDisallow: /Main/HtmlPage.aspx?page=fieldNames2\n"
        )
        response.url = request.full_url
        return response

    monkeypatch.setattr(fetch, "_open", transport)
    with pytest.raises(ValueError, match="robots policy"):
        fetch.fetch_family(tmp_path)
    assert requested == [fetch.BASE + "/robots.txt"]
