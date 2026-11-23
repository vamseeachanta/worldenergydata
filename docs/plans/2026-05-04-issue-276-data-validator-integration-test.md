# Plan: Issue #276 — Add integration test for DataValidator.generate_interactive_report

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/276
**Status:** plan-review
**Tier:** T1 (single test addition)

## Context
Phase 2B added 22 unit tests for `data_validator.py` but left `generate_interactive_report`
untested because it requires filesystem + Plotly rendering.

## Plan

### Task 1 — Locate the class and method
```bash
grep -n "generate_interactive_report" src/worldenergydata/common/validators/data_validator.py
```

### Task 2 — Add test to existing test file
File: `tests/unit/test_validators_data_validator.py`
Add class `TestGenerateInteractiveReport`:

```python
class TestGenerateInteractiveReport:
    def test_generates_html_file(self, tmp_path):
        # Arrange
        validator = DataValidator()
        results = validator.validate_dataframe(sample_df)  # use existing fixture
        output_path = tmp_path / "report.html"

        # Act
        validator.generate_interactive_report(results, output_path)

        # Assert
        assert output_path.exists()
        content = output_path.read_text()
        assert "<html" in content.lower()
        assert "Quality Score" in content or "quality" in content.lower()

    def test_report_contains_validation_data(self, tmp_path):
        validator = DataValidator()
        results = validator.validate_dataframe(sample_df)
        output_path = tmp_path / "report.html"
        validator.generate_interactive_report(results, output_path)
        content = output_path.read_text()
        # Should mention at least one column from sample_df
        assert any(col in content for col in sample_df.columns)
```

### Task 3 — Verify test passes
```bash
uv run pytest tests/unit/test_validators_data_validator.py::TestGenerateInteractiveReport -v
```

## Acceptance Criteria
- `TestGenerateInteractiveReport.test_generates_html_file` passes
- HTML file is written to `tmp_path` and contains `<html` marker
