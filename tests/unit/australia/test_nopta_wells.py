"""Offline NOPTA contracts; all well values below are synthetic."""
import copy
import io
import json
import urllib.error
from pathlib import Path

import pytest

from worldenergydata.australia.field_concept import build_australia_field_concept
from worldenergydata.australia.metadata import nopta_wells as nw
from worldenergydata.australia.metadata.well_enrichment import enrich_field_metadata

ORIGINAL_PREFLIGHT = nw.access_preflight

FIXTURE = Path(__file__).parent / "fixtures" / "nopta_synthetic.json"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("network forbidden in offline tests")
    monkeypatch.setattr(nw, "open_request", deny)
    monkeypatch.setattr(nw.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(nw, "access_preflight", lambda: [])


@pytest.fixture
def sample():
    return json.loads(FIXTURE.read_text())


def test_metadata_and_missing_depth(sample):
    layer = nw.parse_layer(sample["layer"])
    rows = nw.normalize_page(sample["pages"][0], layer)
    assert rows[0]["well_identifier"] == "synthetic-1"
    assert rows[0]["water_depth"] is None
    assert rows[0]["water_depth_unit"] is None
    assert rows[0]["water_depth_datum"] is None
    assert rows[0]["field_name"] is None
    assert rows[0]["spatial_reference"] == {"wkid": 4283}
    assert rows[0]["longitude"] == 130.0
    assert rows[0]["source_columns"]["TitleNumber"] == "synthetic-title"


def test_reject_missing_fields_and_pagination(sample):
    for key in ("fields", "advancedQueryCapabilities"):
        bad = copy.deepcopy(sample["layer"])
        bad[key] = [] if key == "fields" else {}
        with pytest.raises(ValueError):
            nw.parse_layer(bad)


def test_paging_and_query_limits(sample, monkeypatch):
    seen = []

    def fetch(url, **kwargs):
        seen.append(url)
        return json.dumps(sample["pages"][len(seen)-1]).encode()
    monkeypatch.setattr(nw, "get_bytes", fetch)
    rows, evidence = nw.fetch_wells(sample["layer"], where="OBJECTID <= 5")
    assert len(rows) == 2
    assert len(evidence) == 2
    assert "resultRecordCount=1" in seen[0]
    assert "resultOffset=1" in seen[1]
    assert "orderByFields=OBJECTID" in seen[0]


def test_page_cap_and_duplicate_ids_fail(sample, monkeypatch):
    monkeypatch.setattr(
        nw, "get_bytes", lambda url, **kwargs: json.dumps(sample["pages"][0]).encode()
    )
    with pytest.raises(ValueError, match="page cap"):
        nw.fetch_wells(sample["layer"], max_pages=1)
    with pytest.raises(ValueError, match="duplicate"):
        nw.fetch_wells(sample["layer"])


@pytest.mark.parametrize("url", [
    "http://gis.spatial.nopta.gov.au/gis/rest/services/Public/Wells/FeatureServer/0/query",
    "https://example.org/query", nw.QUERY_URL + "?token=secret",
    "https://user@gis.spatial.nopta.gov.au/gis/rest/services/Public/Wells/FeatureServer/0/query",
])
def test_destination_rejected(url):
    with pytest.raises(ValueError):
        nw.get_bytes(url)


def test_response_cap_and_timeout(monkeypatch):
    class Response(io.BytesIO):
        status = 200
    seen = []

    def open_mock(request, timeout):
        seen.append(timeout)
        return Response(b"x" * 11)
    monkeypatch.setattr(nw, "open_request", open_mock)
    with pytest.raises(ValueError, match="byte cap"):
        nw.get_bytes(nw.QUERY_URL, max_bytes=10)
    assert seen == [30]


def test_refusal_no_retry(monkeypatch):
    def refused(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "refused", {}, None)
    monkeypatch.setattr(nw, "open_request", refused)
    with pytest.raises(urllib.error.HTTPError):
        nw.get_bytes(nw.QUERY_URL)


@pytest.mark.parametrize("unit,value,expected", [("m", 100, 100), ("ft", 100, 30.48)])
def test_measured_preference(unit, value, expected):
    well = {"well_identifier": "synthetic-1", "field_name": "Synthetic Field",
            "water_depth": value, "water_depth_unit": unit,
            "water_depth_datum": "synthetic sea level", "latitude": -20.0,
            "longitude": 130.0, "spatial_reference": {"wkid": 4283}}
    meta = {"field_name": "Synthetic Field", "well_identifier": "synthetic-1",
            "water_depth_m": 78, "source": "synthetic fallback"}
    enriched = enrich_field_metadata(meta, [well])
    assert enriched["water_depth_m"] == pytest.approx(expected)
    assert enriched["value_origins"]["water_depth_m"] == "measured"
    assert enriched["latitude"] == -20.0
    assert enriched["spatial_reference"] == {"wkid": 4283}
    concept = build_australia_field_concept(meta, wells=[well])
    assert concept.water_depth_m == pytest.approx(expected)
    assert "water_depth_m=measured" in concept.data_source


@pytest.mark.parametrize("change", [
    {"water_depth": None}, {"water_depth_unit": "unknown"},
    {"water_depth_datum": None}, {"water_depth_datum": True},
    {"water_depth_datum": 123}, {"water_depth_datum": "   "}, {"field_name": None},
    {"field_name": "Another Field"}, {"water_depth": -1},
])
def test_unknown_or_unlinked_depth_keeps_default(change):
    well = {"well_identifier": "synthetic-1", "field_name": "Synthetic Field",
            "water_depth": 100, "water_depth_unit": "m", "water_depth_datum": "sea level"}
    well.update(change)
    meta = {"field_name": "Synthetic Field", "well_identifier": "synthetic-1", "water_depth_m": 78}
    result = enrich_field_metadata(meta, [well])
    assert result["water_depth_m"] == 78
    assert result["value_origins"]["water_depth_m"] == "default"
    assert meta["water_depth_m"] == 78


def test_no_identifier_does_not_guess(sample):
    rows = nw.normalize_page(sample["pages"][0], nw.parse_layer(sample["layer"]))
    result = enrich_field_metadata({"field_name": "Synthetic Field"}, rows)
    assert result["water_depth_m"] is None
    assert result["value_origins"]["water_depth_m"] == "missing"


def test_manifest_exact_reproduction(sample):
    result = nw.fixture_manifest(FIXTURE.read_bytes())
    target = FIXTURE.with_name("nopta_synthetic_manifest.json")
    assert nw.json_bytes(result) == target.read_bytes()


def test_schema_describes_normalized_rows(sample):
    schema_path = Path(nw.__file__).parent.parent / "data" / "nopta_well.schema.json"
    schema = json.loads(schema_path.read_text())
    rows = nw.normalize_page(sample["pages"][0], nw.parse_layer(sample["layer"]))
    assert set(rows[0]) == set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["water_depth"]["type"] == ["number", "null"]
    assert schema["properties"]["water_depth_unit"]["enum"] == ["m", "ft", None]


@pytest.mark.parametrize("robots", [b"User-agent: *\nDisallow: /", b"<html>challenge</html>"])
def test_preflight_refuses_access(robots, monkeypatch):
    calls = []

    def respond(url):
        calls.append(url)
        return robots

    monkeypatch.setattr(nw, "get_bytes", respond)
    with pytest.raises(ValueError):
        ORIGINAL_PREFLIGHT()
    assert calls == [nw.ROBOTS_URL]


def test_preflight_records_missing_robots_and_terms(monkeypatch):
    def response(url):
        if url == nw.ROBOTS_URL:
            raise urllib.error.HTTPError(url, 404, "missing", {}, None)
        return ("All material on this  website is licensed under a Creative Commons "
                "Attribution 4.0 International Licence").encode()
    monkeypatch.setattr(nw, "get_bytes", response)
    import hashlib

    monkeypatch.setattr(
        nw, "REVIEWED_TERMS_SHA256", hashlib.sha256(response(nw.TERMS_URL)).hexdigest()
    )
    records = ORIGINAL_PREFLIGHT()
    assert records[0]["status"] == 404
    assert records[1]["source_url"] == nw.TERMS_URL
    assert records[1]["size_bytes"] > 0
    assert len(records[1]["sha256"]) == 64


def test_redirect_is_refused():
    with pytest.raises(ValueError, match="redirect"):
        nw.NoRedirect().redirect_request(None, None, 302, "found", {}, "https://example.org")


@pytest.mark.parametrize("name", [None, "", "   "])
def test_missing_explicit_field_link_never_selects(name):
    meta = {"field_name": name, "well_identifier": "synthetic-1"}
    well = {"field_name": name, "well_identifier": "synthetic-1", "latitude": -20,
            "longitude": 130, "spatial_reference": {"wkid": 4283},
            "water_depth": 100, "water_depth_unit": "m", "water_depth_datum": "sea level"}
    result = enrich_field_metadata(meta, [well])
    assert result["water_depth_m"] is None
    assert result.get("latitude") is None


def test_enrichment_is_idempotent_and_preserves_measured_origin():
    meta = {"field_name": "Synthetic Field", "well_identifier": "synthetic-1", "water_depth_m": 78}
    well = {"field_name": "Synthetic Field", "well_identifier": "synthetic-1",
            "water_depth": 100, "water_depth_unit": "m", "water_depth_datum": "sea level"}
    first = enrich_field_metadata(meta, [well])
    second = enrich_field_metadata(first, [])
    assert second == first
    assert "water_depth_m=measured" in build_australia_field_concept(first).data_source


def test_changed_terms_fail_closed(monkeypatch):
    terms = ("All material on this  website is licensed under a Creative Commons "
             "Attribution 4.0 International Licence. Automated access is forbidden.").encode()
    monkeypatch.setattr(
        nw, "get_bytes",
        lambda url: b"User-agent: *\nAllow: /" if url == nw.ROBOTS_URL else terms
    )
    with pytest.raises(ValueError, match="terms changed"):
        ORIGINAL_PREFLIGHT()


def test_total_budget_bounds_transport(sample, monkeypatch):
    def transport(url, *, max_bytes=2_000_000):
        assert max_bytes == 1
        raise ValueError("response byte cap exceeded")
    monkeypatch.setattr(nw, "get_bytes", transport)
    with pytest.raises(ValueError, match="byte cap"):
        nw.fetch_wells(sample["layer"], max_total_bytes=1)
