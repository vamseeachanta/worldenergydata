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

Generalized safety analysis toolkit for multi-client use.

Example usage:
    from worldenergydata.safety_analysis import (
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

# Adapters
from worldenergydata.safety_analysis.adapters import (
    BaseAdapter,
    CSVAdapter,
    HSEAdapter,
)

# Calibrator
from worldenergydata.safety_analysis.calibrator import (
    HSE_TO_ENIGMA_MAP,
    MIN_INCIDENTS_FOR_CALIBRATION,
    CalibrationRecord,
    CalibrationReport,
    EnigmaCalibrator,
)
from worldenergydata.safety_analysis.config import AnalysisConfig
from worldenergydata.safety_analysis.constants import (
    ClassifierType,
    FeatureType,
    IncidentType,
    ObservationType,
    SeverityLevel,
)
from worldenergydata.safety_analysis.core.models import (
    ClassificationResult,
    CorrelationResult,
    SafetyIncident,
    SafetyObservation,
)
from worldenergydata.safety_analysis.core.schemas import (
    SchemaMapping,
    SchemaRegistry,
)
from worldenergydata.safety_analysis.data.loaders import SafetyDataLoader
from worldenergydata.safety_analysis.data.processors import (
    IncidentProcessor,
    ObservationProcessor,
)
from worldenergydata.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyAnalysisError,
    SafetyClassificationError,
    SafetyConfigError,
    SafetyCorrelationError,
    SafetyDataError,
)

# NLP components
from worldenergydata.safety_analysis.nlp import (
    BertClassificationPipeline,
    BertConfig,
    BertEmbedder,
    ClassificationPipeline,
    ModelEntry,
    ModelRegistry,
    SafetyTfidfVectorizer,
    TextPreprocessor,
)

# Reports
from worldenergydata.safety_analysis.reports import (
    BaseReport,
    ClassificationReport,
    CorrelationReport,
    IncidentReport,
    ReportSection,
    SummaryStat,
)

# Risk Index
from worldenergydata.safety_analysis.risk_index import (
    ActivityRiskScore,
    CompositeScore,
    DataAssembler,
    DimensionScore,
    NormalizationResult,
    RiskCategory,
    RiskDashboard,
    RiskScorer,
    generate_methodology_html,
    normalize_to_scale,
    percentile_rank,
    risk_index_app,
)

# Skill
from worldenergydata.safety_analysis.skill import (
    SKILL_NAME,
    EnigmaResult,
    enigma_safety_analysis,
)

__version__ = "0.1.0"
__all__ = [
    # Calibrator
    "EnigmaCalibrator",
    "CalibrationReport",
    "CalibrationRecord",
    "HSE_TO_ENIGMA_MAP",
    "MIN_INCIDENTS_FOR_CALIBRATION",
    # Skill
    "enigma_safety_analysis",
    "EnigmaResult",
    "SKILL_NAME",
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
    "BertConfig",
    "BertEmbedder",
    "BertClassificationPipeline",
    # Adapters
    "BaseAdapter",
    "HSEAdapter",
    "CSVAdapter",
    # Reports
    "BaseReport",
    "ReportSection",
    "SummaryStat",
    "IncidentReport",
    "CorrelationReport",
    "ClassificationReport",
    # Risk Index
    "ActivityRiskScore",
    "CompositeScore",
    "DataAssembler",
    "DimensionScore",
    "NormalizationResult",
    "RiskCategory",
    "RiskDashboard",
    "RiskScorer",
    "generate_methodology_html",
    "normalize_to_scale",
    "percentile_rank",
    "risk_index_app",
]
