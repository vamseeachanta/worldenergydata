"""Offline command and contract checks with synthetic retained inputs."""

import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def screening_fixture():
    return json.loads(
        (
            Path(__file__).parents[3] / "fixtures/bsee/pipeline_screening.json"
        ).read_text()
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
    writer = csv.DictWriter(
        output, fieldnames=screening_fixture["permit_headers"], lineterminator="\n"
    )
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
