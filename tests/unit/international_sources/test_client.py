"""Transport tests use synthetic bytes, without network requests."""

import hashlib
import io
import json
from email.message import Message
from urllib.error import URLError
from urllib.request import HTTPHandler, HTTPSHandler
from urllib.response import addinfourl

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
    metadata = json.dumps(
        {
            "id": "fdvb-hsrf",
            "rowsUpdatedAt": 0,
            "columns": [{"fieldName": "produccion_bls"}],
        }
    ).encode("utf-8")
    rows = json.dumps(
        [{"campo": "EXAMPLE", "vigencia": "2024", "mes": "1", "produccion_bls": "2.5"}]
    ).encode("utf-8")
    requests = []

    def open_response(request, timeout):
        requests.append(request.full_url)
        return Response(
            metadata if "/api/views/" in request.full_url else rows,
            url=request.full_url,
        )

    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=open_response
    )
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
    "payload,content_type,error,message",
    [
        (
            b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}]}',
            "text/html",
            ValueError,
            "source returned non-JSON content",
        ),
        (
            b"<html>application shell</html>",
            "application/json",
            ValueError,
            "source returned invalid JSON",
        ),
        (
            (
                b'{"id":"fdvb-hsrf","id":"fdvb-hsrf",'
                b'"columns":[{"fieldName":"produccion_bls"}]}'
            ),
            "application/json",
            ValueError,
            "duplicate JSON object key",
        ),
        (
            (
                b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}],'
                b'"value":NaN}'
            ),
            "application/json",
            ValueError,
            "non-finite JSON number",
        ),
        (
            b"null",
            "application/json",
            TypeError,
            "source JSON must be an object or array",
        ),
        (b"\xff", "application/json", ValueError, "source returned invalid JSON"),
    ],
)
def test_non_json_or_ambiguous_json_fails_closed(payload, content_type, error, message):
    client = SourceClient(
        socket_timeout_seconds=2,
        max_bytes=1000,
        opener=opener_for(payload, content_type=content_type),
    )
    with pytest.raises(error, match=message):
        client.colombia_metadata("oil")


@pytest.mark.parametrize(
    "content_type", ["application/json", "application/vnd.example+json"]
)
@pytest.mark.parametrize("excess_bytes", [0, 1])
def test_valid_json_at_byte_cap_passes_and_one_extra_byte_fails(
    content_type, excess_bytes
):
    payload = b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}]}'
    client = SourceClient(
        socket_timeout_seconds=2,
        max_bytes=len(payload),
        opener=opener_for(payload + b" " * excess_bytes, content_type=content_type),
    )
    if excess_bytes:
        with pytest.raises(ValueError, match="source response exceeds byte limit"):
            client.colombia_metadata("oil")
    else:
        discovery, evidence = client.colombia_metadata("oil")
        assert discovery.dataset_id == "fdvb-hsrf"
        assert evidence.raw_bytes == payload
        assert evidence.size_bytes == len(payload)


def test_response_limit_is_enforced_before_decoding():
    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=2, opener=opener_for(b'{"id":"fdvb-hsrf"}')
    )
    with pytest.raises(ValueError, match="byte limit"):
        client.colombia_metadata("oil")


def test_transport_refusal_is_visible_without_retry():
    calls = []

    def refuse(request, timeout):
        calls.append(request.full_url)
        raise URLError("synthetic refusal")

    client = SourceClient(socket_timeout_seconds=2, max_bytes=1000, opener=refuse)
    with pytest.raises(URLError, match="synthetic refusal"):
        client.colombia_metadata("oil")
    assert len(calls) == 1


def test_argentina_identifier_is_encoded_and_metadata_preserved():
    payload = b'{"success":true,"result":{"id":"a/b ?","resources":[]}}'
    urls = []

    def open_response(request, timeout):
        urls.append(request.full_url)
        return Response(payload, url=request.full_url)

    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=open_response
    )
    discovery, evidence = client.argentina_package("a/b ?")
    assert urls == [
        "https://datos.energia.gob.ar/api/3/action/package_show?id=a%2Fb+%3F"
    ]
    assert discovery.dataset_id == "a/b ?"
    assert discovery.license is None
    assert evidence.raw_bytes == payload


