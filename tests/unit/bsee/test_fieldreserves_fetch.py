"""Offline tests; all response bodies in this module are synthetic."""

import io
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from worldenergydata.bsee import fieldreserves_fetch as fetch


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("live network forbidden in tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", denied)


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return fetch.VINTAGE_LISTING


def test_fetch_caps_stream_and_uses_timeout(monkeypatch):
    observed = []

    def transport(request, timeout):
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


def test_fetch_pauses_and_stops_on_refusal(monkeypatch):
    pauses = []
    monkeypatch.setattr(fetch.time, "sleep", pauses.append)
    monkeypatch.setattr(fetch, "_open", lambda *a, **k: Response(b"ok"))
    client = fetch.Client()
    client.get(fetch.VINTAGE_LISTING)
    client.get(fetch.VINTAGE_LISTING)
    assert pauses and pauses[0] >= 2

    def refused(*args, **kwargs):
        raise urllib.error.HTTPError(fetch.VINTAGE_LISTING, 403, "refused", {}, None)

    monkeypatch.setattr(fetch, "_open", refused)
    with pytest.raises(urllib.error.HTTPError):
        client.get(fetch.VINTAGE_LISTING)


def test_listing_renamed_member_fails():
    with pytest.raises(ValueError, match="missing"):
        fetch.validate_listing(
            "<a href='/FieldReserves/Files/renamed.zip'>x</a>", ["2023 Hist.zip"]
        )


def test_manifest_deterministic_and_has_source_digest():
    record = fetch.record(
        "https://example.gov/synthetic", b"synthetic", "2026-10-11T00:00:00Z"
    )
    manifest = fetch.emit_manifest([record], terms="not stated by the source")
    assert manifest == fetch.emit_manifest([record], terms="not stated by the source")
    assert '"size_bytes": 9' in manifest
    assert '"sha256":' in manifest


def test_fixture_manifest_reproduced_from_fixed_fixture_bytes():
    root = Path(__file__).parents[2] / "fixtures/bsee/fieldreserves"
    assert (
        fetch.fixture_manifest(root) == (root / "synthetic_manifest.json").read_text()
    )


def test_committed_live_manifest_reproduced_from_retrieval_metadata_fixture():
    import json

    root = Path(__file__).parents[3]
    inputs = json.loads(
        (
            root / "tests/fixtures/bsee/fieldreserves/live_provenance_inputs.json"
        ).read_text()
    )
    expected = (root / "data/modules/bsee/fieldreserves/manifest.json").read_text()
    assert inputs["data_kind"] == "live-retrieval-metadata"
    assert fetch.emit_manifest(inputs["records"], terms=inputs["terms"]) == expected


def test_redirect_refused_before_followup_request():
    handler = fetch._NoRedirect()
    with pytest.raises(urllib.error.HTTPError):
        handler.redirect_request(None, None, 302, "redirect", {}, "https://other.gov/")


def test_family_preflight_and_fetch_are_offline_and_reproducible(monkeypatch, tmp_path):
    import json

    from tests.unit.bsee.test_fieldreserves_loader import archive

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
    import hashlib

    monkeypatch.setattr(
        fetch, "TERMS_SHA256", hashlib.sha256(responses[fetch.TERMS_URL]).hexdigest()
    )
    for name in fetch.FILES:
        responses[fetch.BASE + "/FieldReserves/Files/" + name.replace(" ", "%20")] = (
            archive("synthetic.txt", b"synthetic")
        )

    def transport(request, timeout):
        response = Response(responses[request.full_url])
        response.geturl = lambda: request.full_url
        return response

    monkeypatch.setattr(fetch, "_open", transport)
    monkeypatch.setattr(fetch.time, "sleep", lambda seconds: None)
    path = fetch.fetch_family(tmp_path)
    data = json.loads(path.read_text())
    assert len(data["records"]) == 8
    assert (
        fetch.emit_manifest(data["records"], terms=fetch.DISCLAIMER) == path.read_text()
    )
    with pytest.raises(FileExistsError):
        fetch.fetch_family(tmp_path)


def test_changed_terms_fail_even_when_original_sentence_is_retained():
    with pytest.raises(ValueError, match="Terms page changed"):
        fetch.verify_terms(
            (fetch.DISCLAIMER + " Automated access is forbidden.").encode()
        )


def test_existing_manifest_preserved_without_network(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("preserved synthetic manifest")
    with pytest.raises(FileExistsError):
        fetch.fetch_family(tmp_path)
    assert path.read_text() == "preserved synthetic manifest"
