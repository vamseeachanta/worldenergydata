"""Offline screening checks; numerical fixtures are synthetic."""

import hashlib
import json
from collections import Counter

import pytest
from scipy.constants import mile


def test_size_code_and_si_units():
    from worldenergydata.bsee.pipeline_screening import decode_size_code, length_to_m

    assert decode_size_code("06") == pytest.approx(0.1524)
    assert decode_size_code("04-06") is None
    assert decode_size_code("") is None
    assert length_to_m(10, "ft") == pytest.approx(3.048)
    assert length_to_m(1, "mile") == pytest.approx(mile)
    with pytest.raises(ValueError):
        length_to_m(1, "unknown")


@pytest.mark.parametrize(
    "field, expected",
    [
        ("midpoint_latitude_deg", 0),
        ("midpoint_longitude_deg", 1),
        ("mean_bearing_deg", 90),
    ],
)
def test_ordered_route_midpoint_and_bearing(field, expected):
    from worldenergydata.bsee.pipeline_screening import route_geometry

    points = [
        {"POINT_NUM": n, "LATITUDE": 0, "LONGITUDE": lon}
        for n, lon in [(3, 2), (1, 0), (2, 1)]
    ]
    assert route_geometry(points)[field] == pytest.approx(expected)


def test_route_length_and_duplicate_sequence_rejection():
    from worldenergydata.bsee.pipeline_screening import route_geometry
    from worldenergydata.metocean.utils.coordinates import haversine_distance

    points = [
        {"POINT_NUM": 1, "LATITUDE": 0, "LONGITUDE": 0},
        {"POINT_NUM": 2, "LATITUDE": 0, "LONGITUDE": 2},
    ]
    assert route_geometry(points)["length_m"] == pytest.approx(
        1000 * haversine_distance(0, 0, 0, 2)
    )
    points[1]["POINT_NUM"] = 1
    with pytest.raises(ValueError, match="sequence"):
        route_geometry(points)


@pytest.fixture
def screening_fixture():
    import json
    from pathlib import Path

    path = Path(__file__).parents[3] / "fixtures/bsee/pipeline_screening.json"
    return json.loads(path.read_text())


@pytest.mark.parametrize(
    "field, expected",
    [
        ("permit_length_m", mile),
        ("status", "ACT"),
        ("contents_density_kg_m3", 0),
    ],
)
def test_active_segment_depth_burial_units_and_empty_case(
    screening_fixture, field, expected
):
    from worldenergydata.bsee.pipeline_screening import build_rows

    rows = build_rows(
        **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
    )
    assert len(rows) == 2
    assert {r["segment_id"] for r in rows} == {"synthetic-active"}
    assert [r["load_case"] for r in rows] == ["empty", "product"]
    assert rows[0][field] == expected
    for row in rows:
        for key in row:
            if not key.endswith("_source"):
                assert row[key + "_source"].split(":", 1)[0] in {
                    "PUBLIC",
                    "DERIVED",
                    "DEFAULT",
                    "UNKNOWN",
                }


