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
        ("min_water_depth_m", 3.048),
        ("buried_design", True),
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
                }


def test_absent_minimum_and_burial_do_not_become_maximum_or_exposed(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows

    screening_fixture["permits"][0].pop("MIN_WTR_DPTH")
    screening_fixture["permits"][0].pop("BURIAL_DESIGN")
    for point in screening_fixture["locations"]:
        point.pop("WATER_DEPTH")
    row = build_rows(
        **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
    )[0]
    assert row["min_water_depth_m"] is None
    assert row["buried_design"] is None
    assert row["min_water_depth_m_source"].startswith("DEFAULT:")


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

    table = [{"nps_in": 6, "od_mm": 200, "wt_mm": 10, "schedule": "SYNTHETIC"}]
    matched = estimate_wall("06", 1000, sizing_defaults, table)
    assert matched["od_m"] == pytest.approx(0.2)
    assert matched["wall_thickness_m"] == pytest.approx(0.01)
    assert matched["wall_thickness_m_source"] == "DERIVED:schedule_lookup"
    fallback = estimate_wall("06", 1000, sizing_defaults)
    assert fallback["wall_thickness_m"] == pytest.approx(
        psi_to_pa(1000) * 0.1524 / (2 * sizing_defaults["smys_pa"]["value"])
    )
    assert fallback["wall_thickness_m_source"] == "DERIVED:hoop_stress_sizing"
    assert fallback["od_m_source"] == "DEFAULT:nominal_od_proxy"
    assert fallback["grade_source"] == "DEFAULT:grade"
    assert estimate_wall("06", None, sizing_defaults)["wall_thickness_m"] is None


def test_sizing_is_attached_to_each_case(screening_fixture, sizing_defaults):
    from worldenergydata.bsee.pipeline_screening import build_rows

    screening_fixture["defaults"].update(sizing_defaults)
    rows = build_rows(
        **{k: screening_fixture[k] for k in ("permits", "locations", "defaults")}
    )
    assert all(r["wall_thickness_m"] > 0 for r in rows)
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
    for quantity in ("hs", "tp"):
        small, large = (
            result[f"{quantity}_{period}yr_" + ("m" if quantity == "hs" else "s")]
            for period in (10, 100)
        )
        assert math.isfinite(small) and large >= small > 0
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
        key: expected[key] for key in ("PUBLIC", "DERIVED", "DEFAULT")
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


def test_bulk_member_selection_alias_and_digest(screening_fixture, tmp_path):
    import csv
    import hashlib
    import io
    import zipfile

    from worldenergydata.bsee.pipeline_screening_io import read_bulk_archive

    archive = tmp_path / "permit.zip"
    output = io.StringIO()
    permit = screening_fixture["permits"][0]
    writer = csv.DictWriter(output, fieldnames=list(permit), lineterminator="\n")
    writer.writeheader()
    writer.writerow(permit)
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr(
            "PipePermRawData/mv_pipeperm_submittals.txt", "IGNORED\nsynthetic\n"
        )
        zipped.writestr("PipePermRawData/mv_pipeperm_segments.txt", output.getvalue())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert (
        list(read_bulk_archive(archive, "permit", digest))[0]["SEGMENT_NUM"]
        == "synthetic-active"
    )
    with pytest.raises(ValueError, match="digest"):
        list(read_bulk_archive(archive, "permit", "0" * 64))
    location = tmp_path / "location.zip"
    with zipfile.ZipFile(location, "w") as zipped:
        zipped.writestr(
            "PipeLocRawData/mv_pipelinelocation.txt",
            "SEGMENT_NUM,ASBUILT_SEQ_NUM,LATITUDE,LONGITUDE\nsynthetic-active,2,0,1\n",
        )
    records = list(
        read_bulk_archive(
            location, "location", hashlib.sha256(location.read_bytes()).hexdigest()
        )
    )
    assert records[0]["POINT_NUM"] == "2"


def test_external_fetch_integrity_and_path_boundary(tmp_path):
    import hashlib
    import json

    from worldenergydata.bsee.pipeline_screening_io import (
        fetch_payload,
        write_artifacts,
    )

    rows = [{"segment_id": "synthetic", "segment_id_source": "DERIVED:synthetic"}]
    revision = {
        "revision": "1",
        "history": [
            {
                "revision": "1",
                "date": "2026-10-15",
                "changed": "Initial issue",
                "why": "Synthetic test",
            }
        ],
    }
    store = tmp_path / "store"
    manifest = write_artifacts(
        rows, store, revision, repository_root=tmp_path / "repository"
    )
    destination = tmp_path / "fetched.csv"
    fetch_payload(manifest, store, destination)
    blob = store / manifest["payload"]["blob"]
    original = blob.read_bytes()
    before = hashlib.sha256(original).hexdigest()
    blob.write_bytes(b"tampered")
    tampered = hashlib.sha256(blob.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="digest"):
        fetch_payload(manifest, store, destination)
    assert destination.read_bytes() == original
    blob.write_bytes(original)
    restored = hashlib.sha256(blob.read_bytes()).hexdigest()
    assert before == restored and before != tampered
    (tmp_path / "negative-probe.json").write_text(
        json.dumps({"before": before, "tampered": tampered, "restored": restored})
        + "\n"
    )
    manifest["payload"]["blob"] = "../outside.csv"
    with pytest.raises(ValueError, match="relative"):
        fetch_payload(manifest, store, destination)


def test_committed_defaults_and_schema_cover_every_field(screening_fixture):
    from pathlib import Path

    import yaml

    from worldenergydata.bsee.pipeline_screening import build_rows, enrich_rows
    from worldenergydata.bsee.pipeline_screening_io import validate_rows

    directory = Path(__file__).parents[4] / "data/modules/pipeline/screening"
    defaults = yaml.safe_load((directory / "defaults.yaml").read_text())
    schema = yaml.safe_load((directory / "schema.yaml").read_text())
    assert all("value" in item and item.get("rationale") for item in defaults.values())
    rows = enrich_rows(
        build_rows(
            screening_fixture["permits"], screening_fixture["locations"], defaults
        ),
        defaults,
    )
    validate_rows(rows, schema, defaults)
    rows[0]["od_m_source"] = "DEFAULT:missing_key"
    with pytest.raises(ValueError, match="default"):
        validate_rows(rows, schema, defaults)


def test_ndbc_retained_response_parse_and_digest(tmp_path):
    import hashlib

    from worldenergydata.bsee.pipeline_screening_sources import (
        fetch_ndbc_histories,
        retain_response,
        retained_input_refs,
    )

    url = "https://www.ndbc.noaa.gov/view_text_file.php?filename=42001h2022.txt.gz&dir=data/historical/stdmet/"
    body = b"# Synthetic observations\n2022 01 01 00 00 90 5 6 1.5 6 5 90 1010 20 20 10 99 0 0\n2022 01 02 00 00 90 5 6 2.5 7 6 90 1010 20 20 10 99 0 0\n"
    metadata = retain_response(tmp_path, url, body, 200, "2026-10-15T00:00:00Z")
    result = fetch_ndbc_histories(["42001"], [2022], tmp_path, allow_network=False)
    assert len(result["42001"]) == 2
    assert result["42001"][0].wave_height_m == 1.5
    refs = retained_input_refs(tmp_path, ["42001"], [2022])
    assert refs[0]["sha256"] == metadata["sha256"]
    assert refs[0]["source_id"] == "noaa-ndbc"
    raw = tmp_path / metadata["body"]
    before = hashlib.sha256(raw.read_bytes()).hexdigest()
    raw.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        fetch_ndbc_histories(["42001"], [2022], tmp_path, allow_network=False)
    raw.write_bytes(body)
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == before


def _command_sources(screening_fixture, tmp_path):
    import csv
    import hashlib
    import io
    import json
    import zipfile

    sources = tmp_path / "sources"
    sources.mkdir()
    specs = [
        ("permit", "mv_pipeperm_segments.txt", screening_fixture["permits"]),
        ("location", "mv_pipelinelocation.txt", screening_fixture["locations"]),
    ]
    ledger = []
    for kind, member, records in specs:
        stream = io.StringIO()
        fields = sorted({key for record in records for key in record})
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
        archive = sources / (kind + ".zip")
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr(member, stream.getvalue())
        ledger.append(
            {
                "file": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "bytes": archive.stat().st_size,
                "record_count": len(records),
            }
        )
    station = sources / "stations.xml"
    station.write_text(
        '<stations><station id="near" lat="0" lon="1" type="buoy" name="Synthetic" /></stations>'
    )
    ledger.append(
        {
            "file": station.name,
            "sha256": hashlib.sha256(station.read_bytes()).hexdigest(),
            "bytes": station.stat().st_size,
            "record_count": 1,
        }
    )
    source_ledger = sources / "sources.json"
    source_ledger.write_text(json.dumps(ledger))
    return sources, source_ledger


def _command_arguments(root, sources, source_ledger, tmp_path, name):
    import sys

    flags = {
        "permit-zip": sources / "permit.zip",
        "location-zip": sources / "location.zip",
        "station-xml": sources / "stations.xml",
        "source-ledger": source_ledger,
        "output": tmp_path / name,
        "cache": tmp_path / "cache",
        "execution-record": tmp_path / "execution.json",
    }
    command = [sys.executable, str(root / "scripts/bsee/build_pipeline_screening.py")]
    for flag, value in flags.items():
        command.extend(["--" + flag, str(value)])
    return command + ["--offline"]


def test_offline_command_builds_twice_with_pinned_criteria(screening_fixture, tmp_path):
    import hashlib
    import json
    import os
    import subprocess
    from datetime import datetime
    from pathlib import Path

    root = Path(__file__).parents[4]
    sources, source_ledger = _command_sources(screening_fixture, tmp_path)
    child_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}
    }
    for name in ("first", "second"):
        command = _command_arguments(root, sources, source_ledger, tmp_path, name)
        completed = subprocess.run(
            command, env=child_env, capture_output=True, text=True
        )
        assert completed.returncode == 0, completed.stderr
    first = json.loads((tmp_path / "first/manifest.json").read_text())
    assert first == json.loads((tmp_path / "second/manifest.json").read_text())
    criteria = first["criteria"]
    assert datetime.fromisoformat(criteria["recorded_at"]) <= datetime.fromisoformat(
        criteria["first_run_started_at"]
    )
    assert (
        criteria["schema_sha256"]
        == hashlib.sha256(
            (root / "data/modules/pipeline/screening/schema.yaml").read_bytes()
        ).hexdigest()
    )


