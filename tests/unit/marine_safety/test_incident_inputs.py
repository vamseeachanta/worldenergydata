"""Agreement checks use independently specified, synthetic input records."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/marine_safety" / f"{name}.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def inputs(tmp_path):
    contents = {
        "canadian_tsb/occurrence.csv": (
            "OccID,OccDate,Summary,AccIncTypeDisplayEng,TotalDeaths\n"
            "A,2020-01-01,hatch failure,Sinking,1\n"
            "B,2020-01-02,,Collision,0\n"
        ),
        "dlp_historical/Accidents_1995-2012.csv": (
            "BARDID,Date,Redactednarrative,AccidentEvent1,Numberdeaths\n"
            "C,2020-01-03,engine failure,Collision,0\n"
            "D,2020-01-04,capsized,Capsizing,2\n"
            "E,2020-01-05,   ,Collision,0\n"
        ),
    }
    sources = []
    for name, text in contents.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        sources.append(
            {
                "id": name.split("/")[0],
                "path": name,
                "url": "https://example.org/input.csv",
                "status": "FETCHED",
                "download_date_utc": "2026-01-01T00:00:00Z",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "row_count": 2 if name.startswith("canadian") else 3,
            }
        )
    manifest = {
        "schema_version": 1,
        "sources": sources,
        "counts": {
            "input_rows": 5,
            "excluded_empty_description_rows": 2,
            "analysed_rows": 3,
            "foundering_rows": 2,
            "fatal_incident_rows": 2,
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return tmp_path, manifest_path, manifest


def test_missing_input_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    generator = module("generate_incident_report")
    with pytest.raises(FileNotFoundError, match="Required incident input"):
        generator.load_incident_data(tmp_path)


def test_fixture_agrees_with_manifest(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, manifest = inputs
    generator = module("generate_incident_report")
    result = generator.load_incident_data(root, manifest_path)
    assert result["counts"] == manifest["counts"]
    assert len(result["all_incidents"]) == 3
    assert len(result["foundering"]) == 2
    assert len(result["fatality"]) == 2


def test_negative_control_changed_count(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, manifest = inputs
    changed = copy.deepcopy(manifest)
    changed["counts"]["analysed_rows"] = 4
    manifest_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="Count agreement failed"):
        module("generate_incident_report").load_incident_data(root, manifest_path)


def test_changed_digest_rejected(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, _ = inputs
    with (root / "canadian_tsb/occurrence.csv").open("a") as stream:
        stream.write("F,2020-01-06,another row,Sinking,0\n")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        module("generate_incident_report").load_incident_data(root, manifest_path)


def test_required_columns_rejected(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, manifest = inputs
    path = root / manifest["sources"][0]["path"]
    path.write_text("wrong\nvalue\n")
    manifest["sources"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Required columns"):
        module("generate_incident_report").load_incident_data(root, manifest_path)


def test_blocked_fetch_records_unknowns(tmp_path, monkeypatch):
    from requests import HTTPError, Response

    fetcher = module("incident_inputs")

    def blocked(*args, **kwargs):
        response = Response()
        response.status_code = 403
        response.reason = "Forbidden"
        raise HTTPError(response=response)

    monkeypatch.setattr(fetcher, "get", blocked)
    manifest = fetcher.fetch_inputs(tmp_path / "raw", tmp_path / "manifest.json")
    assert manifest["counts"] == "NOT_EVALUATED"
    for source in manifest["sources"]:
        assert source["status"] == "NOT_EVALUATED"
        assert source["sha256"] == "NOT_EVALUATED"
        assert source["row_count"] == "NOT_EVALUATED"
        assert source["download_date_utc"] == "NOT_EVALUATED"
        assert source["error"] == "HTTP 403: Forbidden"
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest


def test_manifest_has_explicit_publication_limitations():
    manifest = json.loads(
        (ROOT / "config/marine_safety_input_manifest.json").read_text()
    )
    assert manifest["excluded_sources"][0]["id"] == "imo_gisis"
    assert "account" in manifest["excluded_sources"][0]["reason"]
    assert len(manifest["sources"]) == 2
    for source in manifest["sources"]:
        assert source["url"].startswith("https://")
        if source["status"] == "NOT_EVALUATED":
            assert source["row_count"] == "NOT_EVALUATED"
            assert manifest["counts"] == "NOT_EVALUATED"


def test_provenance_report_marks_unavailable_counts(inputs):
    root, _, manifest = inputs
    fetcher = module("incident_inputs")
    manifest["counts"] = "NOT_EVALUATED"
    html = fetcher.provenance_html(manifest)
    assert "NOT_EVALUATED" in html
    assert "2026-01-01T00:00:00Z" in html
    assert "https://example.org/input.csv" in html
    assert "Revision history" in html
    assert "account" in html


def test_successful_fetch_counts_and_readback(inputs, tmp_path, monkeypatch):
    import io

    root, _, fixture_manifest = inputs
    fetcher = module("incident_inputs")
    payloads = iter(
        (root / source["path"]).read_bytes() for source in fixture_manifest["sources"]
    )

    class Response(io.BytesIO):
        status_code = 200

        def raise_for_status(self):
            pass

        @property
        def raw(self):
            return self

    monkeypatch.setattr(fetcher, "get", lambda *a, **kw: Response(next(payloads)))
    external = tmp_path / "archive"
    output = tmp_path / "fetched.json"
    manifest = fetcher.fetch_inputs(external, output)
    assert manifest["counts"] == fixture_manifest["counts"]
    assert fetcher.load_inputs(external, output)["counts"] == fixture_manifest["counts"]
    for source in manifest["sources"]:
        assert source["path"].startswith("sha256/")
        assert (
            source["sha256"]
            == hashlib.sha256((external / source["path"]).read_bytes()).hexdigest()
        )


def test_cli_missing_input_nonzero(tmp_path):
    import os
    import subprocess
    import sys

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/marine_safety/generate_incident_report.py"),
            "--input-dir",
            str(tmp_path / "missing"),
            "--output-dir",
            str(tmp_path / "reports"),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Required incident input missing" in result.stderr
    assert not (tmp_path / "reports").exists()


@pytest.mark.parametrize(
    "field",
    [
        "input_rows",
        "excluded_empty_description_rows",
        "analysed_rows",
        "foundering_rows",
        "fatal_incident_rows",
    ],
)
def test_each_changed_analysis_count_is_rejected(inputs, field):
    root, manifest_path, manifest = inputs
    manifest["counts"][field] += 1
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Count agreement failed"):
        module("incident_inputs").load_inputs(root, manifest_path)


def test_published_summary_agrees_with_manifest():
    from bs4 import BeautifulSoup

    manifest = json.loads(
        (ROOT / "config/marine_safety_input_manifest.json").read_text()
    )
    soup = BeautifulSoup(
        (ROOT / "reports/marine_safety/executive_summary.html").read_text(),
        "html.parser",
    )
    section = soup.find(id="input-provenance")
    assert section is not None
    tables = section.find_all("table")
    records = tables[1].find_all("tr")[1:]
    assert len(records) == len(manifest["sources"])
    for row, source in zip(records, manifest["sources"]):
        assert [cell.get_text() for cell in row.find_all("td")] == [
            str(source[key])
            for key in (
                "id",
                "url",
                "download_date_utc",
                "sha256",
                "row_count",
                "status",
            )
        ]
    if manifest["counts"] == "NOT_EVALUATED":
        assert "NOT_EVALUATED" in section.find("p").get_text()


def test_source_row_count_drift_rejected(inputs):
    root, manifest_path, manifest = inputs
    manifest["sources"][0]["row_count"] += 1
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Count agreement failed.*row_count"):
        module("incident_inputs").load_inputs(root, manifest_path)


def test_archive_escape_rejected(inputs):
    root, manifest_path, manifest = inputs
    manifest["sources"][0]["path"] = "../outside.csv"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="inside the raw input directory"):
        module("incident_inputs").load_inputs(root, manifest_path)


def test_source_identity_rights_and_count_discrepancy():
    fetcher = module("incident_inputs")
    manifest = json.loads(fetcher.DEFAULT_MANIFEST.read_text())
    for source in (*fetcher.SOURCES, *manifest["sources"]):
        assert source["license"]
        assert source["license_url"].startswith("https://")
        assert source["license_evidence_url"].startswith("https://")
        if source["id"] == "dlp_historical":
            assert source["upstream_name"] == "Accidents.csv"
            note = source["count_reconciliation"]
            assert note["previously_reported_rows"] == 93237
            assert note["issue"] == 1529
            assert note["cause"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("damage", [None, "bytes", "count", "escape", "missing"])
def test_transient_failure_reuses_only_verified_archive(inputs, monkeypatch, damage):
    from requests import RequestException

    root, manifest_path, manifest = inputs
    fetcher = module("incident_inputs")
    manifest["revisions"] = [
        {"revision": "7", "date": "2026-01-01", "changes": "Earlier issue."}
    ]
    for item, definition in zip(manifest["sources"], fetcher.SOURCES):
        item["url"] = definition["url"]
    source = manifest["sources"][0]
    if damage == "bytes":
        (root / source["path"]).write_text("tampered\n")
    elif damage == "count":
        source["row_count"] += 1
    elif damage == "escape":
        source["path"] = "../outside.csv"
    elif damage == "missing":
        source["path"] = "missing.csv"
    manifest_path.write_text(json.dumps(manifest))

    def failed(*args, **kwargs):
        raise RequestException("temporary outage")

    monkeypatch.setattr(fetcher, "get", failed)
    result = fetcher.fetch_inputs(root, manifest_path)
    assert result["revisions"] == manifest["revisions"]
    retained = result["sources"][0]
    assert retained["response_layer"] == "network"
    if damage is None:
        for key in ("status", "path", "sha256", "row_count", "download_date_utc"):
            assert retained[key] == source[key]
        assert result["counts"] == manifest["counts"]
        assert fetcher.load_inputs(root, manifest_path)["counts"] == manifest["counts"]
    else:
        assert retained["status"] == "NOT_EVALUATED"
        assert result["counts"] == "NOT_EVALUATED"
    assert result["sources"][1]["status"] == "FETCHED"
    assert json.loads(manifest_path.read_text()) == result


def test_revision_history_is_manifest_driven_and_escaped(inputs):
    _, _, manifest = inputs
    manifest["revisions"] = [
        {"revision": "9", "date": "2030-01-02", "changes": "Change <criteria>."},
        {"revision": "10", "date": "2030-02-03", "changes": "Next issue."},
    ]
    html = module("incident_inputs").provenance_html(manifest)
    assert "<td>9</td><td>2030-01-02</td>" in html
    assert "<td>10</td><td>2030-02-03</td>" in html
    assert "Change &lt;criteria&gt;." in html
    assert "2026-10-19" not in html


@pytest.mark.parametrize("retry_succeeds", [False, True])
def test_forbidden_retried_once_with_explicit_agent(
    inputs, monkeypatch, retry_succeeds
):
    import io

    from requests import HTTPError, Response

    root, _, manifest = inputs
    fetcher = module("incident_inputs")
    calls = []

    class Download(io.BytesIO):
        status_code = 200

        def raise_for_status(self):
            pass

        @property
        def raw(self):
            return self

    def download(url, **kwargs):
        calls.append((url, kwargs))
        definition = next(source for source in fetcher.SOURCES if source["url"] == url)
        attempts = sum(previous == url for previous, _ in calls)
        if definition["id"] == "canadian_tsb" and (attempts == 1 or not retry_succeeds):
            response = Response()
            response.status_code = 403
            response.reason = "Forbidden"
            raise HTTPError(response=response)
        source = next(
            item for item in manifest["sources"] if item["id"] == definition["id"]
        )
        return Download((root / source["path"]).read_bytes())

    monkeypatch.setattr(fetcher, "get", download)
    result = fetcher.fetch_inputs(root / "new", root / "new.json")
    tsb_calls = [kw for url, kw in calls if url == fetcher.SOURCES[0]["url"]]
    assert len(tsb_calls) == 2
    assert tsb_calls[1]["headers"]["User-Agent"]
    tsb = result["sources"][0]
    assert tsb["attempts"][0]["response_layer"] == "http-access"
    assert tsb["attempts"][0]["http_status"] == 403
    assert tsb["response_layer"] == ("http" if retry_succeeds else "http-access")
    assert tsb["status"] == ("FETCHED" if retry_succeeds else "NOT_EVALUATED")
    if retry_succeeds:
        assert result["counts"] == manifest["counts"]
