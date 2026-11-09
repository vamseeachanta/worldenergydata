"""Report contract tests; synthetic inputs are not regulator observations."""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

from worldenergydata.analysis import operator_onepager as report

FIXTURES = Path(__file__).parents[2] / "fixtures" / "operator_onepager"


@pytest.fixture
def bundle():
    return json.loads((FIXTURES / "worked_example.json").read_text(encoding="utf-8"))


def test_golden(bundle):
    assert report.render_html(bundle, "001") == (
        FIXTURES / "worked_example.html"
    ).read_text(encoding="utf-8")


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


def test_unknown_summary_key_is_rejected(bundle):
    summary = bundle["operators"][0]["summary"]
    summary["well_count_totl"] = summary.pop("well_count_total")
    with pytest.raises(ValueError, match="Unknown summary key"):
        report.render_html(bundle, "001")


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


@pytest.mark.parametrize("version", [True, False, 1.0, 0.0])
def test_non_integer_schema_versions_rejected(bundle, version):
    bundle["schema_version"] = version
    with pytest.raises(ValueError, match="Unsupported snapshot schema version"):
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


def test_large_finite_peer_rates_produce_finite_bar_widths(bundle):
    """Ratios 1e308/1e308 and 8/1e308 round to 100.0% and 0.0%."""
    bundle["operators"][0]["screen"]["peer_comparison"]["operator"]["value"] = 1e308
    page = report.render_html(bundle, "001")
    assert re.findall(r'style="width:([^"]+)"', page) == ["100.0%", "0.0%"]


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


@pytest.mark.parametrize(
    ("value", "display"),
    [(0.04, "0.04"), (-0.04, "-0.04"), (0.0254, "0.0254"), (1e-12, "1e-12")],
)
def test_small_evidence_preserves_supplied_precision(bundle, value, display):
    evidence = bundle["operators"][0]["screen"]["candidates"][0]["evidence"][0]
    evidence.update(label="Reported change", value=value, unit="fraction")
    assert f"Reported change: {display} fraction [regulator]" in report.render_html(
        bundle, "001"
    )


def test_small_peer_labels_agree_with_bar_widths(bundle):
    """Hand calculation: 0.04 / 0.08 = 0.5; widths are 50.0% and 100.0%."""
    peer = bundle["operators"][0]["screen"]["peer_comparison"]
    peer["operator"]["value"] = 0.04
    peer["median"]["value"] = 0.08
    page = report.render_html(bundle, "001")
    assert "Operator: 0.04 bbl/day [regulator]" in page
    assert "Peer median: 0.08 bbl/day [screen]" in page
    assert re.findall(r'style="width:([^"]+)"', page) == ["50.0%", "100.0%"]


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
    html.write_text("<!doctype html><p>test</p>", encoding="utf-8", newline="\n")
    pdf = tmp_path / "out.pdf"
    rejected = pdf.with_suffix(".rejected.pdf")
    rejected.write_bytes(b"%PDF-previous rejected output")
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
    assert not rejected.exists()
    profile = next(
        a.split("=", 1)[1] for a in calls[0] if a.startswith("--user-data-dir=")
    )
    assert not Path(profile).exists()


@pytest.mark.parametrize("pages", ["Pages: 2\n", "Pages: 0\n", "not a PDF"])
def test_pdf_overflow_or_invalid_readback_is_not_published(
    tmp_path, monkeypatch, pages
):
    html = tmp_path / "in.html"
    html.write_text("test", encoding="utf-8", newline="\n")
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
    assert (tmp_path / "out.rejected.pdf").read_bytes() == b"%PDF-test"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "in.html",
        "out.pdf",
        "out.rejected.pdf",
    ]


def _find_pdf_tools():
    chrome = next(
        (
            path
            for name in (
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
            )
            if (path := shutil.which(name))
        ),
        None,
    )
    pdfinfo = shutil.which("pdfinfo")
    if chrome is None or pdfinfo is None:
        if os.environ.get("ONEPAGER_REQUIRE_PDF") == "1":
            pytest.fail("PDF integration requires Chrome or Chromium and pdfinfo")
        pytest.skip("PDF integration requires Chrome or Chromium and pdfinfo")
    return {"chrome": chrome, "pdfinfo": pdfinfo}


@pytest.fixture
def pdf_tools():
    return _find_pdf_tools()


