"""Australia adapter — screening-only (no production feed yet) (#721).

Australia has no open per-field offshore production database, so this adapter is
deliberately a SCREENING-ONLY placeholder: ``fetch`` returns a valid but EMPTY
STANDARD_COLUMNS frame (it never fabricates volumes). It is registered/routable
so ``region="australia"`` resolves and the field-development chain can run its
metadata -> FieldConcept -> ``recommend()`` path; ``available_fields`` comes from
the committed CC-BY DataVic metadata fixture.

Because it emits no volumes, it is intentionally EXCLUDED from the production
``_ALL_ADAPTERS`` volume-conformance suite (which requires non-empty output);
it has its own dedicated test instead. A real production feed (AEMO GBB /
PEPS-SA) is a #721 follow-on that would promote it into that suite.
"""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import ProductionQuery


class AustraliaAdapter(AbstractProductionAdapter):
    """Australia screening-only adapter (empty production; metadata-driven)."""

    region: str = "australia"

    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        # No production source yet — honest empty STANDARD_COLUMNS frame.
        return self._empty_frame()

    def available_fields(self) -> List[str]:
        loader = self._metadata_loader()
        if loader is None:
            return []
        return loader.available_fields()

    def date_range(self) -> Tuple[str, str]:
        # No production series -> no date range.
        return ("", "")

    @staticmethod
    def _metadata_loader():
        try:
            from worldenergydata.australia.metadata.field_metadata_loader import (
                AustraliaFieldMetadataLoader,
            )

            return AustraliaFieldMetadataLoader()
        except ModuleNotFoundError:
            return None
