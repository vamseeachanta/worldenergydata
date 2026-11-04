"""Agreement checks use independently specified, synthetic input records."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def legacy_text_defaults(monkeypatch):
    original_open = Path.open
    original_read_text = Path.read_text

    def legacy_open(
        path, mode="r", buffering=-1, encoding=None, errors=None, newline=None
    ):
        if "b" not in mode:
            if encoding in (None, "locale"):
                encoding = "cp1252"
            if newline is None:
                newline = "\r\n"
        return original_open(
            path,
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(Path, "open", legacy_open)

    def legacy_read_text(path, encoding=None, errors=None):
        return original_read_text(path, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.setattr(Path, "read_text", legacy_read_text)


@pytest.mark.parametrize("report", ["executive", "detail"])
def test_report_text_uses_utf8_and_lf_with_legacy_defaults(
    tmp_path, monkeypatch, legacy_text_defaults, report
):
    import pandas as pd

    generator = module("generate_incident_report")
    monkeypatch.setattr(
        generator, "unverified_notice", lambda *_: "<p>Synthetic → note</p>"
    )
    monkeypatch.chdir(tmp_path)
    if report == "executive":
        analyses = {
            "hatch": {"detected": 0, "total": 0, "by_severity": {}},
            "foundering": {
                "total": 0,
                "total_fatalities": 0,
                "avg_fatalities": 0,
                "by_fatality_range": {},
            },
            "fatality": {"total": 0, "total_deaths": 0, "by_cause": {}},
        }
        generator.generate_executive_summary({}, analyses, tmp_path, False)
        output = tmp_path / "executive_summary.html"
    else:
        generator.generate_detailed_report(
            "foundering",
            pd.DataFrame({"description": ["Synthetic note"]}),
            {},
            [],
            tmp_path,
            False,
        )
        output = tmp_path / "foundering_analysis.html"
    content = output.read_bytes()
    assert "Synthetic → note" in content.decode("utf-8")
    assert b"\r\n" not in content


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
        path.write_text(text, encoding="utf-8", newline="\n")
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
        "units": "records",
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
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
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
    # Hand count: 2 + 3 = 5 records; B is empty and E is whitespace.
    # A, C, D remain (3); A and D founder (2) and have deaths > 0 (2).
    assert result["counts"] == manifest["counts"]
    assert len(result["all_incidents"]) == 3
    assert len(result["foundering"]) == 2
    assert len(result["fatality"]) == 2
    # The count unit is incident records: 1 + 2 = 3 deaths in 2 records.
    assert result["manifest"]["units"] == "records"
    assert result["fatality"]["fatalities"].sum() == 3


@pytest.mark.parametrize("source_index", [0, 1])
def test_each_required_input_is_mandatory(inputs, source_index):
    root, manifest_path, manifest = inputs
    missing = manifest["sources"][source_index]["path"]
    (root / missing).unlink()
    with pytest.raises(
        FileNotFoundError, match="Required incident input missing"
    ) as error:
        module("generate_incident_report").load_incident_data(root, manifest_path)
    assert missing in str(error.value)


def test_retained_input_count_agreement():
    """Verify real retained inputs when the external archive is available."""
    raw_dir = os.environ.get("MARINE_SAFETY_RAW_DIR")
    if not raw_dir:
        pytest.skip(
            "Retained inputs absent: set MARINE_SAFETY_RAW_DIR to the external archive"
        )
    fetcher = module("incident_inputs")
    manifest_path = Path(
        os.environ.get("MARINE_SAFETY_MANIFEST", fetcher.DEFAULT_MANIFEST)
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = Path(raw_dir).resolve()
    missing = [
        source["path"]
        for source in manifest["sources"]
        if not (root / source["path"]).is_file()
    ]
    if missing:
        pytest.skip(
            "Retained inputs absent from external archive: " + ", ".join(missing)
        )
    # Invalid digests, schemas, source counts and analysis counts must fail,
    # rather than being converted into a skip once the files are present.
    result = module("generate_incident_report").load_incident_data(root, manifest_path)
    counts = manifest["counts"]
    assert (
        sum(source["row_count"] for source in manifest["sources"])
        == counts["input_rows"]
    )
    assert len(result["all_incidents"]) == counts["analysed_rows"]
    assert len(result["hatch"]) == counts["analysed_rows"]
    assert len(result["foundering"]) == counts["foundering_rows"]
    assert len(result["fatality"]) == counts["fatal_incident_rows"]
    assert (
        counts["input_rows"] - counts["analysed_rows"]
        == counts["excluded_empty_description_rows"]
    )
    assert result["counts"] == counts


def test_retained_agreement_runs_against_configured_archive(inputs, monkeypatch):
    root, manifest_path, _ = inputs
    monkeypatch.setenv("MARINE_SAFETY_RAW_DIR", str(root))
    monkeypatch.setenv("MARINE_SAFETY_MANIFEST", str(manifest_path))
    test_retained_input_count_agreement()


def test_retained_agreement_does_not_skip_count_drift(inputs, monkeypatch):
    root, manifest_path, manifest = inputs
    manifest["counts"]["foundering_rows"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("MARINE_SAFETY_RAW_DIR", str(root))
    monkeypatch.setenv("MARINE_SAFETY_MANIFEST", str(manifest_path))
    with pytest.raises(ValueError, match="Count agreement failed"):
        test_retained_input_count_agreement()


def test_loader_reads_utf8_manifest_with_legacy_defaults(inputs, legacy_text_defaults):
    root, manifest_path, manifest = inputs
    manifest["note"] = "Synthetic → criterion"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    result = module("generate_incident_report").load_incident_data(root, manifest_path)
    assert result["manifest"]["note"] == manifest["note"]


def test_negative_control_changed_count(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, manifest = inputs
    changed = copy.deepcopy(manifest)
    changed["counts"]["analysed_rows"] = 4
    manifest_path.write_text(json.dumps(changed), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Count agreement failed"):
        module("generate_incident_report").load_incident_data(root, manifest_path)


def test_changed_digest_rejected(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, _ = inputs
    with (root / "canadian_tsb/occurrence.csv").open(
        "a", encoding="utf-8", newline="\n"
    ) as stream:
        stream.write("F,2020-01-06,another row,Sinking,0\n")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        module("generate_incident_report").load_incident_data(root, manifest_path)


def test_required_columns_rejected(inputs, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    root, manifest_path, manifest = inputs
    path = root / manifest["sources"][0]["path"]
    path.write_text("wrong\nvalue\n", encoding="utf-8", newline="\n")
    manifest["sources"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
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
    assert (
        json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == manifest
    )


def test_manifest_has_explicit_publication_limitations():
    manifest = json.loads(
        (ROOT / "config/marine_safety_input_manifest.json").read_text(encoding="utf-8")
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
    _root, _, manifest = inputs
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

    from requests import Response
    from urllib3.response import HTTPResponse

    root, _, fixture_manifest = inputs
    fetcher = module("incident_inputs")
    payloads = iter(
        (root / source["path"]).read_bytes() for source in fixture_manifest["sources"]
    )

    def download(*args, **kwargs):
        response = Response()
        response.status_code = 200
        response.raw = HTTPResponse(
            body=io.BytesIO(next(payloads)), preload_content=False
        )
        return response

    monkeypatch.setattr(fetcher, "get", download)
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


def test_fetch_keeps_temporary_payloads_in_external_root(tmp_path, monkeypatch):
    from requests import RequestException

    fetcher = module("incident_inputs")
    root = tmp_path / "archive"
    locations = []

    def unavailable(source, temporary):
        locations.append(temporary.resolve())
        raise RequestException("Synthetic offline response")

    monkeypatch.setattr(fetcher, "download_input", unavailable)
    fetcher.fetch_inputs(root, tmp_path / "manifest.json")
    assert len(locations) == 2
    assert all(path.is_relative_to(root) for path in locations)
    assert not list(root.glob("marine-input-*"))


@pytest.mark.parametrize("child", ["", "raw"])
def test_fetch_rejects_repository_data_root_before_network(
    tmp_path, monkeypatch, child
):
    fetcher = module("incident_inputs")
    monkeypatch.setattr(fetcher, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        fetcher, "download_input", lambda *_: pytest.fail("Network reached")
    )
    with pytest.raises(ValueError, match="outside the repository"):
        fetcher.fetch_inputs(tmp_path / child, tmp_path / "manifest.json")
    assert not (tmp_path / "manifest.json").exists()


def test_fetch_manifest_uses_utf8_and_lf(inputs, monkeypatch, legacy_text_defaults):
    from requests import RequestException

    root, manifest_path, manifest = inputs
    manifest["revisions"] = [{"changes": "Synthetic → criterion"}]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    fetcher = module("incident_inputs")

    def unavailable(*_):
        raise RequestException("Synthetic offline response")

    monkeypatch.setattr(fetcher, "download_input", unavailable)
    result = fetcher.fetch_inputs(root, manifest_path)
    assert result["revisions"] == manifest["revisions"]
    assert json.loads(manifest_path.read_bytes().decode("utf-8")) == result
    assert b"\r\n" not in manifest_path.read_bytes()


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
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Count agreement failed"):
        module("incident_inputs").load_inputs(root, manifest_path)


def test_published_summary_agrees_with_manifest():
    from bs4 import BeautifulSoup

    manifest = json.loads(
        (ROOT / "config/marine_safety_input_manifest.json").read_text(encoding="utf-8")
    )
    soup = BeautifulSoup(
        (ROOT / "reports/marine_safety/executive_summary.html").read_text(
            encoding="utf-8"
        ),
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
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Count agreement failed.*row_count"):
        module("incident_inputs").load_inputs(root, manifest_path)


def test_archive_escape_rejected(inputs):
    root, manifest_path, manifest = inputs
    manifest["sources"][0]["path"] = "../outside.csv"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="inside the raw input directory"):
        module("incident_inputs").load_inputs(root, manifest_path)


def test_source_identity_rights_and_count_discrepancy():
    fetcher = module("incident_inputs")
    manifest = json.loads(fetcher.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
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
        (root / source["path"]).write_text("tampered\n", encoding="utf-8", newline="\n")
    elif damage == "count":
        source["row_count"] += 1
    elif damage == "escape":
        source["path"] = "../outside.csv"
    elif damage == "missing":
        source["path"] = "missing.csv"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")

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
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == result


@pytest.mark.parametrize("read_error", [TimeoutError, OSError])
@pytest.mark.parametrize("reuse_archive", [False, True])
def test_body_read_failure_records_attempts_and_reuses_verified_archives(
    inputs, monkeypatch, read_error, reuse_archive
):
    import io

    from requests import Response
    from urllib3.response import HTTPResponse

    root, manifest_path, manifest = inputs
    fetcher = module("incident_inputs")
    for source, definition in zip(manifest["sources"], fetcher.SOURCES):
        source["url"] = definition["url"]
    if reuse_archive:
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    else:
        manifest_path = root / "new-manifest.json"
    calls = []
    responses = []

    class InterruptedBody(io.BytesIO):
        def read(self, *args, **kwargs):
            if self.tell():
                raise read_error("Response body interrupted")
            return super().read(*args, **kwargs)

    def interrupted_download(url, **kwargs):
        calls.append(url)
        response = Response()
        response.status_code = 200
        response.raw = HTTPResponse(
            body=InterruptedBody(b"partial response\n"), preload_content=False
        )
        responses.append(response)
        return response

    monkeypatch.setattr(fetcher, "get", interrupted_download)
    result = fetcher.fetch_inputs(root, manifest_path)

    assert calls == [definition["url"] for definition in fetcher.SOURCES]
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == result
    assert all(response.raw.closed for response in responses)
    assert not (root / "sha256").exists()
    for source, previous in zip(result["sources"], manifest["sources"]):
        assert source["error"] == "Network request failed or timed out"
        assert source["response_layer"] == "network"
        assert source["attempted_at_utc"]
        assert source["attempts"] == [
            {
                "user_agent": "requests default",
                "http_status": 200,
                "response_layer": "network",
            }
        ]
        assert fetcher.sha256(root / previous["path"]) == previous["sha256"]
        for key in ("status", "path", "sha256", "row_count", "download_date_utc"):
            if reuse_archive:
                assert source[key] == previous[key]
            elif key != "path":
                assert source[key] == "NOT_EVALUATED"
    if reuse_archive:
        assert result["counts"] == manifest["counts"]
        assert fetcher.load_inputs(root, manifest_path)["counts"] == manifest["counts"]
    else:
        assert result["counts"] == "NOT_EVALUATED"
        assert result["readiness"] == "unavailable"


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
    from urllib3.response import HTTPResponse

    root, _, manifest = inputs
    fetcher = module("incident_inputs")
    calls = []

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
        response = Response()
        response.status_code = 200
        response.raw = HTTPResponse(
            body=io.BytesIO((root / source["path"]).read_bytes()), preload_content=False
        )
        return response

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
