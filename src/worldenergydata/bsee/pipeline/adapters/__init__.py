"""Multi-source regulatory data adapters for the field analysis pipeline.

Each adapter normalizes a regulatory data source into the common FieldContext
contract defined by the BSEE pipeline (WRK-017), enabling cross-source analysis.

Adapters:
    - bsee: US federal offshore (Bureau of Safety and Environmental Enforcement)
    - sodir: Norwegian Continental Shelf (Sodir / NPD FactPages)
    - rrc: Texas onshore and state waters (Railroad Commission of Texas)
    - cnh: Mexican offshore and onshore (Comisión Nacional de Hidrocarburos)
    - anp: Brazilian pre-salt and conventional (Agência Nacional do Petróleo)
"""

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    AdapterInterface,
    AdapterResult,
    DataAvailability,
    DomainStatus,
    SourceMetadata,
)
from worldenergydata.bsee.pipeline.adapters.multi_source_query import (
    MultiSourceQuery,
)
from worldenergydata.bsee.pipeline.adapters.benchmarking import (
    CrossSourceBenchmark,
)

__all__ = [
    "AdapterInterface",
    "AdapterResult",
    "CrossSourceBenchmark",
    "DataAvailability",
    "DomainStatus",
    "MultiSourceQuery",
    "SourceMetadata",
]
