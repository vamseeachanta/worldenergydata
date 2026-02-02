"""Tests for HSE Risk Index RiskScorer."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from worldenergydata.modules.safety_analysis.risk_index.models import (
    CompositeScore,
    DimensionScore,
    RiskCategory,
)
from worldenergydata.modules.safety_analysis.risk_index.scorer import RiskScorer


def _make_assembled_df(rows: list[dict]) -> pd.DataFrame:
    """Build a DataFrame matching DataAssembler output schema."""
    columns = [
        "activity_code",
        "activity_name",
        "total_incidents",
        "fatalities",
        "injuries",
        "fatality_rate",
        "injury_rate",
        "tri_carcinogen_lbs",
        "inc_rate",
        "confidence",
        "sources",
        "weighted_incident_count",
    ]
    data = []
    for r in rows:
        row = {col: r.get(col) for col in columns}
        data.append(row)
    return pd.DataFrame(data, columns=columns)


def _five_activity_df() -> pd.DataFrame:
    """Standard five-activity fixture with varied metrics."""
    return _make_assembled_df(
        [
            {
                "activity_code": "DRL",
                "activity_name": "Drilling",
                "total_incidents": 100,
                "fatalities": 10,
                "injuries": 40,
                "fatality_rate": 0.10,
                "injury_rate": 0.40,
                "tri_carcinogen_lbs": 5000.0,
                "inc_rate": 0.30,
                "confidence": "high",
                "sources": ["bsee", "osha"],
                "weighted_incident_count": 25.0,
            },
            {
                "activity_code": "PRD",
                "activity_name": "Production",
                "total_incidents": 200,
                "fatalities": 5,
                "injuries": 60,
                "fatality_rate": 0.025,
                "injury_rate": 0.30,
                "tri_carcinogen_lbs": 15000.0,
                "inc_rate": 0.10,
                "confidence": "high",
                "sources": ["bsee", "osha", "epa_tri"],
                "weighted_incident_count": 40.0,
            },
            {
                "activity_code": "TRN",
                "activity_name": "Transportation",
                "total_incidents": 50,
                "fatalities": 8,
                "injuries": 20,
                "fatality_rate": 0.16,
                "injury_rate": 0.40,
                "tri_carcinogen_lbs": 200.0,
                "inc_rate": 0.50,
                "confidence": "medium",
                "sources": ["phmsa"],
                "weighted_incident_count": 7.5,
            },
            {
                "activity_code": "MNT",
                "activity_name": "Maintenance",
                "total_incidents": 80,
                "fatalities": 2,
                "injuries": 30,
                "fatality_rate": 0.025,
                "injury_rate": 0.375,
                "tri_carcinogen_lbs": 800.0,
                "inc_rate": 0.20,
                "confidence": "medium",
                "sources": ["osha"],
                "weighted_incident_count": 16.0,
            },
            {
                "activity_code": "DSM",
                "activity_name": "Decommissioning",
                "total_incidents": 20,
                "fatalities": 1,
                "injuries": 5,
                "fatality_rate": 0.05,
                "injury_rate": 0.25,
                "tri_carcinogen_lbs": 100.0,
                "inc_rate": 0.05,
                "confidence": "low",
                "sources": ["bsee"],
                "weighted_incident_count": 6.0,
            },
        ]
    )


class TestScoreActivitiesBasic:
    """Given assembled DataFrame with 5+ activities, scorer produces
    CompositeScore with one ActivityRiskScore per activity."""

    def test_returns_composite_score(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        assert isinstance(result, CompositeScore)

    def test_one_score_per_activity(self):
        df = _five_activity_df()
        scorer = RiskScorer()
        result = scorer.score(df)
        assert len(result.scores) == len(df)

    def test_activity_codes_match(self):
        df = _five_activity_df()
        scorer = RiskScorer()
        result = scorer.score(df)
        codes = {s.activity_code for s in result.scores}
        expected = set(df["activity_code"])
        assert codes == expected

    def test_all_scores_have_three_dimensions(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for activity_score in result.scores:
            assert isinstance(activity_score.acute, DimensionScore)
            assert isinstance(activity_score.chronic, DimensionScore)
            assert isinstance(activity_score.compliance, DimensionScore)

    def test_composite_scores_in_valid_range(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for activity_score in result.scores:
            assert 1.0 <= activity_score.composite_score <= 10.0


class TestAcuteDimensionWeights:
    """Verify 0.40/0.35/0.25 weighting of fatality_rate/injury_rate/frequency."""

    def test_acute_dimension_name(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert s.acute.dimension == "acute"

    def test_acute_subscores_contain_expected_keys(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert "fatality_rate" in s.acute.subscores
            assert "injury_rate" in s.acute.subscores
            assert "frequency" in s.acute.subscores

    def test_acute_score_is_weighted_sum(self):
        """Acute score = 0.40*fatality_rate_score + 0.35*injury_rate_score
        + 0.25*frequency_score."""
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            expected = (
                0.40 * s.acute.subscores["fatality_rate"]
                + 0.35 * s.acute.subscores["injury_rate"]
                + 0.25 * s.acute.subscores["frequency"]
            )
            assert abs(s.acute.score - expected) < 0.01


class TestChronicDimension:
    """Verify chronic = tri_carcinogen_score alone."""

    def test_chronic_dimension_name(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert s.chronic.dimension == "chronic"

    def test_chronic_subscores_contain_tri(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert "tri_carcinogen_lbs" in s.chronic.subscores

    def test_chronic_score_equals_tri_score(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert (
                abs(s.chronic.score - s.chronic.subscores["tri_carcinogen_lbs"]) < 0.01
            )


class TestComplianceDimension:
    """Verify compliance = inc_rate_score alone."""

    def test_compliance_dimension_name(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert s.compliance.dimension == "compliance"

    def test_compliance_subscores_contain_inc_rate(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert "inc_rate" in s.compliance.subscores

    def test_compliance_score_equals_inc_rate_score(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            assert abs(s.compliance.score - s.compliance.subscores["inc_rate"]) < 0.01


class TestCompositeWeights:
    """Verify 0.50/0.25/0.25 composite weighting."""

    def test_composite_is_weighted_sum_of_dimensions(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            expected = (
                0.50 * s.acute.score
                + 0.25 * s.chronic.score
                + 0.25 * s.compliance.score
            )
            assert abs(s.composite_score - expected) < 0.01


class TestKnownAnswerVerification:
    """Hand-computed scores for activities with known values.

    Use a 4-activity DF so normalize_to_scale gives us predictable buckets.
    With 4 items ranked [1,2,3,4], percentile_rank gives [0.25, 0.50, 0.75, 1.0].
    normalize_to_scale maps: 0.25*9+0.5=2.75->3, 0.50*9+0.5=5.0->5,
    0.75*9+0.5=7.25->7, 1.0*9+0.5=10->10.
    So sorted values map to [3, 5, 7, 10].
    """

    def _four_activity_df(self) -> pd.DataFrame:
        return _make_assembled_df(
            [
                {
                    "activity_code": "A",
                    "activity_name": "Alpha",
                    "total_incidents": 10,
                    "fatalities": 0,
                    "injuries": 1,
                    "fatality_rate": 0.00,
                    "injury_rate": 0.10,
                    "tri_carcinogen_lbs": 100.0,
                    "inc_rate": 0.01,
                    "confidence": "low",
                    "sources": ["osha"],
                    "weighted_incident_count": 2.0,
                },
                {
                    "activity_code": "B",
                    "activity_name": "Bravo",
                    "total_incidents": 50,
                    "fatalities": 2,
                    "injuries": 10,
                    "fatality_rate": 0.04,
                    "injury_rate": 0.20,
                    "tri_carcinogen_lbs": 500.0,
                    "inc_rate": 0.10,
                    "confidence": "medium",
                    "sources": ["bsee"],
                    "weighted_incident_count": 15.0,
                },
                {
                    "activity_code": "C",
                    "activity_name": "Charlie",
                    "total_incidents": 100,
                    "fatalities": 5,
                    "injuries": 30,
                    "fatality_rate": 0.05,
                    "injury_rate": 0.30,
                    "tri_carcinogen_lbs": 2000.0,
                    "inc_rate": 0.25,
                    "confidence": "high",
                    "sources": ["bsee", "osha"],
                    "weighted_incident_count": 25.0,
                },
                {
                    "activity_code": "D",
                    "activity_name": "Delta",
                    "total_incidents": 200,
                    "fatalities": 20,
                    "injuries": 80,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.40,
                    "tri_carcinogen_lbs": 10000.0,
                    "inc_rate": 0.50,
                    "confidence": "high",
                    "sources": ["bsee", "osha", "epa_tri"],
                    "weighted_incident_count": 50.0,
                },
            ]
        )

    def test_known_normalized_scores(self):
        """Verify all four metrics rank in the expected order."""
        scorer = RiskScorer()
        result = scorer.score(self._four_activity_df())
        scores_by_code = {s.activity_code: s for s in result.scores}

        # All metrics monotonically increase from A->B->C->D.
        # So rank order is A=3, B=5, C=7, D=10 for every metric.
        # Acute for D: 0.40*10 + 0.35*10 + 0.25*10 = 10.0
        d_score = scores_by_code["D"]
        assert abs(d_score.acute.score - 10.0) < 0.01
        assert abs(d_score.chronic.score - 10.0) < 0.01
        assert abs(d_score.compliance.score - 10.0) < 0.01
        # Composite for D: 0.50*10 + 0.25*10 + 0.25*10 = 10.0
        assert abs(d_score.composite_score - 10.0) < 0.01

    def test_known_lowest_activity(self):
        scorer = RiskScorer()
        result = scorer.score(self._four_activity_df())
        scores_by_code = {s.activity_code: s for s in result.scores}

        # A has lowest rank (3) for all metrics
        # Acute for A: 0.40*3 + 0.35*3 + 0.25*3 = 3.0
        a_score = scores_by_code["A"]
        assert abs(a_score.acute.score - 3.0) < 0.01
        assert abs(a_score.chronic.score - 3.0) < 0.01
        assert abs(a_score.compliance.score - 3.0) < 0.01
        assert abs(a_score.composite_score - 3.0) < 0.01

    def test_known_middle_activity(self):
        scorer = RiskScorer()
        result = scorer.score(self._four_activity_df())
        scores_by_code = {s.activity_code: s for s in result.scores}

        # B has rank 5 for all metrics
        b_score = scores_by_code["B"]
        assert abs(b_score.acute.score - 5.0) < 0.01
        assert abs(b_score.composite_score - 5.0) < 0.01


class TestCategoryAssignment:
    """High-risk activities get CRITICAL/HIGH, low-risk get LOW/MEDIUM."""

    def test_highest_risk_is_critical_or_high(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        # Find the activity with the max composite score
        max_score = max(result.scores, key=lambda s: s.composite_score)
        assert max_score.category in (RiskCategory.CRITICAL, RiskCategory.HIGH)

    def test_lowest_risk_is_low_or_medium(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        min_score = min(result.scores, key=lambda s: s.composite_score)
        assert min_score.category in (RiskCategory.LOW, RiskCategory.MEDIUM)

    def test_category_matches_composite_score(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        for s in result.scores:
            expected_cat = RiskCategory.from_score(s.composite_score)
            assert s.category == expected_cat


class TestMissingMetricHandling:
    """When an activity has NaN for tri_carcinogen_lbs, use DEFAULT_SCORE 5.5."""

    def test_nan_tri_gets_default_score(self):
        df = _make_assembled_df(
            [
                {
                    "activity_code": "A",
                    "activity_name": "Alpha",
                    "total_incidents": 50,
                    "fatalities": 5,
                    "injuries": 10,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.20,
                    "tri_carcinogen_lbs": np.nan,
                    "inc_rate": 0.15,
                    "confidence": "medium",
                    "sources": ["osha"],
                    "weighted_incident_count": 10.0,
                },
                {
                    "activity_code": "B",
                    "activity_name": "Bravo",
                    "total_incidents": 100,
                    "fatalities": 10,
                    "injuries": 30,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.30,
                    "tri_carcinogen_lbs": 5000.0,
                    "inc_rate": 0.25,
                    "confidence": "high",
                    "sources": ["bsee", "osha"],
                    "weighted_incident_count": 25.0,
                },
            ]
        )
        scorer = RiskScorer()
        result = scorer.score(df)
        scores_by_code = {s.activity_code: s for s in result.scores}
        # A has NaN tri, should get DEFAULT_SCORE (5.5) for chronic
        a_chronic = scores_by_code["A"].chronic.score
        assert abs(a_chronic - RiskScorer.DEFAULT_SCORE) < 0.01

    def test_nan_inc_rate_gets_default_score(self):
        df = _make_assembled_df(
            [
                {
                    "activity_code": "A",
                    "activity_name": "Alpha",
                    "total_incidents": 50,
                    "fatalities": 5,
                    "injuries": 10,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.20,
                    "tri_carcinogen_lbs": 500.0,
                    "inc_rate": np.nan,
                    "confidence": "medium",
                    "sources": ["osha"],
                    "weighted_incident_count": 10.0,
                },
                {
                    "activity_code": "B",
                    "activity_name": "Bravo",
                    "total_incidents": 100,
                    "fatalities": 10,
                    "injuries": 30,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.30,
                    "tri_carcinogen_lbs": 5000.0,
                    "inc_rate": 0.25,
                    "confidence": "high",
                    "sources": ["bsee", "osha"],
                    "weighted_incident_count": 25.0,
                },
            ]
        )
        scorer = RiskScorer()
        result = scorer.score(df)
        scores_by_code = {s.activity_code: s for s in result.scores}
        a_compliance = scores_by_code["A"].compliance.score
        assert abs(a_compliance - RiskScorer.DEFAULT_SCORE) < 0.01


class TestSingleActivity:
    """Edge case with only one activity (no distribution to rank against)."""

    def test_single_activity_returns_one_score(self):
        df = _make_assembled_df(
            [
                {
                    "activity_code": "SOLO",
                    "activity_name": "Solo Activity",
                    "total_incidents": 50,
                    "fatalities": 5,
                    "injuries": 10,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.20,
                    "tri_carcinogen_lbs": 1000.0,
                    "inc_rate": 0.15,
                    "confidence": "medium",
                    "sources": ["osha"],
                    "weighted_incident_count": 10.0,
                },
            ]
        )
        scorer = RiskScorer()
        result = scorer.score(df)
        assert len(result.scores) == 1

    def test_single_activity_score_in_valid_range(self):
        df = _make_assembled_df(
            [
                {
                    "activity_code": "SOLO",
                    "activity_name": "Solo Activity",
                    "total_incidents": 50,
                    "fatalities": 5,
                    "injuries": 10,
                    "fatality_rate": 0.10,
                    "injury_rate": 0.20,
                    "tri_carcinogen_lbs": 1000.0,
                    "inc_rate": 0.15,
                    "confidence": "medium",
                    "sources": ["osha"],
                    "weighted_incident_count": 10.0,
                },
            ]
        )
        scorer = RiskScorer()
        result = scorer.score(df)
        s = result.scores[0]
        assert 1.0 <= s.composite_score <= 10.0
        assert 1.0 <= s.acute.score <= 10.0
        assert 1.0 <= s.chronic.score <= 10.0
        assert 1.0 <= s.compliance.score <= 10.0


class TestAllEqualValues:
    """All activities with same metrics get middle scores."""

    def _equal_df(self) -> pd.DataFrame:
        row = {
            "activity_code": None,
            "activity_name": None,
            "total_incidents": 50,
            "fatalities": 5,
            "injuries": 10,
            "fatality_rate": 0.10,
            "injury_rate": 0.20,
            "tri_carcinogen_lbs": 1000.0,
            "inc_rate": 0.15,
            "confidence": "medium",
            "sources": ["osha"],
            "weighted_incident_count": 10.0,
        }
        rows = []
        for _i, code in enumerate(["A", "B", "C", "D", "E"]):
            r = dict(row)
            r["activity_code"] = code
            r["activity_name"] = f"Activity {code}"
            rows.append(r)
        return _make_assembled_df(rows)

    def test_all_equal_get_same_composite(self):
        scorer = RiskScorer()
        result = scorer.score(self._equal_df())
        composites = [s.composite_score for s in result.scores]
        assert len(set(composites)) == 1

    def test_all_equal_score_near_middle(self):
        scorer = RiskScorer()
        result = scorer.score(self._equal_df())
        for s in result.scores:
            # With all-tied values, normalize_to_scale yields a middle-ish
            # value. The exact value depends on the normalizer: 5 items at
            # same rank gives percentile_rank = 0.6 for all (avg of 1..5 / 5).
            # 0.6 * 9 + 0.5 = 5.9 -> round -> 6. So all subscores = 6.
            # composite = 0.5*6 + 0.25*6 + 0.25*6 = 6.0
            # Allow some tolerance for rounding
            assert 4.0 <= s.composite_score <= 7.0


class TestMetadataPopulated:
    """Composite metadata includes weights, source info, generation date."""

    def test_metadata_has_weights(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        assert "composite_weights" in result.metadata
        assert result.metadata["composite_weights"] == {
            "acute": 0.50,
            "chronic": 0.25,
            "compliance": 0.25,
        }

    def test_metadata_has_acute_weights(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        assert "acute_weights" in result.metadata
        assert result.metadata["acute_weights"] == {
            "fatality_rate": 0.40,
            "injury_rate": 0.35,
            "frequency": 0.25,
        }

    def test_metadata_has_activity_count(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        assert "activity_count" in result.metadata
        assert result.metadata["activity_count"] == 5

    def test_generated_at_is_recent(self):
        scorer = RiskScorer()
        before = datetime.now(timezone.utc)
        result = scorer.score(_five_activity_df())
        after = datetime.now(timezone.utc)
        assert before <= result.generated_at <= after

    def test_metadata_has_normalization_method(self):
        scorer = RiskScorer()
        result = scorer.score(_five_activity_df())
        assert "normalization_method" in result.metadata
        assert result.metadata["normalization_method"] == "percentile_rank"
