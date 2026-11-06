"""Cross-builder regressions for the report export sweep (issue #1302)."""

import ast
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from worldenergydata.safety_analysis.risk_index import cli

# Issue #1302: generator-owned HTML must contain zero source lint markers.
_TEMPLATE_MODULES = [
    "packages/worldenergydata-reporting/src/worldenergydata/reporting/templates/plotly_report_template.py",
    "packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/cli.py",
    "packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_tables.py",
    "packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py",
    "packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_report.py",
    "packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/reporting.py",
]


@pytest.mark.parametrize("relative_path", _TEMPLATE_MODULES)
def test_report_builder_template_literals_are_clean(relative_path):
    """Inspect non-docstring literals without executing any engineering model."""
    repo = Path(__file__).resolve().parents[3]
    tree = ast.parse((repo / relative_path).read_text(encoding="utf-8"))
    _assert_template_literals_are_clean(tree, relative_path)


def _assert_template_literals_are_clean(tree, relative_path):
    """Ban lint markers in all string segments except actual docstrings."""
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and ast.get_docstring(node, clean=False) is not None
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            for marker in ("noqa", "pylint:", "type: ignore"):
                assert marker not in node.value, (relative_path, node.lineno, marker)


@pytest.mark.parametrize("marker", ["noqa", "pylint:", "type: ignore"])
def test_template_guard_allows_docstrings(marker):
    """Module, class, function and async-function documentation is not emitted."""
    source = f'''"""{marker}"""
class Example:
    """{marker}"""
    def render(self):
        """{marker}"""
        return "<p>example</p>"
async def build():
    """{marker}"""
    return "<p>example</p>"
'''
    _assert_template_literals_are_clean(ast.parse(source), "example.py")


@pytest.mark.parametrize("marker", ["noqa", "pylint:", "type: ignore"])
@pytest.mark.parametrize(
    "source",
    [
        'html = "<p>{marker}</p>"',
        'html = f"<p>{{value}}</p> {marker}"',
        'def render():\n    return None\n    "{marker}"',
    ],
)
def test_template_guard_rejects_non_docstring_markers(marker, source):
    """Ordinary and formatted strings, including later expressions, stay checked."""
    with pytest.raises(AssertionError):
        _assert_template_literals_are_clean(
            ast.parse(f'"""{marker}"""\n' + source.format(marker=marker)), "example.py"
        )


def test_risk_score_json_future_datetime_column_uses_iso(tmp_path, monkeypatch):
    """Schema-independent forward guard for possible future datetime columns.

    The current score records contain no dates. Injecting a datetime here
    checks future export compatibility, not a defect in today's score schema.
    Literal format example from pandas 2.3.3 to_json date_format/date_unit:

    https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.DataFrame.to_json.html
    Subtracting the synthetic +02:00 offset gives the hand-written UTC answer
    "2026-01-02T01:04:05.123Z"; NaT is null. Values are format examples only.
    This checks the actual CLI file, without loading external incident data.
    """
    import json

    records = [
        {"activity": "example", "date": pd.Timestamp("2026-01-02T03:04:05.123+02:00")},
        {"activity": "example", "date": pd.NaT},
    ]
    monkeypatch.setattr(cli, "_load_and_score", lambda _: (pd.DataFrame(), records))
    monkeypatch.setattr(cli, "_print_summary_table", lambda _: None)
    output = tmp_path / "scores"
    result = CliRunner().invoke(
        cli.app, ["export", "--format", "json", "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(output.with_suffix(".json").read_text(encoding="utf-8")) == [
        {"activity": "example", "date": "2026-01-02T01:04:05.123Z"},
        {"activity": "example", "date": None},
    ]
