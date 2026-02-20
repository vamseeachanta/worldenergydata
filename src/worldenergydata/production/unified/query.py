"""ProductionQuery and ProductionResult dataclasses for the unified interface.

These data structures define the API contract between callers and the
UnifiedProductionClient. All adapters consume ProductionQuery and
contribute rows that are assembled into ProductionResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


# Standard columns that every adapter must return.
STANDARD_COLUMNS: tuple[str, ...] = (
    "region",
    "field_name",
    "year",
    "month",
    "oil_bbl",
    "gas_mcf",
    "water_bbl",
    "condensate_bbl",
    "source",
)


@dataclass
class ProductionQuery:
    """Parameters that drive a cross-regional production data request.

    Attributes:
        regions: Region keys to query, e.g. ``["ncs", "ukcs", "brazil"]``.
        fields: Optional list of field names to filter. ``None`` returns all.
        start: Inclusive start period as ``"YYYY-MM"``. ``None`` = no lower bound.
        end: Inclusive end period as ``"YYYY-MM"``. ``None`` = no upper bound.
        parameters: Production stream columns to include in the result.
    """

    regions: List[str]
    fields: Optional[List[str]] = None
    start: Optional[str] = None
    end: Optional[str] = None
    parameters: tuple[str, ...] = ("oil_bbl", "gas_mcf", "water_bbl")


@dataclass
class ProductionResult:
    """Output of a UnifiedProductionClient.query() call.

    Attributes:
        query: The original query that produced this result.
        data: Normalised monthly production rows.  Columns match
              ``STANDARD_COLUMNS``.
        summary: Per-field aggregate statistics (peak_rate, cumulative,
                 avg_monthly).
        sources_used: Adapter source identifiers that contributed data.
        coverage_gaps: Descriptions of missing date ranges per field.
    """

    query: ProductionQuery
    data: pd.DataFrame
    summary: pd.DataFrame
    sources_used: List[str]
    coverage_gaps: List[dict]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_empty(self) -> bool:
        """Return True when the data frame contains no rows."""
        return self.data.empty
