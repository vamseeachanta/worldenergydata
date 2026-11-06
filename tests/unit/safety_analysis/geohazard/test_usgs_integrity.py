"""Synthetic protocol integrity cases; no hazard or engineering acceptance limits.

Sources read 2026-10-19: USGS GeoJSON Summary v1.0, Output,
https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php;
USGS event-service v1, limit, https://earthquake.usgs.gov/fdsnws/event/1/#limit;
RFC 8259 (2017), sections 4 and 6, https://www.rfc-editor.org/rfc/rfc8259.
All numbers below are synthetic inputs, not earthquake observations.
"""

import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType
from typing import NoReturn
from urllib.parse import parse_qs, urlparse

import pytest

MODULE = "worldenergydata.safety_analysis.geohazard.usgs"
SOURCE = "https://example.invalid/synthetic-query"


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Unmocked HTTP is forbidden, including paths that are expected to fail."""
    import urllib.request

    def blocked(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Network forbidden in offline tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", blocked)
    return importlib.import_module(MODULE)


def collection(size: int = 1) -> dict:
    """Construct N unique synthetic rows; the independent count is N.

    USGS Output specifies [longitude, latitude, depth] and integer event time.
    Zero coordinates/time and null magnitude/depth are synthetic test inputs.
    """
    return {
        "type": "FeatureCollection",
        "metadata": {"count": size},
        "features": [
            {
                "type": "Feature",
                "id": f"synthetic-{index}",
                "properties": {"time": 0, "mag": None},
                "geometry": {"type": "Point", "coordinates": [0, 0, None]},
            }
            for index in range(size)
        ],
    }


def encode(payload: dict) -> bytes:
    return json.dumps(payload).encode()


@pytest.mark.parametrize(
    "member",
    [
        '"type": "FeatureCollection"',
        '"count": 1',
        '"id": "synthetic-0"',
        '"mag": null',
        '"coordinates": [0, 0, null]',
    ],
)
def test_duplicate_json_members_are_rejected(api: ModuleType, member: str) -> None:
    """Each replacement adds the same key twice; no last-value choice is valid.

    RFC 8259 section 4 describes duplicate-name interoperability problems.
    Rejection is this client's integrity policy, including identical values.
    """
    raw = encode(collection()).replace(member.encode(), f"{member}, {member}".encode())
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(raw, SOURCE)


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_nonfinite_json_numbers_are_rejected(api: ModuleType, number: str) -> None:
    """RFC 8259 section 6 forbids special values; float overflow is unusable.

    Even an unused extension field must not carry a non-finite decoded value.
    """
    raw = encode(collection())[:-1] + f', "extension": {number}}}'.encode()
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(raw, SOURCE)


@pytest.mark.parametrize("event_id", ["", "   ", None, 1, True])
def test_event_identifier_must_be_nonempty_text(api: ModuleType, event_id) -> None:
    """USGS Output requires a string ID; blank IDs cannot identify an event."""
    payload = collection()
    payload["features"][0]["id"] = event_id
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(encode(payload), SOURCE)


@pytest.mark.parametrize("event_time", [True, 0.5, "0", None])
def test_event_time_must_be_integer(api: ModuleType, event_time) -> None:
    """USGS Output specifies Long Integer, excluding bool/fraction/text/null."""
    payload = collection()
    payload["features"][0]["properties"]["time"] = event_time
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(encode(payload), SOURCE)


@pytest.mark.parametrize(
    "raw",
    [
        b"null",
        b"[]",
        b'{"type":"FeatureCollection","features":{}}',
        b'{"type":"FeatureCollection","features":[null]}',
        b'{"type":"FeatureCollection","features":[{}]}',
        b"\xff",
    ],
)
def test_malformed_documents_raise_service_error(api: ModuleType, raw: bytes) -> None:
    """These literals lack the USGS collection/row shape or valid JSON encoding."""
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(raw, SOURCE)


def test_excessive_nesting_raises_service_error(api: ModuleType) -> None:
    """Nesting beyond the interpreter's recursion limit cannot produce a row."""
    depth = sys.getrecursionlimit() + 1
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(b"[" * depth + b"0" + b"]" * depth, SOURCE)