@pytest.mark.parametrize("ci", ["false", "true"])
def test_missing_pdf_tools_fail_when_required(monkeypatch, ci):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setenv("CI", ci)
    monkeypatch.setenv("ONEPAGER_REQUIRE_PDF", "1")
    try:
        with pytest.raises(pytest.fail.Exception, match="PDF integration requires"):
            _find_pdf_tools()
    except pytest.skip.Exception:
        pytest.fail("Required PDF tools were silently skipped")


@pytest.mark.parametrize("ci", ["false", "true"])
def test_missing_pdf_tools_skip_with_explicit_reason_when_optional(monkeypatch, ci):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setenv("CI", ci)
    monkeypatch.delenv("ONEPAGER_REQUIRE_PDF", raising=False)
    with pytest.raises(pytest.skip.Exception, match="PDF integration requires"):
        _find_pdf_tools()


def _pdf_page_count(pdf, pdfinfo):
    info = subprocess.run(
        [pdfinfo, str(pdf)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    pages = re.search(r"^Pages:\s+(\d+)\s*$", info.stdout, re.MULTILINE)
    assert pages is not None, info.stdout
    return int(pages.group(1))


@pytest.mark.integration
def test_worked_example_pdf_is_one_real_page(bundle, tmp_path, pdf_tools):
    html = tmp_path / "onepager.html"
    html.write_text(report.render_html(bundle, "001"), encoding="utf-8", newline="\n")
    pdf = tmp_path / "onepager.pdf"

    report.render_pdf(html, pdf, **pdf_tools)

    assert pdf.read_bytes().startswith(b"%PDF-")
    assert _pdf_page_count(pdf, pdf_tools["pdfinfo"]) == 1


@pytest.mark.integration
def test_make_pdf_target_is_one_real_page(tmp_path, pdf_tools):
    subprocess.run(
        [
            "make",
            "onepager",
            "OPERATOR=001",
            f"INPUT={(FIXTURES / 'worked_example.json').as_posix()}",
            f"OUTPUT={tmp_path.as_posix()}",
            f"ONEPAGER_PYTHON={Path(sys.executable).as_posix()}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=300,
    )
    pdf = tmp_path / "onepager.pdf"
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert _pdf_page_count(pdf, pdf_tools["pdfinfo"]) == 1


@pytest.mark.integration
def test_real_pdf_overflow_preserves_accepted_destination(bundle, tmp_path, pdf_tools):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle), encoding="utf-8", newline="\n")
    arguments = [
        "--input",
        source.as_posix(),
        "--operator",
        "001",
        "--output-dir",
        tmp_path.as_posix(),
        "--chrome",
        pdf_tools["chrome"],
        "--pdfinfo",
        pdf_tools["pdfinfo"],
    ]
    html = tmp_path / "onepager.html"
    pdf = tmp_path / "onepager.pdf"
    assert report.main(arguments) == 0
    accepted = pdf.read_bytes()
    accepted_html = html.read_bytes()

    bundle["operators"][0]["screen"]["method"] = "Synthetic screen evidence. " * 1000
    source.write_text(json.dumps(bundle), encoding="utf-8", newline="\n")
    with pytest.raises(SystemExit) as error:
        report.main(arguments)

    assert error.value.code == 1
    assert html.read_bytes() == accepted_html
    assert pdf.read_bytes() == accepted
    assert _pdf_page_count(pdf, pdf_tools["pdfinfo"]) == 1
    rejected = [path for path in tmp_path.glob("*.pdf") if path != pdf]
    assert len(rejected) == 1
    assert rejected[0].name == "onepager.rejected.pdf"
    assert _pdf_page_count(rejected[0], pdf_tools["pdfinfo"]) > 1
    assert not list(tmp_path.glob("onepager-build-*"))


def test_cli_html_only(bundle, tmp_path):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle), encoding="utf-8", newline="\n")
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
    assert (tmp_path / "onepager.preview.html").read_text(
        encoding="utf-8"
    ) == report.render_html(bundle, "001")
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
        encoding="utf-8",
        check=True,
    )
    assert "--html-only" in result.stdout
    assert (tmp_path / "onepager.preview.html").read_text(encoding="utf-8") == (
        FIXTURES / "worked_example.html"
    ).read_text(encoding="utf-8")


