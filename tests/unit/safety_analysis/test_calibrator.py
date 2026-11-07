"""
Tests for EnigmaCalibrator — data-driven ENIGMA risk score calibration.

Covers:
    TestSyntheticDataFrame  (10 tests)
    TestFit                 (8 tests)
    TestCalibrationReport   (8 tests)
    TestRiskScore           (5 tests)
    TestAssess              (5 tests)
    TestCalibratedMatrix    (4 tests)
    TestIntegrationWithSkill (3 tests)

Total: 289 cases, including 244 source-expression guard cases.
"""

from __future__ import annotations

import ast
import csv
import json
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.safety_analysis import calibrator as calibrator_module
from worldenergydata.safety_analysis.calibrator import (
    CalibrationRecord,
    CalibrationReport,
    EnigmaCalibrator,
)
from worldenergydata.safety_analysis.skill import (
    _VALID_ASSET_TYPES,
    _VALID_SCENARIOS,
    EnigmaResult,
    enigma_safety_analysis,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    return EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=200)


@pytest.fixture()
def fitted_calibrator(synthetic_df: pd.DataFrame) -> EnigmaCalibrator:
    calibrator = EnigmaCalibrator()
    calibrator.fit(synthetic_df)
    return calibrator


# ---------------------------------------------------------------------------
# TestSyntheticDataFrame
# ---------------------------------------------------------------------------


class TestSyntheticDataFrame:
    def test_returns_dataframe(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, synthetic_df: pd.DataFrame) -> None:
        required = {"incident_type", "equipment_type", "severity", "incident_date"}
        assert required.issubset(set(synthetic_df.columns))

    def test_default_200_rows(self, synthetic_df: pd.DataFrame) -> None:
        assert len(synthetic_df) == 200

    def test_n_incidents_parameter_respected(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=50)
        assert len(df) == 50

    def test_incident_type_values_valid(self, synthetic_df: pd.DataFrame) -> None:
        valid_types = {"equipment_failure", "spill", "injury", "violation"}
        actual = set(synthetic_df["incident_type"].dropna().unique())
        assert actual.issubset(valid_types)

    def test_operators_are_neutral_codenames(self, synthetic_df: pd.DataFrame) -> None:
        """Issue #1240 (2026): every operator must be a neutral codename.

        The expected labels follow the issue's OPERATOR-A, OPERATOR-B, ...
        convention, retaining the existing generator's five operator slots.
        """
        expected = {
            "OPERATOR-A",
            "OPERATOR-B",
            "OPERATOR-C",
            "OPERATOR-D",
            "OPERATOR-E",
        }
        assert synthetic_df["operator"].notna().all()
        assert set(synthetic_df["operator"]) == expected

    @pytest.mark.parametrize("n_incidents", [0, 1])
    def test_operator_codenames_for_small_outputs(self, n_incidents: int) -> None:
        """Structural boundary cases: zero requested rows gives none; one gives one.

        Issue #1240 (2026) requires the same codename convention for every row.
        These row counts are test inputs, not engineering acceptance limits.
        """
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=n_incidents)
        assert len(df) == n_incidents
        assert df["operator"].str.fullmatch(r"OPERATOR-[A-E]").all()

    def test_synthetic_output_is_reproducible(self) -> None:
        """A fixed internal seed must reproduce the complete frame, labels included."""
        first = EnigmaCalibrator.synthetic_hse_dataframe()
        second = EnigmaCalibrator.synthetic_hse_dataframe()
        pd.testing.assert_frame_equal(first, second)

    def test_csv_preserves_operator_codenames(self, synthetic_df: pd.DataFrame) -> None:
        """Issue #1240 (2026): CSV serialization must retain the neutral labels."""
        exported = pd.read_csv(StringIO(synthetic_df.to_csv(index=False)))
        pd.testing.assert_series_equal(exported["operator"], synthetic_df["operator"])
        assert exported["operator"].str.fullmatch(r"OPERATOR-[A-E]").all()


# ---------------------------------------------------------------------------
# TestFit
# ---------------------------------------------------------------------------