def test_argentina_response_identity_must_match_requested_id_or_name():
    payload = b'{"success":true,"result":{"id":"other-id","name":"other-name","resources":[]}}'
    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=opener_for(payload)
    )
    with pytest.raises(
        ValueError, match="CKAN response dataset differs from requested dataset"
    ):
        client.argentina_package("requested")


@pytest.mark.parametrize("requested", ["example-id", "example-name"])
def test_argentina_accepts_package_id_or_name_and_keeps_canonical_id(requested):
    payload = b'{"success":true,"result":{"id":"example-id","name":"example-name","resources":[]}}'
    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=opener_for(payload)
    )
    discovery, _ = client.argentina_package(requested)
    assert discovery.dataset_id == "example-id"


def test_wrong_dataset_response_is_rejected():
    client = SourceClient(
        socket_timeout_seconds=2,
        max_bytes=1000,
        opener=opener_for(
            b'{"id":"5dux-bfvx","columns":[{"fieldName":"produccionkpc"}]}'
        ),
    )
    with pytest.raises(ValueError, match="dataset"):
        client.colombia_metadata("oil")


@pytest.mark.parametrize(
    "timeout,limit", [(0, 1), (float("nan"), 1), (1, 0), (1, True)]
)
def test_invalid_resource_bounds_are_rejected(timeout, limit):
    with pytest.raises(ValueError):
        SourceClient(socket_timeout_seconds=timeout, max_bytes=limit)


def test_overflowing_json_number_is_rejected():
    client = SourceClient(
        socket_timeout_seconds=2,
        max_bytes=1000,
        opener=opener_for(
            b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}],'
            b'"value":1e999}'
        ),
    )
    with pytest.raises(ValueError, match="finite"):
        client.colombia_metadata("oil")


def test_https_downgrade_is_rejected():
    def redirect(request, timeout):
        return Response(
            b'{"id":"fdvb-hsrf"}', url=request.full_url.replace("https:", "http:")
        )

    client = SourceClient(socket_timeout_seconds=2, max_bytes=1000, opener=redirect)
    with pytest.raises(ValueError, match="redirect"):
        client.colombia_metadata("oil")


def test_off_host_response_is_rejected_even_with_valid_metadata():
    def off_host(request, timeout):
        return Response(
            b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}]}',
            url="https://datos.energia.gob.ar/redirected",
        )

    client = SourceClient(socket_timeout_seconds=2, max_bytes=1000, opener=off_host)
    with pytest.raises(ValueError, match="source redirect is unverified"):
        client.colombia_metadata("oil")


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize(
    "location",
    [
        "https://datos.energia.gob.ar/redirected",
        "https://www.datos.gov.co/redirected",
        "http://www.datos.gov.co/redirected",
    ],
)
def test_default_transport_refuses_redirect_before_read_or_next_request(
    monkeypatch, status, location
):
    requests = []
    reads = []

    class RedirectBody(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            return super().read(size)

    body = RedirectBody(b"x" * 1001)

    def https_open(handler, request):
        requests.append(request.full_url)
        if len(requests) > 1:
            pytest.fail("redirect target was requested")
        headers = Message()
        headers["Location"] = location
        response = addinfourl(body, headers, request.full_url, status)
        response.msg = "Redirect"
        return response

    monkeypatch.setattr(HTTPSHandler, "https_open", https_open)
    monkeypatch.setattr(HTTPHandler, "http_open", https_open)
    client = SourceClient(socket_timeout_seconds=2, max_bytes=1000)
    with pytest.raises(ValueError, match="redirects are disabled"):
        client.colombia_metadata("oil")
    assert requests == ["https://www.datos.gov.co/api/views/fdvb-hsrf.json"]
    assert reads == []
    assert body.closed


def test_default_transport_accepts_valid_json_and_forwards_socket_timeout(monkeypatch):
    payload = b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}]}'
    body = io.BytesIO(payload)

    def https_open(handler, request):
        assert request.timeout == 2
        headers = Message()
        headers["Content-Type"] = "application/json"
        response = addinfourl(body, headers, request.full_url, 200)
        response.msg = "OK"
        return response

    monkeypatch.setattr(HTTPSHandler, "https_open", https_open)
    client = SourceClient(socket_timeout_seconds=2, max_bytes=len(payload))
    discovery, evidence = client.colombia_metadata("oil")
    assert discovery.dataset_id == "fdvb-hsrf"
    assert evidence.url == "https://www.datos.gov.co/api/views/fdvb-hsrf.json"
    assert evidence.raw_bytes == payload
    assert body.closed


