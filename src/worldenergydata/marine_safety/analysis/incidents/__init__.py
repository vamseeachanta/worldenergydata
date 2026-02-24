"""
Incident-Specific Analysis Modules

This package contains specialized analyzers for specific types of marine
safety incidents, such as hatch maloperation, foundering, collisions, etc.

WRK-320 additions:
    incident_taxonomy    — IMO/MAIB root-cause taxonomy and DataFrame normaliser
    uscg_client          — USCG MISLE public CSV loader
    incident_correlator  — Cross-database correlation (MAIB/NTSB/USCG) and pattern report
"""

from worldenergydata.marine_safety.analysis.incidents.hatch_maloperation_analysis import (
    HatchMaloperationAnalyzer,
)
from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    IncidentDataFrameNormaliser,
    IncidentTaxonomyClassifier,
    RootCauseType,
    TaxonomyRecord,
    build_taxonomy_summary,
)
from worldenergydata.marine_safety.analysis.incidents.uscg_client import (
    load_dataframe_as_uscg,
    load_uscg_csv,
    load_uscg_csv_to_records,
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
    # USCG loader
    "load_uscg_csv",
    "load_uscg_csv_to_records",
    "load_dataframe_as_uscg",
    # Correlator
    "CorrelationConfig",
    "CorrelationMatch",
    "IncidentCorrelator",
    "build_correlation_summary",
    "build_pattern_report",
]
