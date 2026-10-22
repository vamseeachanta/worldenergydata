# ABOUTME: Integration test for DataValidator.generate_interactive_report (HTML output)
# ABOUTME: Exercises the real Plotly->HTML report writer and asserts the file + markers (#276)

import json
import os
import re
import sys
from html.parser import HTMLParser

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from validators.data_validator import DataValidator  # noqa: E402

# generate_interactive_report lazily imports plotly (see #277). Skip cleanly if
# the optional viz dependency is not installed in the test environment.
pytest.importorskip("plotly")


class BalancedReportParser(HTMLParser):
    """Check explicitly balanced tags and collect scripts without executing JS."""

    # WHATWG HTML, Syntax / Void elements (accessed 2026-10-22):
    # https://html.spec.whatwg.org/multipage/syntax.html#void-elements
    void_tags = set(
        "area base br col embed hr img input link meta source track wbr".split()
    )

    def __init__(self):
        super().__init__()
        self.stack = []
        self.scripts = []
        self.external_scripts = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_tags:
            self.stack.append(tag)
        if tag == "script":
            self.scripts.append("")
            self.external_scripts.extend(value for key, value in attrs if key == "src")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void_tags:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        assert self.stack and self.stack.pop() == tag, f"Unbalanced closing tag: {tag}"

    def handle_data(self, data):
        if self.stack and self.stack[-1] == "script":
            self.scripts[-1] += data


class TestGenerateInteractiveReport:
    def test_writes_html_file_with_expected_markers(self, tmp_path):
        """Independent arithmetic for a three-column synthetic frame.

        Source for the existing scoring policy: DataValidator.validate_dataframe,
        missing-data and type-issue branches (regression, not a qualified metric).
        One missing name in three rows gives round(1/3, 3) = 0.333. Only
        columns with missing data enter the mean, so 0.333 / 1 > 0.3 and
        the missing-data penalty is 40. One nonnumeric value costs 5.
        Required fields exist and IDs are unique: 100 - 40 - 5 = 55.
        The gauge must contain 55 and the summary must display "55.0/100".
        """
        validator = DataValidator()

        # A small DataFrame with a missing value and a non-numeric "value"
        # so the report renders the quality gauge, missing-data bar, and
        # type-issue bar (deterministic input).
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["a", None, "c"],
                "value": [10.0, 20.0, "bad"],
            }
        )
        results = validator.validate_dataframe(
            df, required_fields=["id", "name"], unique_field="id"
        )

        output_path = tmp_path / "report.html"
        validator.generate_interactive_report(results, output_path)

        # (a) the HTML file is created
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        html = output_path.read_text(encoding="utf-8")

        # (b) expected HTML markers
        assert "<html" in html.lower()
        # Plotly embeds its div/script into the page
        assert "plotly" in html.lower()
        # Report title set via fig.update_layout(title_text="Data Validation Report")
        assert "Data Validation Report" in html
        # Section / gauge title from the subplot
        assert "Quality Score" in html

        parser = BalancedReportParser()
        parser.feed(html)
        parser.close()
        assert not parser.stack
        assert not parser.external_scripts, "Plotly must be embedded for offline use"

        # Read the actual rendered figure rather than inspecting the input dict.
        pattern = re.compile(r'Plotly\.newPlot\(\s*"[^"]+",\s*')
        script = next(text for text in parser.scripts if pattern.search(text))
        match = pattern.search(script)
        traces, _ = json.JSONDecoder().raw_decode(script[match.end() :])
        indicator = next(trace for trace in traces if trace["type"] == "indicator")
        table = next(trace for trace in traces if trace["type"] == "table")
        assert indicator["value"] == 55
        assert "55.0/100" in table["cells"]["values"][1]

    def test_creates_parent_directory_if_missing(self, tmp_path):
        validator = DataValidator()
        df = pd.DataFrame({"id": [1, 2], "value": [1.0, 2.0]})
        results = validator.validate_dataframe(df, required_fields=["id"])

        # Nested output dir that does not yet exist
        output_path = tmp_path / "nested" / "out" / "report.html"
        validator.generate_interactive_report(results, output_path)

        assert output_path.exists()
        assert "<html" in output_path.read_text(encoding="utf-8").lower()
