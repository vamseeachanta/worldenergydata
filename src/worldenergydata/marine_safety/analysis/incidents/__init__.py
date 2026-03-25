"""
Incident-Specific Analysis Modules

This package contains specialized analyzers for specific types of marine
safety incidents, such as hatch maloperation, foundering, collisions, etc.

WRK-320 additions:
    incident_taxonomy    — IMO/MAIB root-cause taxonomy and DataFrame normaliser
    uscg_client          — USCG MISLE public CSV loader
    maib_loader          — MAIB occurrence CSV loader (taxonomy pipeline)
    ntsb_marine_loader   — NTSB CAROL API loader (taxonomy pipeline)
    incident_correlator  — Cross-database correlation (MAIB/NTSB/USCG) and pattern report
"""

from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
    HatchMaloperationAnalyzer,
)
from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    IncidentDataFrameNormaliser,
    IncidentTaxonomyClassifier,
    MISLE_OPERATION_COLUMN,
    OperationPhase,
    OperationPhaseClassifier,
    RootCauseType,
    TaxonomyRecord,
    build_taxonomy_summary,
)
from worldenergydata.marine_safety.analysis.incidents.uscg_client import (
    load_dataframe_as_uscg,
    load_uscg_csv,
    load_uscg_csv_to_records,
)
from worldenergydata.marine_safety.analysis.incidents.maib_loader import (
    MAIBLoader,
    describe_maib_dataset,
    load_dataframe_as_maib,
    load_maib_csv,
    load_maib_csv_to_records,
)
from worldenergydata.marine_safety.analysis.incidents.ntsb_marine_loader import (
    NTSBMarineLoader,
    fetch_ntsb_marine,
    load_dataframe_as_ntsb,
)
from worldenergydata.marine_safety.analysis.incidents.incident_correlator import (
    CorrelationConfig,
    CorrelationMatch,
    IncidentCorrelator,
    build_correlation_summary,
    build_pattern_report,
)

__all__ = [
    "HatchMaloperationAnalyzer",
    # Taxonomy
    "RootCauseType",
    "TaxonomyRecord",
    "IncidentTaxonomyClassifier",
    "IncidentDataFrameNormaliser",
    "build_taxonomy_summary",
    # Operation phase
    "OperationPhase",
    "OperationPhaseClassifier",
    "MISLE_OPERATION_COLUMN",
    # USCG loader
    "load_uscg_csv",
    "load_uscg_csv_to_records",
    "load_dataframe_as_uscg",
    # MAIB loader
    "MAIBLoader",
    "load_maib_csv",
    "load_maib_csv_to_records",
    "load_dataframe_as_maib",
    "describe_maib_dataset",
    # NTSB marine loader
    "NTSBMarineLoader",
    "fetch_ntsb_marine",
    "load_dataframe_as_ntsb",
    # Correlator
    "CorrelationConfig",
    "CorrelationMatch",
    "IncidentCorrelator",
    "build_correlation_summary",
    "build_pattern_report",
]
