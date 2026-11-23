"""Skeleton adapter for Brazil ANP (Agencia Nacional do Petroleo).

No ANP module exists in the codebase.  This adapter documents the gap and
returns empty results so that PipelineRunner can include ANP in
multi-source queries and clearly report what is missing.

ANP open data portal: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos

When a ``brazil_anp`` module is implemented, replace the stub ``adapt()``
with real transformation logic.
"""

from __future__ import annotations

from typing import Any

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    SourceMetadata,
)
from worldenergydata.bsee.pipeline.adapters.data_availability import (
    ANP_AVAILABILITY,
)

_ANP_OPEN_DATA_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"


class ANPAdapter(AdapterInterface):
    """Skeleton adapter for Brazil ANP regulatory data.

    Returns empty DataFrames with detailed warnings explaining that no
    ANP module exists in the codebase yet.
    """

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        """Return an empty result with gap-documentation warnings."""
        warnings: list[str] = [
            "ANP adapter: no brazil_anp module exists in the codebase. "
            "All domains return empty data.",
            "Wellbore: ANP open data portal publishes well data but "
            "no loader is implemented.",
            "Well path: well trajectory availability from ANP open data "
            "is unconfirmed.",
            "Casing: casing program details are not typically published "
            "by ANP in open data.",
            "Drilling/completion: ANP open data has well metadata "
            "(spud dates, depths) but no loader is implemented.",
            "Intervention: intervention data is not available from " "ANP open data.",
            "Production: ANP publishes monthly production by field/well "
            f"on its open data portal ({_ANP_OPEN_DATA_URL}) but no "
            "loader is implemented.",
        ]

        return AdapterResult(
            source=self.get_metadata(),
            field_code=query,
            field_name=query,
            leases=(),
            well_count=0,
            warnings=warnings,
        )

    def get_metadata(self) -> SourceMetadata:
        """Return ANP source metadata."""
        return SourceMetadata(
            source_id="anp",
            source_name=(
                "Agencia Nacional do Petroleo, " "Gas Natural e Biocombustiveis"
            ),
            jurisdiction=(
                "Brazilian offshore and onshore " "(pre-salt and conventional)"
            ),
            api_base_url=_ANP_OPEN_DATA_URL,
            update_cadence="monthly",
        )

    def get_availability(self) -> DataAvailability:
        """Return pre-built ANP availability from the data-availability matrix."""
        return ANP_AVAILABILITY
