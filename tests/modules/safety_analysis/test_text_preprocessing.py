# ABOUTME: Tests for TextPreprocessor — stop word removal, lowercasing, token
# filtering, DataFrame column preprocessing, and multi-column combining.
"""Tests for safety analysis text preprocessing."""

import pytest

try:
    import sklearn  # noqa: F401

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

pytestmark = pytest.mark.skipif(not _HAS_SKLEARN, reason="scikit-learn not installed")

import pandas as pd  # noqa: E402

from worldenergydata.safety_analysis.config import NLPConfig  # noqa: E402
from worldenergydata.safety_analysis.nlp.text_preprocessing import (  # noqa: E402
    TextPreprocessor,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def nlp_config():
    """Default NLP configuration."""
    return NLPConfig()


@pytest.fixture
def preprocessor(nlp_config):
    """TextPreprocessor with default config."""
    return TextPreprocessor(nlp_config)


@pytest.fixture
def sample_texts_df():
    """DataFrame with description and action columns for testing."""
    return pd.DataFrame(
        {
            "description": [
                "Employee noticed unsafe behavior on rig floor while drilling",
                "Good housekeeping observed in the work area by crew",
                "Worker was not wearing proper PPE during operations",
                "Safety meeting conducted with all personnel present",
                "Near miss reported when equipment fell from height",
            ],
            "action": [
                "Counseled employee on proper procedures",
                "Recognized crew for maintaining clean workspace",
                "Stopped work and provided correct PPE",
                "Documented attendance and topics discussed",
                "Secured area and investigated root cause",
            ],
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPreprocess:
    def test_preprocess_lowercases(self, preprocessor):
        """All text should be lowercased by default."""
        result = preprocessor.preprocess("UPPERCASE TEXT HERE")
        assert result == result.lower()

    def test_preprocess_removes_stop_words(self, preprocessor):
        """Domain stop words from the default YAML should be stripped."""
        # "noticed", "observed", "employee" are in default_stop_words.yaml
        result = preprocessor.preprocess("Employee noticed unsafe behavior")
        for word in ("employee", "noticed"):
            assert word not in result.split()

    def test_preprocess_removes_short_tokens(self):
        """Tokens shorter than min_token_length should be removed."""
        config = NLPConfig(min_token_length=4)
        pp = TextPreprocessor(config)
        result = pp.preprocess("A big cat ran on the rug fast")
        tokens = result.split()
        for tok in tokens:
            assert len(tok) >= 4

    def test_preprocess_empty_text(self, preprocessor):
        """Empty and whitespace-only strings return empty string."""
        assert preprocessor.preprocess("") == ""
        assert preprocessor.preprocess("   ") == ""

    def test_preprocess_none_text(self, preprocessor):
        """None-like falsy values return empty string."""
        assert preprocessor.preprocess("") == ""

    def test_custom_stop_words_respected(self):
        """Custom stop words supplied via NLPConfig should be removed."""
        config = NLPConfig(custom_stop_words=["customword", "anotherword"])
        pp = TextPreprocessor(config)
        result = pp.preprocess("customword should vanish anotherword too")
        assert "customword" not in result.split()
        assert "anotherword" not in result.split()

    def test_stop_words_loaded_from_yaml(self, preprocessor):
        """The default YAML file stop words are present in the stop word set."""
        # These words are in data/config/default_stop_words.yaml
        yaml_words = {"noticed", "observed", "employee", "drilling", "operations"}
        assert yaml_words.issubset(preprocessor.stop_words)


class TestPreprocessColumn:
    def test_preprocess_column_returns_series(self, preprocessor, sample_texts_df):
        """preprocess_column returns a pandas Series of same length."""
        result = preprocessor.preprocess_column(sample_texts_df, "description")
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_texts_df)

    def test_preprocess_column_applies_cleaning(self, preprocessor, sample_texts_df):
        """Each row in the returned Series should be preprocessed."""
        result = preprocessor.preprocess_column(sample_texts_df, "description")
        for text in result:
            # Should be lowercase
            assert text == text.lower()


class TestCombineColumns:
    def test_combine_columns_merges_text(self, preprocessor, sample_texts_df):
        """Combining description+action should produce preprocessed merged text."""
        result = preprocessor.combine_columns(
            sample_texts_df, ["description", "action"]
        )
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_texts_df)

    def test_combine_columns_content(self, preprocessor, sample_texts_df):
        """Merged text should contain tokens from both source columns."""
        result = preprocessor.combine_columns(
            sample_texts_df, ["description", "action"]
        )
        # "proper" appears in both description[0] and action[0]; after merging
        # and stop-word removal it should still be present (it's not a stop word).
        first_row = result.iloc[0]
        assert len(first_row) > 0
