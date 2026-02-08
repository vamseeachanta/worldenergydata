# ABOUTME: Tests for SafetyTfidfVectorizer — fit/transform, feature names,
# max_features, ngram_range, save/load persistence, and error handling.
"""Tests for safety analysis TF-IDF vectorizer."""

import pytest

try:
    import sklearn  # noqa: F401

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

pytestmark = pytest.mark.skipif(not _HAS_SKLEARN, reason="scikit-learn not installed")

from scipy import sparse  # noqa: E402

from worldenergydata.safety_analysis.config import (  # noqa: E402
    AnalysisConfig,
    NLPConfig,
)
from worldenergydata.safety_analysis.nlp.tfidf_vectorizer import (  # noqa: E402
    SafetyTfidfVectorizer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_texts():
    """Small corpus of safety-domain sentences."""
    return [
        "worker fell from ladder during maintenance",
        "safety harness properly worn at all times",
        "spill contained immediately by response team",
        "equipment inspection completed before operations",
        "near miss avoided due to quick response",
    ]


@pytest.fixture
def vectorizer():
    """SafetyTfidfVectorizer with bounded feature count."""
    config = NLPConfig(max_features=100)
    return SafetyTfidfVectorizer(config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFitTransform:
    def test_fit_transform_returns_sparse(self, vectorizer, sample_texts):
        """fit_transform should return a sparse matrix."""
        matrix = vectorizer.fit_transform(sample_texts)
        assert sparse.issparse(matrix)

    def test_fit_transform_shape(self, vectorizer, sample_texts):
        """Rows should match number of documents."""
        matrix = vectorizer.fit_transform(sample_texts)
        assert matrix.shape[0] == len(sample_texts)

    def test_transform_after_fit(self, vectorizer, sample_texts):
        """transform() after fit() should produce the same column count."""
        vectorizer.fit(sample_texts)
        matrix = vectorizer.transform(sample_texts)
        assert sparse.issparse(matrix)
        assert matrix.shape[0] == len(sample_texts)

    def test_transform_without_fit_raises(self, vectorizer, sample_texts):
        """Calling transform() before fit() should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="fitted"):
            vectorizer.transform(sample_texts)


class TestFeatures:
    def test_get_feature_names_returns_strings(self, vectorizer, sample_texts):
        """get_feature_names returns a list of strings after fitting."""
        vectorizer.fit(sample_texts)
        names = vectorizer.get_feature_names()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)
        assert len(names) > 0

    def test_max_features_respected(self, sample_texts):
        """Matrix width should not exceed max_features."""
        config = NLPConfig(max_features=5)
        vec = SafetyTfidfVectorizer(config)
        matrix = vec.fit_transform(sample_texts)
        assert matrix.shape[1] <= 5

    def test_ngram_range_produces_bigrams(self, sample_texts):
        """ngram_range=(1,2) should include bigram features."""
        config = NLPConfig(ngram_range=(1, 2), max_features=200)
        vec = SafetyTfidfVectorizer(config)
        vec.fit(sample_texts)
        names = vec.get_feature_names()
        # At least some features should contain a space (bigrams)
        bigrams = [n for n in names if " " in n]
        assert len(bigrams) > 0

    def test_vocabulary_size_property(self, vectorizer, sample_texts):
        """vocabulary_size should be positive after fitting."""
        assert vectorizer.vocabulary_size == 0
        vectorizer.fit(sample_texts)
        assert vectorizer.vocabulary_size > 0


class TestPersistence:
    def test_save_and_load(self, vectorizer, sample_texts, tmp_path):
        """Saved then loaded vectorizer should produce identical transforms."""
        vectorizer.fit(sample_texts)
        original_matrix = vectorizer.transform(sample_texts)

        save_path = tmp_path / "vec.joblib"
        vectorizer.save(save_path)

        loaded = SafetyTfidfVectorizer.load(save_path)
        loaded_matrix = loaded.transform(sample_texts)

        # Shapes and values must match
        assert original_matrix.shape == loaded_matrix.shape
        diff = abs(original_matrix - loaded_matrix).sum()
        assert diff < 1e-10

    def test_load_nonexistent_raises(self, tmp_path):
        """Loading from a missing path should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SafetyTfidfVectorizer.load(tmp_path / "no_such_file.joblib")


class TestConfigIntegration:
    def test_config_from_analysis_config(self, sample_texts):
        """Vectorizer can be created from AnalysisConfig().nlp."""
        analysis_cfg = AnalysisConfig()
        vec = SafetyTfidfVectorizer(analysis_cfg.nlp)
        matrix = vec.fit_transform(sample_texts)
        assert matrix.shape[0] == len(sample_texts)
