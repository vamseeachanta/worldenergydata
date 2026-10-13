"""Regression coverage for unreproducible incident report publication."""

import ast
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
NOTICE = (
    "Figures on this page could not be re-derived from data held in this "
    "repository; treat as unverified"
)
PAGES = (
    "reports/IMO_GISIS_Executive_Report.html",
    "reports/marine_safety/executive_summary.html",
    "reports/marine_safety/hatch_analysis.html",
    "reports/marine_safety/foundering_analysis.html",
    "reports/marine_safety/fatality_analysis.html",
)
# No repository-backed agreement test can cover these absent raw inputs.
AGREEMENT_TEST_PAGES = set()


def assert_notice(html: str) -> None:
    """Require one visible notice as the first text following the main title."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    assert heading is not None
    text = next(item for item in heading.next_siblings if str(item).strip())
    assert text.name == "p"
    assert text.get_text(strip=True) == NOTICE
    assert html.count(NOTICE) == 1


def load_generator(name: str):
    """Load a function-based generator without executing its command entry."""
    path = ROOT / "scripts/marine_safety" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("page", PAGES)
def test_committed_page_notice(page: str) -> None:
    """Existing figures remain visibly unverified without JavaScript."""
    assert_notice((ROOT / page).read_text(encoding="utf-8"))


@pytest.mark.parametrize("kind", ("hatch", "foundering", "fatality"))
@pytest.mark.parametrize("generator", ("incident", "optimized"))
def test_detail_writer_notice(kind, generator, tmp_path, monkeypatch) -> None:
    """Both detail writers default to marking each incident category."""
    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.chdir(tmp_path)
    if generator == "incident":
        module = load_generator("generate_incident_report")
        module.generate_detailed_report(kind, pd.DataFrame(), {}, [], tmp_path, False)
    else:
        module = load_generator("generate_optimized_report")
        module.generate_optimized_html(kind, "incidents.csv", {}, [], tmp_path)
    assert_notice((tmp_path / f"{kind}_analysis.html").read_text())


def test_summary_writer_notice(tmp_path, monkeypatch) -> None:
    """The summary writer marks output even when supplied a synthetic analysis."""
    monkeypatch.syspath_prepend(str(ROOT))
    module = load_generator("generate_incident_report")
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
    module.generate_executive_summary({}, analyses, tmp_path, False)
    assert_notice((tmp_path / "executive_summary.html").read_text())


def test_imo_template_notice(monkeypatch) -> None:
    """Inspect the actual template without importing its absent-data loader."""
    monkeypatch.syspath_prepend(str(ROOT))
    module = load_generator("generate_optimized_report")
    tree = ast.parse((ROOT / "reports/imo_gisis_analysis_report.py").read_text())
    template = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "html_content" for t in node.targets
        )
    )
    chunks = []
    for node in template.values:
        if isinstance(node, ast.Constant):
            chunks.append(node.value)
        elif "unverified_notice" in ast.unparse(node.value):
            assert isinstance(node.value, ast.Call)
            assert node.value.func.id == "unverified_notice"
            chunks.append(
                module.unverified_notice(ast.literal_eval(node.value.args[0]))
            )
    assert_notice("".join(chunks))


def test_verified_pages_have_agreement_coverage() -> None:
    """An absent agreement test cannot authorize omission of the notice."""
    module = load_generator("generate_optimized_report")
    assert hasattr(module, "VERIFIED_PAGES")
    assert set(module.VERIFIED_PAGES) == AGREEMENT_TEST_PAGES


def test_landing_index_omits_unverified_reports(tmp_path, monkeypatch) -> None:
    """Published files do not re-enter the landing report navigation."""
    spec = importlib.util.spec_from_file_location(
        "report_pages", ROOT / "scripts/build_pages.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PUBLIC", tmp_path)
    monkeypatch.setattr(module, "ASSETS", tmp_path / "assets")
    module.build(domains=["marine_safety"])
    html = (tmp_path / "index.html").read_text()
    for page in PAGES:
        assert Path(page).name not in html


def test_report_lists_relabel_unverified_pages() -> None:
    """Retained report descriptions expose their unverified status."""
    summary = (ROOT / "reports/REPORT_SUMMARY.md").read_text()
    assert "**Status:** unverified" in summary
    readme = (ROOT / "reports/marine_safety/README.md").read_text()
    for page in PAGES[1:]:
        entry = next(
            line
            for line in readme.splitlines()
            if line.startswith(f"- **{Path(page).name}")
        )
        assert "unverified" in entry


def test_inventory_relabels_unverified_pages() -> None:
    """The generated inventory cannot advertise these pages as current analysis."""
    import csv

    with (ROOT / "docs/modules/report-inventory.csv").open() as stream:
        rows = {row["path"]: row for row in csv.DictReader(stream)}
    for page in PAGES:
        assert rows[page]["classification"] == "unverified"