def test_invalid_input_and_missing_pdf_executable(bundle, tmp_path, monkeypatch):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle), encoding="utf-8", newline="\n")

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
    source.write_text("not-json", encoding="utf-8", newline="\n")
    with pytest.raises(SystemExit) as error:
        report.main(arguments)
    assert error.value.code == 1


def test_browser_timeout_fails_without_replacing_outputs(
    bundle, tmp_path, monkeypatch, capsys
):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle), encoding="utf-8", newline="\n")
    html = tmp_path / "onepager.html"
    html.write_text("previous accepted HTML", encoding="utf-8", newline="\n")
    pdf = tmp_path / "onepager.pdf"
    pdf.write_bytes(b"previous accepted PDF")
    calls = []

    def stalled(args, **kwargs):
        calls.append((args, kwargs))
        raise subprocess.TimeoutExpired(args, 120)

    monkeypatch.setattr(report.subprocess, "run", stalled)
    with pytest.raises(SystemExit) as error:
        report.main(
            [
                "--input",
                source.as_posix(),
                "--operator",
                "001",
                "--output-dir",
                tmp_path.as_posix(),
            ]
        )

    assert error.value.code == 1
    assert "timed out" in capsys.readouterr().err
    assert calls[0][1]["timeout"] == 120
    assert html.read_text(encoding="utf-8") == "previous accepted HTML"
    assert pdf.read_bytes() == b"previous accepted PDF"
    profile = next(
        a.split("=", 1)[1] for a in calls[0][0] if a.startswith("--user-data-dir=")
    )
    assert not Path(profile).exists()
    assert not list(tmp_path.glob("onepager-build-*"))


@pytest.mark.parametrize("contents", [b"", b"partial output", b"%PDF-partial"])
@pytest.mark.parametrize("failure", ["missing", "timeout", "nonzero", "readback"])
def test_failed_pdf_build_does_not_publish_rejection(
    tmp_path, monkeypatch, contents, failure
):
    html = tmp_path / "in.html"
    html.write_text("test", encoding="utf-8", newline="\n")
    pdf = tmp_path / "onepager.pdf"
    pdf.write_bytes(b"accepted PDF")
    rejected = pdf.with_suffix(".rejected.pdf")
    rejected.write_bytes(b"%PDF-previous rejection")

    def run(args, **kwargs):
        if args[0] == "chrome":
            candidate = Path(
                next(
                    a.split("=", 1)[1] for a in args if a.startswith("--print-to-pdf=")
                )
            )
            candidate.write_bytes(contents)
            if failure == "missing":
                raise FileNotFoundError("browser absent")
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 120)
            if failure == "nonzero":
                raise subprocess.CalledProcessError(1, args)
        else:
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(report.subprocess, "run", run)
    expected_error = {
        "missing": FileNotFoundError,
        "timeout": subprocess.TimeoutExpired,
        "nonzero": subprocess.CalledProcessError,
        "readback": (
            subprocess.CalledProcessError
            if contents.startswith(b"%PDF-")
            else ValueError
        ),
    }[failure]
    with pytest.raises(expected_error):
        report.render_pdf(html, pdf, chrome="chrome")
    assert pdf.read_bytes() == b"accepted PDF"
    assert rejected.read_bytes() == b"%PDF-previous rejection"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "in.html",
        "onepager.pdf",
        "onepager.rejected.pdf",
    ]


def test_html_preview_preserves_accepted_pair(bundle, tmp_path):
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(bundle), encoding="utf-8", newline="\n")
    html = tmp_path / "onepager.html"
    html.write_text("previous accepted HTML", encoding="utf-8", newline="\n")
    pdf = tmp_path / "onepager.pdf"
    pdf.write_bytes(b"previous accepted PDF")

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

    assert html.read_text(encoding="utf-8") == "previous accepted HTML"
    assert pdf.read_bytes() == b"previous accepted PDF"
    assert (tmp_path / "onepager.preview.html").read_text(
        encoding="utf-8"
    ) == report.render_html(bundle, "001")


@pytest.fixture
def onepager_ci():
    workflow = Path(__file__).parents[3] / ".github" / "workflows" / "ci.yml"
    return yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]


