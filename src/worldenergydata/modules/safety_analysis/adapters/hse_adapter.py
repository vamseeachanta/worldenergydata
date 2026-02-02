# ABOUTME: Adapter bridging HSE module incident data into safety analysis format.
"""
HSE Module Adapter

Bridges the existing HSE (Health, Safety, Environment) module's
incident records into the safety analysis format using configurable
schema mappings.
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from worldenergydata.common import get_logger
from worldenergydata.modules.safety_analysis.adapters.base_adapter import BaseAdapter
from worldenergydata.modules.safety_analysis.core.models import (
    SafetyIncident,
    SafetyObservation,
)
from worldenergydata.modules.safety_analysis.core.schemas import SchemaMapping
from worldenergydata.modules.safety_analysis.data.loaders import SafetyDataLoader
from worldenergydata.modules.safety_analysis.data.processors import (
    IncidentProcessor,
    ObservationProcessor,
)
from worldenergydata.modules.safety_analysis.exceptions import SafetyDataError

logger = get_logger(__name__)


class HSEAdapter(BaseAdapter):
    """Adapts HSE module's incident records for safety analysis.

    Provides loading from CSV files with a default column mapping
    that matches the HSE module's data format. Optionally accepts a
    database session for direct database queries.
    """

    name = "hse"

    def __init__(
        self,
        db_session=None,
        schema: Optional[SchemaMapping] = None,
    ) -> None:
        """Initialize HSE adapter.

        Args:
            db_session: Optional database session for direct queries.
            schema: Optional custom schema mapping. Uses HSE defaults
                if not provided.
        """
        self._session = db_session
        self._schema = schema or self._default_schema()

    @staticmethod
    def _default_schema() -> SchemaMapping:
        """Default column mapping for HSE incidents."""
        return SchemaMapping(
            name="hse_default",
            source_type="incident",
            asset_id_column="facility_name",
            datetime_column="incident_date",
            description_column="description",
            type_column="incident_type",
            severity_column="severity",
        )

    def load_observations(
        self,
        csv_path: Optional[Path] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load observation cards from CSV.

        Args:
            csv_path: Path to the observations CSV file.
            **kwargs: Additional arguments for the data loader.

        Returns:
            DataFrame with raw observation data.

        Raises:
            SafetyDataError: If csv_path is not provided.
        """
        if csv_path is None:
            raise SafetyDataError(
                message="csv_path required for HSE observations",
                code="SAFETY_MISSING_PATH",
            )
        logger.info("Loading HSE observations from %s", csv_path)
        loader = SafetyDataLoader()
        return loader.load(csv_path, **kwargs)

    def load_incidents(
        self,
        csv_path: Optional[Path] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load incidents from CSV or HSE database.

        Args:
            csv_path: Path to the incidents CSV file.
            **kwargs: Additional arguments for the data loader.

        Returns:
            DataFrame with raw incident data.

        Raises:
            SafetyDataError: If csv_path is not provided.
        """
        if csv_path is None:
            raise SafetyDataError(
                message="csv_path required for HSE incidents",
                code="SAFETY_MISSING_PATH",
            )
        logger.info("Loading HSE incidents from %s", csv_path)
        loader = SafetyDataLoader()
        return loader.load(csv_path, **kwargs)

    def process_observations(self, df: pd.DataFrame) -> List[SafetyObservation]:
        """Transform raw observation DataFrame into domain models.

        Args:
            df: Raw observation DataFrame.

        Returns:
            List of SafetyObservation models.
        """
        proc = ObservationProcessor(self._schema)
        return proc.process(df)

    def process_incidents(self, df: pd.DataFrame) -> List[SafetyIncident]:
        """Transform raw incident DataFrame into domain models.

        Args:
            df: Raw incident DataFrame.

        Returns:
            List of SafetyIncident models.
        """
        proc = IncidentProcessor(self._schema)
        return proc.process(df)
