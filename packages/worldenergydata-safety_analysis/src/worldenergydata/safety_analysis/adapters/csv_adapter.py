# ABOUTME: Generic CSV file adapter with configurable schema mapping.
"""
Generic CSV Adapter

Loads safety observation and incident data from CSV files with
configurable schema mappings for column name translation.
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from worldenergydata.common import get_logger
from worldenergydata.safety_analysis.adapters.base_adapter import BaseAdapter
from worldenergydata.safety_analysis.core.models import (
    SafetyIncident,
    SafetyObservation,
)
from worldenergydata.safety_analysis.core.schemas import SchemaMapping
from worldenergydata.safety_analysis.data.loaders import SafetyDataLoader
from worldenergydata.safety_analysis.data.processors import (
    IncidentProcessor,
    ObservationProcessor,
)
from worldenergydata.safety_analysis.exceptions import SafetyDataError

logger = get_logger(__name__)


class CSVAdapter(BaseAdapter):
    """Generic adapter for loading safety data from CSV files.

    Accepts separate file paths and schema mappings for observations
    and incidents. Useful for one-off data imports where the column
    layout does not match any known module format.
    """

    name = "csv"

    def __init__(
        self,
        observations_path: Optional[Path] = None,
        incidents_path: Optional[Path] = None,
        observation_schema: Optional[SchemaMapping] = None,
        incident_schema: Optional[SchemaMapping] = None,
    ) -> None:
        """Initialize CSV adapter.

        Args:
            observations_path: Path to observations CSV file.
            incidents_path: Path to incidents CSV file.
            observation_schema: Schema mapping for observation columns.
            incident_schema: Schema mapping for incident columns.
        """
        self._obs_path = observations_path
        self._inc_path = incidents_path
        self._obs_schema = observation_schema
        self._inc_schema = incident_schema

    def load_observations(self, **kwargs) -> pd.DataFrame:
        """Load observation data from the configured CSV file.

        Returns:
            DataFrame with raw observation data.

        Raises:
            SafetyDataError: If no observations path is configured.
        """
        if self._obs_path is None:
            raise SafetyDataError(
                message="No observations path configured",
                code="SAFETY_MISSING_PATH",
            )
        logger.info("Loading CSV observations from %s", self._obs_path)
        return SafetyDataLoader().load(self._obs_path, **kwargs)

    def load_incidents(self, **kwargs) -> pd.DataFrame:
        """Load incident data from the configured CSV file.

        Returns:
            DataFrame with raw incident data.

        Raises:
            SafetyDataError: If no incidents path is configured.
        """
        if self._inc_path is None:
            raise SafetyDataError(
                message="No incidents path configured",
                code="SAFETY_MISSING_PATH",
            )
        logger.info("Loading CSV incidents from %s", self._inc_path)
        return SafetyDataLoader().load(self._inc_path, **kwargs)

    def process_observations(self, df: pd.DataFrame) -> List[SafetyObservation]:
        """Transform raw observation DataFrame into domain models.

        Args:
            df: Raw observation DataFrame.

        Returns:
            List of SafetyObservation models.

        Raises:
            SafetyDataError: If no observation schema is configured.
        """
        if self._obs_schema is None:
            raise SafetyDataError(
                message="No observation schema configured",
                code="SAFETY_MISSING_SCHEMA",
            )
        return ObservationProcessor(self._obs_schema).process(df)

    def process_incidents(self, df: pd.DataFrame) -> List[SafetyIncident]:
        """Transform raw incident DataFrame into domain models.

        Args:
            df: Raw incident DataFrame.

        Returns:
            List of SafetyIncident models.

        Raises:
            SafetyDataError: If no incident schema is configured.
        """
        if self._inc_schema is None:
            raise SafetyDataError(
                message="No incident schema configured",
                code="SAFETY_MISSING_SCHEMA",
            )
        return IncidentProcessor(self._inc_schema).process(df)