def _run_change_detector(
    onepager_ci, monkeypatch, tmp_path, paths, before="", after=""
):
    assert "operator-onepager-changes" in onepager_ci, "PDF changes must be scoped"
    step = next(
        step
        for step in onepager_ci["operator-onepager-changes"]["steps"]
        if step.get("id") == "paths"
    )
    payload = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    output = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", output.as_posix())
    monkeypatch.setenv("BASE_SHA", "base")
    monkeypatch.setenv("HEAD_SHA", "head")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.setenv(key, "inherited-binding")
    responses = {
        ("merge-base", "base", "head"): "ancestor\n",
        ("diff", "--no-renames", "--name-only", "-z", "ancestor", "head", "--"): (
            b"\0".join(path.encode("utf-8") for path in paths)
            + (b"\0" if paths else b"")
        ),
        ("show", "ancestor:Makefile"): before,
        ("show", "head:Makefile"): after,
        ("ls-tree", "--name-only", "ancestor", "--", "Makefile"): (
            "Makefile\n" if before is not None else ""
        ),
        ("ls-tree", "--name-only", "head", "--", "Makefile"): (
            "Makefile\n" if after is not None else ""
        ),
    }

    def git_output(command, **kwargs):
        assert command[0] == "git"
        assert not (
            {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"} & kwargs["env"].keys()
        )
        return responses[tuple(command[1:])]

    monkeypatch.setattr(subprocess, "check_output", git_output)
    exec(compile(payload, "<workflow-change-detector>", "exec"), {})
    return output.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize(
    "paths, expected",
    [
        ([], "required=false"),
        (["src/worldenergydata/analysis/operator_onepager.py"], "required=true"),
        (["tests/unit/analysis/test_operator_onepager.py"], "required=true"),
        (["tests/fixtures/operator_onepager/nested/input.json"], "required=true"),
        (["tests/fixtures/operator_onepager/line\nbreak.json"], "required=true"),
        (["docs/guide.md"], "required=false"),
        (["docs/space and $(false).md"], "required=false"),
        (["tests/fixtures/operator_onepager-other/input.json"], "required=false"),
    ],
)
def test_ci_detects_only_report_paths(
    onepager_ci, monkeypatch, tmp_path, paths, expected
):
    assert _run_change_detector(onepager_ci, monkeypatch, tmp_path, paths) == expected


@pytest.mark.parametrize(
    "change", ["unrelated", "variable", "recipe", "html_recipe", "prerequisite"]
)
def test_ci_detects_makefile_target_changes_only(
    onepager_ci, monkeypatch, tmp_path, change
):
    before = (
        "other:\n\techo old\nONEPAGER_PYTHON ?= python3\n"
        "onepager:\n\techo report\nonepager-html:\n\techo preview\n"
    )
    after = before.replace("echo old", "echo new")
    if change == "recipe":
        after = after.replace("echo report", "echo changed")
    elif change == "html_recipe":
        after = after.replace("echo preview", "echo changed")
    elif change == "variable":
        after = after.replace("?= python3", "?= python")
    elif change == "prerequisite":
        after = after.replace("onepager:", "onepager: input")
    assert _run_change_detector(
        onepager_ci, monkeypatch, tmp_path, ["Makefile"], before, after
    ) == ("required=false" if change == "unrelated" else "required=true")


@pytest.mark.parametrize("missing", ["base", "head"])
def test_ci_makefile_addition_or_removal_requires_pdf(
    onepager_ci, monkeypatch, tmp_path, missing
):
    before = None if missing == "base" else "onepager:\n\techo report\n"
    after = None if missing == "head" else "onepager:\n\techo report\n"
    assert (
        _run_change_detector(
            onepager_ci, monkeypatch, tmp_path, ["Makefile"], before, after
        )
        == "required=true"
    )


@pytest.mark.parametrize("outcome", ["passed", "skipped", "failure", "missing"])
def test_ci_requires_all_pdf_cases_to_run(onepager_ci, monkeypatch, tmp_path, outcome):
    steps = onepager_ci["operator-onepager-pdf"]["steps"]
    matches = [
        step for step in steps if step["name"] == "Verify required PDF test results"
    ]
    assert matches, "Required PDF cases must have recorded outcomes"
    payload = matches[0]["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    result = tmp_path / "results.xml"
    names = [
        "test_worked_example_pdf_is_one_real_page",
        "test_make_pdf_target_is_one_real_page",
        "test_real_pdf_overflow_preserves_accepted_destination",
    ]
    cases = "".join(f'<testcase name="{name}"/>' for name in names)
    if outcome == "missing":
        cases = cases.replace(f'<testcase name="{names[0]}"/>', "")
    elif outcome != "passed":
        cases = cases.replace(
            f'<testcase name="{names[0]}"/>',
            f'<testcase name="{names[0]}"><{outcome}/></testcase>',
        )
    result.write_text(f"<testsuite>{cases}</testsuite>", encoding="utf-8", newline="\n")
    monkeypatch.setenv("REPORT_XML", result.as_posix())
    if outcome == "passed":
        exec(compile(payload, "<workflow-pdf-results>", "exec"), {})
    else:
        with pytest.raises(SystemExit):
            exec(compile(payload, "<workflow-pdf-results>", "exec"), {})


def test_ci_detector_errors_do_not_report_irrelevant(
    onepager_ci, monkeypatch, tmp_path
):
    assert "operator-onepager-changes" in onepager_ci, "PDF changes must be scoped"
    step = next(
        step
        for step in onepager_ci["operator-onepager-changes"]["steps"]
        if step.get("id") == "paths"
    )
    payload = step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    output = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", output.as_posix())
    monkeypatch.setenv("BASE_SHA", "absent")
    monkeypatch.setenv("HEAD_SHA", "head")

    def failed_git(command, **kwargs):
        raise subprocess.CalledProcessError(128, command)

    monkeypatch.setattr(subprocess, "check_output", failed_git)
    with pytest.raises(subprocess.CalledProcessError):
        exec(compile(payload, "<workflow-change-detector>", "exec"), {})
    assert not output.exists()


@pytest.mark.parametrize(
    "domains, changes, required, pdf, succeeds",
    [
        ("success", "success", "true", "success", True),
        ("success", "success", "false", "skipped", True),
        ("success", "success", "true", "skipped", False),
        ("success", "success", "true", "failure", False),
        ("success", "success", "true", "cancelled", False),
        ("success", "success", "true", "", False),
        ("success", "failure", "false", "skipped", False),
        ("success", "skipped", "", "skipped", False),
        ("success", "cancelled", "", "skipped", False),
        ("success", "success", "", "skipped", False),
        ("success", "success", "false", "failure", False),
        ("success", "success", "false", "success", False),
        ("failure", "success", "false", "skipped", False),
        ("skipped", "success", "true", "success", False),
    ],
)
def test_ci_gate_accepts_only_explained_pdf_results(
    onepager_ci, domains, changes, required, pdf, succeeds
):
    step = next(
        step
        for step in onepager_ci["pr-gate"]["steps"]
        if step["name"] == "Gate on full result"
    )
    environment = os.environ.copy()
    environment.update(
        FULL_RESULT=domains,
        CHANGES_RESULT=changes,
        PDF_REQUIRED=required,
        PDF_RESULT=pdf,
    )
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert (result.returncode == 0) is succeeds, result.stdout + result.stderr


def test_ci_pdf_job_is_scoped_and_main_replay_is_preserved(onepager_ci):
    assert "operator-onepager-changes" in onepager_ci, "PDF changes must be scoped"
    detector = onepager_ci["operator-onepager-changes"]
    assert any(
        step.get("with", {}).get("fetch-depth") == 0 for step in detector["steps"]
    )
    pdf = onepager_ci["operator-onepager-pdf"]
    assert "operator-onepager-changes" in pdf["needs"]
    assert "needs.operator-onepager-changes.outputs.required == 'true'" in pdf["if"]
    assert pdf["runs-on"] == "ubuntu-latest"
    assert "operator-onepager-changes" in onepager_ci["pr-gate"]["needs"]
    assert set(onepager_ci["pr-gate"]["needs"]) == {
        "mode",
        "domain-tests",
        "operator-onepager-changes",
        "operator-onepager-pdf",
    }
    assert "!cancelled()" in onepager_ci["pr-gate"]["if"]
    assert "github.event_name == 'pull_request'" in onepager_ci["pr-gate"]["if"]
    assert "github.event_name" in detector["if"]
    assert "'pull_request'" in detector["if"]
    assert onepager_ci["pr-gate"]["runs-on"] == onepager_ci["mode"]["runs-on"]
    assert any(
        "REPLAY_RESULT" in step.get("env", {})
        for step in onepager_ci["pr-gate"]["steps"]
    )
    assert "test" not in onepager_ci, "The full matrix belongs to the daily workflow"
