"""Offline refresh tests. All incident rows in the fixture are synthetic."""

import csv
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = (
    ROOT / "packages/worldenergydata-bsee/src/worldenergydata/hse/public_refresh.py"
)
spec = importlib.util.spec_from_file_location("hse_public_refresh", MODULE)
refresh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = refresh
spec.loader.exec_module(refresh)
FIXTURE = Path(__file__).parent / "fixtures/incinv_synthetic.csv"
URL = "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip"


@pytest.fixture
def case(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    raw = data / "incidents.csv"
    raw.write_bytes(FIXTURE.read_bytes())
    manifest = {
        "source_kind": "synthetic",
        "files": [
            {
                "file": raw.name,
                "url": URL,
                "downloaded_at": "2026-10-01T00:00:00Z",
                "size_bytes": raw.stat().st_size,
                "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            }
        ],
    }
    cfg = {
        "taxonomy_dir": str(
            ROOT
            / "packages/worldenergydata-safety_analysis/src"
            / "worldenergydata/safety_analysis/taxonomy"
        ),
        "data_dir": str(data),
        "output_dir": str(tmp_path / "outputs"),
        "source_file": raw.name,
        "source_kind": "synthetic",
        "encoding": "utf-8",
        "quantity": "investigation records",
        "unit": "count",
        "earliest_date": "1900-01-01",
        "latest_date": "2026-10-01",
    }
    (data / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return cfg, raw, manifest


def reseal(cfg, raw, manifest):
    entry = manifest["files"][0]
    entry["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    entry["size_bytes"] = raw.stat().st_size
    (Path(cfg["data_dir"]) / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def edit_rows(cfg, raw, manifest, edit):
    with raw.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    edit(rows)
    with raw.open("w", encoding="utf-8", newline="\n") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    reseal(cfg, raw, manifest)


def test_synthetic_headlines_and_chart_exports(case):
    cfg, _, _ = case
    before = {k: v for k, v in sys.modules.items() if k.startswith("worldenergydata")}
    result = refresh.analyze(cfg)
    assert result["incinv_total_records"] == 4
    assert result["drill_total"] == 2
    assert result["drill_pct_of_incinv"] == 50.0
    assert result["drill_by_year"] == {"2020": 1, "2021": 0, "2022": 1}
    assert result["drill_year_range"] == [2020, 2022]
    assert result["drill_confidence_buckets"] == {
        "direct_code(>=0.90)": 1,
        "keyword_low(<0.50)": 1,
    }
    assert result["drill_subactivity_distribution"] == {"well_control": 1, "logging": 1}
    assert result["drill_top_areas"] == {"AA": 1, "CC": 1}
    assert result["drill_distinct_leases"] == 1
    assert result["drill_severity_proxy"] == {"major": 1, "other": 1}
    assert result["source"]["source_kind"] == "synthetic"
    assert result["source"]["files"][0]["downloaded_at"] == "2026-10-01T00:00:00Z"
    out = Path(cfg["output_dir"])
    qa = json.loads((out / "incinv-qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "pass"
    assert qa["date_range"] == ["2020-01-02", "2022-04-05"]
    assert qa["missing_optional_leases"] == 1
    inventory = json.loads((out / refresh.INVENTORY).read_text(encoding="utf-8"))
    assert inventory["total_rows"] == 4
    assert inventory["intervention_keyword_hits"]["workover"] == 1
    assert inventory["intervention_keyword_hits"]["wireline"] == 1
    assert inventory["war_join"]["status"] == "not_evaluated"
    for name in refresh.CHARTS:
        with (out / f"{name}.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        assert rows[0] == ["category", "investigation records [count]"]
        assert (
            dict((row[0], int(row[1])) for row in rows[1:])
            == result[refresh.CHARTS[name]]
        )
        assert sum(int(row[1]) for row in rows[1:]) == result["drill_total"]
    assert {
        k: v for k, v in sys.modules.items() if k.startswith("worldenergydata")
    } == before


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("empty", "row_count"),
        ("duplicate", "duplicate_keys"),
        ("missing_key", "missing_keys"),
        ("bad_date", "date_range"),
        ("future_date", "date_range"),
        ("unit", "unit"),
        ("digest", "integrity"),
        ("size", "integrity"),
        ("missing_manifest", "provenance"),
        ("missing_timestamp", "provenance"),
        ("bad_url", "provenance"),
        ("missing_column", "schema"),
        ("duplicate_column", "schema"),
        ("encoding", "schema"),
        ("non_utc", "provenance"),
        ("source_kind", "provenance"),
        ("old_date", "date_range"),
        ("malformed_row", "schema"),
    ],
)
def test_fail_closed(case, mode, reason):
    cfg, raw, manifest = case
    refresh.analyze(cfg)  # A failed refresh must also invalidate earlier numbers.
    if mode == "empty":
        edit_rows(cfg, raw, manifest, lambda rows: rows.clear())
    elif mode == "duplicate":
        edit_rows(cfg, raw, manifest, lambda rows: rows.append(rows[0].copy()))
    elif mode == "missing_key":
        edit_rows(cfg, raw, manifest, lambda rows: rows[0].update(AREA_BLOCK=""))
    elif mode in {"bad_date", "future_date"}:
        value = "bad" if mode == "bad_date" else "1/1/2099"
        edit_rows(cfg, raw, manifest, lambda rows: rows[0].update(DATE_OCCURRED=value))
    elif mode == "old_date":
        edit_rows(
            cfg, raw, manifest, lambda rows: rows[0].update(DATE_OCCURRED="1/1/1899")
        )
    elif mode == "non_utc":
        manifest["files"][0]["downloaded_at"] = "2026-10-01T00:00:00+01:00"
    elif mode == "source_kind":
        cfg["source_kind"] = "unsupported"
    elif mode == "duplicate_column":
        text = raw.read_text(encoding="utf-8").replace(
            "DATE_OCCURRED,", "DATE_OCCURRED,DATE_OCCURRED,", 1
        )
        raw.write_text(text, encoding="utf-8")
        reseal(cfg, raw, manifest)
    elif mode == "encoding":
        raw.write_bytes(raw.read_bytes() + b"\xff")
        reseal(cfg, raw, manifest)
    elif mode == "unit":
        cfg["unit"] = "barrels"
    elif mode == "digest":
        raw.write_bytes(raw.read_bytes() + b"\n")
    elif mode == "size":
        manifest["files"][0]["size_bytes"] += 1
    elif mode == "missing_manifest":
        manifest["files"] = []
    elif mode == "missing_timestamp":
        manifest["files"][0].pop("downloaded_at")
    elif mode == "bad_url":
        manifest["files"][0]["url"] = "https://example.org/unknown.zip"
    elif mode == "missing_column":
        raw.write_text("DATE_OCCURRED\n1/1/2020\n", encoding="utf-8")
        reseal(cfg, raw, manifest)
    elif mode == "malformed_row":
        raw.write_bytes(raw.read_bytes() + b"1/1/2020\n")
        reseal(cfg, raw, manifest)
    if mode in {"size", "missing_manifest", "missing_timestamp", "bad_url", "non_utc"}:
        (Path(cfg["data_dir"]) / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    with pytest.raises(refresh.QAError, match=reason):
        refresh.analyze(cfg)
    out = Path(cfg["output_dir"])
    qa = json.loads((out / "incinv-qa.json").read_text(encoding="utf-8"))
    assert qa["status"] == "not_evaluated"
    assert reason in qa["reason"]
    for name in (refresh.HEADLINES, refresh.INVENTORY, "incinv-manifest.json"):
        failed = json.loads((out / name).read_text(encoding="utf-8"))
        assert failed["status"] == "not_evaluated"
        assert set(failed) == {"status", "reason"}
    for name in refresh.CHARTS:
        assert len((out / f"{name}.csv").read_text(encoding="utf-8").splitlines()) == 1


def test_download_manifest_and_resume(tmp_path, monkeypatch):
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("IncInvRawData/mv_acc_investigations.txt", FIXTURE.read_bytes())
    calls = []

    def fake_download(url, destination):
        calls.append(url)
        destination.write_bytes(archive.read_bytes())
        return {
            "http_status": 200,
            "etag": '"synthetic-tag"',
            "last_modified": "Thu, 01 Oct 2026 00:00:00 GMT",
        }

    monkeypatch.setattr(refresh, "_download", fake_download)
    cfg = {"data_dir": str(tmp_path / "data"), "url": URL, "source_kind": "public"}
    manifest = refresh.fetch(cfg)
    assert calls == [URL]
    assert manifest["files"][0]["http_status"] == 200
    assert manifest["files"][0]["etag"] == '"synthetic-tag"'
    assert manifest["files"][0]["last_modified"] == "Thu, 01 Oct 2026 00:00:00 GMT"
    for entry in manifest["files"]:
        payload = (Path(cfg["data_dir"]) / entry["file"]).read_bytes()
        assert entry["size_bytes"] == len(payload)
        assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
        assert entry["downloaded_at"].endswith("Z")
    assert refresh.fetch(cfg) == manifest
    assert calls == [URL]


def test_network_failure_has_no_manifest(tmp_path, monkeypatch):
    def unavailable(url, destination):
        raise refresh.NetworkError("BLOCKED-NETWORK")

    monkeypatch.setattr(refresh, "_download", unavailable)
    cfg = {"data_dir": str(tmp_path), "url": URL, "source_kind": "public"}
    with pytest.raises(refresh.NetworkError, match="BLOCKED-NETWORK"):
        refresh.fetch(cfg)
    assert not (tmp_path / "manifest.json").exists()


def test_renderer_and_failed_qa_replace_public_page(case):
    cfg, raw, manifest = case
    spec = importlib.util.spec_from_file_location(
        "hse_renderer", ROOT / "scripts/exploration/drilling_hse_render_html.py"
    )
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    result = refresh.analyze(cfg)
    result["generated_at"] = "2099-12-31T00:00:00Z"
    out = Path(cfg["output_dir"])
    (out / refresh.HEADLINES).write_text(json.dumps(result), encoding="utf-8")
    page = out / "report.html"
    renderer.render(out / refresh.HEADLINES, page)
    text = page.read_text(encoding="utf-8")
    assert "2026-10-01T00:00:00Z" in text
    assert "<td>2</td><td>2026-10-01</td>" in text
    assert "2099-12-31" not in text
    assert "exact archived input" in text
    assert "Correct earlier reproducibility wording" in text
    for value, label in [
        ("2", "DRILL.* investigation records"),
        ("4", "INCINV records screened"),
        ("50.0%", "of investigation records"),
        ("1", "well-control investigation records"),
    ]:
        assert f'<div class="v">{value}</div>\n  <div class="l">{label}</div>' in text
    assert URL in text
    assert "2020-01-02 to 2022-04-05" in text
    assert "incinv-qa.json" in text
    assert "drilling-year-values.csv" in text
    edit_rows(cfg, raw, manifest, lambda rows: rows.clear())
    with pytest.raises(refresh.QAError):
        refresh.analyze(cfg)
    renderer.render(out / refresh.HEADLINES, page)
    text = page.read_text(encoding="utf-8")
    assert "Not evaluated" in text
    assert "Plotly.newPlot" not in text
    assert "kpi" not in text


@pytest.mark.parametrize(
    "script",
    ["drilling_hse_patterns_analysis.py", "intervention_hse_phase1a_explore.py"],
)
def test_cli_offline_config_from_another_directory(case, tmp_path, script):
    import subprocess

    cfg, _, _ = case
    path = tmp_path / "config.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "scripts/exploration" / script),
            "--config",
            str(path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "screened 4" in result.stdout
    assert (Path(cfg["output_dir"]) / refresh.INVENTORY).exists()


def test_failed_network_invalidates_existing_public_outputs(case, monkeypatch):
    cfg, _, _ = case
    spec = importlib.util.spec_from_file_location(
        "hse_cli", ROOT / "scripts/exploration/drilling_hse_patterns_analysis.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    refresh.analyze(cfg)
    config_file = Path(cfg["data_dir"]).parent / "config.json"
    config_file.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(cli, "workflow", lambda: refresh)

    def blocked(config):
        raise refresh.NetworkError("BLOCKED-NETWORK")

    monkeypatch.setattr(refresh, "fetch", blocked)
    with pytest.raises(refresh.NetworkError):
        cli.main(["--config", str(config_file), "--fetch"])
    out = Path(cfg["output_dir"])
    assert (
        json.loads((out / refresh.HEADLINES).read_text(encoding="utf-8"))["status"]
        == "not_evaluated"
    )
    assert "Not evaluated" in (out / "drilling-hse-patterns-2026-07-05.html").read_text(
        encoding="utf-8"
    )


def test_download_records_response_headers(tmp_path, monkeypatch):
    import subprocess

    def response(command, **kwargs):
        headers = Path(command[command.index("--dump-header") + 1])
        headers.write_text(
            'HTTP/1.1 302 Found\r\nETag: "redirect"\r\n\r\n'
            'HTTP/2 200\r\neTaG: "synthetic-tag"\r\n'
            "Last-Modified: Thu, 01 Oct 2026 00:00:00 GMT\r\n\r\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="200", stderr="")

    monkeypatch.setattr(refresh.subprocess, "run", response)
    destination = tmp_path / "archive.zip"
    evidence = refresh._download(URL, destination)
    assert evidence == {
        "http_status": 200,
        "etag": '"synthetic-tag"',
        "last_modified": "Thu, 01 Oct 2026 00:00:00 GMT",
    }
    request = json.loads(destination.with_suffix(".request.json").read_text())
    assert request["etag"] == evidence["etag"]
    assert request["last_modified"] == evidence["last_modified"]


def test_years_cover_source_window_when_drill_is_sparse(case):
    cfg, raw, manifest = case
    edit_rows(cfg, raw, manifest, lambda rows: rows[1].update(DATE_OCCURRED="1/1/2018"))
    result = refresh.analyze(cfg)
    assert result["drill_by_year"] == {
        "2018": 0,
        "2019": 0,
        "2020": 1,
        "2021": 0,
        "2022": 1,
    }
    edit_rows(
        cfg,
        raw,
        manifest,
        lambda rows: [row.update(ACCIDENT_TYPE="Fire") for row in rows],
    )
    result = refresh.analyze(cfg)
    assert result["drill_total"] == 0
    assert result["drill_by_year"] == {str(year): 0 for year in range(2018, 2023)}
    assert result["drill_year_range"] is None
    assert result["drill_confidence_buckets"] == {}


@pytest.mark.parametrize(
    "text,label",
    [
        ("Fatality, Blowout", "fatality"),
        ("Explosion, LTA", "major"),
        ("LTA, Fire", "injury_lost_time"),
        ("RW/JT", "injury_lost_time"),
        ("Damage >$25K, Muster", "serious"),
        ("Evacuation", "evacuation_muster"),
        ("unclassified", "other"),
    ],
)
def test_analyst_severity_precedence(text, label):
    assert refresh._severity(text) == label
