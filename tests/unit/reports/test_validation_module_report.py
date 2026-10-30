"""Calculation anchors and consistency checks for the validation module report."""

import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "validation_module_report", ROOT / "scripts/build_validation_module_report.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
REBUILD = "PYTHONPATH=src uv run --no-project --with pandas --with PyYAML python scripts/build_validation_module_report.py"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.sections = []
        self.metrics = {}
        self.metric = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "section" and attrs.get("class") == "report-section":
            self.sections.append(attrs["id"])
        if "data-number" in attrs:
            self.metric = attrs["data-number"]

    def handle_data(self, data):
        if self.metric:
            self.metrics[self.metric] = float(data.replace("−", "-"))
            self.metric = None


@pytest.fixture
def result():
    return builder.calculate()


def test_hand_anchor_lower_boundary(result):
    # Published lower bound: 0. At x=0, 0 >= 0 and 0 <= 100: no errors.
    # Integers are exact; absolute tolerance is zero.
    case = result["cases"][1]
    assert case["value"] == 0
    assert case["errors"] == 0
    assert case["accepted"] is True


def test_hand_anchor_upper_boundary(result):
    # At x=100, 100 <= 100: inclusive module accepts. Public x < 100 rejects.
    # The acceptance mismatch count for this case is exactly one.
    case = result["cases"][4]
    assert case["value"] == 100
    assert case["errors"] == 0
    assert case["accepted"] is True
    assert case["reference_accepted"] is False
    assert result["disagreements"] == 1


def test_hand_anchor_counts(result):
    # Inputs -1,0,10,99,100,101: only -1 < 0 and 101 > 100 fail the module.
    # Six inputs less two rejects gives four accepts; two one-field errors.
    assert result["records"] == 6
    assert result["accepted"] == 4
    assert result["rejected"] == 2
    assert result["batch_errors"] == 2
    # One mismatch / six cases * 100 = 16 2/3 percent; display to 0.1 percent.
    assert result["disagreement_percent"] == pytest.approx(16.7, abs=0.05)


def test_worked_example_consistency(result):
    from worldenergydata.validation import DataValidator

    schema = builder.make_schema()
    for case in result["cases"]:
        accepted, errors = DataValidator(schema, strict=False).validate(
            {"value": case["value"]}
        )
        assert case["accepted"] == accepted
        assert case["errors"] == len(errors)
    accepted, errors = DataValidator(schema, strict=False).validate(
        [{"value": case["value"]} for case in result["cases"]]
    )
    assert accepted is False
    assert len(errors) == result["batch_errors"]
    assert [error.row_index for error in errors] == result["batch_error_rows"]


def test_rebuild_and_every_displayed_number_consistency(tmp_path, result):
    output = tmp_path / "report"
    builder.build(output)
    fresh = (output / "index.html").read_text(encoding="utf-8")
    stored = (builder.DEST / "index.html").read_text(encoding="utf-8")
    # No platform-dependent float strings: all calculation values use display digits.
    assert fresh == stored, f"Report changed. Rebuild with: {REBUILD}"
    assert (output / "changes.json").read_text(encoding="utf-8") == (
        builder.DEST / "changes.json"
    ).read_text(encoding="utf-8"), REBUILD
    page = Page()
    page.feed(fresh)
    expected = builder.report_numbers(result)
    assert page.metrics.keys() == expected.keys()
    for key, value in expected.items():
        assert page.metrics[key] == pytest.approx(value, abs=0.000001), key
    # Recompute the headline directly from the displayed inputs and displayed bounds.
    from worldenergydata.validation import DataValidator

    displayed_schema = builder.make_schema()
    displayed_schema.fields["value"].min_value = page.metrics["input-minimum"]
    displayed_schema.fields["value"].max_value = page.metrics["input-maximum"]
    displayed_accepts = sum(
        DataValidator(displayed_schema, strict=False).validate(
            {"value": page.metrics[f"case-{index}-value"]}
        )[0]
        for index in range(1, int(page.metrics["summary-records"]) + 1)
    )
    assert displayed_accepts == page.metrics["summary-accepted"]
    embedded = json.loads(
        re.search(
            r'<script id="calculation" type="application/json">(.*?)</script>',
            fresh,
            re.S,
        )[1]
    )
    assert embedded == result
    assert b"\r" not in (output / "index.html").read_bytes()
    assert b"\r" not in (output / "changes.json").read_bytes()


def test_structure_style_sources_and_public_text():
    html = (builder.DEST / "index.html").read_text(encoding="utf-8")
    page = Page()
    page.feed(html)
    assert len(page.sections) == 10
    assert len(page.ids) == len(set(page.ids))
    for link in page.links:
        if link.startswith("#"):
            assert link[1:] in page.ids, link
    assert '<body class="hs-doc">' in html
    assert builder.house_style() in html
    assert "Draft for maintainer review" in html
    assert "showSaveFilePicker" in html and "comments.json" in html
    assert 'id="changes"' in html and 'id="limit-chart"' in html
    assert 'data-limit="minimum"' in html and 'data-limit="maximum"' in html
    assert "<h4" not in html and "<strong" not in html
    assert not re.search(r"\b(could|should|would)\b", html, re.I)
    for source in builder.load_basis()["sources"]:
        assert source["http_status"] == 200
        assert source["url"] in html
        assert len(source["response_sha256"]) == 64


def test_evidence_and_calculation_source_fingerprints():
    basis = builder.load_basis()
    assert basis["existing_tests"]["passed"] == sum(
        item["passed"] for item in basis["existing_tests"]["files"]
    )
    for item in basis["existing_tests"]["files"]:
        assert builder.digest(ROOT / item["path"]) == item["sha256"], (
            "Test evidence is stale; rerun the recorded existing-test command, then "
            "refresh basis.json with its actual results before " + REBUILD
        )
    html = (builder.DEST / "index.html").read_text(encoding="utf-8")
    for path in builder.CALCULATION_SOURCES:
        assert builder.digest(ROOT / path) in html, REBUILD


def test_documented_interface_limits():
    from worldenergydata.validation import DataValidator
    from worldenergydata.validation.schema import DataType as AlternateType
    from worldenergydata.validation.schema import FieldSchema as AlternateField
    from worldenergydata.validation.schema import ValidationSchema as AlternateSchema
    from worldenergydata.validation.schemas import ValidationSchema

    alternate = AlternateSchema(name="AlternateNumeric")
    alternate.add_field(
        AlternateField(name="value", data_type=AlternateType.FLOAT, max_value=100)
    )
    # Alternate enumeration passes the .value type lookup but misses numeric dispatch.
    assert DataValidator(alternate, strict=False).validate({"value": 101})[0]
    generic = ValidationSchema(name="Generic")
    generic.add_field(builder.make_schema().fields["value"])
    assert generic.validate({"value": 101}).is_valid
    # The demonstrated schema does reject this same out-of-range number.
    assert not DataValidator(builder.make_schema(), strict=False).validate(
        {"value": 101}
    )[0]


def test_embedded_interaction_controls():
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable; embedded interaction checks require Node")
    completed = subprocess.run(
        [
            node,
            str(ROOT / "tests/unit/reports/validation_report_interactions.cjs"),
            str(builder.DEST / "index.html"),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr
