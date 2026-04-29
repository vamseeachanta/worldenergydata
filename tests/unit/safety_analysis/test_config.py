"""Tests for safety analysis configuration models."""

from pathlib import Path

from worldenergydata.safety_analysis.config import (
    AnalysisConfig,
    CorrelationConfig,
    HyperparamConfig,
    NLPConfig,
)


class TestNLPConfig:
    def test_defaults(self):
        c = NLPConfig()
        assert c.min_token_length == 2
        assert c.max_token_length == 50
        assert c.lowercase is True
        assert c.analyzer == "word"
        assert c.max_features is None
        assert c.ngram_range == (1, 1)
        assert c.stop_words_file is None
        assert c.custom_stop_words == []

    def test_custom(self):
        c = NLPConfig(
            min_token_length=3,
            custom_stop_words=["the", "and"],
            ngram_range=(1, 2),
            max_features=5000,
        )
        assert c.min_token_length == 3
        assert c.custom_stop_words == ["the", "and"]
        assert c.ngram_range == (1, 2)
        assert c.max_features == 5000


class TestHyperparamConfig:
    def test_defaults(self):
        c = HyperparamConfig()
        assert c.max_evals == 50
        assert c.cv_folds == 5
        assert c.scoring_metric == "f1_weighted"
        assert c.random_state == 42
        assert c.test_size == 0.2

    def test_custom(self):
        c = HyperparamConfig(max_evals=100, cv_folds=10, test_size=0.3)
        assert c.max_evals == 100
        assert c.cv_folds == 10
        assert c.test_size == 0.3


class TestCorrelationConfig:
    def test_defaults(self):
        c = CorrelationConfig()
        assert c.lag_min == -30
        assert c.lag_max == 30
        assert c.rolling_window == 7
        assert c.min_observations == 30
        assert c.frequency == "D"

    def test_custom(self):
        c = CorrelationConfig(lag_max=60, frequency="W-SUN")
        assert c.lag_max == 60
        assert c.frequency == "W-SUN"


class TestAnalysisConfig:
    def test_defaults(self):
        c = AnalysisConfig()
        assert c.data_dir.is_absolute()
        assert c.data_dir.name == "safety_analysis"
        assert c.data_dir.parent.name == "data"
        assert c.model_dir == Path("models/safety_analysis")
        assert c.default_frequency == "D"
        assert c.window_size == 10
        assert c.step_size == 1

    def test_nested_nlp(self):
        c = AnalysisConfig()
        assert isinstance(c.nlp, NLPConfig)
        assert c.nlp.lowercase is True

    def test_nested_hyperparams(self):
        c = AnalysisConfig()
        assert isinstance(c.hyperparams, HyperparamConfig)
        assert c.hyperparams.random_state == 42

    def test_nested_correlation(self):
        c = AnalysisConfig()
        assert isinstance(c.correlation, CorrelationConfig)
        assert c.correlation.lag_max == 30

    def test_bert_defaults(self):
        c = AnalysisConfig()
        assert c.bert_model_name == "bert-base-uncased"
        assert c.bert_max_length == 512
        assert c.bert_batch_size == 32
        assert c.bert_device == "cpu"
        assert c.bert_pooling == "cls"

    def test_ensure_directories(self, tmp_path):
        c = AnalysisConfig(
            data_dir=tmp_path / "data",
            model_dir=tmp_path / "models",
            report_dir=tmp_path / "reports",
        )
        c.ensure_directories()
        assert (tmp_path / "data").is_dir()
        assert (tmp_path / "models").is_dir()
        assert (tmp_path / "reports").is_dir()
