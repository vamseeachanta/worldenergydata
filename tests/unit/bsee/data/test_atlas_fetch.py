"""Offline fetch policy probes; transport payloads are explicitly synthetic."""

import hashlib
import io
import json
import zipfile
from argparse import Namespace
from pathlib import Path
from urllib.error import HTTPError

import pytest

from scripts.bsee import fetch_sands_atlas
from scripts.bsee.fetch_sands_atlas import verify_retained_files
from worldenergydata.bsee import atlas_fetch
from worldenergydata.field_development.data_availability import DatasetUnavailableError

from .test_atlas import FIXTURES, SCHEMA


@pytest.fixture
def independent_roster(tmp_path, monkeypatch):
    roster = tmp_path / "synthetic_roster.json"
    roster.write_text(
        json.dumps(
            [{"name": "Synthetic field", "region": "US Gulf of Mexico", "block": "MC1"}]
        ),
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(fetch_sands_atlas, "ROSTER_PATH", roster)
    return roster


def test_fetch_preserves_existing_disclaimer(tmp_path):
    path = tmp_path / "disclaimer.html"
    path.write_text("retained evidence", encoding="utf-8", newline="\n")
    with pytest.raises(FileExistsError):
        atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert path.read_text(encoding="utf-8") == "retained evidence"


def test_refusal_stops_after_one_request(tmp_path, monkeypatch):
    calls = []

    def refuse(url):
        calls.append(url)
        raise HTTPError(url, 403, "refused", {}, None)

    monkeypatch.setattr(atlas_fetch, "_request_bytes", refuse)
    with pytest.raises(HTTPError):
        atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert calls == [atlas_fetch.SOURCE_PAGE]
    assert (
        json.loads((tmp_path / "refusal.json").read_text(encoding="utf-8"))[
            "http_status"
        ]
        == 403
    )
    assert (
        json.loads((tmp_path / "handmade-fixture.json").read_text(encoding="utf-8"))[
            "synthetic"
        ]
        is True
    )


def test_sequential_fetch_manifest_and_real_fixture_export(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("synthetic.accdb", b"synthetic transport fixture")
    link = "https://www.data.bsee.gov/GGStudies/Files/2023%20Atlas%20Update.zip"
    calls = []

    def retrieve(url):
        calls.append(url)
        payload = {
            atlas_fetch.SOURCE_PAGE: f'<a href="{link}">Download</a>'.encode(),
            atlas_fetch.TERMS_URL: b"synthetic disclaimer transport fixture",
            link: archive.getvalue(),
        }[url]
        return payload

    def export(command, stdout, check):
        assert check
        stdout.write((FIXTURES / f"{command[-1]}.csv").read_text(encoding="utf-8"))

    monkeypatch.setattr(atlas_fetch, "_request_bytes", retrieve)
    monkeypatch.setattr(atlas_fetch.subprocess, "run", export)
    manifest = atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert calls == [atlas_fetch.SOURCE_PAGE, atlas_fetch.TERMS_URL, link]
    assert manifest["row_counts"]["2023sands"] == 5
    assert (tmp_path / "2023xref_oper-comp.csv").read_bytes() == (
        FIXTURES / "2023xref_oper-comp.csv"
    ).read_bytes()
    for record in manifest["files"]:
        assert record["sha256"] and record["size_bytes"] > 0
        assert record["retrieved_at_utc"] and record["terms"]
    committed = json.loads(
        (SCHEMA.parent / "manifest.json").read_text(encoding="utf-8")
    )
    assert (SCHEMA.parent / "manifest.json").read_bytes() == (
        json.dumps(committed, indent=2) + "\n"
    ).encode()
    assert set(manifest) == set(committed)
    assert {record["file"] for record in manifest["files"]} == {
        record["file"] for record in committed["files"]
    }
    assert all(
        set(record) == set(committed["files"][0])
        for record in manifest["files"] + committed["files"]
    )
    assert set(manifest["row_counts"]) == set(committed["row_counts"])
    assert (
        json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == manifest
    )


def test_incomplete_manifest_cannot_validate_consumed_tables(tmp_path):
    with pytest.raises(ValueError, match="manifest"):
        verify_retained_files(tmp_path, {"files": []})


@pytest.mark.parametrize(
    "code,status",
    [
        (401, "refused"),
        (403, "refused"),
        (429, "refused"),
        (404, "client_error"),
        (503, "server_error"),
    ],
)
def test_download_failure_status(tmp_path, monkeypatch, code, status):
    def fail(url):
        raise HTTPError(url, code, "synthetic failure", {}, None)

    monkeypatch.setattr(atlas_fetch, "_request_bytes", fail)
    monkeypatch.setattr(atlas_fetch.time, "sleep", lambda _: None)
    with pytest.raises(HTTPError):
        atlas_fetch.fetch_atlas(tmp_path, SCHEMA)
    assert (
        json.loads((tmp_path / "refusal.json").read_text(encoding="utf-8"))["status"]
        == status
    )


def test_access_member_size_checked_before_read(tmp_path, monkeypatch):
    with zipfile.ZipFile(tmp_path / "atlas-2023.zip", "w") as stream:
        stream.writestr("synthetic.accdb", b"too large")
    monkeypatch.setattr(atlas_fetch, "MAX_ACCESS_DATABASE_BYTES", 2, raising=False)

    def forbidden_read(*args):
        pytest.fail("oversized member must not be read")

    monkeypatch.setattr(zipfile.ZipFile, "read", forbidden_read)
    with pytest.raises(ValueError, match="size ceiling"):
        atlas_fetch._export_tables(tmp_path, atlas_fetch.SOURCE_PAGE, "mdb-export")
    assert not (tmp_path / "atlas-2023.accdb").exists()


def retained_manifest(directory):
    records = []
    for table in atlas_fetch.EXPORT_TABLES:
        path = directory / f"{table}.csv"
        path.write_bytes((FIXTURES / path.name).read_bytes())
        records.append(atlas_fetch.file_record(path, atlas_fetch.SOURCE_PAGE))
    return {"files": records, "row_counts": {"2023sands": 5}}


@pytest.mark.parametrize("defect", ["digest", "size", "duplicate", "unsafe", "dotdot"])
def test_retained_integrity_rejects_invalid_records(tmp_path, defect):
    manifest = retained_manifest(tmp_path)
    if defect == "digest":
        manifest["files"][0]["sha256"] = "0" * 64
    elif defect == "size":
        manifest["files"][0]["size_bytes"] += 1
    elif defect == "duplicate":
        manifest["files"].append(manifest["files"][0].copy())
    elif defect == "unsafe":
        manifest["files"][0]["file"] = "../2023sands.csv"
    else:
        manifest["files"][0]["file"] = ".."
    with pytest.raises(ValueError):
        verify_retained_files(tmp_path, manifest)


@pytest.mark.parametrize("key", ["sha256", "size_bytes", "source_url"])
def test_manifest_comparison_ignores_timestamps_and_reports_stable_changes(
    tmp_path, key
):
    manifest = retained_manifest(tmp_path)
    changed = json.loads(json.dumps(manifest))
    changed["files"][0]["retrieved_at_utc"] = "different timestamp"
    assert fetch_sands_atlas.manifest_differences(manifest, changed) == []
    changed["files"][0][key] = "different value"
    assert any(
        key in difference
        for difference in fetch_sands_atlas.manifest_differences(manifest, changed)
    )


@pytest.mark.parametrize("defect", ["missing_file", "added_file", "row_count"])
def test_manifest_comparison_reports_set_and_count_changes(tmp_path, defect):
    manifest = retained_manifest(tmp_path)
    changed = json.loads(json.dumps(manifest))
    if defect == "missing_file":
        changed["files"].pop()
    elif defect == "added_file":
        changed["files"].append({"file": "extra.html"})
    else:
        changed["row_counts"]["2023sands"] += 1
    assert fetch_sands_atlas.manifest_differences(manifest, changed)


@pytest.mark.parametrize("update", [False, True])
def test_script_manifest_write_is_explicit_and_attribution_deterministic(
    tmp_path, monkeypatch, update, independent_roster
):
    directory = tmp_path / "retained"
    directory.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    manifest = retained_manifest(directory)
    (directory / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )
    committed_path = output / "manifest.json"
    original = json.dumps(manifest, separators=(",", ":")).encode()
    committed_path.write_bytes(original)
    args = Namespace(
        data_dir=str(directory),
        output=output,
        reuse=True,
        update_manifest=update,
        mdb_export="mdb-export",
    )
    monkeypatch.setattr(fetch_sands_atlas, "parse_args", lambda _: args)
    fetch_sands_atlas.main()
    expected = (json.dumps(manifest, indent=2) + "\n").encode() if update else original
    assert committed_path.read_bytes() == expected
    attribution = (output / "field_attribution.json").read_bytes()
    result = json.loads(attribution)
    assert len(result["fields"]) == 1
    assert result["fields"][0]["name"] == "Synthetic field"
    assert (
        result["input_sha256"][independent_roster.name]
        == hashlib.sha256(independent_roster.read_bytes()).hexdigest()
    )
    assert all(not Path(key).is_absolute() for key in result["input_sha256"])
    fetch_sands_atlas.main()
    assert (output / "field_attribution.json").read_bytes() == attribution


@pytest.mark.parametrize("stale", [False, True])
def test_script_rejects_withheld_roster_before_source_reads_or_writes(
    tmp_path, monkeypatch, stale
):
    from worldenergydata.field_development import data_availability

    if stale:
        roster = tmp_path / "reports/field-atlas/_roster.json"
        roster.parent.mkdir(parents=True)
        roster.write_text("[]", encoding="utf-8", newline="\n")
        monkeypatch.setattr(data_availability, "ROOT", tmp_path)
        monkeypatch.setattr(fetch_sands_atlas, "ROSTER_PATH", roster)
    output = tmp_path / "output"
    args = Namespace(
        data_dir=str(tmp_path / "unread"),
        output=output,
        reuse=True,
        update_manifest=True,
        mdb_export="mdb-export",
    )
    monkeypatch.setattr(fetch_sands_atlas, "parse_args", lambda _: args)
    with pytest.raises(DatasetUnavailableError, match="redistribution-terms review"):
        fetch_sands_atlas.main()
    assert not output.exists()


def test_script_digest_difference_exits_without_rewriting_manifest(
    tmp_path, monkeypatch, capsys, independent_roster
):
    directory = tmp_path / "retained"
    directory.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    manifest = retained_manifest(directory)
    (directory / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )
    changed = json.loads(json.dumps(manifest))
    changed["files"][0]["sha256"] = "0" * 64
    committed_path = output / "manifest.json"
    committed_path.write_text(json.dumps(changed), encoding="utf-8", newline="\n")
    original = committed_path.read_bytes()
    args = Namespace(
        data_dir=str(directory),
        output=output,
        reuse=True,
        update_manifest=False,
        mdb_export="mdb-export",
    )
    monkeypatch.setattr(fetch_sands_atlas, "parse_args", lambda _: args)
    with pytest.raises(SystemExit) as error:
        fetch_sands_atlas.main()
    assert error.value.code != 0
    assert "sha256" in capsys.readouterr().out
    assert committed_path.read_bytes() == original


def test_transport_pins_host_headers_closes_and_rejects_redirect(monkeypatch):
    calls = []
    closed = []
    status = [200]

    class Connection:
        def __init__(self, host, timeout):
            assert host == "www.data.bsee.gov"
            assert timeout == 120

        def request(self, method, target, headers):
            calls.append((method, target, headers))

        def getresponse(self):
            class Response:
                reason = "synthetic transport response"
                headers = {}

                def read(self):
                    return b"synthetic transport payload"

            response = Response()
            response.status = status[0]
            return response

        def close(self):
            closed.append(True)

    monkeypatch.setattr(atlas_fetch, "HTTPSConnection", Connection)
    assert (
        atlas_fetch._request_bytes(atlas_fetch.SOURCE_PAGE)
        == b"synthetic transport payload"
    )
    assert calls[0] == (
        "GET",
        "/Main/GandG.aspx",
        {"User-Agent": atlas_fetch.USER_AGENT},
    )
    status[0] = 302
    with pytest.raises(HTTPError):
        atlas_fetch._request_bytes(atlas_fetch.SOURCE_PAGE)
    assert len(calls) == len(closed) == 2
