# ABOUTME: Integration tests for ClassificationPipeline — training, prediction,
# evaluation, cross-validation with RF/LR/XGBoost classifiers and TF-IDF features.
"""Tests for safety analysis classification pipeline."""

import random
from unittest.mock import patch

import pytest

try:
    import sklearn  # noqa: F401

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

try:
    import xgboost  # noqa: F401

    _HAS_XGBOOST = True
except ImportError:
    _HAS_XGBOOST = False

pytestmark = pytest.mark.skipif(not _HAS_SKLEARN, reason="scikit-learn not installed")

from worldenergydata.safety_analysis.config import (  # noqa: E402
    AnalysisConfig,
    HyperparamConfig,
)
from worldenergydata.safety_analysis.constants import (  # noqa: E402
    ClassifierType,
)
from worldenergydata.safety_analysis.core.models import (  # noqa: E402
    ClassificationResult,
)
from worldenergydata.safety_analysis.exceptions import (  # noqa: E402
    OptionalDependencyError,
    SafetyClassificationError,
)
from worldenergydata.safety_analysis.nlp.classification_pipeline import (  # noqa: E402
    ClassificationPipeline,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAFE_PHRASES = [
    "good housekeeping observed",
    "proper PPE worn at all times",
    "safety meeting well attended",
    "crew demonstrated safe practices",
    "excellent communication during task",
]
_ATRISK_PHRASES = [
    "worker not wearing hard hat",
    "unsafe lifting technique observed",
    "no fall protection used at height",
    "bypassed safety interlock",
    "failed to follow lockout procedure",
]


@pytest.fixture
def pipeline_config(tmp_path):
    """AnalysisConfig with fast test-friendly hyperparameters."""
    return AnalysisConfig(
        model_dir=tmp_path / "models",
        hyperparams=HyperparamConfig(
            max_evals=5,
            cv_folds=2,
            random_state=42,
            test_size=0.3,
        ),
    )


@pytest.fixture
def pipeline(pipeline_config):
    """ClassificationPipeline with test config."""
    return ClassificationPipeline(pipeline_config)


@pytest.fixture
def training_data():
    """Generate enough labelled training data for classification (~60 samples)."""
    texts = []
    labels = []
    rng = random.Random(42)
    for _ in range(30):
        texts.append(rng.choice(_SAFE_PHRASES) + f" on day {rng.randint(1, 100)}")
        labels.append("safe")
        texts.append(rng.choice(_ATRISK_PHRASES) + f" on day {rng.randint(1, 100)}")
        labels.append("at_risk")
    return texts, labels


# ---------------------------------------------------------------------------
# Training tests
# ---------------------------------------------------------------------------


class TestTrain:
    def test_train_random_forest(self, pipeline, training_data):
        """Training a random forest should return a ModelEntry with metrics."""
        texts, labels = training_data
        entry = pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="test_rf",
        )
        assert entry.model_name == "test_rf"
        assert entry.classifier_type == ClassifierType.RANDOM_FOREST.value
        assert "f1_weighted" in entry.metrics
        assert entry.metrics["f1_weighted"] > 0.0

    def test_train_logistic_regression(self, pipeline, training_data):
        """Training logistic regression should return a valid ModelEntry."""
        texts, labels = training_data
        entry = pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.LOGISTIC_REGRESSION,
            model_name="test_lr",
        )
        assert entry.model_name == "test_lr"
        assert entry.classifier_type == ClassifierType.LOGISTIC_REGRESSION.value
        assert "f1_weighted" in entry.metrics

    @pytest.mark.skipif(not _HAS_XGBOOST, reason="xgboost not installed")
    def test_train_xgboost(self, pipeline, training_data):
        """Training an XGBoost classifier should succeed when the package is available."""
        texts, labels = training_data
        entry = pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.XGBOOST,
            model_name="test_xgb",
        )
        assert entry.model_name == "test_xgb"
        assert entry.classifier_type == ClassifierType.XGBOOST.value
        assert "f1_weighted" in entry.metrics


# ---------------------------------------------------------------------------
# Prediction tests
# ---------------------------------------------------------------------------


class TestPredict:
    def test_predict_after_train(self, pipeline, training_data):
        """predict() after training should return a list of ClassificationResult."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="pred_rf",
        )
        results = pipeline.predict(
            ["worker not wearing helmet", "good safety practices"],
            model_name="pred_rf",
        )
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, ClassificationResult) for r in results)

    def test_predict_single(self, pipeline, training_data):
        """predict_single() should return one ClassificationResult."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="single_rf",
        )
        result = pipeline.predict_single(
            "worker not wearing hard hat", model_name="single_rf"
        )
        assert isinstance(result, ClassificationResult)
        assert 0.0 <= result.confidence <= 1.0

    def test_predict_has_probabilities(self, pipeline, training_data):
        """ClassificationResult.probabilities dict should be populated."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="prob_rf",
        )
        result = pipeline.predict_single(
            "good housekeeping observed", model_name="prob_rf"
        )
        assert result.probabilities is not None
        assert isinstance(result.probabilities, dict)
        assert len(result.probabilities) > 0

    def test_predict_nonexistent_model_raises(self, pipeline):
        """Predicting with a model that was never trained should raise."""
        with pytest.raises(SafetyClassificationError):
            pipeline.predict(["some text"], model_name="does_not_exist")


# ---------------------------------------------------------------------------
# Evaluation tests
# ---------------------------------------------------------------------------


class TestEvaluate:
    def test_evaluate_returns_metrics(self, pipeline, training_data):
        """evaluate() should return a dict with standard classification metrics."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="eval_rf",
        )
        metrics = pipeline.evaluate(texts, labels, model_name="eval_rf")
        assert "f1_weighted" in metrics
        assert metrics["f1_weighted"] > 0.0
        assert "classification_report" in metrics
        assert "confusion_matrix" in metrics


class TestCrossValidate:
    def test_cross_validate_returns_scores(self, pipeline, training_data):
        """cross_validate() should return mean and std for each scoring metric."""
        texts, labels = training_data
        cv_results = pipeline.cross_validate(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            cv=2,
        )
        assert isinstance(cv_results, dict)
        assert "mean_score" in cv_results
        assert "std_score" in cv_results
        assert "scores" in cv_results
        assert cv_results["mean_score"] > 0.0


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    def test_train_without_sklearn_raises(self, pipeline_config):
        """When sklearn is unavailable, constructing the pipeline should raise."""
        with (
            patch(
                "worldenergydata.safety_analysis.nlp"
                ".classification_pipeline._HAS_SKLEARN",
                False,
            ),
            pytest.raises(OptionalDependencyError),
        ):
            ClassificationPipeline(pipeline_config)
