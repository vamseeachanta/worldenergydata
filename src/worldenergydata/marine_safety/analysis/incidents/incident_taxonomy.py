"""
ABOUTME: IMO/MAIB-aligned root-cause taxonomy for multi-source incident correlation.
ABOUTME: Classifies incidents from MAIB, NTSB, and USCG MISLE into a unified schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd


class RootCauseType(str, Enum):
    """
    IMO/MAIB standard root-cause taxonomy.

    Aligned with:
    - MAIB occurrence categorisation (UK MAIB Annual Report taxonomy)
    - IMO Casualty Investigation Code (Circular MSC-MEPC.3/Circ.4)
    - USCG MISLE cause codes
    - NTSB probable cause framework
    """

    HUMAN_ERROR = "human_error"
    """Operator error, watchkeeping failure, decision-making failure."""

    EQUIPMENT_FAILURE = "equipment_failure"
    """Mechanical, electrical, or instrumentation system failure."""

    ENVIRONMENTAL = "environmental"
    """Adverse weather, sea state, current, tidal conditions."""

    PROCEDURE = "procedure"
    """Inadequate procedures, non-compliance, SMS deficiency."""

    DESIGN_DEFECT = "design_defect"
    """Inherent design issue, classification deficiency, type approval gap."""

    MANAGEMENT = "management"
    """Organisational failure, safety culture, supervision deficiency."""

    UNKNOWN = "unknown"
    """Insufficient data to determine root cause."""


# ---------------------------------------------------------------------------
# Source-specific keyword mappings
# ---------------------------------------------------------------------------

# Each entry maps a keyword pattern (lower-cased) to a RootCauseType.
# Ordered from most-specific to most-general within each category.

_KEYWORD_MAP: List[tuple[str, RootCauseType]] = [
    # Human error — MAIB/NTSB terminology
    ("watchkeeping", RootCauseType.HUMAN_ERROR),
    ("inattention", RootCauseType.HUMAN_ERROR),
    ("misidentif", RootCauseType.HUMAN_ERROR),
    ("misjudg", RootCauseType.HUMAN_ERROR),
    ("operator error", RootCauseType.HUMAN_ERROR),
    ("human error", RootCauseType.HUMAN_ERROR),
    ("crew error", RootCauseType.HUMAN_ERROR),
    ("navigat.*error", RootCauseType.HUMAN_ERROR),
    ("fatigue", RootCauseType.HUMAN_ERROR),
    ("intoxicat", RootCauseType.HUMAN_ERROR),
    ("distract", RootCauseType.HUMAN_ERROR),
    ("decision", RootCauseType.HUMAN_ERROR),
    ("lookout", RootCauseType.HUMAN_ERROR),
    ("bridge team", RootCauseType.HUMAN_ERROR),
    ("personnel error", RootCauseType.HUMAN_ERROR),
    # Equipment failure — USCG MISLE / MAIB
    ("machinery failure", RootCauseType.EQUIPMENT_FAILURE),
    ("equipment failure", RootCauseType.EQUIPMENT_FAILURE),
    ("mechanical failure", RootCauseType.EQUIPMENT_FAILURE),
    ("steering.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("propulsion.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("engine.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("electrical.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("instrument.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("sensor.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("valve.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("pump.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("hatch.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("component.*fail", RootCauseType.EQUIPMENT_FAILURE),
    ("malfunction", RootCauseType.EQUIPMENT_FAILURE),
    # Environmental
    ("adverse weather", RootCauseType.ENVIRONMENTAL),
    ("severe weather", RootCauseType.ENVIRONMENTAL),
    ("heavy seas", RootCauseType.ENVIRONMENTAL),
    ("rough seas", RootCauseType.ENVIRONMENTAL),
    ("high winds", RootCauseType.ENVIRONMENTAL),
    ("restricted visibility", RootCauseType.ENVIRONMENTAL),
    ("fog", RootCauseType.ENVIRONMENTAL),
    ("sea state", RootCauseType.ENVIRONMENTAL),
    ("tidal current", RootCauseType.ENVIRONMENTAL),
    ("storm", RootCauseType.ENVIRONMENTAL),
    ("hurricane", RootCauseType.ENVIRONMENTAL),
    ("wave", RootCauseType.ENVIRONMENTAL),
    # Procedure
    ("inadequate procedure", RootCauseType.PROCEDURE),
    ("non-compliance", RootCauseType.PROCEDURE),
    ("sms.*deficien", RootCauseType.PROCEDURE),
    ("safety management", RootCauseType.PROCEDURE),
    ("procedural.*violation", RootCauseType.PROCEDURE),
    ("permit.*work", RootCauseType.PROCEDURE),
    ("lockout.*tagout", RootCauseType.PROCEDURE),
    ("procedure not followed", RootCauseType.PROCEDURE),
    # Design defect
    ("design.*defect", RootCauseType.DESIGN_DEFECT),
    ("design.*deficien", RootCauseType.DESIGN_DEFECT),
    ("structural.*defect", RootCauseType.DESIGN_DEFECT),
    ("type approval", RootCauseType.DESIGN_DEFECT),
    ("classification.*deficien", RootCauseType.DESIGN_DEFECT),
    ("inherent.*design", RootCauseType.DESIGN_DEFECT),
    # Management
    ("safety culture", RootCauseType.MANAGEMENT),
    ("organisational.*failure", RootCauseType.MANAGEMENT),
    ("organizational.*failure", RootCauseType.MANAGEMENT),
    ("management.*failure", RootCauseType.MANAGEMENT),
    ("supervision.*deficien", RootCauseType.MANAGEMENT),
    ("inadequate.*supervision", RootCauseType.MANAGEMENT),
    ("company.*failure", RootCauseType.MANAGEMENT),
    ("shore.*management", RootCauseType.MANAGEMENT),
]


# ---------------------------------------------------------------------------
# Source-specific field name normalisers
# ---------------------------------------------------------------------------

# Maps from raw source column names to canonical names used internally.
USCG_COLUMN_MAP: Dict[str, str] = {
    "REPORT_NUM": "report_id",
    "MASTER_KEY": "report_id",
    "VESSEL_NAME": "vessel_name",
    "VES_NAME": "vessel_name",
    "EVENT_DATE": "incident_date",
    "DATE": "incident_date",
    "LATITUDE": "latitude",
    "LAT": "latitude",
    "LONGITUDE": "longitude",
    "LON": "longitude",
    "CASUALTY_TYPE": "incident_type",
    "PRIMARY_CAUSE": "primary_cause",
    "NARRATIVE": "narrative",
    "INJURY_COUNT": "injury_count",
    "FATALITY_COUNT": "fatality_count",
    "VESSEL_TYPE": "vessel_type",
    "VES_TYPE": "vessel_type",
}

MAIB_COLUMN_MAP: Dict[str, str] = {
    "Occurrence_Id": "report_id",
    "Date": "incident_date",
    "Accident_Title": "title",
    "Main_Event": "incident_type",
    "Abstract": "narrative",
    "Vessel_Name": "vessel_name",
    "Vessel_Type": "vessel_type",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Deaths": "fatality_count",
    "Injuries": "injury_count",
}

NTSB_COLUMN_MAP: Dict[str, str] = {
    "EventId": "report_id",
    "EventDate": "incident_date",
    "AccidentTitle": "title",
    "IncidentType": "incident_type",
    "ProbableCause": "primary_cause",
    "Narrative": "narrative",
    "VesselName": "vessel_name",
    "VesselType": "vessel_type",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "FatalCount": "fatality_count",
    "InjuryCount": "injury_count",
}


# ---------------------------------------------------------------------------
# Core dataclass
# ---------------------------------------------------------------------------


@dataclass
class TaxonomyRecord:
    """
    A single incident record normalised to the shared taxonomy schema.

    Attributes:
        report_id: Source-specific report identifier.
        source: Data source agency (uscg, maib, ntsb).
        incident_date: Date of incident (ISO 8601 string or None).
        vessel_name: Vessel name as reported.
        vessel_type: Vessel type, normalised.
        incident_type: Type/category of incident.
        root_cause: Classified root-cause type.
        raw_cause: Original cause text before classification.
        narrative: Incident narrative text.
        latitude: Decimal latitude, or None.
        longitude: Decimal longitude, or None.
        fatality_count: Number of fatalities recorded.
        injury_count: Number of injuries recorded.
        extra: Additional source-specific fields.
    """

    report_id: str
    source: str
    incident_date: Optional[str]
    vessel_name: Optional[str]
    vessel_type: Optional[str]
    incident_type: Optional[str]
    root_cause: RootCauseType
    raw_cause: Optional[str]
    narrative: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    fatality_count: int = 0
    injury_count: int = 0
    extra: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Taxonomy classifier
# ---------------------------------------------------------------------------


class IncidentTaxonomyClassifier:
    """
    Classifies marine incidents into the IMO/MAIB root-cause taxonomy.

    Operates on free-text cause descriptions and incident narratives.
    Applies a priority-ordered keyword scan with regex support.
    """

    def __init__(self) -> None:
        # Pre-compile all patterns for efficiency
        self._compiled: List[tuple[re.Pattern, RootCauseType]] = [
            (re.compile(pat, re.IGNORECASE), cat)
            for pat, cat in _KEYWORD_MAP
        ]

    def classify(
        self,
        primary_cause: Optional[str] = None,
        narrative: Optional[str] = None,
    ) -> RootCauseType:
        """
        Classify an incident into a RootCauseType.

        Args:
            primary_cause: Primary cause field from the source record.
            narrative: Narrative / description text.

        Returns:
            RootCauseType enum value.
        """
        candidates = [
            str(primary_cause) if primary_cause else "",
            str(narrative) if narrative else "",
        ]
        combined = " ".join(c for c in candidates if c).strip()
        if not combined:
            return RootCauseType.UNKNOWN

        for pattern, cause_type in self._compiled:
            if pattern.search(combined):
                return cause_type

        return RootCauseType.UNKNOWN

    def classify_dataframe(
        self,
        df: pd.DataFrame,
        cause_col: str = "primary_cause",
        narrative_col: str = "narrative",
    ) -> pd.Series:
        """
        Classify all rows in a DataFrame.

        Args:
            df: DataFrame with incident records.
            cause_col: Column name for primary cause text.
            narrative_col: Column name for narrative text.

        Returns:
            pd.Series of RootCauseType values indexed like df.
        """
        if df.empty:
            return pd.Series(dtype=object)

        def _row_classify(row: pd.Series) -> RootCauseType:
            cause = row.get(cause_col) if cause_col in row.index else None
            narr = row.get(narrative_col) if narrative_col in row.index else None
            return self.classify(
                primary_cause=cause if pd.notna(cause) else None,
                narrative=narr if pd.notna(narr) else None,
            )

        return df.apply(_row_classify, axis=1)


# ---------------------------------------------------------------------------
# DataFrame normaliser
# ---------------------------------------------------------------------------


class IncidentDataFrameNormaliser:
    """
    Normalises raw source DataFrames to a canonical column set.

    Handles USCG MISLE CSV exports, MAIB occurrence CSVs, and NTSB data.
    """

    SOURCE_COLUMN_MAPS: Dict[str, Dict[str, str]] = {
        "uscg": USCG_COLUMN_MAP,
        "maib": MAIB_COLUMN_MAP,
        "ntsb": NTSB_COLUMN_MAP,
    }

    def normalise(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        Apply source-specific column renaming and add a source column.

        Args:
            df: Raw DataFrame from the source.
            source: Source identifier ('uscg', 'maib', 'ntsb').

        Returns:
            Normalised DataFrame with canonical column names.
        """
        if df.empty:
            return df.copy()

        col_map = self.SOURCE_COLUMN_MAPS.get(source.lower(), {})
        # Rename only columns that exist in df
        rename = {k: v for k, v in col_map.items() if k in df.columns}
        result = df.rename(columns=rename).copy()
        result["source"] = source.lower()

        # Coerce numeric fields
        for col in ("fatality_count", "injury_count"):
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)

        # Coerce coordinate fields
        for col in ("latitude", "longitude"):
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors="coerce")

        return result

    def to_taxonomy_records(
        self,
        df: pd.DataFrame,
        source: str,
        classifier: Optional[IncidentTaxonomyClassifier] = None,
    ) -> List[TaxonomyRecord]:
        """
        Convert a normalised DataFrame into TaxonomyRecord instances.

        Args:
            df: Normalised DataFrame (output of normalise()).
            source: Source identifier.
            classifier: Optional pre-built classifier; creates one if None.

        Returns:
            List of TaxonomyRecord instances.
        """
        if classifier is None:
            classifier = IncidentTaxonomyClassifier()

        records: List[TaxonomyRecord] = []
        for _, row in df.iterrows():
            cause_text = row.get("primary_cause") if "primary_cause" in row.index else None
            narrative_text = row.get("narrative") if "narrative" in row.index else None

            root_cause = classifier.classify(
                primary_cause=cause_text if pd.notna(cause_text) else None,
                narrative=narrative_text if pd.notna(narrative_text) else None,
            )

            record = TaxonomyRecord(
                report_id=str(row.get("report_id", "")),
                source=source,
                incident_date=_safe_str(row.get("incident_date")),
                vessel_name=_safe_str(row.get("vessel_name")),
                vessel_type=_safe_str(row.get("vessel_type")),
                incident_type=_safe_str(row.get("incident_type")),
                root_cause=root_cause,
                raw_cause=_safe_str(cause_text),
                narrative=_safe_str(narrative_text),
                latitude=_safe_float(row.get("latitude")),
                longitude=_safe_float(row.get("longitude")),
                fatality_count=int(row.get("fatality_count", 0) or 0),
                injury_count=int(row.get("injury_count", 0) or 0),
            )
            records.append(record)

        return records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_str(value) -> Optional[str]:
    """Return string or None for NaN/None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s else None


def _safe_float(value) -> Optional[float]:
    """Return float or None for NaN/None."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if pd.isna(f) else f
    except (ValueError, TypeError):
        return None


def build_taxonomy_summary(records: List[TaxonomyRecord]) -> pd.DataFrame:
    """
    Aggregate TaxonomyRecord list into a summary by root_cause / source.

    Args:
        records: List of classified TaxonomyRecord instances.

    Returns:
        DataFrame with columns: root_cause, source, count, fatalities, injuries.
    """
    if not records:
        return pd.DataFrame(
            columns=["root_cause", "source", "count", "fatalities", "injuries"]
        )

    rows = [
        {
            "root_cause": r.root_cause.value,
            "source": r.source,
            "count": 1,
            "fatalities": r.fatality_count,
            "injuries": r.injury_count,
        }
        for r in records
    ]

    df = pd.DataFrame(rows)
    summary = (
        df.groupby(["root_cause", "source"])
        .agg(count=("count", "sum"), fatalities=("fatalities", "sum"), injuries=("injuries", "sum"))
        .reset_index()
        .sort_values(["root_cause", "source"])
    )
    return summary
