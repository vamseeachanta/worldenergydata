"""Skeleton adapter for Mexico CNH (Comision Nacional de Hidrocarburos).

All MexicoCNHData collectors are stubs returning empty data.  This adapter
documents the gap so that PipelineRunner can include CNH in multi-source
queries and clearly report what is missing.

Once ``mexico_cnh.data.MexicoCNHData`` collectors are wired to the SIH
portal scrapers, replace the stub ``adapt()`` with real transformation
logic.
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
    CNH_AVAILABILITY,
)

# SIH base URL used across metadata and warnings
_SIH_URL = "https://sih.hidrocarburos.gob.mx"

# Valid regions mirror MexicoCNH.VALID_REGIONS
_VALID_REGIONS = (
    "sureste",
    "norte",
    "aguas_profundas",
    "aguas_someras",
    "terrestre",
)

# Valid contract round identifiers mirror MexicoCNH.VALID_CONTRACT_ROUNDS
_VALID_CONTRACT_ROUNDS = ("R01", "R02", "R03", "R04", "MIG", "ASG")


class CNHAdapter(AdapterInterface):
    """Skeleton adapter for Mexico CNH regulatory data.

    Returns empty DataFrames with detailed warnings explaining that the
    underlying ``MexicoCNHData`` collectors are stubs.  Region and
    contract-round kwargs are accepted but not yet used.
    """

    def adapt(self, query: str, **kwargs: Any) -> AdapterResult:
        """Return an empty result with gap-documentation warnings."""
        region = kwargs.get("region", "")
        contract_round = kwargs.get("contract_round", "")

        warnings: list[str] = [
            "CNH adapter: all domains return empty data because "
            "MexicoCNHData collectors are stubs.",
            "Wellbore: SIHScraper.export_well_data() exists but "
            "_collect_wells() returns []. No data on disk.",
            "Well path: SIH portal does not expose directional " "survey station data.",
            "Casing: SIH portal does not publish casing program data.",
            "Drilling/completion: scraper infrastructure exists "
            "(fecha_inicio, profundidad_total) but collector not wired.",
            "Intervention: SIH scope is production/contract reporting; "
            "no workover data source identified.",
            "Production: strongest domain -- SIHScraper.export_production_data() "
            "is implemented (Selenium) but collector stub not wired.",
        ]

        if region and region not in _VALID_REGIONS:
            warnings.append(
                f"Unrecognised region '{region}'. " f"Valid: {_VALID_REGIONS}"
            )
        if contract_round and contract_round not in _VALID_CONTRACT_ROUNDS:
            warnings.append(
                f"Unrecognised contract round '{contract_round}'. "
                f"Valid: {_VALID_CONTRACT_ROUNDS}"
            )

        return AdapterResult(
            source=self.get_metadata(),
            field_code=query,
            field_name=query,
            leases=(),
            well_count=0,
            warnings=warnings,
        )

    def get_metadata(self) -> SourceMetadata:
        """Return CNH source metadata."""
        return SourceMetadata(
            source_id="cnh",
            source_name="Comision Nacional de Hidrocarburos",
            jurisdiction="Mexican offshore and onshore",
            api_base_url=_SIH_URL,
            update_cadence="monthly",
        )

    def get_availability(self) -> DataAvailability:
        """Return pre-built CNH availability from the data-availability matrix."""
        return CNH_AVAILABILITY
