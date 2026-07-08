"""Regression tests for the Buckskin V50 economics report surface."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import scripts.build_pages as build_pages
import scripts.lower_tertiary.regenerate_field_economics_v50 as regen

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FDAS_DIR = PROJECT_ROOT / "docs/modules/bsee/analysis/production/FDAS_V30"
REPORTS_DIR = PROJECT_ROOT / "reports/lower_tertiary"
CAPABILITIES_PAGE = PROJECT_ROOT / "reports/capabilities/index.html"

BUCKSKIN_LEASES = {"G25806", "G25813", "G25814", "G25815", "G25823", "G32650"}


def _norm_lease(value: str) -> str:
    return str(value).strip().upper().replace('"', "").replace(" ", "")


def test_v50_kc_dnc_input_exists_with_buckskin_totals():
    path = FDAS_DIR / "drilling_and_completion_days_v21_kc.csv"
    assert path.exists(), "V50 KC D&C input CSV must be committed"

    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    buckskin = [
        row for row in rows if _norm_lease(row["SURF_LEASE_NUM"]) in BUCKSKIN_LEASES
    ]

    assert len(rows) == 253
    assert len({row["API_WELL_NUMBER"] for row in buckskin}) == 25
    dc_days = sum(
        round(float(row["DRILLING_DAYS"]) + float(row["COMPLETION_DAYS"]))
        for row in buckskin
    )
    assert dc_days == 2056


def test_v50_batch_regenerator_includes_buckskin():
    assert "Buckskin" in regen.PRODUCERS


def test_buckskin_v50_report_is_published():
    path = REPORTS_DIR / "field_economics_buckskin_v50.md"
    assert path.exists(), "Buckskin V50 economics report must be published"
    md = path.read_text(encoding="utf-8")

    assert "# Buckskin Field Economics Report" in md
    assert "**Data window:** 2000-09 -> 2026-04 (latest V50-KC recompute)" in md
    assert re.search(r"\| \*\*NPV @ 10%\*\* \| \*\*\$-?[0-9,]+\.[0-9] M\*\* \|", md)


def test_fdas_comparison_replaces_buckskin_wed_placeholder():
    md = (REPORTS_DIR / "fdas_revision_comparison.md").read_text(encoding="utf-8")
    row = next(
        line for line in md.splitlines() if line.startswith("| Buckskin | −541.4 |")
    )
    cells = [cell.strip() for cell in row.strip("|").split("|")]

    assert cells[2] != "–", row
    assert cells[3] != "–", row
    assert cells[4] == "–", row
    assert "no Buckskin V50 recompute yet" not in cells[6]


def test_pages_builder_indexes_buckskin_v50_report():
    reports = {
        slug: path.name
        for slug, path in build_pages._lower_tertiary_economics_reports()
    }

    assert reports["buckskin"] == "field_economics_buckskin_v50.md"


def test_capabilities_validation_section_links_key_validation_reports():
    html = CAPABILITIES_PAGE.read_text(encoding="utf-8")
    validation_section = html.split('<section class="chan" id="validation">', 1)[1]
    validation_section = validation_section.split("</section>", 1)[0]

    assert "four linked reports" in validation_section
    assert "../wo-april-2026-validation.html" in validation_section
    assert "../completion/verification.html" in validation_section
    assert "../fdas-revision-comparison.html" in validation_section
    assert "../economics-buckskin.html" in validation_section


def test_capabilities_validation_table_links_fdas_revision_comparison_row():
    html = CAPABILITIES_PAGE.read_text(encoding="utf-8")
    validation_section = html.split('<section class="chan" id="validation">', 1)[1]
    validation_section = validation_section.split("</section>", 1)[0]
    table_body = validation_section.split("<tbody>", 1)[1].split("</tbody>", 1)[0]

    expected_row = (
        '<tr><td><a href="../fdas-revision-comparison.html">'
        "FDAS revision comparison</a></td>"
        "<td>V50-vs-wed D&amp;C + component economics</td>"
        '<td class="val">D&amp;C Δ=0; 40 component rows verified</td>'
        '<td class="pub">2026-04 wed-latest reconciliation</td></tr>'
    )

    assert expected_row in table_body
