"""Unified cross-regional production query interface.

Entry point::

    from worldenergydata.production.unified import UnifiedProductionClient
    from worldenergydata.production.unified.query import ProductionQuery

    client = UnifiedProductionClient()
    result = client.query(ProductionQuery(regions=["ncs", "gom", "brazil"]))
"""

from __future__ import annotations

from typing import List

import pandas as pd

from worldenergydata.production.unified.query import (
    ProductionQuery,
    ProductionResult,
    STANDARD_COLUMNS,
)
from worldenergydata.production.unified.router import RegionRouter
from worldenergydata.production.unified.normalizer import Normalizer


class UnifiedProductionClient:
    """Orchestrate cross-regional production queries.

    The client owns a ``RegionRouter`` that maps region strings to adapters
    and a ``Normalizer`` that validates and standardises the merged output.

    Example::

        client = UnifiedProductionClient()
        result = client.query(
            ProductionQuery(
                regions=["ncs", "ukcs"],
                start="2020-01",
                end="2023-12",
            )
        )
        print(result.data.head())
        print(result.summary)
    """

    def __init__(self) -> None:
        self._router = RegionRouter()
        self._normalizer = Normalizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, query: ProductionQuery) -> ProductionResult:
        """Execute a cross-regional production query.

        Args:
            query: ``ProductionQuery`` specifying regions, optional field
                filters, date range, and parameter columns.

        Returns:
            ``ProductionResult`` with normalised data, summary stats,
            sources list, and coverage gaps.
        """
        canonical_regions = self._router.resolve_regions(query.regions)

        frames: List[pd.DataFrame] = []
        sources_used: List[str] = []

        for region in canonical_regions:
            adapter = self._router.get_adapter(region)
            df = adapter.fetch(query)

            if not df.empty:
                frames.append(df)
                # Collect unique source labels
                for src in df["source"].unique():
                    if src not in sources_used:
                        sources_used.append(src)

        if frames:
            merged = pd.concat(frames, ignore_index=True)
        else:
            merged = pd.DataFrame(columns=list(STANDARD_COLUMNS))

        # Validate and normalise
        if not merged.empty:
            self._normalizer.validate(merged)

        normalised = self._normalizer.normalize(merged)
        summary = self._normalizer.build_summary(normalised)
        gaps = self._normalizer.find_coverage_gaps(normalised)

        return ProductionResult(
            query=query,
            data=normalised,
            summary=summary,
            sources_used=sources_used,
            coverage_gaps=gaps,
        )

    def list_regions(self) -> List[str]:
        """Return all supported canonical region keys."""
        return self._router.list_regions()


__all__ = [
    "UnifiedProductionClient",
    "ProductionQuery",
    "ProductionResult",
    "RegionRouter",
    "Normalizer",
]
