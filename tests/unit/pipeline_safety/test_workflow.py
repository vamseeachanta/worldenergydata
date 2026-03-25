# ABOUTME: Tests for PipelineSafetyWorkflow FFS assessment module.
# ABOUTME: Covers PipelineDefect characterization, FFSResult, verdicts, and reporting.

"""
Tests for worldenergydata.pipeline_safety.workflow

Covers:
- PipelineDefect dataclass field presence and correctness
- FFSResult dataclass field presence and correctness
- characterize() conversion from PHMSA incident dict
- assess_ffs() Modified B31G and original B31G methods
- Verdict logic: accept / monitor / repair / replace
- One-call assess() shortcut
- generate_report() batch DataFrame output
- verdict_summary() counts
- case_study_narrative() content checks
- Folias factor calculation
- Safety factor application
- Remaining life estimation
"""

import math

import pandas as pd
import pytest

from worldenergydata.pipeline_safety.workflow import (
    FFSResult,
    PipelineDefect,
    PipelineSafetyWorkflow,
    _failure_pressure_b31g,
    _failure_pressure_modified_b31g,
    _folias_factor,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workflow():
    return PipelineSafetyWorkflow()


@pytest.fixture()
def minimal_incident():
    """Minimal PHMSA-style incident dict with explicit geometry."""
    return {
        "incident_id": "TEST-001",
        "year": 2020,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 30.0,
        "length_mm": 150.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TX-A",
    }


@pytest.fixture()
def shallow_incident():
    """Shallow corrosion defect — expected verdict: accept."""
    return {
        "incident_id": "SHALLOW-001",
        "year": 2021,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 15.0,
        "length_mm": 80.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TX-B",
    }


@pytest.fixture()
def deep_incident():
    """Deep corrosion defect (>=80%) — expected verdict: replace."""
    return {
        "incident_id": "DEEP-001",
        "year": 2022,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 82.0,
        "length_mm": 300.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TX-C",
    }


@pytest.fixture()
def moderate_incident():
    """Moderate defect (50-79% depth, sufficient safe pressure) — monitor."""
    return {
        "incident_id": "MOD-001",
        "year": 2023,
        "pipeline_type": "gas_transmission",
        "defect_type": "corrosion",
        "depth_pct_wall": 55.0,
        "length_mm": 200.0,
        "pipe_od_mm": 323.85,
        "wall_thickness_mm": 9.53,
        "smys_mpa": 358.53,
        "maop_mpa": 6.895,
        "location": "TX-D",
    }


@pytest.fixture()
def sample_df(minimal_incident, shallow_incident, deep_incident):
    """Three-row DataFrame for batch testing."""
    return pd.DataFrame([minimal_incident, shallow_incident, deep_incident])


# ---------------------------------------------------------------------------
# Section 1: PipelineDefect characterization
# ---------------------------------------------------------------------------


class TestCharacterize:
    def test_returns_pipeline_defect_instance(self, workflow, minimal_incident):
        result = workflow.characterize(minimal_incident)
        assert isinstance(result, PipelineDefect)

    def test_incident_id_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.incident_id == "TEST-001"

    def test_location_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.location == "TX-A"

    def test_defect_type_mapped(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.defect_type == "corrosion"

    def test_depth_pct_wall_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.depth_pct_wall == pytest.approx(30.0)

    def test_length_mm_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.length_mm == pytest.approx(150.0)

    def test_pipe_od_mm_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.pipe_od_mm == pytest.approx(323.85)

    def test_wall_thickness_mm_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.wall_thickness_mm == pytest.approx(9.53)

    def test_smys_mpa_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.smys_mpa == pytest.approx(358.53)

    def test_maop_mpa_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.maop_mpa == pytest.approx(6.895)

    def test_year_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.year == 2020

    def test_source_is_phmsa(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        assert defect.source == "phmsa"

    def test_cause_category_mapped_to_defect_type(self, workflow):
        incident = {
            "incident_id": "CC-001",
            "cause_category": "external corrosion",
            "year": 2020,
        }
        defect = workflow.characterize(incident)
        assert defect.defect_type == "corrosion"

    def test_defaults_applied_when_fields_missing(self, workflow):
        defect = workflow.characterize({"incident_id": "BARE-001"})
        assert defect.pipe_od_mm > 0
        assert defect.wall_thickness_mm > 0
        assert defect.smys_mpa > 0
        assert defect.maop_mpa > 0

    def test_liquid_pipeline_maop_default(self, workflow):
        incident = {"incident_id": "LIQ-001", "pipeline_type": "hazardous_liquid"}
        defect = workflow.characterize(incident)
        # liquid default MAOP (5.516) < gas default MAOP (6.895)
        assert defect.maop_mpa < 6.895


# ---------------------------------------------------------------------------
# Section 2: FFSResult fields
# ---------------------------------------------------------------------------


class TestFFSResultFields:
    def test_returns_ffs_result_instance(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect)
        assert isinstance(result, FFSResult)

    def test_incident_id_preserved(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect)
        assert result.incident_id == "TEST-001"

    def test_method_field_set(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect, method="modified_b31g")
        assert result.method == "modified_b31g"

    def test_failure_pressure_positive(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect)
        assert result.failure_pressure_mpa > 0

    def test_safe_pressure_less_than_failure_pressure(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect)
        assert result.safe_pressure_mpa < result.failure_pressure_mpa

    def test_safety_factor_applied(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect, safety_factor=1.39)
        expected = result.failure_pressure_mpa / 1.39
        assert result.safe_pressure_mpa == pytest.approx(expected, rel=1e-3)

    def test_safety_factor_field_stored(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect, safety_factor=1.25)
        assert result.safety_factor == pytest.approx(1.25)

    def test_verdict_is_valid_value(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect)
        assert result.verdict in {"accept", "monitor", "repair", "replace"}

    def test_notes_field_non_empty(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect)
        assert isinstance(result.notes, str)
        assert len(result.notes) > 0


# ---------------------------------------------------------------------------
# Section 3: Verdict logic
# ---------------------------------------------------------------------------


class TestVerdictLogic:
    def test_deep_defect_verdict_replace(self, workflow, deep_incident):
        defect = workflow.characterize(deep_incident)
        result = workflow.assess_ffs(defect)
        assert result.verdict == "replace"

    def test_shallow_defect_verdict_accept(self, workflow, shallow_incident):
        defect = workflow.characterize(shallow_incident)
        result = workflow.assess_ffs(defect)
        assert result.verdict == "accept"

    def test_80_pct_depth_triggers_replace(self, workflow):
        incident = {
            "incident_id": "CRIT-001",
            "depth_pct_wall": 80.0,
            "length_mm": 200.0,
            "pipe_od_mm": 323.85,
            "wall_thickness_mm": 9.53,
            "smys_mpa": 358.53,
            "maop_mpa": 6.895,
        }
        defect = workflow.characterize(incident)
        result = workflow.assess_ffs(defect)
        assert result.verdict == "replace"

    def test_moderate_depth_monitor(self, workflow, moderate_incident):
        defect = workflow.characterize(moderate_incident)
        result = workflow.assess_ffs(defect)
        # safe_pressure >= MAOP and depth >= 50% → monitor or repair/replace
        # Given the geometry, safe pressure should exceed MAOP for 55% depth
        assert result.verdict in {"monitor", "repair", "replace"}

    def test_verdict_repair_when_safe_pressure_below_maop(self, workflow):
        # Force very high MAOP so safe_pressure < MAOP but depth < 80%
        incident = {
            "incident_id": "RPR-001",
            "depth_pct_wall": 60.0,
            "length_mm": 400.0,
            "pipe_od_mm": 323.85,
            "wall_thickness_mm": 9.53,
            "smys_mpa": 358.53,
            "maop_mpa": 100.0,  # unrealistically high to force repair
        }
        defect = workflow.characterize(incident)
        result = workflow.assess_ffs(defect)
        assert result.verdict in {"repair", "replace"}


# ---------------------------------------------------------------------------
# Section 4: Method variants
# ---------------------------------------------------------------------------


class TestMethodVariants:
    def test_b31g_method_works(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect, method="b31g")
        assert result.method == "b31g"
        assert result.failure_pressure_mpa > 0

    def test_modified_b31g_method_works(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect, method="modified_b31g")
        assert result.method == "modified_b31g"
        assert result.failure_pressure_mpa > 0

    def test_b31g_and_modified_differ(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        r1 = workflow.assess_ffs(defect, method="b31g")
        r2 = workflow.assess_ffs(defect, method="modified_b31g")
        # The two methods produce different pressures
        assert r1.failure_pressure_mpa != r2.failure_pressure_mpa


# ---------------------------------------------------------------------------
# Section 5: One-call assess() shortcut
# ---------------------------------------------------------------------------


class TestAssessShortcut:
    def test_assess_returns_ffs_result(self, workflow, minimal_incident):
        result = workflow.assess(minimal_incident)
        assert isinstance(result, FFSResult)

    def test_assess_modified_b31g(self, workflow, minimal_incident):
        result = workflow.assess(minimal_incident, method="modified_b31g")
        assert result.method == "modified_b31g"

    def test_assess_b31g(self, workflow, minimal_incident):
        result = workflow.assess(minimal_incident, method="b31g")
        assert result.method == "b31g"


# ---------------------------------------------------------------------------
# Section 6: generate_report() batch assessment
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_returns_dataframe(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        assert isinstance(report, pd.DataFrame)

    def test_row_count_matches_input(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        assert len(report) == len(sample_df)

    def test_required_columns_present(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        required = {
            "incident_id",
            "defect_type",
            "failure_pressure_mpa",
            "safe_pressure_mpa",
            "verdict",
            "remaining_life_years",
        }
        assert required.issubset(set(report.columns))

    def test_failure_pressures_all_positive(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        assert (report["failure_pressure_mpa"] > 0).all()

    def test_verdicts_are_valid(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        valid = {"accept", "monitor", "repair", "replace"}
        assert set(report["verdict"].unique()).issubset(valid)

    def test_deep_incident_verdict_replace_in_report(
        self, workflow, sample_df
    ):
        report = workflow.generate_report(sample_df)
        deep_row = report[report["incident_id"] == "DEEP-001"]
        assert len(deep_row) == 1
        assert deep_row.iloc[0]["verdict"] == "replace"


# ---------------------------------------------------------------------------
# Section 7: verdict_summary()
# ---------------------------------------------------------------------------


class TestVerdictSummary:
    def test_returns_dict(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        summary = workflow.verdict_summary(report)
        assert isinstance(summary, dict)

    def test_all_four_keys_present(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        summary = workflow.verdict_summary(report)
        assert set(summary.keys()) == {"accept", "monitor", "repair", "replace"}

    def test_counts_sum_to_total(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        summary = workflow.verdict_summary(report)
        assert sum(summary.values()) == len(sample_df)

    def test_empty_df_returns_zeros(self, workflow):
        empty = pd.DataFrame(columns=["verdict"])
        summary = workflow.verdict_summary(empty)
        assert summary == {"accept": 0, "monitor": 0, "repair": 0, "replace": 0}


# ---------------------------------------------------------------------------
# Section 8: case_study_narrative()
# ---------------------------------------------------------------------------


class TestCaseStudyNarrative:
    def test_returns_non_empty_string(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        narrative = workflow.case_study_narrative(report)
        assert isinstance(narrative, str)
        assert len(narrative) > 0

    def test_contains_phmsa(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        narrative = workflow.case_study_narrative(report)
        assert "PHMSA" in narrative

    def test_contains_b31g(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        narrative = workflow.case_study_narrative(report)
        assert "B31G" in narrative

    def test_contains_incident_count(self, workflow, sample_df):
        report = workflow.generate_report(sample_df)
        narrative = workflow.case_study_narrative(report)
        assert str(len(sample_df)) in narrative

    def test_empty_df_returns_fallback(self, workflow):
        empty = pd.DataFrame(
            columns=[
                "incident_id",
                "defect_type",
                "failure_pressure_mpa",
                "safe_pressure_mpa",
                "verdict",
                "remaining_life_years",
            ]
        )
        narrative = workflow.case_study_narrative(empty)
        assert isinstance(narrative, str)
        assert len(narrative) > 0


# ---------------------------------------------------------------------------
# Section 9: Internal calculation sanity checks
# ---------------------------------------------------------------------------


class TestInternalCalculations:
    def test_folias_factor_greater_than_one_for_nontrivial_defect(self):
        # L=150mm, OD=323.85mm, t=9.53mm → L²/Dt = 150²/(323.85*9.53) ≈ 7.28
        M = _folias_factor(150.0, 323.85, 9.53)
        assert M > 1.0

    def test_folias_factor_formula_small_A(self):
        # A = 1.0 → M = sqrt(1 + 0.6275 - 0.003375) = sqrt(1.624125)
        L = math.sqrt(1.0 * 323.85 * 9.53)  # L²/(OD*t) = 1.0
        M = _folias_factor(L, 323.85, 9.53)
        expected = math.sqrt(1.0 + 0.6275 * 1.0 - 0.003375 * 1.0)
        assert M == pytest.approx(expected, rel=1e-6)

    def test_folias_factor_large_A_linear(self):
        # Force A > 50: L²/(OD*t) = 60 → M = 0.032*60 + 3.3 = 5.22
        L = math.sqrt(60.0 * 323.85 * 9.53)
        M = _folias_factor(L, 323.85, 9.53)
        expected = 0.032 * 60.0 + 3.3
        assert M == pytest.approx(expected, rel=1e-6)

    def test_modified_b31g_failure_pressure_positive(self):
        pf = _failure_pressure_modified_b31g(30.0, 150.0, 323.85, 9.53, 358.53)
        assert pf > 0

    def test_b31g_failure_pressure_positive(self):
        pf = _failure_pressure_b31g(30.0, 150.0, 323.85, 9.53, 358.53)
        assert pf > 0

    def test_safety_factor_139_applied_correctly(self, workflow, minimal_incident):
        defect = workflow.characterize(minimal_incident)
        result = workflow.assess_ffs(defect, safety_factor=1.39)
        assert result.safe_pressure_mpa == pytest.approx(
            result.failure_pressure_mpa / 1.39, rel=1e-3
        )

    def test_remaining_life_positive_for_corrosion(self, workflow):
        incident = {
            "incident_id": "RL-001",
            "defect_type": "corrosion",
            "depth_pct_wall": 30.0,
            "wall_thickness_mm": 9.53,
            "pipe_od_mm": 323.85,
            "smys_mpa": 358.53,
            "maop_mpa": 6.895,
        }
        defect = workflow.characterize(incident)
        result = workflow.assess_ffs(defect)
        assert result.remaining_life_years is not None
        assert result.remaining_life_years > 0

    def test_remaining_life_none_for_mechanical(self, workflow):
        incident = {
            "incident_id": "RL-002",
            "defect_type": "mechanical",
            "depth_pct_wall": 20.0,
            "wall_thickness_mm": 9.53,
            "pipe_od_mm": 323.85,
            "smys_mpa": 358.53,
            "maop_mpa": 6.895,
        }
        defect = workflow.characterize(incident)
        result = workflow.assess_ffs(defect)
        assert result.remaining_life_years is None
