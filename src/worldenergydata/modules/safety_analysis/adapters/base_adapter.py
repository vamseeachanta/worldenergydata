# ABOUTME: Abstract base class for safety data source adapters.
"""
Base Adapter for Safety Data Sources

Defines the interface that all safety data adapters must implement
to load and transform data from external sources into the unified
SafetyObservation/SafetyIncident models.
"""

from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd

from worldenergydata.common import get_logger

logger = get_logger(__name__)


class BaseAdapter(ABC):
    """Base adapter for integrating external data sources.

    All data source adapters (CSV, HSE database, API, etc.) must
    inherit from this class and implement the abstract methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""

    @abstractmethod
    def load_observations(self, **kwargs) -> pd.DataFrame:
        """Load observation data from the source.

        Returns:
            DataFrame with raw observation data.
        """

    @abstractmethod
    def load_incidents(self, **kwargs) -> pd.DataFrame:
        """Load incident data from the source.

        Returns:
            DataFrame with raw incident data.
        """

    def load_all(self, **kwargs) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load both observations and incidents.

        Returns:
            Tuple of (observations_df, incidents_df).
        """
        logger.info("Loading all data from adapter '%s'", self.name)
        return self.load_observations(**kwargs), self.load_incidents(**kwargs)
