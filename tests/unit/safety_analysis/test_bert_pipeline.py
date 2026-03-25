# ABOUTME: Tests for BERT embedding extraction and classification pipeline.
"""Tests for BERT-based embedding and classification in safety analysis."""

import random
from unittest.mock import patch

import numpy as np
import pytest

try:
    import torch  # noqa: F401
    from transformers import AutoModel, AutoTokenizer  # noqa: F401

    _HAS_BERT = True
except ImportError:
    _HAS_BERT = False

try:
    import sklearn  # noqa: F401

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

# Skip entire module if BERT deps not available
pytestmark = pytest.mark.skipif(
    not (_HAS_BERT and _HAS_SKLEARN),
    reason="torch/transformers or scikit-learn not installed",
)

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
from worldenergydata.safety_analysis.nlp.bert_pipeline import (  # noqa: E402
    BertClassificationPipeline,
    BertConfig,
    BertEmbedder,
)
from worldenergydata.safety_analysis.nlp.model_registry import (  # noqa: E402
    ModelEntry,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAFE_PHRASES = [
    "worker wearing proper safety equipment during operations",
    "good housekeeping maintained in work area",
    "crew following all safety protocols correctly",
    "proper lockout tagout procedure followed",
    "safety meeting conducted with all hands",
]
_ATRISK_PHRASES = [
    "employee not wearing required hard hat",
    "unsafe lifting technique observed on site",
    "no fall protection used while working at height",
    "safety interlock bypassed during maintenance",
    "failed to follow lockout tagout procedure",
]


@pytest.fixture
def bert_config():
    """BertConfig with small max_length for faster testing."""
    return BertConfig(
        model_name="bert-base-uncased",
        max_length=128,
        batch_size=4,
        device="cpu",
        pooling_strategy="cls",
    )


@pytest.fixture
def embedder(bert_config):
    """BertEmbedder initialised with test config."""
    return BertEmbedder(bert_config)


@pytest.fixture
def pipeline_config(tmp_path):
    """AnalysisConfig with fast test-friendly hyperparameters."""
    return AnalysisConfig(
        model_dir=tmp_path / "models",
        hyperparams=HyperparamConfig(
            max_evals=3,
            cv_folds=2,
            random_state=42,
            test_size=0.3,
        ),
    )


@pytest.fixture
def pipeline(pipeline_config, bert_config):
    """BertClassificationPipeline with test config."""
    return BertClassificationPipeline(
        config=pipeline_config,
        bert_config=bert_config,
    )


@pytest.fixture
def training_data():
    """Generate enough labelled text data for training (~50 samples)."""
    texts, labels = [], []
    rng = random.Random(42)
    for _ in range(25):
        texts.append(rng.choice(_SAFE_PHRASES) + f" on shift {rng.randint(1, 50)}")
        labels.append("safe")
        texts.append(rng.choice(_ATRISK_PHRASES) + f" on shift {rng.randint(1, 50)}")
        labels.append("at_risk")
    return texts, labels


# ---------------------------------------------------------------------------
# BertConfig tests
# ---------------------------------------------------------------------------


class TestBertConfig:
    def test_default_config(self):
        """Default BertConfig values are correct."""
        config = BertConfig()

        assert config.model_name == "bert-base-uncased"
        assert config.max_length == 512
        assert config.batch_size == 32
        assert config.device == "cpu"
        assert config.pooling_strategy == "cls"

    def test_custom_config(self):
        """Custom values are respected by BertConfig."""
        config = BertConfig(
            model_name="bert-large-uncased",
            max_length=256,
            batch_size=16,
            device="cpu",
            pooling_strategy="mean",
        )

        assert config.model_name == "bert-large-uncased"
        assert config.max_length == 256
        assert config.batch_size == 16
        assert config.pooling_strategy == "mean"


# ---------------------------------------------------------------------------
# BertEmbedder tests
# ---------------------------------------------------------------------------


class TestBertEmbedder:
    def test_embed_texts_returns_numpy(self, embedder):
        """embed_texts() should return a numpy ndarray."""
        texts = ["safety equipment worn correctly"]
        result = embedder.embed_texts(texts)

        assert isinstance(result, np.ndarray)

    def test_embed_texts_shape(self, embedder):
        """Embedding shape should be (n_texts, embedding_dim)."""
        texts = ["first observation text", "second observation text"]
        result = embedder.embed_texts(texts)

        assert result.shape == (2, embedder.embedding_dim)

    def test_embedding_dim(self, embedder):
        """embedding_dim should be 768 for bert-base-uncased."""
        assert embedder.embedding_dim == 768

    def test_batch_processing(self, embedder):
        """Embedder should handle more texts than batch_size (batch_size=4)."""
        texts = [f"observation number {i}" for i in range(10)]
        result = embedder.embed_texts(texts)

        assert result.shape == (10, embedder.embedding_dim)

    def test_mean_pooling(self):
        """Mean pooling strategy should produce different embeddings than CLS."""
        config_cls = BertConfig(
            model_name="bert-base-uncased",
            max_length=128,
            batch_size=4,
            pooling_strategy="cls",
        )
        config_mean = BertConfig(
            model_name="bert-base-uncased",
            max_length=128,
            batch_size=4,
            pooling_strategy="mean",
        )
        embedder_cls = BertEmbedder(config_cls)
        embedder_mean = BertEmbedder(config_mean)

        texts = ["worker following safety protocol on the rig"]
        emb_cls = embedder_cls.embed_texts(texts)
        emb_mean = embedder_mean.embed_texts(texts)

        # Both should have correct shape
        assert emb_cls.shape == emb_mean.shape == (1, 768)
        # Strategies produce different vectors
        assert not np.allclose(emb_cls, emb_mean)


# ---------------------------------------------------------------------------
# BertClassificationPipeline tests
# ---------------------------------------------------------------------------


class TestBertClassificationPipeline:
    def test_train_random_forest(self, pipeline, training_data):
        """Training a random forest should return a ModelEntry with metrics."""
        texts, labels = training_data
        entry = pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="bert_rf",
        )

        assert isinstance(entry, ModelEntry)
        assert entry.model_name == "bert_rf"
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
            model_name="bert_lr",
        )

        assert isinstance(entry, ModelEntry)
        assert entry.model_name == "bert_lr"
        assert entry.classifier_type == ClassifierType.LOGISTIC_REGRESSION.value
        assert "f1_weighted" in entry.metrics

    def test_predict_after_train(self, pipeline, training_data):
        """predict() after training should return a list of ClassificationResult."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="bert_pred_rf",
        )

        results = pipeline.predict(
            ["worker not wearing helmet", "good safety practices"],
            model_name="bert_pred_rf",
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
            model_name="bert_single_rf",
        )

        result = pipeline.predict_single(
            "worker not wearing hard hat", model_name="bert_single_rf"
        )

        assert isinstance(result, ClassificationResult)
        assert 0.0 <= result.confidence <= 1.0

    def test_predict_feature_type_is_bert(self, pipeline, training_data):
        """ClassificationResult.feature_type should be 'bert'."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="bert_ft_rf",
        )

        result = pipeline.predict_single(
            "good housekeeping on drill floor", model_name="bert_ft_rf"
        )

        assert result.feature_type == "bert"

    def test_evaluate(self, pipeline, training_data):
        """evaluate() should return a dict with f1_weighted."""
        texts, labels = training_data
        pipeline.train(
            texts,
            labels,
            classifier_type=ClassifierType.RANDOM_FOREST,
            model_name="bert_eval_rf",
        )

        metrics = pipeline.evaluate(texts, labels, model_name="bert_eval_rf")

        assert isinstance(metrics, dict)
        assert "f1_weighted" in metrics
        assert metrics["f1_weighted"] > 0.0

    def test_predict_nonexistent_model_raises(self, pipeline):
        """Predicting with a non-existent model should raise SafetyClassificationError."""
        with pytest.raises(SafetyClassificationError):
            pipeline.predict(["some text"], model_name="does_not_exist")


# ---------------------------------------------------------------------------
# Optional dependency error test
# ---------------------------------------------------------------------------


class TestOptionalDependencyError:
    def test_bert_missing_raises(self):
        """When torch/transformers are unavailable, BertEmbedder init should raise."""
        with (
            patch(
                "worldenergydata.safety_analysis.nlp.bert_pipeline._HAS_BERT",
                False,
            ),
            pytest.raises(OptionalDependencyError),
        ):
            BertEmbedder()
