# ABOUTME: Tests for ModelRegistry and ModelEntry — save/load models, metadata
# persistence, listing, best-model selection, deletion, and error paths.
"""Tests for safety analysis model registry."""

from datetime import datetime, timezone

import pytest

try:
    import sklearn  # noqa: F401

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

pytestmark = pytest.mark.skipif(not _HAS_SKLEARN, reason="scikit-learn not installed")

if _HAS_SKLEARN:
    from sklearn.ensemble import RandomForestClassifier

    from worldenergydata.modules.safety_analysis.exceptions import (
        SafetyClassificationError,
    )
    from worldenergydata.modules.safety_analysis.nlp.model_registry import (
        ModelEntry,
        ModelRegistry,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry_dir(tmp_path):
    """Temporary directory for model storage."""
    return tmp_path / "models"


@pytest.fixture
def registry(registry_dir):
    """ModelRegistry backed by a temp directory."""
    return ModelRegistry(registry_dir)


@pytest.fixture
def sample_model():
    """A tiny fitted RandomForest for serialisation tests."""
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit([[1, 0], [0, 1], [1, 1], [0, 0]], [0, 1, 1, 0])
    return model


@pytest.fixture
def sample_entry(registry_dir):
    """ModelEntry metadata for the sample model."""
    return ModelEntry(
        model_name="test_rf_model",
        classifier_type="random_forest",
        feature_type="tfidf",
        created_at=datetime.now(timezone.utc),
        metrics={"f1_weighted": 0.85, "accuracy": 0.90},
        params={"n_estimators": 10, "random_state": 42},
        model_path=registry_dir / "test_rf_model" / "model.joblib",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSaveAndLoad:
    def test_save_and_load_model(self, registry, sample_model, sample_entry):
        """Saved model should produce the same predictions after loading."""
        # Arrange
        test_data = [[1, 0], [0, 1]]
        original_preds = sample_model.predict(test_data).tolist()

        # Act
        registry.save_model(sample_model, sample_entry)
        loaded_model, loaded_entry = registry.load_model("test_rf_model")

        # Assert
        assert loaded_model.predict(test_data).tolist() == original_preds
        assert loaded_entry.model_name == "test_rf_model"
        assert loaded_entry.classifier_type == "random_forest"

    def test_get_entry_metadata_only(self, registry, sample_model, sample_entry):
        """get_entry should return metadata without loading the model."""
        registry.save_model(sample_model, sample_entry)
        entry = registry.get_entry("test_rf_model")
        assert entry.model_name == "test_rf_model"
        assert entry.metrics["f1_weighted"] == 0.85

    def test_load_nonexistent_raises(self, registry):
        """Loading a model that does not exist should raise an error."""
        with pytest.raises(SafetyClassificationError, match="not found"):
            registry.load_model("nonexistent_model")


class TestModelEntrySerialization:
    def test_model_entry_round_trip(self, sample_entry):
        """ModelEntry should survive dict serialisation and reconstruction."""
        data = sample_entry.model_dump()
        reconstructed = ModelEntry(**data)
        assert reconstructed.model_name == sample_entry.model_name
        assert reconstructed.metrics == sample_entry.metrics
        assert reconstructed.params == sample_entry.params


class TestListModels:
    def test_list_models_returns_all(self, registry, sample_model, registry_dir):
        """Saving multiple models then listing returns all of them."""
        names = ["model_a", "model_b", "model_c"]
        for name in names:
            entry = ModelEntry(
                model_name=name,
                classifier_type="random_forest",
                metrics={"f1_weighted": 0.80},
                model_path=registry_dir / name / "model.joblib",
            )
            registry.save_model(sample_model, entry)

        entries = registry.list_models()
        assert len(entries) == 3
        listed_names = {e.model_name for e in entries}
        assert listed_names == set(names)

    def test_list_models_empty(self, registry):
        """An empty registry should return an empty list."""
        assert registry.list_models() == []


class TestGetBestModel:
    def test_get_best_model_by_f1(self, registry, sample_model, registry_dir):
        """get_best_model returns the model with the highest metric value."""
        scores = [0.70, 0.95, 0.80]
        for i, score in enumerate(scores):
            name = f"model_{i}"
            entry = ModelEntry(
                model_name=name,
                classifier_type="random_forest",
                metrics={"f1_weighted": score},
                model_path=registry_dir / name / "model.joblib",
            )
            registry.save_model(sample_model, entry)

        _, best_entry = registry.get_best_model(metric="f1_weighted")
        assert best_entry.model_name == "model_1"
        assert best_entry.metrics["f1_weighted"] == 0.95

    def test_get_best_model_empty_registry_raises(self, registry):
        """get_best_model on an empty registry should raise."""
        with pytest.raises(SafetyClassificationError, match="No models"):
            registry.get_best_model()


class TestDeleteModel:
    def test_delete_model_removes_files(self, registry, sample_model, sample_entry):
        """Deleted model should no longer be loadable or listed."""
        registry.save_model(sample_model, sample_entry)
        assert len(registry.list_models()) == 1

        registry.delete_model("test_rf_model")
        assert len(registry.list_models()) == 0

        with pytest.raises(SafetyClassificationError, match="not found"):
            registry.load_model("test_rf_model")

    def test_delete_nonexistent_raises(self, registry):
        """Deleting a model that does not exist should raise."""
        with pytest.raises(SafetyClassificationError, match="not found"):
            registry.delete_model("ghost_model")
