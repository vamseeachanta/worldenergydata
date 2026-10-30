"""Offline audit regressions; all well, terms and byte inputs are synthetic.

The acceptance basis is issue 1164: missing identities never select, measured
origins survive repetition, changed terms stop data requests, and each request
uses the remaining aggregate budget. Expected counts are hand enumerated.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from worldenergydata.australia.metadata import nopta_wells as nw
from worldenergydata.australia.metadata.well_enrichment import enrich_field_metadata


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("network forbidden in offline tests")

    monkeypatch.setattr(nw, "open_request", deny)


@pytest.fixture
def sample():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "nopta_synthetic.json").read_text()
    )


@pytest.mark.parametrize("identifier", [None, "", " \t", False, 7])
def test_absent_or_nontext_well_identity_never_selects(identifier):
    """Uwi is textual; absent, whitespace or nontext identities select no well."""
    meta = {"field_name": "synthetic", "well_identifier": identifier}
    well = dict(
        meta, water_depth=12, water_depth_unit="m", water_depth_datum="synthetic"
    )
    result = enrich_field_metadata(meta, [well])
    assert result["water_depth_m"] is None
    assert result["value_origins"]["water_depth_m"] == "missing"


def test_repetition_retains_depth_and_coordinate_origins():
    """Values 12 m and (0, 0) are synthetic; identity conversion leaves 12 m.

    The spatial-reference identifier is inherited from nopta_synthetic.json's
    layer metadata. Repetition, empty input and an unusable linked well must all
    retain the two measured origins without accumulating source suffixes.
    """
    meta = {"field_name": "synthetic", "well_identifier": "synthetic-well"}
    layer = json.loads(
        (Path(__file__).parent / "fixtures" / "nopta_synthetic.json").read_text()
    )["layer"]
    well = dict(
        meta,
        water_depth=12,
        water_depth_unit="m",
        water_depth_datum="synthetic",
        latitude=0,
        longitude=0,
        spatial_reference=layer["spatialReference"],
    )
    before = copy.deepcopy(well)
    first = enrich_field_metadata(meta, [well])
    assert first["water_depth_m"] == 12
    assert first["value_origins"] == {
        "water_depth_m": "measured",
        "coordinates": "measured",
    }
    for rows in ([well], [], [dict(meta, water_depth=None)]):
        assert enrich_field_metadata(first, rows) == first
    assert well == before
    assert "water_depth_m" not in meta


@pytest.mark.parametrize("changed", [False, True])
def test_terms_assessment_precedes_every_data_request(sample, monkeypatch, changed):
    """Synthetic reviewed bytes allow one query; appending a ban allows none.

    Retaining the old licence sentence is insufficient: the full byte digest
    must agree. The original access_preflight is exercised through fetch_wells.
    """
    reviewed = b"Synthetic licence sentence."
    monkeypatch.setattr(
        nw, "REVIEWED_TERMS_SHA256", hashlib.sha256(reviewed).hexdigest()
    )
    calls = []

    def transport(url, **kwargs):
        calls.append(url)
        if url == nw.ROBOTS_URL:
            return b"User-agent: *\nAllow: /"
        if url == nw.TERMS_URL:
            return reviewed + (b" Automated access forbidden." if changed else b"")
        return b'{"features": [], "exceededTransferLimit": false}'

    monkeypatch.setattr(nw, "get_bytes", transport)
    if changed:
        with pytest.raises(ValueError, match="terms changed"):
            nw.fetch_wells(sample["layer"])
        assert calls == [nw.ROBOTS_URL, nw.TERMS_URL]
    else:
        rows, evidence = nw.fetch_wells(sample["layer"])
        assert rows == []
        assert len(calls) == len(evidence) == 3


@pytest.mark.parametrize("remaining", [0, 1])
def test_later_page_uses_remaining_budget(sample, monkeypatch, remaining):
    """Budget = length(first page) + remainder, so second cap is remainder.

    With a zero remainder the first query is the only data request. With a
    one-byte remainder the second transport receives exactly one byte as cap.
    Policy preflight evidence is separate from this data-response byte budget.
    """
    first = json.dumps(sample["pages"][0]).encode()
    caps = []
    monkeypatch.setattr(nw, "access_preflight", list)

    def transport(url, *, max_bytes):
        caps.append(max_bytes)
        if len(caps) == 1:
            return first
        raise ValueError("response byte cap exceeded")

    monkeypatch.setattr(nw, "get_bytes", transport)
    with pytest.raises(ValueError, match="byte cap"):
        nw.fetch_wells(sample["layer"], max_total_bytes=len(first) + remaining)
    assert caps == ([len(first)] if remaining == 0 else [len(first) + 1, 1])


@pytest.mark.parametrize("limit", [True, 1.5, "1", None])
def test_noninteger_byte_limits_fail_before_transport(sample, monkeypatch, limit):
    """Byte counts must be integers; invalid inputs permit zero requests."""
    with pytest.raises(ValueError, match="byte cap"):
        nw.get_bytes(nw.QUERY_URL, max_bytes=limit)
    with pytest.raises(ValueError, match="query limits"):
        nw.fetch_wells(sample["layer"], max_total_bytes=limit)
