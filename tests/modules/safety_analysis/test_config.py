"""Tests for safety analysis configuration."""

from worldenergydata.safety_analysis.config import (
    AnalysisConfig,
    CorrelationConfig,
    HyperparamConfig,
    NLPConfig,
)


class TestNLPConfig:
    def test_defaults(self):
        config = NLPConfig()
        assert config.lowercase is True
        assert config.analyzer == "word"
        assert config.min_token_length == 2
        assert config.custom_stop_words == []

    def test_custom_stop_words(self):
        config = NLPConfig(custom_stop_words=["rig", "drill"])
        assert "rig" in config.custom_stop_words


class TestHyperparamConfig:
    def test_defaults(self):
        config = HyperparamConfig()
        assert config.max_evals == 50
        assert config.cv_folds == 5
        assert config.random_state == 42
        assert config.test_size == 0.2


class TestCorrelationConfig:
    def test_defaults(self):
        config = CorrelationConfig()
        assert config.lag_min == -30
        assert config.lag_max == 30
        assert config.rolling_window == 7
        assert config.min_observations == 30


class TestAnalysisConfig:
    def test_defaults(self):
        config = AnalysisConfig()
        assert config.window_size == 10
        assert config.step_size == 1
        assert config.default_frequency == "D"

    def test_nested_configs(self):
        config = AnalysisConfig()
        assert isinstance(config.nlp, NLPConfig)
        assert isinstance(config.hyperparams, HyperparamConfig)
        assert isinstance(config.correlation, CorrelationConfig)

    def test_ensure_directories(self, tmp_path):
        config = AnalysisConfig(
            data_dir=tmp_path / "data",
            model_dir=tmp_path / "models",
            report_dir=tmp_path / "reports",
        )
        config.ensure_directories()
        assert (tmp_path / "data").exists()
        assert (tmp_path / "models").exists()
        assert (tmp_path / "reports").exists()
