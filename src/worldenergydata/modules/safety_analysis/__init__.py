"""
Safety Analysis Module - Technical Safety Data Analysis

This module provides configurable safety analysis tools for HSE
(Health, Safety, Environment) data including:
- NLP classification of safety observations (TF-IDF + ML classifiers)
- Observation-incident lag correlation analysis
- Time series feature engineering (30+ statistical/FFT features)
- Incident aggregation and hurt index computation
- Seasonal decomposition and trend analysis
- Statistical hypothesis testing (t-test, ANOVA, chi-square)
- Configurable schema mappings for any data source

Ported from the ENIGMA project and generalized for multi-client use.

Example usage:
    from worldenergydata.modules.safety_analysis import (
        SafetyObservation,
        SafetyIncident,
        SafetyDataLoader,
        ObservationProcessor,
        SchemaMapping,
        SchemaRegistry,
        AnalysisConfig,
    )

    # Load and process observations
    loader = SafetyDataLoader()
    raw_df = loader.load("observations.csv")

    schema = SchemaMapping(
        name="my_source",
        asset_id_column="rig_id",
        datetime_column="date",
        description_column="description",
    )
    processor = ObservationProcessor(schema)
    observations = processor.process(raw_df)
"""

from worldenergydata.modules.safety_analysis.config import AnalysisConfig
from worldenergydata.modules.safety_analysis.constants import (
    ClassifierType,
    FeatureType,
    IncidentType,
    ObservationType,
    SeverityLevel,
)
from worldenergydata.modules.safety_analysis.core.models import (
    ClassificationResult,
    CorrelationResult,
    SafetyIncident,
    SafetyObservation,
)
from worldenergydata.modules.safety_analysis.core.schemas import (
    SchemaMapping,
    SchemaRegistry,
)
from worldenergydata.modules.safety_analysis.data.loaders import SafetyDataLoader
from worldenergydata.modules.safety_analysis.data.processors import (
    IncidentProcessor,
    ObservationProcessor,
)
from worldenergydata.modules.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyAnalysisError,
    SafetyClassificationError,
    SafetyConfigError,
    SafetyCorrelationError,
    SafetyDataError,
)

# NLP components
from worldenergydata.modules.safety_analysis.nlp import (
    ClassificationPipeline,
    ModelEntry,
    ModelRegistry,
    SafetyTfidfVectorizer,
    TextPreprocessor,
)

__version__ = "0.1.0"
__all__ = [
    # Config
    "AnalysisConfig",
    # Constants
    "SeverityLevel",
    "ObservationType",
    "IncidentType",
    "ClassifierType",
    "FeatureType",
    # Models
    "SafetyObservation",
    "SafetyIncident",
    "ClassificationResult",
    "CorrelationResult",
    # Schemas
    "SchemaMapping",
    "SchemaRegistry",
    # Data
    "SafetyDataLoader",
    "ObservationProcessor",
    "IncidentProcessor",
    # Exceptions
    "SafetyAnalysisError",
    "SafetyDataError",
    "SafetyClassificationError",
    "SafetyCorrelationError",
    "SafetyConfigError",
    "OptionalDependencyError",
    # NLP
    "TextPreprocessor",
    "SafetyTfidfVectorizer",
    "ModelEntry",
    "ModelRegistry",
    "ClassificationPipeline",
]
