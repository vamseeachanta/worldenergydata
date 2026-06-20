# ABOUTME: Integration test for DataValidator.generate_interactive_report (HTML output)
# ABOUTME: Exercises the real Plotly->HTML report writer and asserts the file + markers (#276)

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from validators.data_validator import DataValidator

# generate_interactive_report lazily imports plotly (see #277). Skip cleanly if
# the optional viz dependency is not installed in the test environment.
pytest.importorskip("plotly")


class TestGenerateInteractiveReport:
    def test_writes_html_file_with_expected_markers(self, tmp_path):
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

    def test_creates_parent_directory_if_missing(self, tmp_path):
        validator = DataValidator()
        df = pd.DataFrame({"id": [1, 2], "value": [1.0, 2.0]})
        results = validator.validate_dataframe(df, required_fields=["id"])

        # Nested output dir that does not yet exist
        output_path = tmp_path / "nested" / "out" / "report.html"
        validator.generate_interactive_report(results, output_path)

        assert output_path.exists()
        assert "<html" in output_path.read_text(encoding="utf-8").lower()
