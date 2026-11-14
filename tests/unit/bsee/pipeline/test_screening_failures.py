"""Failure paths and review regressions use disposable inputs."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from worldenergydata.bsee.pipeline_screening_io import (
    _write_once,
    qa_counts,
    read_bulk_archive,
    validate_rows,
    write_artifacts,
)


def test_source_metadata_is_required(tmp_path):
    revision = {"revision": "1", "history": [{"revision": "1"}]}
    with pytest.raises(ValueError, match="source metadata"):
        write_artifacts(
            [],
            tmp_path / "out",
            revision,
            repository_root=tmp_path / "repo",
            inputs=[{"source_id": "noaa-ndbc", "sha256": "0" * 64}],
        )


@pytest.mark.parametrize("tag,value", [("bad", 1), ("PUBLIC:x", float("inf"))])
def test_invalid_cells_reject(tag, value):
    with pytest.raises(ValueError):
        qa_counts([{"segment_id": value, "segment_id_source": tag}])


def test_conflicting_write_rejects_and_preserves_bytes(tmp_path):
    file = tmp_path / "value"
    _write_once(file, b"original")
    with pytest.raises(ValueError, match="different bytes"):
        _write_once(file, b"changed")
    assert file.read_bytes() == b"original"


@pytest.mark.parametrize("output_inside,store_inside", [(True, False), (False, True)])
def test_repository_boundaries(tmp_path, output_inside, store_inside):
    root = tmp_path / "repo"
    revision = {"revision": "1", "history": [{"revision": "1"}]}
    with pytest.raises(ValueError, match="outside"):
        write_artifacts(
            [],
            root / "out" if output_inside else tmp_path / "out",
            revision,
            repository_root=root,
            store_root=root / "store" if store_inside else tmp_path / "store",
        )


@pytest.mark.parametrize(
    "members,kind,message",
    [
        ({"mv_pipeperm_segments.txt": "SEGMENT_NUM\nx\n"}, "permit", "header"),
        ({"other.txt": "x"}, "permit", "member"),
        ({}, "wrong", "kind"),
        (
            {"mv_pipeperm_segments.txt": "SEGMENT_NUM,SEGMENT_NUM\nx,x\n"},
            "permit",
            "header",
        ),
    ],
)
def test_bulk_errors(tmp_path, members, kind, message):
    path = tmp_path / "input.zip"
    with zipfile.ZipFile(path, "w") as z:
        for name, raw in members.items():
            z.writestr(name, raw)
    with pytest.raises(ValueError, match=message):
        list(
            read_bulk_archive(path, kind, hashlib.sha256(path.read_bytes()).hexdigest())
        )


@pytest.mark.parametrize(
    "value,tag,message", [(None, "UNKNOWN:absent", "Required"), (1, "PUBLIC:x", "type")]
)
def test_schema_value_failures(value, tag, message):
    schema = {"fields": {"segment_id": {"type": "string", "nullable": False}}}
    with pytest.raises(ValueError, match=message):
        validate_rows([{"segment_id": value, "segment_id_source": tag}], schema, {})


def test_route_rejections_and_outliers_are_reported(tmp_path):
    from worldenergydata.bsee.pipeline_screening import build_rows
    from worldenergydata.bsee.pipeline_screening_qa import engineering_qa

    defaults = {
        "permit_length_unit": {"value": "ft"},
        "empty_density": {"value": 0},
        "product_density": {"value": None},
        "status_meanings": {"value": {"ACT": "ACTIVE"}},
    }
    permits = [
        {"SEGMENT_NUM": "x", "STATUS_CODE": "ACT", "SEG_LENGTH": 1},
        {"SEGMENT_NUM": "y", "STATUS_CODE": "ACT", "SEG_LENGTH": 1},
    ]
    locations = [
        {"SEGMENT_NUM": "x", "POINT_NUM": 1, "LATITUDE": 100, "LONGITUDE": 0},
        {"SEGMENT_NUM": "y", "POINT_NUM": 1, "LATITUDE": 0, "LONGITUDE": 0},
        {"SEGMENT_NUM": "y", "POINT_NUM": 2, "LATITUDE": 0, "LONGITUDE": 1},
    ]
    rows = build_rows(permits, locations, defaults)
    qa = engineering_qa(rows)
    assert qa["rejected_routes"]["count"] == 1
    assert qa["rejected_routes"]["segments"][0]["segment_id"] == "x"
    assert qa["length_outliers"]["count"] == 1
    assert qa["length_outliers"]["segments"][0]["segment_id"] == "y"
    revision = {
        "revision": "1",
        "history": [
            {
                "revision": "1",
                "date": "2026-10-17",
                "changed": "synthetic",
                "why": "regression",
            }
        ],
    }
    output = tmp_path / "output"
    write_artifacts(rows, output, revision, repository_root=tmp_path / "repo")
    saved = json.loads((output / "qa.json").read_text())
    assert saved["rejected_routes"] == qa["rejected_routes"]
    assert saved["length_outliers"] == qa["length_outliers"]
    page = (output / "qa.html").read_text()
    assert "rejected_routes" in page and "length_outliers" in page
    assert "&quot;x&quot;" in page and "&quot;y&quot;" in page


def test_station_cache_tampering_is_rejected(tmp_path):
    from worldenergydata.bsee.pipeline_screening_io import cached_station_summaries

    cached_station_summaries({"synth": []}, tmp_path, {})
    file = next((tmp_path / "station-results").glob("*.json"))
    data = json.loads(file.read_text())
    data["result"]["complete_annual_maxima"] = 999
    original = file.read_bytes()
    file.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="digest"):
        cached_station_summaries({"synth": []}, tmp_path, {})
    file.write_bytes(original)
    assert file.read_bytes() == original


@pytest.mark.parametrize(
    "code,status,layer",
    [
        (6, 0, "name_resolution"),
        (7, 0, "network_reachability"),
        (28, 0, "network_timeout"),
        (0, 403, "auth_rejection"),
        (0, 404, "application_error"),
        (0, 503, "application_error"),
        (0, 200, None),
    ],
)
def test_transfer_classification_and_cleanup(
    tmp_path, monkeypatch, code, status, layer
):
    from types import SimpleNamespace

    import worldenergydata.bsee.pipeline_screening_sources as sources

    def run(command, **kwargs):
        Path(command[command.index("--output") + 1]).write_bytes(b"synthetic")
        return SimpleNamespace(
            returncode=code,
            stdout=str(status).encode(),
            stderr=b"synthetic error" if code else b"",
        )

    monkeypatch.setattr(sources.subprocess, "run", run)
    transport = sources._RetainedTransport(tmp_path, True, 10)
    transport._download("https://www.ndbc.noaa.gov/synthetic")
    metadata = json.loads(next((tmp_path / "responses").glob("*.json")).read_text())
    assert metadata["failure_layer"] == layer
    assert metadata["http_status"] == status
    assert not list((tmp_path / "transfers").iterdir())
    assert transport.blocked == bool(code or status in (401, 403, 429) or status >= 500)


@pytest.mark.parametrize("change", ["locator", "url"])
def test_retained_locator_and_url_mismatch(tmp_path, change):
    import httpx

    from worldenergydata.bsee.pipeline_screening_sources import (
        _response_path,
        _RetainedTransport,
        retain_response,
    )

    url = "https://www.ndbc.noaa.gov/synthetic"
    metadata = retain_response(tmp_path, url, b"x", 200, "2026-10-17T00:00:00Z")
    metadata["body" if change == "locator" else "url"] = "../outside"
    _response_path(tmp_path, url).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="digest"):
        _RetainedTransport(tmp_path, False, 10)(httpx.Request("GET", url))


def test_invalid_station_identifier_rejects(tmp_path):
    from worldenergydata.bsee.pipeline_screening_sources import fetch_ndbc_histories

    with pytest.raises(ValueError, match="station identifier"):
        fetch_ndbc_histories(["../bad"], [2022], tmp_path, allow_network=False)


def build_script():
    import runpy

    root = Path(__file__).parents[4]
    return runpy.run_path(str(root / "scripts/bsee/build_pipeline_screening.py"))


def test_sediment_parser_and_missing_table(tmp_path):
    parse = build_script()["_sediment"]
    assert parse(None) == []
    file = tmp_path / "data.zip"
    with zipfile.ZipFile(file, "w") as z:
        z.writestr(
            "GMX_EXT.TXT", "Latitude,Longitude,Sand,Mud,Gravel\n27,-90,10,80,10\n"
        )
    assert parse(file)[0]["Mud"] == "80"
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("other.txt", "")
    with pytest.raises(ValueError, match="sediment table"):
        parse(file)


def test_build_output_guard(monkeypatch):
    from types import SimpleNamespace

    script = build_script()
    main = script["main"]
    main.__globals__["_arguments"] = lambda: SimpleNamespace(
        output=script["ROOT"], cache=Path("/unused"), execution_record=Path("/unused")
    )
    with pytest.raises(ValueError, match="external"):
        main()


def test_status_dictionary_ignores_hidden_state(tmp_path):
    from worldenergydata.bsee.pipeline_screening_metadata import (
        status_table,
        status_table_digest,
    )

    html = '<input value="state"><table><tr class="dxgvDataRow"><td></td><td>ACT</td><td></td><td>ACTIVE</td></tr></table>'
    file = tmp_path / "status.html"
    file.write_text(html)
    before = status_table_digest(status_table(file))
    file.write_text(html.replace("state", "changed-state"))
    assert status_table_digest(status_table(file)) == before
    file.write_text(html.replace("ACTIVE", "CHANGED"))
    assert status_table_digest(status_table(file)) != before


def test_missing_ci_and_duplicate_hours_cannot_qualify(monkeypatch):
    from types import SimpleNamespace

    import worldenergydata.bsee.pipeline_screening_environment as env

    maximum = SimpleNamespace(
        observation_time=__import__("datetime").datetime(2000, 1, 1),
        wave_height_m=2,
        dominant_wave_period_s=7,
    )
    monkeypatch.setattr(
        env,
        "_counted_maxima",
        lambda records, atlantic: {year: maximum for year in range(10)},
    )
    monkeypatch.setattr(
        env,
        "_qualified_fit",
        lambda *args: SimpleNamespace(
            return_levels={10: 3}, lower_ci={}, upper_ci={}, distribution="GEV"
        ),
    )
    row = env._station_record_summary([])
    assert row["hs_10yr_m"] is None
    assert row["hs_10yr_m_source"] == "UNKNOWN:missing_confidence_interval"


def test_station_and_soil_radius_and_wave_requirement():
    from datetime import datetime
    from types import SimpleNamespace

    from worldenergydata.bsee.pipeline_screening import (
        build_rows,
        enrich_rows,
        station_environment,
    )

    stations = [
        SimpleNamespace(station_id="dry", latitude=0, longitude=0, metadata={}),
        SimpleNamespace(station_id="wave", latitude=0, longitude=0.1, metadata={}),
    ]
    record = SimpleNamespace(
        observation_time=datetime(2022, 1, 1), wave_height_m=1, dominant_wave_period_s=5
    )
    histories = {"dry": [SimpleNamespace(wave_height_m=None)], "wave": [record]}
    assert station_environment(0, 0, stations, histories)["station_id"] == "wave"
    assert station_environment(10, 0, stations, histories)["station_id"] is None
    defaults = {
        "permit_length_unit": {"value": "ft"},
        "empty_density": {"value": 0},
        "product_density": {"value": None},
        "status_meanings": {"value": {"ACT": "ACTIVE"}},
    }
    rows = build_rows(
        [{"SEGMENT_NUM": "x", "STATUS_CODE": "ACT", "SEG_LENGTH": 0}],
        [{"SEGMENT_NUM": "x", "POINT_NUM": 1, "LATITUDE": 0, "LONGITUDE": 0}],
        defaults,
    )
    assert rows[0]["permit_length_m"] is None
    row = enrich_rows(
        rows,
        defaults,
        sediment=[{"Latitude": 10, "Longitude": 0, "Sand": 80, "Mud": 20, "Gravel": 0}],
    )[0]
    assert row["soil_type"] is None
    assert row["seabed_current_m_s"] is None


def test_offline_replay_never_sleeps_for_network_rate_limits(tmp_path, monkeypatch):
    import worldenergydata.metocean.clients.base_client as base
    from worldenergydata.bsee.pipeline_screening_sources import (
        fetch_ndbc_histories,
        retain_response,
    )

    for year in (2022, 2023):
        url = f"https://www.ndbc.noaa.gov/view_text_file.php?filename=synthh{year}.txt.gz&dir=data/historical/stdmet/"
        retain_response(tmp_path, url, b"not found", 404, "2026-10-17T00:00:00Z")

    def sleep(seconds):
        pytest.fail("Offline replay must not wait for a network rate limit")

    monkeypatch.setattr(base.time, "sleep", sleep)
    assert fetch_ndbc_histories(
        ["synth"], [2022, 2023], tmp_path, allow_network=False
    ) == {"synth": []}


def test_missing_retained_body_fails_closed(tmp_path):
    from worldenergydata.bsee.pipeline_screening_sources import (
        fetch_ndbc_histories,
        retain_response,
    )

    url = "https://www.ndbc.noaa.gov/view_text_file.php?filename=synthh2022.txt.gz&dir=data/historical/stdmet/"
    metadata = retain_response(tmp_path, url, b"synthetic", 200, "2026-10-17T00:00:00Z")
    (tmp_path / metadata["body"]).unlink()
    with pytest.raises(ValueError, match="body unavailable"):
        fetch_ndbc_histories(["synth"], [2022], tmp_path, allow_network=False)