@pytest.mark.parametrize("declared", [-1, 0, 2, True, 1.0, "1", None])
def test_collection_count_must_equal_row_count(api: ModuleType, declared) -> None:
    """One literal feature means count=1; all alternatives contradict its type/count.

    USGS Output specifies metadata.count as Integer. Exact row agreement is
    the client's integrity policy, not a comparison with an earlier request.
    """
    payload = collection()
    payload["metadata"]["count"] = declared
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(encode(payload), SOURCE)


@pytest.mark.parametrize("metadata", [None, [], "invalid"])
def test_metadata_must_be_object_when_present(api: ModuleType, metadata) -> None:
    """USGS Output declares metadata as an object, not null/array/string."""
    payload = collection()
    payload["metadata"] = metadata
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(encode(payload), SOURCE)


@pytest.mark.parametrize("size", [0, 1, 2])
@pytest.mark.parametrize(
    "metadata_kind", ["count", "omitted-count", "omitted-metadata"]
)
def test_valid_collection_counts_and_nulls(
    api: ModuleType, size: int, metadata_kind: str
) -> None:
    """N constructed distinct features yield N rows, with nulls preserved.

    Optional count omission preserves the existing recorded fixture contract.
    """
    payload = collection(size)
    if metadata_kind == "omitted-count":
        payload["metadata"] = {}
    elif metadata_kind == "omitted-metadata":
        del payload["metadata"]
    rows = api.parse_geojson(encode(payload), SOURCE)
    assert len(rows) == size
    assert [row.event_id for row in rows] == [f"synthetic-{i}" for i in range(size)]
    assert all(row.depth_km is None and row.magnitude is None for row in rows)


def test_duplicate_event_ids_are_rejected(api: ModuleType) -> None:
    """Two copies of one ID represent one identity, not two distinct events."""
    payload = collection(2)
    payload["features"][1]["id"] = payload["features"][0]["id"]
    with pytest.raises(api.ServiceError, match="GeoJSON"):
        api.parse_geojson(encode(payload), SOURCE)


@pytest.mark.parametrize(
    "count,returned,limit,mismatch,saturated",
    [
        (0, 0, 3, False, False),
        (1, 1, 3, False, False),
        (1, 2, 3, True, False),
        (2, 1, 3, True, False),
        (1, 1, 1, False, True),
        (1, 2, 2, True, True),
        (2, 2, 2, False, True),
    ],
)
def test_query_diagnostics(
    api: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    returned: int,
    limit: int,
    mismatch: bool,
    saturated: bool,
) -> None:
    """Hand truth table: mismatch=(N != C); saturated=(N >= L).

    N is the independently constructed feature count, C is the earlier count,
    and L is the caller's input cap (USGS event-service v1, limit parameter).
    Neither predicate establishes catalogue completeness or unchanged identity.
    """
    client = api.USGSClient()
    calls = []

    def get(url: str) -> bytes:
        calls.append(url)
        return str(count).encode() if "/count?" in url else encode(collection(returned))

    monkeypatch.setattr(client, "_get", get)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result = client.query_box(
        0,
        1,
        0,
        1,
        start=start,
        end=start + timedelta(days=1),
        min_magnitude=0,
        limit=limit,
    )
    assert len(result.events) == returned
    assert result.matched_count == count
    assert result.requested_limit == limit
    assert result.count_mismatch is mismatch
    assert result.limit_reached is saturated
    assert len(calls) == (2 if count else 1)
    if count:
        assert parse_qs(urlparse(calls[-1]).query)["limit"] == [str(limit)]


def test_legacy_result_has_unknown_limit(api: ModuleType) -> None:
    """An omitted cap is unknown; a zero-row result agrees with a zero count."""
    result = api.QueryResult((), None, SOURCE, "synthetic retrieval stamp", 0)
    assert result.requested_limit is None
    assert result.limit_reached is None
    assert result.count_mismatch is False


def test_no_content_after_positive_count_is_observable(
    api: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C=1 and N=0 gives mismatch=True; N=0 is below the input cap L=1."""
    client = api.USGSClient()
    monkeypatch.setattr(client, "_get", lambda url: b"1" if "/count?" in url else None)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result = client.query_radius(
        0,
        0,
        1,
        start=start,
        end=start + timedelta(days=1),
        min_magnitude=0,
        limit=1,
    )
    assert result.raw is None and result.events == ()
    assert result.count_mismatch is True
    assert result.limit_reached is False
