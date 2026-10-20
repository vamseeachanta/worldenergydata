"""Bounded transport tests use synthetic bytes, without network requests."""

import hashlib
import io
import json
from email.message import Message
from urllib.error import URLError

import pytest

from worldenergydata.international_sources.client import SourceClient


class Response(io.BytesIO):
    def __init__(self, payload, content_type="application/json", url=None):
        super().__init__(payload)
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.url = url

    def geturl(self):
        return self.url


def opener_for(payload, **kwargs):
    def open_response(request, timeout):
        assert timeout == 2
        assert request.get_header("Accept") == "application/json"
        return Response(payload, url=request.full_url, **kwargs)

    return open_response


def test_collected_page_keeps_evidence_and_never_claims_complete_coverage():
    """One synthetic monthly row contains exactly the supplied 2.5 bbl.

    Independent expected byte count is len(payload); SHA-256 is checked against
    hashlib over the original supplied bytes rather than a JSON reserialization.
    """
    metadata = json.dumps({"id": "fdvb-hsrf", "rowsUpdatedAt": 0}).encode()
    rows = json.dumps(
        [{"campo": "EXAMPLE", "vigencia": "2024", "mes": "1", "produccion_bls": "2.5"}]
    ).encode()
    requests = []

    def open_response(request, timeout):
        requests.append(request.full_url)
        return Response(
            metadata if "/api/views/" in request.full_url else rows,
            url=request.full_url,
        )

    client = SourceClient(timeout_seconds=2, max_bytes=1000, opener=open_response)
    page = client.colombia_page("oil", limit=1, offset=0)
    assert len(requests) == 2
    assert page.metadata.dataset_id == "fdvb-hsrf"
    assert str(page.observations[0].volume) == "2.5"
    assert page.rows_evidence.sha256 == hashlib.sha256(rows).hexdigest()
    assert page.rows_evidence.size_bytes == len(rows)
    assert page.rows_evidence.raw_bytes == rows
    assert page.rows_evidence.observed_at.tzinfo is not None
    assert page.complete is False


@pytest.mark.parametrize(
    "payload,content_type",
    [
        (b"<html>application shell</html>", "text/html"),
        (b"<html>application shell</html>", "application/json"),
        (b'{"success":false,"success":true}', "application/json"),
        (b'{"value":NaN}', "application/json"),
        (b"null", "application/json"),
    ],
)
def test_non_json_or_ambiguous_json_fails_closed(payload, content_type):
    client = SourceClient(
        timeout_seconds=2,
        max_bytes=1000,
        opener=opener_for(payload, content_type=content_type),
    )
    with pytest.raises((ValueError, TypeError)):
        client.colombia_metadata("oil")


def test_response_limit_is_enforced_before_decoding():
    client = SourceClient(
        timeout_seconds=2, max_bytes=2, opener=opener_for(b'{"id":"fdvb-hsrf"}')
    )
    with pytest.raises(ValueError, match="byte limit"):
        client.colombia_metadata("oil")


def test_transport_refusal_is_visible_without_retry():
    calls = []

    def refuse(request, timeout):
        calls.append(request.full_url)
        raise URLError("synthetic refusal")

    client = SourceClient(timeout_seconds=2, max_bytes=1000, opener=refuse)
    with pytest.raises(URLError, match="synthetic refusal"):
        client.colombia_metadata("oil")
    assert len(calls) == 1


def test_argentina_identifier_is_encoded_and_metadata_preserved():
    payload = b'{"success":true,"result":{"id":"a/b ?","resources":[]}}'
    urls = []

    def open_response(request, timeout):
        urls.append(request.full_url)
        return Response(payload, url=request.full_url)

    client = SourceClient(timeout_seconds=2, max_bytes=1000, opener=open_response)
    discovery, evidence = client.argentina_package("a/b ?")
    assert urls == [
        "https://datos.energia.gob.ar/api/3/action/package_show?id=a%2Fb+%3F"
    ]
    assert discovery.dataset_id == "a/b ?"
    assert discovery.license is None
    assert evidence.raw_bytes == payload


def test_wrong_dataset_response_is_rejected():
    client = SourceClient(
        timeout_seconds=2, max_bytes=1000, opener=opener_for(b'{"id":"5dux-bfvx"}')
    )
    with pytest.raises(ValueError, match="dataset"):
        client.colombia_metadata("oil")


@pytest.mark.parametrize(
    "timeout,limit", [(0, 1), (float("nan"), 1), (1, 0), (1, True)]
)
def test_invalid_resource_bounds_are_rejected(timeout, limit):
    with pytest.raises(ValueError):
        SourceClient(timeout_seconds=timeout, max_bytes=limit)


def test_overflowing_json_number_is_rejected():
    client = SourceClient(
        timeout_seconds=2,
        max_bytes=1000,
        opener=opener_for(b'{"id":"fdvb-hsrf","value":1e999}'),
    )
    with pytest.raises(ValueError, match="finite"):
        client.colombia_metadata("oil")


def test_https_downgrade_is_rejected():
    def redirect(request, timeout):
        return Response(
            b'{"id":"fdvb-hsrf"}', url=request.full_url.replace("https:", "http:")
        )

    client = SourceClient(timeout_seconds=2, max_bytes=1000, opener=redirect)
    with pytest.raises(ValueError, match="redirect"):
        client.colombia_metadata("oil")
