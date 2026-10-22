"""Numerical anchors and consistency checks for the federal acreage report."""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from worldenergydata.federal_acreage import FixtureRecordProvider, evaluate

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / "docs/reports/modules/wfederalacreage"
EXAMPLE = ROOT / "examples/workflows/federal-acreage-evidence/fixture_records.json"
SCRIPT = ROOT / "scripts/reports/build_federal_acreage_report.py"
REBUILD = "PYTHONPATH=src python scripts/reports/build_federal_acreage_report.py"
SPEC = importlib.util.spec_from_file_location("acreage_report_builder", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result():
    provider = FixtureRecordProvider(EXAMPLE)
    return evaluate(provider.tract, *provider.records_for_tract(provider.tract))


def test_hand_worked_gross_anchor(result):
    # Nominal section = 640 acres; quarter-quarter = 640 / (4 * 4) = 40.
    # Eight supplied tract cells: 8 * 40 = 320 acres. Absolute tolerance 1e-9 acre.
    assert result.acreage.gross_area_acres.value == pytest.approx(320, abs=1e-9)


def test_hand_worked_coverage_anchor(result):
    # Four active cells + two expired cells + one hectare-record cell + one
    # repeated active cell - one shared cell = 7 unique cells; 7 * 40 = 280 acres.
    assert result.acreage.federal_record_coverage_acres.value == pytest.approx(
        280, abs=1e-9
    )


def test_hand_worked_leased_anchor(result):
    # Four active cells + one distinct active cell + one repeated cell
    # - one shared cell = 5 unique active cells; 5 * 40 = 200 acres.
    assert result.acreage.leased_acres.value == pytest.approx(200, abs=1e-9)


def test_headline_from_displayed_inputs(result):
    # Displayed gross 320 less coverage 280 = 40 acres without supplied records.
    soup = BeautifulSoup(builder.render_report(), "html.parser")
    gross = float(soup.select_one('[data-metric="gross"]').text)
    covered = float(soup.select_one('[data-metric="coverage"]').text)
    uncovered = float(soup.select_one('[data-metric="no_record"]').text)
    assert gross - covered == pytest.approx(uncovered, abs=1e-9)
    assert uncovered == pytest.approx(result.acreage.no_record_acres.value, abs=1e-9)


def test_every_worked_number_is_a_module_consistency_check(result):
    soup = BeautifulSoup(builder.render_report(), "html.parser")
    values = builder.example_metrics(result)
    assert values == {
        "gross": result.acreage.gross_area_acres.value,
        "coverage": result.acreage.federal_record_coverage_acres.value,
        "leased": result.acreage.leased_acres.value,
        "expired": result.acreage.expired_or_nonleased_acres.value,
        "no_record": result.acreage.no_record_acres.value,
        "tract_cells": len(result.tract.aliquots),
        "record_count": len(result.records),
        "exception_count": len(result.exceptions),
        "cell_area": result.tract.gross_area_acres / len(result.tract.aliquots),
        "hectare_input": result.records[4].area.value,
        "converted": result.records[4].area_acres.value,
        "overlap": next(e.acres for e in result.exceptions if e.kind == "overlap"),
        "tolerance": 0.5,  # Existing software policy in _check_area, not a survey tolerance.
        "zero": 0,
    }
    for node in soup.select("[data-metric]"):
        key = node["data-metric"]
        assert node.text == builder.display_number(key, values[key])
    worked = soup.select_one("#section-6")
    assert worked.select("[data-metric]")
    for node in worked.select("[data-metric]"):
        node.decompose()
    # Dates, input identifiers and source-reference link labels are not quantities.
    for node in worked.select("a, code, time, title, figcaption"):
        node.decompose()
    text = worked.get_text(" ")
    assert not re.search(r"(?<!\w)\d+(?:\.\d+)?", text.split("Worked example", 1)[1])
    assert values["converted"] == pytest.approx(result.records[4].area_acres.value)
    assert values["overlap"] == result.exceptions[-1].acres


def test_chart_payload_is_a_module_consistency_check(result):
    soup = BeautifulSoup(builder.render_report(), "html.parser")
    payload = json.loads(soup.select_one("#chart-data").string)
    assert payload["limit"] == result.acreage.gross_area_acres.value
    assert payload["areas"] == [
        round(getattr(result.acreage, key).value, 4) for key in builder.ROLLUP_LABELS
    ]
    assert "tract-area bound" in soup.select_one("#area-chart").get_text()


def test_rebuild_matches_committed_report(tmp_path):
    output = tmp_path / "report.html"
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env["PYTHONPATH"] = str(ROOT / "src")
    # Child resolution is independent of any inherited Git worktree binding.
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    fresh = output.read_text(encoding="utf-8")
    saved = (FOLDER / "index.html").read_text(encoding="utf-8")
    # Values are rounded to displayed precision; no CPU-sensitive float text.
    assert fresh == saved, f"Report is stale. Rebuild: {REBUILD}"
    assert b"\r" not in output.read_bytes()


def test_calculation_digests_and_source_preservation(tmp_path):
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in builder.INPUTS
    }
    builder.write_report(tmp_path / "index.html")
    after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in builder.INPUTS
    }
    assert before == after
    soup = BeautifulSoup(builder.render_report(), "html.parser")
    saved = json.loads(soup.select_one("#calculation-digests").string)
    assert saved == builder.calculation_digests(), f"Rebuild: {REBUILD}"


