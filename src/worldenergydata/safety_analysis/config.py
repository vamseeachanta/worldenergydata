"""
Safety Analysis Configuration

Pydantic settings for the safety analysis module, loaded from
environment variables with the SAFETY_ prefix.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from worldenergydata.common.data_resolver import get_data_root_safe


class NLPConfig(BaseModel):
    """Configuration for NLP text processing."""

    stop_words_file: Optional[Path] = None
    custom_stop_words: List[str] = Field(default_factory=list)
    min_token_length: int = 2
    max_token_length: int = 50
    lowercase: bool = True
    analyzer: str = "word"
    max_features: Optional[int] = None
    ngram_range: tuple = (1, 1)


class HyperparamConfig(BaseModel):
    """Configuration for hyperparameter optimization."""

    max_evals: int = 50
    cv_folds: int = 5
    scoring_metric: str = "f1_weighted"
    random_state: int = 42
    test_size: float = 0.2


class CorrelationConfig(BaseModel):
    """Configuration for correlation analysis."""

    lag_min: int = -30
    lag_max: int = 30
    rolling_window: int = 7
    min_observations: int = 30
    frequency: str = "D"


class AnalysisConfig(BaseSettings):
    """Main configuration for safety analysis module."""

    model_config = {"env_prefix": "SAFETY_", "case_sensitive": False}

    # Data paths
    data_dir: Path = Field(default_factory=lambda: get_data_root_safe() / "safety_analysis")
    model_dir: Path = Path("models/safety_analysis")
    report_dir: Path = Path("reports/safety_analysis")

    # Analysis settings
    default_frequency: str = "D"
    window_size: int = 10
    step_size: int = 1

    # NLP settings
    nlp: NLPConfig = Field(default_factory=NLPConfig)

    # Hyperparameter optimization
    hyperparams: HyperparamConfig = Field(default_factory=HyperparamConfig)

    # Correlation settings
    correlation: CorrelationConfig = Field(default_factory=CorrelationConfig)

    # BERT settings
    bert_model_name: str = "bert-base-uncased"
    bert_max_length: int = 512
    bert_batch_size: int = 32
    bert_device: str = "cpu"
    bert_pooling: str = "cls"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [self.data_dir, self.model_dir, self.report_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
