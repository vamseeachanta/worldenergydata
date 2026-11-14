"""Citation-panel build gate required by issue #377, Acceptance criteria.

The worked cases use a synthetic YAML mapping and literal citation rows.
By inspection, ``field.amount`` exists and ``field.missing`` does not; each
required metadata cell must contain text. These are structural expectations,
with no engineering values, equations or acceptance tolerances.
"""

from types import SimpleNamespace

import pandas as pd
import pytest

REQUIRED_COLUMNS = ("input", "publisher", "code_id", "revision")


@pytest.fixture
def builder():
    from worldenergydata.lower_tertiary import comprehensive_report

    return comprehensive_report


@pytest.fixture(params=("render_markdown", "render_html"))
def render(builder, request):
    return getattr(builder, request.param)


@pytest.fixture
def citation_case(tmp_path, monkeypatch, builder):
    source = tmp_path / "source.yml"
    source.write_text("field:\n  amount: caller supplied\n", encoding="utf-8")
    monkeypatch.setattr(builder, "repository_root", lambda: tmp_path)
    row = {
        "input": "Synthetic input",
        "publisher": "Synthetic publisher",
        "code_id": "source.yml#field.amount",
        "revision": "Synthetic revision",
    }
    panel = pd.DataFrame(
        [row.copy(), row.copy()], index=["source", "calculation"], dtype=object
    )
    economics = SimpleNamespace(
        field_id="synthetic", citations=pd.DataFrame([row.copy()])
    )
    report = SimpleNamespace(
        economics_run=SimpleNamespace(results=[economics]),
        field_payloads={"synthetic": {}},
        revision_record={"revision": "A", "history": [{"revision": "A"}]},
    )
    monkeypatch.setattr(builder, "_report_citations", lambda result, econ: panel)
    return report, panel


def test_complete_rendered_panel_is_accepted(citation_case, builder):
    report, _ = citation_case
    builder._validate_report(report)


@pytest.mark.parametrize("column", REQUIRED_COLUMNS)
def test_missing_rendered_column_fails_before_writing(
    citation_case, tmp_path, column, render
):
    report, panel = citation_case
    panel.drop(columns=column, inplace=True)
    output = tmp_path / "output" / "report"
    with pytest.raises(ValueError, match=f"citation {column}"):
        render(report, output)
    assert not output.parent.exists()


@pytest.mark.parametrize("column", REQUIRED_COLUMNS)
@pytest.mark.parametrize("value", ["", " \t", None, pd.NA, float("nan"), False])
def test_invalid_rendered_metadata_fails_before_writing(
    citation_case, tmp_path, column, value, render
):
    report, panel = citation_case
    panel.loc["calculation", column] = value
    output = tmp_path / "output" / "report"
    with pytest.raises(ValueError, match=f"citation {column}"):
        render(report, output)
    assert not output.parent.exists()


def test_empty_rendered_panel_fails_before_writing(citation_case, tmp_path, render):
    report, panel = citation_case
    panel.drop(index=panel.index, inplace=True)
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="citations"):
        render(report, output)
    assert not output.exists()


def test_unresolved_later_reference_fails_before_writing(
    citation_case, tmp_path, render
):
    report, panel = citation_case
    panel.loc["calculation", "code_id"] = "source.yml#field.missing"
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="Unresolved citation"):
        render(report, output)
    assert not output.exists()


def test_upstream_citation_metadata_is_still_required(citation_case, builder):
    report, _ = citation_case
    economics = next(iter(report.economics_run.results))
    economics.citations["publisher"] = ""
    with pytest.raises(ValueError, match="citation publisher"):
        builder._validate_report(report)


def test_source_without_publisher_fails_before_writing(
    citation_case, tmp_path, monkeypatch, render, builder
):
    """A relative source URL has no publisher authority, by inspection."""
    report, _ = citation_case
    reference = {
        "id": "synthetic-reference",
        "title": "Synthetic document",
        "url": "relative-source",
        "retrieved": "not retrieved",
        "sha256": "Not established",
        "http_status": "not retrieved",
        "retrieval_status": "not retrieved",
    }
    rows = builder._citation_rows(
        {"sources": {"amount": [reference]}},
        "synthetic",
        "Synthetic input",
        "source.yml#field.amount",
        "Synthetic basis",
        "amount",
    )
    monkeypatch.setattr(
        builder, "_report_citations", lambda result, econ: pd.DataFrame(rows)
    )
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="citation publisher"):
        render(report, output)
    assert not output.exists()