def test_single_file_structure_sources_and_public_wording():
    html = builder.render_report()
    soup = BeautifulSoup(html, "html.parser")
    assert soup.body["class"] == ["hs-doc"]
    assert len(soup.select("main > section")) == 10
    assert not soup.select("h4, h5, h6, b, strong, script[src], link[rel=stylesheet]")
    assert "Draft for maintainer review" in soup.get_text()
    for link in soup.select('a[href^="#"]'):
        assert soup.find(id=link["href"][1:]), link["href"]
    assert soup.select_one("#section-1").find_next_sibling()["id"] == "revision-history"
    for word in ("owner", "could", "should", "would", "certified", "compliant"):
        assert not re.search(rf"\b{word}\b", soup.get_text().lower())
    assert not re.search(r"/(?:home|mnt)/|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", html)
    for ref in ("ref-survey", "ref-sets", "ref-acre", "ref-si"):
        assert soup.select_one(f"#{ref} a[href^='https://']")
    assert "NOT_EVALUATED" in soup.get_text()
    changes = json.loads((FOLDER / "changes.json").read_text(encoding="utf-8"))
    assert changes["revision"] == soup.html["data-revision"]
    assert changes == json.loads(soup.select_one("#change-data").string)
    assert "showDirectoryPicker" in html
    assert "createWritable" in html
    assert "textContent" in html
    assert "innerHTML" not in html
    assert "fetch(" not in html
    assert (FOLDER / "house-style.css").read_text(encoding="utf-8") in html


def test_text_files_are_utf8_lf():
    for path in [SCRIPT, Path(__file__), *FOLDER.iterdir()]:
        raw = path.read_bytes()
        assert b"\r" not in raw, path.name
        assert raw.decode("utf-8").endswith("\n"), path.name


def test_builder_rejects_input_overwrite(tmp_path, monkeypatch):
    # Mutation probes use a disposable source, never the canonical fixture.
    disposable = tmp_path / "input.html"
    disposable.write_text("source evidence\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(builder, "INPUTS", (disposable,))
    before = disposable.read_bytes()
    with pytest.raises(ValueError, match="output"):
        builder.write_report(disposable)
    assert disposable.read_bytes() == before


def test_chart_graphics_and_hover_are_module_consistency_checks(result):
    soup = BeautifulSoup(builder.render_report(), "html.parser")
    # The rendered bars, not only embedded numerical metadata, carry the values.
    fields = [
        "gross_area_acres",
        "federal_record_coverage_acres",
        "leased_acres",
        "expired_or_nonleased_acres",
        "no_record_acres",
    ]
    labels = [
        "Gross tract",
        "Record coverage",
        "Active leases",
        "Expired or nonleased",
        "Without supplied records",
    ]
    for bar, field, label in zip(soup.select(".bar"), fields, labels, strict=True):
        area = getattr(result.acreage, field).value
        gross = result.acreage.gross_area_acres.value
        assert bar["aria-label"] == (
            f"Synthetic tract; {label}; acreage {area:.0f} acres; "
            f"gross tract-area bound {gross:.0f} acres"
        )
        assert bar.title.text == bar["aria-label"]
        assert float(bar["height"]) == pytest.approx(210 * area / gross, abs=0.0005)


def test_source_digests_are_stable_across_crlf_checkouts(tmp_path, monkeypatch):
    source = tmp_path / "calculation.py"
    source.write_bytes(b"value = 1\n")
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "INPUTS", (source,))
    expected = builder.calculation_digests()
    source.write_bytes(b"value = 1\r\n")
    assert builder.calculation_digests() == expected
    source.write_bytes(b"value = 2\n")
    assert builder.calculation_digests() != expected


def test_comment_binding_covers_final_rendered_content(monkeypatch):
    original = BeautifulSoup(builder.render_report(), "html.parser")
    original_binding = original.select_one('meta[name="document-binding"]')["content"]
    monkeypatch.setattr(
        builder, "record_table", lambda result: "<tr><td>Changed view</td></tr>"
    )
    changed = BeautifulSoup(builder.render_report(), "html.parser")
    assert (
        changed.select_one('meta[name="document-binding"]')["content"]
        != original_binding
    )


def test_appendix_record_values_are_module_consistency_checks(result):
    soup = BeautifulSoup(builder.render_report(), "html.parser")
    rows = soup.select("#section-10 table")[0].select("tbody tr")
    assert len(rows) == len(result.records)
    for row, record in zip(rows, result.records, strict=True):
        cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
        assert cells[:4] == [
            record.record_serial,
            record.record_status,
            (
                f"{record.area.value:.0f}"
                if record.area.unit == "acres"
                else "Not applicable"
            ),
            (
                f"{record.area.value:.4f}"
                if record.area.unit == "hectares"
                else "Not applicable"
            ),
        ]
        assert cells[5] == (
            "Unavailable"
            if record.intersect_acres.value is None
            else f"{record.intersect_acres.value:.0f}"
        )
