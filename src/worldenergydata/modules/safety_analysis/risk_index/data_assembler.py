"""HSE Risk Index Data Assembler.

Loads incident data from multiple regulatory sources (BSEE, OSHA,
Marine Safety, PHMSA, EPA TRI), classifies each record using the
unified activity taxonomy, and aggregates per-activity metrics for
downstream risk scoring.

Usage:
    assembler = DataAssembler()
    sources = {
        "bsee": bsee_df,
        "osha": osha_df,
        "marine_safety": marine_df,
        "phmsa": phmsa_df,
        "epa_tri": tri_df,
    }
    metrics = assembler.assemble(sources)
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from worldenergydata.modules.safety_analysis.taxonomy.incident_classifier import (
    IncidentClassifier,
)

logger = logging.getLogger(__name__)

VALID_SOURCES = frozenset({"bsee", "osha", "marine_safety", "phmsa", "epa_tri"})

# Output columns for the assembled metrics DataFrame
OUTPUT_COLUMNS = [
    "activity_code",
    "activity_name",
    "total_incidents",
    "fatalities",
    "injuries",
    "fatality_rate",
    "injury_rate",
    "tri_carcinogen_lbs",
    "inc_rate",
    "confidence",
    "sources",
    "weighted_incident_count",
]


class DataAssembler:
    """Loads and aggregates HSE data from multiple sources for risk scoring.

    The assembler takes pre-loaded DataFrames keyed by source name,
    classifies each record via the IncidentClassifier, and produces
    a single DataFrame with one row per activity containing aggregated
    metrics (fatalities, injuries, rates, etc.).

    Class Attributes:
        SOURCE_WEIGHTS: Reliability weights per data source.
        MINIMUM_INCIDENT_THRESHOLD: Below this count, confidence is "low".
    """

    SOURCE_WEIGHTS: Dict[str, float] = {
        "bsee": 0.30,
        "marine_safety": 0.25,
        "osha": 0.20,
        "phmsa": 0.15,
        "epa_tri": 0.10,
    }

    MINIMUM_INCIDENT_THRESHOLD: int = 10

    # Confidence thresholds for classification quality
    _HIGH_CONFIDENCE_THRESHOLD: float = 0.70
    _MEDIUM_CONFIDENCE_THRESHOLD: float = 0.40

    def __init__(self, classifier: Optional[IncidentClassifier] = None) -> None:
        self.classifier = classifier or IncidentClassifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assemble(self, sources: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Classify incidents from all sources and aggregate per activity.

        Args:
            sources: Mapping of source name to DataFrame. Valid source
                names: bsee, osha, marine_safety, phmsa, epa_tri.

        Returns:
            DataFrame with one row per activity and columns defined in
            OUTPUT_COLUMNS.

        Raises:
            ValueError: If an unrecognized source key is provided.
        """
        # Validate source keys
        for key in sources:
            if key not in VALID_SOURCES:
                raise ValueError(
                    f"Unknown source '{key}'. Valid: {sorted(VALID_SOURCES)}"
                )

        classified_frames: List[pd.DataFrame] = []
        for source_name, df in sources.items():
            if df is None:
                raise TypeError(f"Source '{source_name}' DataFrame is None")
            if len(df) == 0:
                continue
            classified = self._classify_source(df, source_name)
            classified_frames.append(classified)

        if not classified_frames:
            return self._empty_result()

        combined = pd.concat(classified_frames, ignore_index=True)
        return self._aggregate_metrics(combined)

    def compute_inc_rate(
        self,
        incs_df: pd.DataFrame,
        inspections_df: pd.DataFrame,
    ) -> float:
        """Compute INC (incident of non-compliance) rate from BSEE data.

        INC rate = (WARNING_INCS + COMP_SHUTIN_INCS) / total_inspections

        Args:
            incs_df: BSEE INCs DataFrame with WARNING_INCS and
                COMP_SHUTIN_INCS columns.
            inspections_df: BSEE inspections DataFrame (one row per
                inspection event).

        Returns:
            INC rate as a float. Returns 0.0 if no inspections exist.
        """
        total_inspections = len(inspections_df)
        if total_inspections == 0:
            return 0.0

        total_warnings = int(incs_df["WARNING_INCS"].sum())
        total_comp_shutins = int(incs_df["COMP_SHUTIN_INCS"].sum())
        total_violations = total_warnings + total_comp_shutins

        return total_violations / total_inspections

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify_source(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Classify each record in a DataFrame and add activity columns.

        Iterates rows, passes each as a dict to the classifier, and
        appends the classification result columns.

        Args:
            df: Source DataFrame with source-specific columns.
            source: Source identifier for the classifier.

        Returns:
            Copy of the DataFrame with added columns: activity,
            activity_name, subactivity, classification_confidence, source.
        """
        result = df.copy()

        activities: List[str] = []
        activity_names: List[str] = []
        subactivities: List[str] = []
        confidences: List[float] = []

        for _, row in df.iterrows():
            record = row.to_dict()
            # Normalize source-specific fields for the classifier
            record = self._normalize_record(record, source)
            classification = self.classifier.classify(record, source)
            activities.append(classification.activity)
            activity_names.append(classification.activity_name)
            subactivities.append(classification.subactivity)
            confidences.append(classification.confidence)

        result["activity"] = activities
        result["activity_name"] = activity_names
        result["subactivity"] = subactivities
        result["classification_confidence"] = confidences
        result["source"] = source

        # Ensure fatalities and injuries columns exist
        if "fatalities" not in result.columns:
            result["fatalities"] = 0
        if "injuries" not in result.columns:
            result["injuries"] = 0

        # For EPA TRI: compute carcinogen release column
        if source == "epa_tri":
            result["_tri_carcinogen_lbs"] = self._compute_tri_carcinogen(df)
        else:
            result["_tri_carcinogen_lbs"] = 0.0

        return result

    def _normalize_record(self, record: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Normalize source-specific field names for the classifier.

        The classifier expects certain field names depending on the
        source. This method ensures the record has the expected keys.
        """
        if source == "phmsa":
            # Map PHMSA columns to what the classifier expects
            if "MAP_EIGHT_CAUSE" in record and "cause_category" not in record:
                record["cause_category"] = record["MAP_EIGHT_CAUSE"]
            if "MAP_EIGHT_SUBCAUSE" in record and "subcause" not in record:
                record["subcause"] = record["MAP_EIGHT_SUBCAUSE"]
            if "CAUSE" in record and "cause_category" not in record:
                record["cause_category"] = record["CAUSE"]
        elif source == "epa_tri":
            # Map EPA TRI columns to what the classifier expects
            if "chemical" in record and "chemical_name" not in record:
                record["chemical_name"] = record["chemical"]
        elif (
            source == "marine_safety"
            and "incident_type" not in record
            and "INCIDENT_TYPE" not in record
        ):
            # Map alternate incident type column names
            for key in ("type", "TYPE"):
                if key in record:
                    record["incident_type"] = record[key]
                    break
        return record

    @staticmethod
    def _compute_tri_carcinogen(df: pd.DataFrame) -> pd.Series:
        """Compute per-record carcinogen release amounts for EPA TRI data.

        Returns the on-site release total for records where carcinogen
        is YES, and 0.0 otherwise.
        """
        carcinogen_col = None
        for col_name in ("carcinogen", "CARCINOGEN", "Carcinogen"):
            if col_name in df.columns:
                carcinogen_col = col_name
                break

        release_col = None
        for col_name in (
            "on-site release total",
            "ON-SITE RELEASE TOTAL",
            "on_site_release_total",
        ):
            if col_name in df.columns:
                release_col = col_name
                break

        if carcinogen_col is None or release_col is None:
            return pd.Series(0.0, index=df.index)

        is_carcinogen = df[carcinogen_col].astype(str).str.upper() == "YES"
        release_amounts = pd.to_numeric(df[release_col], errors="coerce").fillna(0.0)
        return release_amounts.where(is_carcinogen, 0.0)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate_metrics(self, classified: pd.DataFrame) -> pd.DataFrame:
        """Aggregate per-activity metrics from classified records.

        Groups by activity_code and computes:
        - total_incidents, fatalities, injuries
        - fatality_rate, injury_rate
        - tri_carcinogen_lbs
        - weighted_incident_count (source-weight adjusted)
        - confidence (based on count and classification quality)
        - sources (list of contributing sources)

        Args:
            classified: Classified records with activity and source columns.

        Returns:
            DataFrame with one row per activity_code.
        """
        # Ensure numeric types
        classified["fatalities"] = pd.to_numeric(
            classified["fatalities"], errors="coerce"
        ).fillna(0)
        classified["injuries"] = pd.to_numeric(
            classified["injuries"], errors="coerce"
        ).fillna(0)

        # Compute per-record weight based on source
        classified["_weight"] = classified["source"].map(self.SOURCE_WEIGHTS)

        grouped = classified.groupby("activity", sort=False)

        rows: List[Dict[str, Any]] = []
        for activity_code, group in grouped:
            total = len(group)
            fatalities = int(group["fatalities"].sum())
            injuries = int(group["injuries"].sum())
            fatality_rate = fatalities / total if total > 0 else 0.0
            injury_rate = injuries / total if total > 0 else 0.0

            tri_lbs = float(group["_tri_carcinogen_lbs"].sum())

            # Source-weighted incident count
            weighted = float(group["_weight"].sum())

            # Average classification confidence
            avg_conf = float(group["classification_confidence"].mean())

            # Contributing sources
            source_list = sorted(group["source"].unique().tolist())

            # Activity name from first occurrence
            activity_name = group["activity_name"].iloc[0]

            # Confidence level
            confidence = self._compute_confidence(
                pd.Series(
                    {
                        "total_incidents": total,
                        "avg_classification_confidence": avg_conf,
                    }
                )
            )

            rows.append(
                {
                    "activity_code": activity_code,
                    "activity_name": activity_name,
                    "total_incidents": total,
                    "fatalities": fatalities,
                    "injuries": injuries,
                    "fatality_rate": fatality_rate,
                    "injury_rate": injury_rate,
                    "tri_carcinogen_lbs": tri_lbs,
                    "inc_rate": 0.0,  # Populated externally via compute_inc_rate
                    "confidence": confidence,
                    "sources": source_list,
                    "weighted_incident_count": weighted,
                }
            )

        return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    def _compute_confidence(self, activity_data: pd.Series) -> str:
        """Return confidence level based on incident count and quality.

        Logic:
            - "low" if total_incidents < MINIMUM_INCIDENT_THRESHOLD
            - "high" if total_incidents >= threshold AND avg classification
              confidence >= HIGH_CONFIDENCE_THRESHOLD
            - "medium" otherwise

        Args:
            activity_data: Series with 'total_incidents' and
                'avg_classification_confidence' keys.

        Returns:
            One of "high", "medium", "low".
        """
        count = activity_data.get("total_incidents", 0)
        avg_conf = activity_data.get("avg_classification_confidence", 0.0)

        if count < self.MINIMUM_INCIDENT_THRESHOLD:
            return "low"
        if avg_conf >= self._HIGH_CONFIDENCE_THRESHOLD:
            return "high"
        return "medium"

    @staticmethod
    def _empty_result() -> pd.DataFrame:
        """Return an empty DataFrame with the correct output schema."""
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # ------------------------------------------------------------------
    # Static file loaders
    # ------------------------------------------------------------------

    @staticmethod
    def load_bsee_incidents(path: Union[str, Path]) -> pd.DataFrame:
        """Load BSEE accident investigation data from pipe-delimited file.

        Args:
            path: Path to mv_acc_investigations.txt

        Returns:
            DataFrame with BSEE incident columns. Adds fatalities and
            injuries columns derived from ACCIDENT_TYPE.
        """
        path = Path(path)
        df = pd.read_csv(path, sep="|", dtype=str)
        # Strip whitespace from column names
        df.columns = df.columns.str.strip().str.strip('"')
        # Strip whitespace from string values
        for col in df.select_dtypes(include="object"):
            df[col] = df[col].str.strip()

        # Derive fatalities and injuries from ACCIDENT_TYPE
        acc_type = df.get("ACCIDENT_TYPE", pd.Series(dtype=str))
        acc_lower = acc_type.str.lower().fillna("")
        df["fatalities"] = acc_lower.str.contains("fatality").astype(int)
        df["injuries"] = (
            acc_lower.str.contains("injury")
            | acc_lower.str.contains("lta")
            | acc_lower.str.contains("rw/jt")
        ).astype(int)

        logger.info("Loaded %d BSEE incidents from %s", len(df), path)
        return df

    @staticmethod
    def load_osha_accidents(
        accident_path: Union[str, Path],
        injury_path: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        """Load OSHA accident data, optionally joining injury details.

        Args:
            accident_path: Path to osha_accident.csv
            injury_path: Optional path to osha_accident_injury.csv

        Returns:
            DataFrame with OSHA accident columns. If injury_path
            is provided, joins injury counts per summary_nr.
        """
        accident_path = Path(accident_path)
        df = pd.read_csv(accident_path, dtype=str, low_memory=False)

        # Derive fatalities from fatality flag
        df["fatalities"] = (df.get("fatality", "").fillna("") == "X").astype(int)

        if injury_path is not None:
            injury_path = Path(injury_path)
            inj_df = pd.read_csv(injury_path, dtype=str, low_memory=False)
            # Count injuries per summary_nr
            injury_counts = (
                inj_df.groupby("summary_nr").size().reset_index(name="injuries")
            )
            df = df.merge(injury_counts, on="summary_nr", how="left")
            df["injuries"] = df["injuries"].fillna(0).astype(int)
        else:
            df["injuries"] = 0

        logger.info("Loaded %d OSHA accidents from %s", len(df), accident_path)
        return df

    @staticmethod
    def load_marine_incidents(db_path: Union[str, Path]) -> pd.DataFrame:
        """Load marine safety incidents from SQLite database.

        Args:
            db_path: Path to marine_safety.db

        Returns:
            DataFrame with marine incident columns.
        """
        db_path = Path(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            df = pd.read_sql_query(
                "SELECT * FROM incidents",
                conn,
            )
        finally:
            conn.close()

        logger.info("Loaded %d marine incidents from %s", len(df), db_path)
        return df

    @staticmethod
    def load_phmsa_incidents(directory: Union[str, Path]) -> pd.DataFrame:
        """Load PHMSA pipeline incident data from Excel files.

        Reads all .xlsx files in the directory, looking for data sheets
        (sheets that are not field definition sheets).

        Args:
            directory: Path to directory containing PHMSA Excel files.

        Returns:
            Concatenated DataFrame with PHMSA incident columns.
        """
        directory = Path(directory)
        frames: List[pd.DataFrame] = []

        for xlsx_path in sorted(directory.glob("*.xlsx")):
            try:
                xls = pd.ExcelFile(xlsx_path)
                # Find the data sheet (not the fields/dictionary sheet)
                data_sheets = [
                    s
                    for s in xls.sheet_names
                    if "field" not in s.lower() and "dict" not in s.lower()
                ]
                for sheet in data_sheets:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    if len(df) > 0:
                        frames.append(df)
            except Exception:
                logger.warning(
                    "Failed to read PHMSA file: %s", xlsx_path, exc_info=True
                )

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)

        # Normalize fatality/injury columns
        for src, dst in [("FATAL", "fatalities"), ("INJURE", "injuries")]:
            if src in combined.columns:
                combined[dst] = (
                    pd.to_numeric(combined[src], errors="coerce").fillna(0).astype(int)
                )
            elif dst not in combined.columns:
                combined[dst] = 0

        logger.info("Loaded %d PHMSA incidents from %s", len(combined), directory)
        return combined

    @staticmethod
    def load_epa_tri(path: Union[str, Path]) -> pd.DataFrame:
        """Load EPA TRI chemical release data.

        Args:
            path: Path to the combined TRI CSV file.

        Returns:
            DataFrame with TRI release columns.
        """
        path = Path(path)
        df = pd.read_csv(path, dtype=str, low_memory=False)

        # TRI records do not have fatalities/injuries
        df["fatalities"] = 0
        df["injuries"] = 0

        # Ensure release total is numeric
        for col_name in ("on-site release total", "ON-SITE RELEASE TOTAL"):
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").fillna(0.0)

        logger.info("Loaded %d EPA TRI records from %s", len(df), path)
        return df
