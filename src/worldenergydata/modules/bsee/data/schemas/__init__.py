from __future__ import annotations

from worldenergydata.modules.bsee.data.schemas.deepwater_structure import (
    DeepwaterStructureSchema,
)
from worldenergydata.modules.bsee.data.schemas.pipeline import (
    PipelineLocationSchema,
    PipelinePermitSchema,
)
from worldenergydata.modules.bsee.data.schemas.platform import PlatformStructureSchema

__all__ = [
    "PlatformStructureSchema",
    "PipelinePermitSchema",
    "PipelineLocationSchema",
    "DeepwaterStructureSchema",
]