def test_identical_permit_joins_collapse_but_conflicts_fail(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows

    permit = screening_fixture["permits"][0].copy()
    permit["ROW_NUMBER"] = "synthetic-other-grant"
    screening_fixture["permits"].append(permit)
    screening_fixture["permits"][1]["MAOP_PRSS"] = -1
    inputs = {
        key: screening_fixture[key] for key in ("permits", "locations", "defaults")
    }
    assert len(build_rows(**inputs)) == 2
    permit["MAOP_PRSS"] = 2000
    with pytest.raises(ValueError, match="Conflicting"):
        build_rows(**inputs)


def test_known_nonterminal_status_and_missing_status(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows

    inputs = {
        key: screening_fixture[key] for key in ("permits", "locations", "defaults")
    }
    screening_fixture["permits"][0]["STATUS_CODE"] = "PREM"
    assert len(build_rows(**inputs)) == 2
    screening_fixture["permits"][0]["STATUS_CODE"] = None
    assert build_rows(**inputs) == []


def test_public_status_dictionary_filters_terminal_and_unmapped(screening_fixture):
    from pathlib import Path

    import yaml

    from worldenergydata.bsee.pipeline_screening import build_rows

    config = Path(__file__).parents[4] / "data/modules/pipeline/screening/defaults.yaml"
    defaults = yaml.safe_load(config.read_text())
    included = {"ACT", "CNCL", "COMB", "PABN", "PREM", "PROP", "RELQ", "R/C"}
    excluded = {"ABN", "RMV", "OUT", "REM", "A/C", "O/C", "R/A", "R/R"}
    unmapped = {"DECP", "DECR", "APMO", "OPMO"}
    permits = [
        {
            **screening_fixture["permits"][0],
            "SEGMENT_NUM": "synthetic-" + status,
            "STATUS_CODE": status,
        }
        for status in sorted(included | excluded | unmapped)
    ]
    rows = build_rows(permits, [], defaults)
    assert {row["status"] for row in rows} == included


def test_missing_status_dictionary_rejects_selection(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows

    screening_fixture["defaults"].pop("status_meanings", None)
    inputs = {
        key: screening_fixture[key] for key in ("permits", "locations", "defaults")
    }
    with pytest.raises(ValueError, match="status dictionary"):
        build_rows(**inputs)