def test_evidence_records_the_returned_response_url():
    final_url = "https://www.datos.gov.co/api/views/fdvb-hsrf.json?version=1"

    def open_response(request, timeout):
        return Response(
            b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}]}',
            url=final_url,
        )

    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=open_response
    )
    _, evidence = client.colombia_metadata("oil")
    assert evidence.url == final_url


@pytest.mark.parametrize(
    "commodity,dataset_id,column,unit",
    [
        ("oil", "fdvb-hsrf", "produccion_bls", "bbl"),
        ("gas", "5dux-bfvx", "produccionkpc", "Mcf"),
    ],
)
def test_page_preserves_an_omitted_source_null(commodity, dataset_id, column, unit):
    metadata = json.dumps(
        {"id": dataset_id, "columns": [{"fieldName": column}]}
    ).encode("utf-8")
    rows = b'[{"campo":"EXAMPLE","vigencia":"2024","mes":"1"}]'

    def open_response(request, timeout):
        return Response(
            metadata if "/api/views/" in request.full_url else rows,
            url=request.full_url,
        )

    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=open_response
    )
    page = client.colombia_page(commodity, limit=1, offset=0)

    assert len(page.observations) == 1
    assert page.observations[0].volume is None
    assert page.observations[0].unit == unit
    assert page.rows_evidence.raw_bytes == rows
    assert page.complete is False


@pytest.mark.parametrize(
    "commodity,dataset_id", [("oil", "fdvb-hsrf"), ("gas", "5dux-bfvx")]
)
@pytest.mark.parametrize(
    "rows", [b"[]", b'[{"campo":"EXAMPLE","vigencia":"2024","mes":"1"}]']
)
def test_page_rejects_removed_volume_column_before_fetching_rows(
    commodity, dataset_id, rows
):
    metadata = json.dumps(
        {"id": dataset_id, "columns": [{"fieldName": "renamed_volume"}]}
    ).encode("utf-8")
    requests = []

    def open_response(request, timeout):
        requests.append(request.full_url)
        return Response(
            metadata if "/api/views/" in request.full_url else rows,
            url=request.full_url,
        )

    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=open_response
    )
    with pytest.raises(ValueError, match="column"):
        client.colombia_page(commodity, limit=1, offset=0)
    assert len(requests) == 1


@pytest.mark.parametrize("row_count", [0, 1, 2])
def test_page_accepts_record_cap_and_rejects_excess_rows(row_count):
    metadata = b'{"id":"fdvb-hsrf","columns":[{"fieldName":"produccion_bls"}]}'
    rows = json.dumps(
        [{"campo": "EXAMPLE", "vigencia": "2024", "mes": "1", "produccion_bls": "2.5"}]
        * row_count
    ).encode("utf-8")

    def open_response(request, timeout):
        return Response(
            metadata if "/api/views/" in request.full_url else rows,
            url=request.full_url,
        )

    client = SourceClient(
        socket_timeout_seconds=2, max_bytes=1000, opener=open_response
    )
    if row_count > 1:
        with pytest.raises(
            ValueError, match="source returned more rows than requested"
        ):
            client.colombia_page("oil", limit=1, offset=0)
    else:
        page = client.colombia_page("oil", limit=1, offset=0)
        assert len(page.observations) == row_count
        assert page.complete is False
