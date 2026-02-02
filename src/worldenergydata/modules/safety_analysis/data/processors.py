"""
Safety Data Processors

Transform raw data into SafetyObservation and SafetyIncident models
using configurable schema mappings.
"""

from typing import List

import pandas as pd

from worldenergydata.modules.safety_analysis.constants import (
    SEVERITY_LABEL_MAP,
    IncidentType,
    ObservationType,
    SeverityLevel,
)
from worldenergydata.modules.safety_analysis.core.models import (
    SafetyIncident,
    SafetyObservation,
)
from worldenergydata.modules.safety_analysis.core.schemas import SchemaMapping
from worldenergydata.modules.safety_analysis.exceptions import SafetyDataError


class ObservationProcessor:
    """Process raw observation data into SafetyObservation models."""

    def __init__(self, schema: SchemaMapping) -> None:
        self.schema = schema

    def process(self, df: pd.DataFrame) -> List[SafetyObservation]:
        """Transform a DataFrame into a list of SafetyObservation objects."""
        self._validate_columns(df)
        observations = []
        for _, row in df.iterrows():
            obs = self._row_to_observation(row)
            observations.append(obs)
        return observations

    def process_to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw DataFrame into a standardized DataFrame."""
        self._validate_columns(df)
        result = pd.DataFrame()
        result["asset_id"] = df[self.schema.asset_id_column].apply(
            self.schema.extract_asset_id
        )
        result["observed_at"] = pd.to_datetime(
            df[self.schema.datetime_column],
            format=self.schema.datetime_format,
        )
        result["description"] = df[self.schema.description_column].astype(str)

        if self.schema.type_column and self.schema.type_column in df.columns:
            result["observation_type"] = (
                df[self.schema.type_column]
                .map(self.schema.type_mapping)
                .fillna(ObservationType.UNKNOWN.value)
            )
        else:
            result["observation_type"] = ObservationType.UNKNOWN.value

        if self.schema.action_column and self.schema.action_column in df.columns:
            result["action_taken"] = df[self.schema.action_column].astype(str)

        for extra_name, extra_col in self.schema.extra_columns.items():
            if extra_col in df.columns:
                result[extra_name] = df[extra_col]

        return result

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate required columns exist in the DataFrame."""
        required = [
            self.schema.asset_id_column,
            self.schema.datetime_column,
            self.schema.description_column,
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise SafetyDataError.invalid_schema(
                self.schema.name,
                f"Missing required columns: {missing}",
            )

    def _row_to_observation(self, row: pd.Series) -> SafetyObservation:
        """Convert a DataFrame row to a SafetyObservation."""
        raw_id = str(row[self.schema.asset_id_column])
        asset_id = self.schema.extract_asset_id(raw_id)

        dt_val = row[self.schema.datetime_column]
        if isinstance(dt_val, str):
            observed_at = pd.to_datetime(dt_val, format=self.schema.datetime_format)
        else:
            observed_at = pd.Timestamp(dt_val).to_pydatetime()

        obs_type = ObservationType.UNKNOWN
        if self.schema.type_column and self.schema.type_column in row.index:
            raw_type = str(row[self.schema.type_column])
            mapped = self.schema.type_mapping.get(raw_type)
            if mapped:
                try:
                    obs_type = ObservationType(mapped)
                except ValueError:
                    obs_type = ObservationType.UNKNOWN

        action = None
        if self.schema.action_column and self.schema.action_column in row.index:
            action = str(row[self.schema.action_column])

        metadata = {}
        for meta_name, meta_col in self.schema.extra_columns.items():
            if meta_col in row.index:
                metadata[meta_name] = row[meta_col]

        return SafetyObservation(
            asset_id=asset_id,
            observed_at=observed_at,
            description=str(row[self.schema.description_column]),
            observation_type=obs_type,
            action_taken=action,
            metadata=metadata,
        )


class IncidentProcessor:
    """Process raw incident data into SafetyIncident models."""

    def __init__(self, schema: SchemaMapping) -> None:
        self.schema = schema

    def process(self, df: pd.DataFrame) -> List[SafetyIncident]:
        """Transform a DataFrame into a list of SafetyIncident objects."""
        self._validate_columns(df)
        incidents = []
        for _, row in df.iterrows():
            inc = self._row_to_incident(row)
            incidents.append(inc)
        return incidents

    def process_to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw DataFrame into a standardized incident DataFrame."""
        self._validate_columns(df)
        result = pd.DataFrame()
        result["asset_id"] = df[self.schema.asset_id_column].apply(
            self.schema.extract_asset_id
        )
        result["occurred_at"] = pd.to_datetime(
            df[self.schema.datetime_column],
            format=self.schema.datetime_format,
        )

        if self.schema.description_column in df.columns:
            result["description"] = df[self.schema.description_column].astype(str)

        if self.schema.severity_column and self.schema.severity_column in df.columns:
            result["actual_severity"] = (
                df[self.schema.severity_column]
                .map(self.schema.severity_mapping)
                .fillna(SeverityLevel.NO_HURT.value)
            )

        if (
            self.schema.potential_severity_column
            and self.schema.potential_severity_column in df.columns
        ):
            result["potential_severity"] = (
                df[self.schema.potential_severity_column]
                .map(self.schema.severity_mapping)
                .fillna(SeverityLevel.NO_HURT.value)
            )

        if (
            self.schema.work_activity_column
            and self.schema.work_activity_column in df.columns
        ):
            result["work_activity"] = df[self.schema.work_activity_column].astype(str)

        return result

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate required columns exist in the DataFrame."""
        required = [
            self.schema.asset_id_column,
            self.schema.datetime_column,
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise SafetyDataError.invalid_schema(
                self.schema.name,
                f"Missing required columns: {missing}",
            )

    def _row_to_incident(self, row: pd.Series) -> SafetyIncident:
        """Convert a DataFrame row to a SafetyIncident."""
        raw_id = str(row[self.schema.asset_id_column])
        asset_id = self.schema.extract_asset_id(raw_id)

        dt_val = row[self.schema.datetime_column]
        if isinstance(dt_val, str):
            occurred_at = pd.to_datetime(dt_val, format=self.schema.datetime_format)
        else:
            occurred_at = pd.Timestamp(dt_val).to_pydatetime()

        actual_severity = SeverityLevel.NO_HURT
        if self.schema.severity_column and self.schema.severity_column in row.index:
            raw_sev = str(row[self.schema.severity_column])
            mapped_sev = self.schema.severity_mapping.get(raw_sev)
            if mapped_sev:
                actual_severity = SEVERITY_LABEL_MAP.get(
                    mapped_sev, SeverityLevel.NO_HURT
                )

        potential_severity = SeverityLevel.NO_HURT
        if (
            self.schema.potential_severity_column
            and self.schema.potential_severity_column in row.index
        ):
            raw_pot = str(row[self.schema.potential_severity_column])
            mapped_pot = self.schema.severity_mapping.get(raw_pot)
            if mapped_pot:
                potential_severity = SEVERITY_LABEL_MAP.get(
                    mapped_pot, SeverityLevel.NO_HURT
                )

        description = None
        if self.schema.description_column in row.index:
            description = str(row[self.schema.description_column])

        work_activity = None
        if (
            self.schema.work_activity_column
            and self.schema.work_activity_column in row.index
        ):
            work_activity = str(row[self.schema.work_activity_column])

        metadata = {}
        for meta_name, meta_col in self.schema.extra_columns.items():
            if meta_col in row.index:
                metadata[meta_name] = row[meta_col]

        return SafetyIncident(
            asset_id=asset_id,
            occurred_at=occurred_at,
            incident_type=IncidentType.OTHER,
            actual_severity=actual_severity,
            potential_severity=potential_severity,
            description=description,
            work_activity=work_activity,
            metadata=metadata,
        )