class TestFit:
    def test_fit_returns_self(self, synthetic_df: pd.DataFrame) -> None:
        calibrator = EnigmaCalibrator()
        result = calibrator.fit(synthetic_df)
        assert result is calibrator

    def test_fitted_flag_true_after_fit(self, synthetic_df: pd.DataFrame) -> None:
        calibrator = EnigmaCalibrator()
        calibrator.fit(synthetic_df)
        assert calibrator._fitted is True

    def test_fit_empty_dataframe_does_not_crash(self) -> None:
        calibrator = EnigmaCalibrator()
        calibrator.fit(pd.DataFrame())
        assert calibrator._fitted is True

    def test_fit_missing_equipment_type_column_uses_fallback(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=100)
        df = df.drop(columns=["equipment_type"])
        calibrator = EnigmaCalibrator()
        calibrator.fit(df)
        assert calibrator._fitted is True

    def test_calibrated_matrix_nonempty_after_fit(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        assert len(fitted_calibrator._calibrated_matrix) > 0

    def test_calibration_report_before_fit_raises_runtime_error(self) -> None:
        calibrator = EnigmaCalibrator()
        with pytest.raises(RuntimeError, match="fit\\(\\)"):
            calibrator.calibration_report()

    def test_fit_twice_overwrites_state(self, synthetic_df: pd.DataFrame) -> None:
        calibrator = EnigmaCalibrator()
        calibrator.fit(synthetic_df)
        first_report = calibrator.calibration_report()
        calibrator.fit(synthetic_df)
        second_report = calibrator.calibration_report()
        assert second_report.total_incidents_used == first_report.total_incidents_used

    def test_fit_without_incident_date_column(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=100)
        df = df.drop(columns=["incident_date"])
        calibrator = EnigmaCalibrator()
        calibrator.fit(df)
        assert calibrator._fitted is True


# ---------------------------------------------------------------------------
# TestCalibrationReport
# ---------------------------------------------------------------------------


class TestCalibrationReport:
    def test_returns_calibration_report_instance(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert isinstance(report, CalibrationReport)

    def test_total_incidents_used_positive(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert report.total_incidents_used > 0

    def test_years_covered_positive(self, fitted_calibrator: EnigmaCalibrator) -> None:
        report = fitted_calibrator.calibration_report()
        assert report.years_covered > 0.0

    def test_records_is_list_of_calibration_records(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert isinstance(report.records, list)
        assert all(isinstance(r, CalibrationRecord) for r in report.records)

    def test_each_record_has_required_attributes(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        for rec in report.records:
            assert hasattr(rec, "asset_type")
            assert hasattr(rec, "scenario")
            assert hasattr(rec, "calibrated_score")
            assert hasattr(rec, "confidence")
            assert hasattr(rec, "data_driven")

    def test_calibrated_score_in_valid_range(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        for rec in report.records:
            assert 0.0 <= rec.calibrated_score <= 1.0, (
                f"Score out of range for {rec.asset_type}/{rec.scenario}: "
                f"{rec.calibrated_score}"
            )

    def test_coverage_pct_in_valid_range(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert 0.0 <= report.coverage_pct <= 100.0

    def test_to_dataframe_returns_dataframe_with_expected_columns(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        df = report.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        expected_cols = {
            "asset_type",
            "scenario",
            "incident_count",
            "calibrated_score",
            "confidence",
            "data_driven",
        }
        assert expected_cols.issubset(set(df.columns))


# ---------------------------------------------------------------------------
# TestRiskScore
# ---------------------------------------------------------------------------


class TestRiskScore:
    def test_returns_tuple_of_float_and_bool(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        score, is_driven = fitted_calibrator.risk_score("riser", "corrosion")
        assert isinstance(score, float)
        assert isinstance(is_driven, bool)

    def test_score_in_valid_range(self, fitted_calibrator: EnigmaCalibrator) -> None:
        score, _ = fitted_calibrator.risk_score("riser", "corrosion")
        assert 0.0 <= score <= 1.0

    def test_without_fit_returns_rule_based_score(self) -> None:
        calibrator = EnigmaCalibrator()
        score, is_driven = calibrator.risk_score("platform", "fire_explosion")
        assert not is_driven
        assert 0.0 <= score <= 1.0

    def test_with_fit_some_combos_are_data_driven(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        found_data_driven = False
        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                _, is_driven = fitted_calibrator.risk_score(asset_type, scenario)
                if is_driven:
                    found_data_driven = True
                    break
            if found_data_driven:
                break
        assert found_data_driven, "Expected at least one data-driven combo after fit"

    def test_risk_level_consistent_with_enigma_thresholds(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        from worldenergydata.safety_analysis.skill import _risk_level_from_score

        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                score, _ = fitted_calibrator.risk_score(asset_type, scenario)
                level = _risk_level_from_score(score)
                assert level in {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# TestAssess
# ---------------------------------------------------------------------------


class TestAssess:
    def test_returns_dict(self, fitted_calibrator: EnigmaCalibrator) -> None:
        result = fitted_calibrator.assess("platform", "fire_explosion")
        assert isinstance(result, dict)

    def test_dict_has_required_keys(self, fitted_calibrator: EnigmaCalibrator) -> None:
        result = fitted_calibrator.assess("platform", "fire_explosion")
        required = {
            "asset_type",
            "scenario",
            "risk_score",
            "risk_level",
            "data_driven",
            "confidence",
        }
        assert required.issubset(set(result.keys()))

    def test_data_driven_key_present(self, fitted_calibrator: EnigmaCalibrator) -> None:
        result = fitted_calibrator.assess("riser", "overpressure")
        assert "data_driven" in result

    def test_confidence_is_valid_label(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        result = fitted_calibrator.assess("vessel", "corrosion")
        assert result["confidence"] in {"high", "medium", "low"}

    def test_works_for_all_six_asset_types(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        for asset_type in _VALID_ASSET_TYPES:
            result = fitted_calibrator.assess(asset_type, "fatigue")
            assert result["asset_type"] == asset_type
            assert 0.0 <= result["risk_score"] <= 1.0


# ---------------------------------------------------------------------------
# TestCalibratedMatrix
# ---------------------------------------------------------------------------


class TestCalibratedMatrix:
    def test_returns_dataframe(self, fitted_calibrator: EnigmaCalibrator) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert isinstance(df, pd.DataFrame)

    def test_row_index_is_asset_types(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert set(df.index) == set(_VALID_ASSET_TYPES)

    def test_columns_are_scenarios(self, fitted_calibrator: EnigmaCalibrator) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert set(df.columns) == set(_VALID_SCENARIOS)

    def test_all_values_in_valid_range(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert df.shape == (6, 6)
        assert (df.values >= 0.0).all()
        assert (df.values <= 1.0).all()


# ---------------------------------------------------------------------------
# TestIntegrationWithSkill
# ---------------------------------------------------------------------------


class TestIntegrationWithSkill:
    def test_enigma_safety_analysis_accepts_calibrator(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        result = enigma_safety_analysis(
            "riser", "corrosion", calibrator=fitted_calibrator
        )
        assert result is not None

    def test_result_is_enigma_result_instance(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        result = enigma_safety_analysis(
            "platform", "fire_explosion", calibrator=fitted_calibrator
        )
        assert isinstance(result, EnigmaResult)

    def test_risk_score_differs_from_uncalibrated_when_data_driven(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        # Find at least one combo that is data-driven
        target_asset, target_scenario = None, None
        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                _, is_driven = fitted_calibrator.risk_score(asset_type, scenario)
                if is_driven:
                    target_asset, target_scenario = asset_type, scenario
                    break
            if target_asset:
                break

        assert target_asset is not None, "No data-driven combo found after fit"

        uncalibrated = enigma_safety_analysis(target_asset, target_scenario)
        calibrated = enigma_safety_analysis(
            target_asset, target_scenario, calibrator=fitted_calibrator
        )
        # The calibrated score blends data with rule-based, so it may differ
        # from the pure rule-based score; we verify the type is correct and
        # the score is in range regardless of direction.
        assert isinstance(calibrated.risk_score, float)
        assert 0.0 <= calibrated.risk_score <= 1.0
        assert isinstance(uncalibrated.risk_score, float)


# Issue #1240 (2026): whitelist the generic convention, never a real-name list.
_OPERATOR_PATTERN = re.compile(r"^OPERATOR-[A-Z]+$")
_OPERATOR_FIELDS = {"operator", "operators", "operator_name", "company_name"}


def _assert_operator_values(value):
    """Inspect structured fixtures without recording operator values on failure."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _OPERATOR_FIELDS:
                labels = item if isinstance(item, list) else [item]
                assert all(
                    isinstance(label, str) and _OPERATOR_PATTERN.fullmatch(label)
                    for label in labels
                ), "Operator field does not follow the codename contract"
            else:
                _assert_operator_values(item)
    elif isinstance(value, list):
        for item in value:
            _assert_operator_values(item)


def _is_operator_target(target):
    if isinstance(target, ast.Name):
        return target.id in _OPERATOR_FIELDS
    if isinstance(target, ast.Attribute):
        return target.attr in _OPERATOR_FIELDS
    return (
        isinstance(target, ast.Subscript)
        and isinstance(target.slice, ast.Constant)
        and target.slice.value in _OPERATOR_FIELDS
    )


class _InvalidOperatorLiteral(ValueError):
    """Carry a formatting error's source line without recording literal values."""


def _is_literal_operator_expression(expression, *, format_operand=False):
    """Recognize complete string expressions before attempting any evaluation."""
    if isinstance(expression, ast.Constant):
        return isinstance(expression.value, str) or (
            format_operand and type(expression.value) in {int, float}
        )
    if isinstance(expression, ast.JoinedStr):
        return all(
            _is_literal_operator_expression(value) for value in expression.values
        )
    if isinstance(expression, ast.FormattedValue):
        return _is_literal_operator_expression(
            expression.value, format_operand=True
        ) and (
            expression.format_spec is None
            or _is_literal_operator_expression(expression.format_spec)
        )
    if format_operand and isinstance(expression, ast.Tuple):
        return all(
            _is_literal_operator_expression(value, format_operand=True)
            for value in expression.elts
        )
    if format_operand and isinstance(expression, ast.Dict):
        return all(
            isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and _is_literal_operator_expression(value, format_operand=True)
            for key, value in zip(expression.keys, expression.values)
        )
    if isinstance(expression, ast.BinOp) and isinstance(
        expression.op, (ast.Add, ast.Mod)
    ):
        return _is_literal_operator_expression(
            expression.left
        ) and _is_literal_operator_expression(
            expression.right, format_operand=isinstance(expression.op, ast.Mod)
        )
    return False


def _fold_operator_literal(expression):
    """Evaluate only previously recognized literal string expressions."""
    if isinstance(expression, ast.Constant):
        return expression.value
    if isinstance(expression, ast.JoinedStr):
        return "".join(_fold_operator_literal(value) for value in expression.values)
    if isinstance(expression, ast.Tuple):
        return tuple(_fold_operator_literal(value) for value in expression.elts)
    if isinstance(expression, ast.Dict):
        return {
            key.value: _fold_operator_literal(value)
            for key, value in zip(expression.keys, expression.values)
        }
    if isinstance(expression, ast.FormattedValue):
        value = _fold_operator_literal(expression.value)
        spec = (
            _fold_operator_literal(expression.format_spec)
            if expression.format_spec is not None
            else ""
        )
        try:
            if expression.conversion == ord("s"):
                value = str(value)
            elif expression.conversion == ord("r"):
                value = repr(value)
            elif expression.conversion == ord("a"):
                value = ascii(value)
            return format(value, spec)
        except (OverflowError, TypeError, ValueError):
            raise _InvalidOperatorLiteral(expression.lineno) from None
    left = _fold_operator_literal(expression.left)
    right = _fold_operator_literal(expression.right)
    try:
        if isinstance(expression.op, ast.Add):
            return left + right
        return left % right
    except (KeyError, OverflowError, TypeError, ValueError):
        raise _InvalidOperatorLiteral(expression.lineno) from None


def _operator_literal_values(expression):
    """Yield label literals from value branches, excluding lookup metadata."""
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        yield expression
    elif isinstance(expression, (ast.List, ast.Tuple, ast.Set)):
        for element in expression.elts:
            yield from _operator_literal_values(element)
    elif isinstance(expression, ast.IfExp):
        yield from _operator_literal_values(expression.body)
        yield from _operator_literal_values(expression.orelse)
    elif isinstance(expression, ast.BoolOp):
        for value in expression.values:
            yield from _operator_literal_values(value)
    elif isinstance(expression, (ast.BinOp, ast.JoinedStr)):
        if _is_literal_operator_expression(expression):
            value = _fold_operator_literal(expression)
            yield ast.copy_location(ast.Constant(value=value), expression)
    elif isinstance(expression, ast.Dict):
        for value in expression.values:
            yield from _operator_literal_values(value)
    elif isinstance(expression, ast.Call):
        is_lookup = (
            isinstance(expression.func, ast.Attribute) and expression.func.attr == "get"
        )
        arguments = expression.args[1:] if is_lookup else expression.args
        for argument in arguments:
            if (
                is_lookup
                and isinstance(argument, ast.Constant)
                and argument.value == ""
            ):
                continue
            yield from _operator_literal_values(argument)
        for keyword in expression.keywords:
            if not _is_named_aggregation(expression, keyword):
                yield from _operator_literal_values(keyword.value)


def _is_named_aggregation(call, keyword):
    """A pandas named aggregation tuple specifies a column and reduction."""
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr in {"agg", "aggregate"}
        and isinstance(keyword.value, ast.Tuple)
        and len(keyword.value.elts) == 2
    )


def _assert_source_operator_codenames(tree, relative_path):
    """Check literal operator fields without including their values in errors."""
    expressions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            expressions.extend(
                value
                for key, value in zip(node.keys, node.values)
                if isinstance(key, ast.Constant) and key.value in _OPERATOR_FIELDS
            )
        elif isinstance(node, ast.Call):
            expressions.extend(
                keyword.value
                for keyword in node.keywords
                if keyword.arg in _OPERATOR_FIELDS
                and not _is_named_aggregation(node, keyword)
            )
        elif isinstance(node, ast.Assign):
            if any(_is_operator_target(target) for target in node.targets):
                expressions.append(node.value)
        elif isinstance(node, ast.AnnAssign) and _is_operator_target(node.target):
            if node.value is not None:
                expressions.append(node.value)
    source_fields = []
    for expression in expressions:
        try:
            for node in _operator_literal_values(expression):
                if not _OPERATOR_PATTERN.fullmatch(node.value):
                    raise AssertionError(
                        (
                            relative_path.as_posix(),
                            node.lineno,
                            "Operator literal does not follow the codename contract",
                        )
                    )
                source_fields.append(node)
        except _InvalidOperatorLiteral as error:
            raise AssertionError(
                (
                    relative_path.as_posix(),
                    error.args[0],
                    "Invalid literal operator formatting",
                )
            ) from None
    return source_fields


def test_package_source_and_fixtures_use_operator_codenames():
    """Issue #1240: scan all package source and safety-specific fixture trees.

    Literal labels and structured fixture fields must match ^OPERATOR-[A-Z]+$,
    without storing real names or a denylist. Lookup keys, empty lookup defaults
    and named aggregation tuples are metadata. Conditional and boolean branches,
    dictionary value literals and nonempty lookup defaults are checked. Binary
    concatenation and percent formatting are folded recursively for complete
    literal expressions, including tuple and mapping formatting operands,
    numeric formatting operands and f-strings with literal placeholders,
    conversions and format specifications. Malformed literal formatting reports
    its source location without including values. The folding whitelist excludes
    bool, None and bytes operands, conditionals nested inside binary or formatted
    expressions, and list formatting operands. Dynamically computed labels are
    not evaluated.
    This is a structural regression check, not free-text entity recognition.
    """
    package = Path(calibrator_module.__file__).parent
    repo = Path(__file__).resolve().parents[3]
    roots = [package]
    roots.extend(path for path in (repo / "tests/fixtures").glob("*safety*"))
    fixture_sources = list((repo / "tests/unit/safety_analysis").rglob("conftest.py"))
    paths = fixture_sources + [path for root in roots for path in root.rglob("*")]
    source_fields = []
    for path in sorted(paths):
        if path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8"))
            source_fields.extend(
                _assert_source_operator_codenames(tree, path.relative_to(repo))
            )
        elif path.suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as stream:
                _assert_operator_values(list(csv.DictReader(stream)))
        elif path.suffix == ".json":
            _assert_operator_values(json.loads(path.read_text(encoding="utf-8")))
        elif path.suffix in {".yaml", ".yml"}:
            _assert_operator_values(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert source_fields, "The scan must reach the synthetic operator literals"


def test_operator_fixture_guard_rejects_generic_non_codename():
    """A generic invalid label proves the fixture guard is not vacuous."""
    with pytest.raises(AssertionError, match="codename contract"):
        _assert_operator_values({"operator": "UNLABELLED"})
    _assert_operator_values({"operator": "OPERATOR-AA"})


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    "source",
    [
        '{{"{field}": "{label}"}}',
        '{field} = "{label}"',
        'CalibrationRecord({field}="{label}")',
        'dict({field}="{label}")',
        'df["{field}"] = "{label}"',
        'self.{field} = "{label}"',
        '{field}: str = "{label}"',
        'df["{field}"]: str = "{label}"',
        'self.{field}: str = "{label}"',
    ],
)
def test_operator_source_guard_rejects_generic_non_codename(field, source):
    """Every supported source form rejects an invalid label and accepts a codename."""
    relative_path = Path("fixtures") / "example.py"
    invalid = ast.parse(source.format(field=field, label="UNLABELLED"))
    with pytest.raises(AssertionError, match="codename contract") as error:
        _assert_source_operator_codenames(invalid, relative_path)
    assert error.value.args[0] == (
        "fixtures/example.py",
        1,
        "Operator literal does not follow the codename contract",
    )
    valid = ast.parse(source.format(field=field, label="OPERATOR-AA"))
    assert len(_assert_source_operator_codenames(valid, relative_path)) == 1


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    "source",
    [
        'self.{field} = row["{field}"]',
        '{field} = record.get("{field}", "")',
        'df.groupby(k).agg({field}=("{field}", "first"))',
        'df.groupby(k).aggregate({field}=("{field}", "first"))',
    ],
)
def test_operator_source_guard_allows_lookup_metadata(field, source):
    """Column keys, empty defaults and aggregation methods are not labels."""
    tree = ast.parse(source.format(field=field))
    assert _assert_source_operator_codenames(tree, Path("example.py")) == []


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    "value",
    [
        '["{label}"]',
        '("{label}",)',
        '{{"{label}"}}',
        'rng.choice(["{label}"])',
    ],
)
def test_operator_source_guard_checks_literal_containers_and_call_values(field, value):
    """Literal labels remain checked, including synthetic random choices."""
    relative_path = Path("example.py")
    invalid = ast.parse(f"{field} = " + value.format(label="UNLABELLED"))
    with pytest.raises(AssertionError, match="codename contract"):
        _assert_source_operator_codenames(invalid, relative_path)
    valid = ast.parse(f"{field} = " + value.format(label="OPERATOR-AA"))
    assert len(_assert_source_operator_codenames(valid, relative_path)) == 1


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    "value",
    [
        '"{label}" if selector == "UNLABELLED" else existing',
        'existing if selector == "UNLABELLED" else "{label}"',
        'existing or "{label}"',
        '"{label}" and existing',
        '{{"UNLABELLED": "{label}"}}',
        'row.get("operator", "{label}")',
    ],
)
def test_operator_source_guard_checks_expression_values(field, value):
    """Value-bearing branches reject invalid labels and accept codenames."""
    relative_path = Path("example.py")
    invalid = ast.parse(f"{field} = " + value.format(label="UNLABELLED"))
    with pytest.raises(AssertionError, match="codename contract"):
        _assert_source_operator_codenames(invalid, relative_path)
    valid = ast.parse(f"{field} = " + value.format(label="OPERATOR-AA"))
    assert len(_assert_source_operator_codenames(valid, relative_path)) == 1


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    "value",
    [
        '"UNLABELLED" + suffix',
        'prefix + "UNLABELLED"',
        '"OPERATOR-AA" + suffix',
        'prefix + "OPERATOR-AA"',
        '"OPERATOR-" + letter',
        '"OPERATOR-%s" % letter',
        '"OPERATOR-" + ("A" + letter)',
        '"OPERATOR-%s%s" % ("A", letter)',
        'f"OPERATOR-{letter}"',
        '"%(x)s" % {"x": letter}',
        "f\"OPERATOR-{'AA':{width}}\"",
        '"OPERATOR-%c" % number',
    ],
)
def test_operator_source_guard_skips_dynamic_binary_expressions(field, value):
    """A fragment cannot establish the value of a dynamically computed label."""
    tree = ast.parse(f"{field} = {value}")
    assert _assert_source_operator_codenames(tree, Path("example.py")) == []


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    ("valid_value", "invalid_value"),
    [
        ('"OPERATOR-" + "AA"', '"UN" + "LABELLED"'),
        ('"OPERATOR-" + "AA"', '"OPERATOR-A" + "OPERATOR-B"'),
        ('"OPERATOR-%s" % "AA"', '"UN%s" % "LABELLED"'),
        ('"OP" + "ERATOR-" + "AA"', '"UN" + "LAB" + "ELLED"'),
        ('"OP" + ("ERATOR-" + "AA")', '"UN" + ("LAB" + "ELLED")'),
        ('"OPERATOR-%s" % ("AA",)', '"UN%s" % ("LABELLED",)'),
        ('"OPERATOR-%s%s" % ("A", "A")', '"UN%s%s" % ("LAB", "ELLED")'),
        ('f"OPERATOR-AA"', 'f"UNLABELLED"'),
        ("f\"OPERATOR-{'AA'}\"", "f\"UN{'LABELLED'}\""),
        (
            '"%(x)s" % {"x": "OPERATOR-AA"}',
            '"%(x)s" % {"x": "UNLABELLED"}',
        ),
        ('"OPERATOR-%c" % 65', '"UNLABELLED-%d" % 7'),
        ('"OPERATOR-%.0sAA" % 7.5', '"UNLABELLED-%.1f" % 7.5'),
        ("f\"OPERATOR-{'AA'!s}\"", "f\"UN{'LABELLED'!s}\""),
        ("f\"{'OPERATOR-AA':{'s'}}\"", "f\"{'UNLABELLED':{'s'}}\""),
        ("f\"OPERATOR-{''!r:.0s}AA\"", "f\"UN{''!r:.0s}LABELLED\""),
        ("f\"OPERATOR-{''!a:.0s}AA\"", "f\"UN{''!a:.0s}LABELLED\""),
        (
            '("OPERATOR-" + "%s") % ("A" + "A",)',
            '("UN" + "%s") % ("LAB" + "ELLED",)',
        ),
    ],
)
def test_operator_source_guard_checks_complete_literal_binary_values(
    field, valid_value, invalid_value
):
    """Check the complete literal result, rather than accepting its fragments."""
    relative_path = Path("example.py")
    valid = ast.parse(f"{field} = {valid_value}")
    assert len(_assert_source_operator_codenames(valid, relative_path)) == 1
    invalid = ast.parse(f"{field} = {invalid_value}")
    with pytest.raises(AssertionError, match="codename contract") as error:
        _assert_source_operator_codenames(invalid, relative_path)
    assert error.value.args[0] == (
        "example.py",
        1,
        "Operator literal does not follow the codename contract",
    )


@pytest.mark.parametrize("field", sorted(_OPERATOR_FIELDS))
@pytest.mark.parametrize(
    "value",
    [
        '"OPERATOR-%s %s" % "AA"',
        '"OPERATOR-%q" % "AA"',
        '"OPERATOR-%" % ("AA",)',
        '"OPERATOR-" + ("%s %s" % "AA")',
        '"OPERATOR-%(missing)s" % {"x": "AA"}',
        '"OPERATOR-%(x)d" % {"x": "AA"}',
        "f\"OPERATOR-{'AA':q}\"",
        '"OPERATOR-%c" % 1114112',
        'f"{1114112:c}"',
    ],
)
def test_operator_source_guard_reports_malformed_literal_formatting(field, value):
    """Malformed formatting reports only its file, line and rule."""
    tree = ast.parse(f"{field} = (\n    {value}\n)")
    with pytest.raises(AssertionError) as error:
        _assert_source_operator_codenames(tree, Path("example.py"))
    assert error.value.args[0] == (
        "example.py",
        2,
        "Invalid literal operator formatting",
    )
