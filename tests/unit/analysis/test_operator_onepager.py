"""Report contract tests; synthetic inputs are not regulator observations."""

import copy
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from worldenergydata.analysis import operator_onepager as report

FIXTURES = Path(__file__).parents[2] / "fixtures" / "operator_onepager"


@pytest.fixture
def bundle():
    return json.loads((FIXTURES / "worked_example.json").read_text())


def test_golden(bundle):
    assert (
        report.render_html(bundle, "001")
        == (FIXTURES / "worked_example.html").read_text()
    )


def test_preserves_values_order_and_chart(bundle):
    """Independent hand calculation: rates 2 and 8 give widths 25% and 100%.

    No domain conversion is applied: oil 120 bbl and gas 600 Mcf are supplied
    totals for the stated period. Candidate rank 1 precedes rank 2 regardless
    of input order. These numbers are invented test inputs, never field data.
    """
    page = report.render_html(bundle, "001")
    assert "120.0 bbl" in page
    assert "600.0 Mcf" in page
    assert "width:25.0%" in page
    assert "width:100.0%" in page
    assert page.index("well-alpha") < page.index("lease-beta")
    assert "lease-level; not allocated to individual wells" in page
    assert "SYNTHETIC EXAMPLE" in page
    assert "2026-01-31" in page
    assert "Synthetic regulator export" in page


def test_missing_is_explicit_and_zero_is_real(bundle):
    bundle["operators"][0]["summary"]["well_count_total"] = None
    bundle["operators"][0]["summary"]["oil_bbl_last12"]["value"] = 0
    page = report.render_html(bundle, "001")
    assert "Total wells</th><td>not captured" in page
    assert "Oil</th><td>0.0 bbl" in page
    assert "Water</th><td>not captured" in page
    assert "False-positive rate: NOT_EVALUATED" in page


def test_registry_operator_without_screen(bundle):
    bundle["operators"].append({"operator_no": "002", "summary": {}})
    page = report.render_html(bundle, "002")
    assert "Operator 002" in page
    assert "Screen not captured; candidacy NOT_EVALUATED" in page
    assert "Peer comparison not captured" in page
    assert "What this data cannot tell you" in page
    assert "Specific uplift, economics and working interest are NOT_EVALUATED" in page


def test_escape_all_input_text(bundle):
    bundle["sources"]["regulator"]["dataset"] = '<img src="remote">'
    bundle["operators"][0]["screen"]["method"] = "<script>alert(1)</script>"
    page = report.render_html(bundle, "001")
    assert "<img" not in page
    assert "<script" not in page
    assert "&lt;script&gt;" in page
    assert "<link" not in page
    assert "url(" not in page


def test_standalone_document_structure(bundle):
    class Document(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = []

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
            assert not ({"src", "srcset", "href"} & dict(attrs).keys())

    document = Document()
    document.feed(report.render_html(bundle, "001"))
    assert document.tags.count("html") == 1
    assert document.tags.count("title") == 1
    assert document.tags.count("section") == 1
    assert "script" not in document.tags
    assert "overflow: hidden" not in report.STYLE


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "12", "—"])
def test_invalid_figures_rejected(bundle, value):
    bundle["operators"][0]["summary"]["oil_bbl_last12"]["value"] = value
    with pytest.raises(ValueError):
        report.render_html(bundle, "001")


@pytest.mark.parametrize("field", ["source", "value"])
def test_partial_measurement_rejected(bundle, field):
    del bundle["operators"][0]["summary"]["oil_bbl_last12"][field]
    with pytest.raises(ValueError):
        report.render_html(bundle, "001")


def test_unknown_operator_and_duplicates(bundle):
    with pytest.raises(ValueError, match="Unknown operator"):
        report.render_html(bundle, "absent")
    bundle["operators"].append(copy.deepcopy(bundle["operators"][0]))
    with pytest.raises(ValueError, match="Duplicate operator"):
        report.render_html(bundle, "001")


@pytest.mark.parametrize("problem", ["source", "vintage", "rank", "evidence", "count"])
def test_bad_provenance_or_screen_rejected(bundle, problem):
    operator = bundle["operators"][0]
    if problem == "source":
        operator["summary"]["oil_bbl_last12"]["source"] = "absent"
    elif problem == "vintage":
        bundle["sources"]["regulator"]["vintage"] = "unknown"
    elif problem == "rank":
        operator["screen"]["candidates"][1]["rank"] = 2
    elif problem == "evidence":
        operator["screen"]["candidates"][0]["evidence"] = []
    else:
        operator["summary"]["well_count_total"]["value"] = 1.5
    with pytest.raises(ValueError):
        report.render_html(bundle, "001")


def test_candidate_limit_is_disclosed(bundle):
    page = report.render_html(bundle, "001", candidate_limit=1)
    assert "well-alpha" in page
    assert "lease-beta" not in page
    assert "1 additional candidates omitted" in page
    assert "What this data cannot tell you" in page
    with pytest.raises(ValueError):
        report.render_html(bundle, "001", candidate_limit=0)


def test_zero_peer_rates_do_not_divide_by_zero(bundle):
    peer = bundle["operators"][0]["screen"]["peer_comparison"]
    peer["operator"]["value"] = peer["median"]["value"] = 0
    assert report.render_html(bundle, "001").count("width:0.0%") == 2


def test_mismatched_peer_periods_rejected(bundle):
    bundle["sources"]["screen"]["period"] = "different window"
    with pytest.raises(ValueError, match="matching reporting periods"):
        report.render_html(bundle, "001")


def test_signed_screen_evidence_preserved(bundle):
    """Synthetic signed observation: a supplied change of -2 stays -2.0."""
    evidence = bundle["operators"][0]["screen"]["candidates"][0]["evidence"][0]
    evidence.update(label="Reported rate change", value=-2, unit="bbl/day")
    assert "Reported rate change: -2.0 bbl/day [regulator]" in report.render_html(
        bundle, "001"
    )


def test_false_positive_percentage(bundle):
    """Hand calculation: 1 false positive / 20 cases = 0.05 = 5.0 percent.

    This is synthetic validation input, not a measured screen performance claim.
    """
    bundle["operators"][0]["screen"]["false_positive_rate"] = {
        "value": 0.05,
        "source": "screen",
    }
    assert "False-positive rate: 5.0 % [screen]" in report.render_html(bundle, "001")
    bundle["operators"][0]["screen"]["false_positive_rate"]["value"] = 1.1
    with pytest.raises(ValueError, match="exceed unity"):
        report.render_html(bundle, "001")


def test_pdf_command_and_single_page_guard(tmp_path, monkeypatch):
    """The issue requires one PDF page and Chrome's header suppression flag."""
    html = tmp_path / "in.html"
    html.write_text("<!doctype html><p>test</p>")
    pdf = tmp_path / "out.pdf"
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        if args[0] == "chrome":
            Path(
                next(
                    a.split("=", 1)[1] for a in args if a.startswith("--print-to-pdf=")
                )
            ).write_bytes(b"%PDF-test")
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0, "Pages: 1\n", "")

    monkeypatch.setattr(report.subprocess, "run", run)
    report.render_pdf(html, pdf, chrome="chrome", pdfinfo="pdfinfo")
    assert "--no-pdf-header-footer" in calls[0]
    assert "--headless=new" in calls[0]
    assert "--no-sandbox" not in calls[0]
    assert pdf.read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize("pages", ["Pages: 2\n", "Pages: 0\n", "not a PDF"])
def test_pdf_overflow_or_invalid_readback_is_not_published(
    tmp_path, monkeypatch, pages
):
    html = tmp_path / "in.html"
    html.write_text("test")
    pdf = tmp_path / "out.pdf"
    pdf.write_bytes(b"previous accepted output")

    def run(args, **kwargs):
        if args[0] == "chrome":
            Path(
                next(
                    a.split("=", 1)[1] for a in args if a.startswith("--print-to-pdf=")
                )
            ).write_bytes(b"%PDF-test")
        return subprocess.CompletedProcess(args, 0, pages, "")

    monkeypatch.setattr(report.subprocess, "run", run)
    with pytest.raises(ValueError, match="exactly one page"):
        report.render_pdf(html, pdf, chrome="chrome", pdfinfo="pdfinfo")
    assert pdf.read_bytes() == b"previous accepted output"


def test_cli_html_only(bundle, tmp_path):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle))
    assert (
        report.main(
            [
                "--input",
                str(source),
                "--operator",
                "001",
                "--output-dir",
                str(tmp_path),
                "--html-only",
            ]
        )
        == 0
    )
    assert (tmp_path / "onepager.html").read_text() == report.render_html(bundle, "001")
    assert not (tmp_path / "onepager.pdf").exists()


def test_make_html_target(tmp_path):
    result = subprocess.run(
        [
            "make",
            "onepager-html",
            "OPERATOR=001",
            f"INPUT={FIXTURES / 'worked_example.json'}",
            f"OUTPUT={tmp_path}",
            f"ONEPAGER_PYTHON={sys.executable}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--html-only" in result.stdout
    assert (tmp_path / "onepager.html").read_text() == (
        FIXTURES / "worked_example.html"
    ).read_text()


def test_invalid_input_and_missing_pdf_executable(bundle, tmp_path, monkeypatch):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle))

    def unavailable(*args, **kwargs):
        raise FileNotFoundError("browser absent")

    monkeypatch.setattr(report, "render_pdf", unavailable)
    arguments = [
        "--input",
        str(source),
        "--operator",
        "001",
        "--output-dir",
        str(tmp_path),
    ]
    with pytest.raises(SystemExit) as error:
        report.main(arguments)
    assert error.value.code == 1
    source.write_text("not-json")
    with pytest.raises(SystemExit) as error:
        report.main(arguments)
    assert error.value.code == 1