def test_unsupported_depth_and_burial_fields_are_removed(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows

    row = build_rows(
        **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
    )[0]
    assert "min_water_depth_m" not in row
    assert "buried_design" not in row


@pytest.fixture
def sizing_defaults():
    return {
        "grade": {"value": "synthetic", "rationale": "Synthetic test material"},
        "smys_pa": {"value": 100000000, "rationale": "Synthetic test strength"},
        "schedule": {"value": "SYNTHETIC", "rationale": "Synthetic dimensional table"},
    }


def test_schedule_lookup_and_hoop_sizing(sizing_defaults):
    from worldenergydata.bsee.pipeline.adapters.units import psi_to_pa
    from worldenergydata.bsee.pipeline_screening import estimate_wall

    table = [
        {
            "nps_in": 6,
            "od_mm": 200,
            "wt_mm": 10,
            "schedule": "SYNTHETIC",
            "source": "synthetic",
            "rights": "synthetic",
            "edition": "test",
        }
    ]
    matched = estimate_wall("06", 1000, sizing_defaults, table)
    assert matched["od_m"] == pytest.approx(0.2)
    assert matched["wall_thickness_m"] == pytest.approx(0.01)
    assert matched["wall_thickness_m_source"] == "DERIVED:schedule_lookup"
    fallback = estimate_wall("06", 1000, sizing_defaults)
    assert fallback["hoop_yield_wall_at_assumed_smys_m"] == pytest.approx(
        psi_to_pa(1000) * 0.1524 / (2 * sizing_defaults["smys_pa"]["value"])
    )
    assert fallback["wall_thickness_m"] is None
    assert fallback["wall_thickness_m_source"] == "UNKNOWN:no_evidenced_wall"
    assert (
        fallback["hoop_yield_wall_at_assumed_smys_m_source"]
        == "DERIVED:hoop_yield_at_assumed_smys"
    )
    assert fallback["od_m_source"] == "DEFAULT:nominal_od_proxy"
    assert fallback["grade_source"] == "DEFAULT:grade"
    assert estimate_wall("06", None, sizing_defaults)["wall_thickness_m"] is None


def test_sizing_is_attached_to_each_case(screening_fixture, sizing_defaults):
    from worldenergydata.bsee.pipeline_screening import build_rows

    screening_fixture["defaults"].update(sizing_defaults)
    rows = build_rows(
        **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
    )
    assert all(r["wall_thickness_m"] is None for r in rows)
    assert all(r["hoop_yield_wall_at_assumed_smys_m"] > 0 for r in rows)
    assert all(r["smys_pa"] == sizing_defaults["smys_pa"]["value"] for r in rows)


def test_ndbc_snapshot_and_return_levels(tmp_path):
    import math
    from datetime import datetime

    from worldenergydata.bsee.pipeline_screening import (
        read_ndbc_stations,
        station_environment,
    )
    from worldenergydata.metocean.clients.ndbc_client import NDBCObservation

    station_file = tmp_path / "stations.xml"
    station_file.write_text(
        '<stations><station id="near" lat="0" lon="1" type="buoy" name="Synthetic" />'
        '<station id="far" lat="0" lon="10" type="buoy" name="Synthetic" /></stations>'
    )
    stations = read_ndbc_stations(station_file)
    observations = [
        NDBCObservation(
            station_id="near",
            observation_time=datetime(year, 1, 1),
            wave_height_m=hs,
            dominant_wave_period_s=tp,
        )
        for year, hs, tp in [(2000, 1, 4), (2001, 3, 8), (2002, 2, 6), (2003, 4, 9)]
    ]
    result = station_environment(0, 1, stations, {"near": observations})
    assert result["station_id"] == "near"
    assert result["record_length_years"] >= 3
    assert result["complete_annual_maxima"] == 0
    assert result["hs_10yr_m"] is result["hs_100yr_m"] is None
    assert "tp_10yr_s" not in result
    missing = station_environment(0, 1, stations, {})
    assert missing["hs_100yr_m"] is None
    assert missing["record_length_years"] is None


def test_environment_defaults_and_public_sediment(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows, enrich_rows

    defaults = screening_fixture["defaults"]
    for key, value in {
        "corrosion_coating": None,
        "corrosion_coating_thickness_m": None,
        "concrete_density_kg_m3": None,
        "seabed_current_m_s": 0.3,
        "friction_coefficient": 0,
        "product_densities": {"OIL": 900},
    }.items():
        defaults[key] = {"value": value, "rationale": "Synthetic fixture assumption"}
    rows = build_rows(
        **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
    )
    enriched = enrich_rows(
        rows,
        defaults,
        sediment=[
            {
                "Latitude": 0,
                "Longitude": 1,
                "Sand": 80,
                "Mud": 20,
                "Gravel": 0,
                "Clay": 0,
            },
        ],
    )
    assert enriched[0]["soil_type"] == "sand"
    assert enriched[0]["soil_type_source"] == "DERIVED:nearest_usgs_texture"
    assert enriched[0]["friction_coefficient_source"].startswith("DEFAULT:")
    assert enriched[0]["wave_direction_deg"] == pytest.approx(180)
    assert enriched[0]["contents_density_kg_m3"] == 0
    assert enriched[1]["contents_density_kg_m3"] == 900


def _matching_artifacts(rows, tmp_path, revision, repository):
    from worldenergydata.bsee.pipeline_screening_io import write_artifacts

    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        write_artifacts(rows, output, revision, repository_root=repository)
    names = {p.relative_to(outputs[0]) for p in outputs[0].rglob("*") if p.is_file()}
    for name in names:
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()
    return outputs[0]


def test_artifacts_source_counts_revision_and_digests(screening_fixture, tmp_path):
    from worldenergydata.bsee.pipeline_screening import build_rows, enrich_rows
    from worldenergydata.bsee.pipeline_screening_io import qa_counts

    rows = enrich_rows(
        build_rows(
            **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
        ),
        screening_fixture["defaults"],
    )
    expected = Counter(
        value.split(":")[0]
        for row in rows
        for key, value in row.items()
        if key.endswith("_source")
    )
    counts = qa_counts(rows)
    assert counts["source_classes"] == {
        key: expected[key] for key in ("PUBLIC", "DERIVED", "DEFAULT", "UNKNOWN")
    }
    revision = {
        "revision": "1",
        "history": [
            {
                "revision": "1",
                "date": "2026-10-15",
                "changed": "Initial issue",
                "why": "Expose screening inputs",
            }
        ],
    }
    repository = tmp_path / "repository"
    repository.mkdir()
    first = _matching_artifacts(rows, tmp_path, revision, repository)
    manifest = json.loads((first / "manifest.json").read_text())
    payload = first / manifest["payload"]["blob"]
    assert (
        hashlib.sha256(payload.read_bytes()).hexdigest()
        == manifest["payload"]["sha256"]
    )
    assert payload.stat().st_size == manifest["payload"]["bytes"]
    page = (first / "qa.html").read_text()
    assert (
        page.index("Summary</h2>")
        < page.index("Revision history</h2>")
        < page.index("Source counts</h2>")
    )
    assert 'data-revision="1"' in page
    assert "<script" not in page and "<link" not in page and "<img" not in page
    assert len((first / "sample.csv").read_text().splitlines()) <= 101


def test_missing_source_and_inconsistent_revision_are_rejected(tmp_path):
    from worldenergydata.bsee.pipeline_screening_io import qa_counts, write_artifacts

    with pytest.raises(ValueError, match="source"):
        qa_counts([{"value": 1}])
    with pytest.raises(ValueError, match="revision"):
        write_artifacts(
            [],
            tmp_path / "out",
            {"revision": "2", "history": [{"revision": "1"}]},
            repository_root=tmp_path / "repository",
        )
