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
        fields = screening_fixture[kind + "_headers"]
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
    from worldenergydata.bsee.pipeline_screening_metadata import publisher_metadata

    urls = {
        "permit.zip": "https://www.data.bsee.gov/Pipeline/Files/PipePermRawData.zip",
        "location.zip": "https://www.data.bsee.gov/Pipeline/Files/PipeLocRawData.zip",
        "stations.xml": "https://www.ndbc.noaa.gov/activestations.xml",
    }
    ledger = [
        publisher_metadata(
            {
                **entry,
                "source_id": (
                    "noaa-ndbc"
                    if entry["file"] == "stations.xml"
                    else "bsee-data-center"
                ),
                "url": urls[entry["file"]],
                "retrieved_at": "2026-10-15T00:00:00Z",
            }
        )
        for entry in ledger
    ]
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
    included = {"ACT", "OUT", "PABN", "PREM"}
    excluded = {
        "ABN",
        "RMV",
        "CNCL",
        "PROP",
        "COMB",
        "RELQ",
        "R/C",
        "REM",
        "A/C",
        "O/C",
        "R/A",
        "R/R",
    }
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
    assert {row["service_state"] for row in rows} == {
        "in_service",
        "out_of_service",
        "abandonment_proposed",
        "removal_proposed",
    }
    assert all(
        row["service_state_source"] == "PUBLIC:bsee-status-dictionary" for row in rows
    )


def test_missing_status_dictionary_rejects_selection(screening_fixture):
    from worldenergydata.bsee.pipeline_screening import build_rows

    screening_fixture["defaults"].pop("status_meanings", None)
    inputs = {
        key: screening_fixture[key] for key in ("permits", "locations", "defaults")
    }
    with pytest.raises(ValueError, match="status dictionary"):
        build_rows(**inputs)
