"""Regression coverage for unreproducible incident report publication."""

import ast
import hashlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
NOTICE = (
    "Figures on this page could not be re-derived from data held in this "
    "repository; treat as unverified."
)
LINKED_NOTICE = NOTICE.replace("on this page", "in the linked report")
PAGES = (
    "reports/IMO_GISIS_Executive_Report.html",
    "reports/marine_safety/executive_summary.html",
    "reports/marine_safety/hatch_analysis.html",
    "reports/marine_safety/foundering_analysis.html",
    "reports/marine_safety/fatality_analysis.html",
)
HATCH_SENTENCE = (
    "The assessment-class and annual charts count records analysed by assessment "
    "class and year, respectively, not detected hatch incidents."
)
HATCH_TITLES = (
    "Records Analysed by Assessment Class (Top Categories)",
    "Records Analysed per Year (Last 10 Years)",
)
# No repository-backed agreement test can cover these absent raw inputs.
AGREEMENT_TEST_PAGES = set()


def assert_notice(html: str, expected: str = NOTICE) -> None:
    """Require one visible notice as the first text following the main title."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    assert heading is not None
    text = next(item for item in heading.next_siblings if str(item).strip())
    assert text.name == "p"
    assert text.get_text(strip=True) == expected
    assert html.count(expected) == 1


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
    html = (ROOT / page).read_text(encoding="utf-8")
    assert_notice(html)
    if page.endswith("hatch_analysis.html"):
        notice = BeautifulSoup(html, "html.parser").find("p", class_="unverified")
        assert notice.find_next_sibling().get_text(strip=True) == HATCH_SENTENCE


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


@pytest.mark.parametrize(
    "name", ("imo", "ms-exec", "ms-hatch", "ms-foundering", "ms-fatality")
)
def test_capability_writer_notice(name: str) -> None:
    """Retained capability inputs place the same warning beneath the title."""
    spec = importlib.util.spec_from_file_location(
        "report_capabilities", ROOT / "scripts/capabilities/build_onepagers.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entry = next(item for item in module.SPECS if item["id"] == name)
    assert_notice(module._render_html(entry), LINKED_NOTICE)


@pytest.mark.parametrize(
    "name", ("imo", "ms-exec", "ms-hatch", "ms-foundering", "ms-fatality")
)
def test_committed_capability_notice(name: str) -> None:
    """Generated companion pages expose the status of their linked figures."""
    assert_notice(
        (ROOT / f"reports/capabilities/pdf/{name}.html").read_text(), LINKED_NOTICE
    )


def test_capability_descriptions_are_retained() -> None:
    """Warning insertion preserves existing descriptive and date-range text."""
    descriptions = {
        "imo": "Recorded occurrences span 1900-01-01 to 2025-06-09.",
        "ms-exec": "An overview of the combined casualty records",
        "ms-hatch": "Incident narratives are screened for hatch",
        "ms-foundering": "Foundering incidents are grouped to examine reported fatalities",
        "ms-fatality": "Fatal incidents are grouped by recorded cause and category",
    }
    for name, text in descriptions.items():
        html = (ROOT / f"reports/capabilities/pdf/{name}.html").read_text()
        assert text in BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


@pytest.mark.parametrize(
    "title, previous",
    (
        (HATCH_TITLES[0], "Hatch Incidents by Assessment Class (Top Categories)"),
        (HATCH_TITLES[1], "Hatch Incidents per Year (Last 10 Years)"),
    ),
)
def test_committed_hatch_chart_titles(title: str, previous: str) -> None:
    """Record-count charts identify their population without changing data."""
    html = (ROOT / "reports/marine_safety/hatch_analysis.html").read_text()
    assert f"title: '{title}'" in html
    assert f"title: '{previous}'" not in html


def test_hatch_record_constants() -> None:
    """The hand-marked page agrees with the shared record-chart constants."""
    module = load_generator("generate_optimized_report")
    assert module.HATCH_RECORD_NOTICE == HATCH_SENTENCE
    assert module.HATCH_RECORD_TITLES == HATCH_TITLES


@pytest.mark.parametrize(
    "name, digest",
    (
        (
            "hatchSeverity",
            "fed8eb406ef82fea1e438f250e680403689c524745aa442a6b43f9b32b00cbe1",
        ),
        (
            "hatchTrend",
            "7bf547189bb89d47dc4444ba2f91e0304ae9b4aea4c425a4bc32298920826a10",
        ),
    ),
)
def test_committed_hatch_series(name: str, digest: str) -> None:
    """Pin every embedded series byte to the starting report data."""
    html = (ROOT / "reports/marine_safety/hatch_analysis.html").read_text()
    value = re.search(rf"const {name} = (\{{.*?\}});", html, re.S).group(1)
    assert hashlib.sha256(value.encode()).hexdigest() == digest


@pytest.mark.parametrize(
    "page",
    PAGES
    + tuple(
        f"reports/capabilities/pdf/{name}.html"
        for name in ("imo", "ms-exec", "ms-hatch", "ms-foundering", "ms-fatality")
    ),
)
def test_committed_notice_style(page: str) -> None:
    """Notices have a distinct quiet rule and retain plain text weight."""
    soup = BeautifulSoup((ROOT / page).read_text(), "html.parser")
    first = soup.find("h1").find_next_sibling()
    assert "unverified" in first.get("class", [])
    styles = " ".join(style.get_text() for style in soup.find_all("style"))
    rule = re.search(r"(?:\.header p)?\.unverified\s*\{([^}]+)\}", styles)
    assert rule is not None
    assert "font-weight: 400" in rule.group(1)
    assert "opacity: 0.75" in rule.group(1)
    assert not any(token in rule.group(1) for token in ("background", "border"))


def test_shared_notice_has_no_import_side_effects() -> None:
    """Capability notice imports do not load plotting or configure logging."""
    code = (
        "import logging, sys; "
        "from scripts.capabilities import build_onepagers; "
        "from scripts.marine_safety import report_notice; "
        "assert not logging.getLogger().handlers; "
        "assert 'pandas' not in sys.modules; "
        "assert 'plotly' not in sys.modules; "
        "assert report_notice.VERIFIED_PAGES == ()"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)


@pytest.mark.parametrize(
    "path",
    (
        "scripts/marine_safety/generate_incident_report.py",
        "scripts/marine_safety/generate_optimized_report.py",
        "reports/imo_gisis_analysis_report.py",
    ),
)
def test_writer_notice_style(path: str) -> None:
    """All incident writers insert the shared style in their HTML templates."""
    tree = ast.parse((ROOT / path).read_text())
    templates = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.JoinedStr) and "<style>" in ast.unparse(n)
    ]
    assert templates
    assert all(
        any(
            isinstance(n, ast.FormattedValue)
            and isinstance(n.value, ast.Name)
            and n.value.id == "NOTICE_STYLE"
            for n in template.values
        )
        for template in templates
    )


def test_publication_docstring_marks_unverified() -> None:
    """Publication documentation distinguishes availability from qualification."""
    tree = ast.parse((ROOT / "scripts/build_pages.py").read_text())
    function = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "build_marine_safety"
    )
    doc = ast.get_docstring(function)
    assert "marked unverified" in doc
    assert "Only real-data reports are published" not in doc
