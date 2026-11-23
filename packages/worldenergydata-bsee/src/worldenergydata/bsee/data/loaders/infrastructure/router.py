"""Infrastructure data router."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from worldenergydata.bsee.data.loaders.infrastructure.pipeline_loader import (
    PipelineLoader,
)
from worldenergydata.bsee.data.loaders.infrastructure.platform_loader import (
    PlatformLoader,
)


class InfrastructureRouter:
    """Route infrastructure data queries to appropriate loader."""

    def __init__(self):
        self.platform_loader = PlatformLoader()
        self.pipeline_loader = PipelineLoader()

    def router(self, cfg: Dict[str, Any]) -> tuple:
        """Route infrastructure queries based on configuration."""
        logger.info("Infrastructure data router invoked")
        return cfg, {
            "platform_loader": self.platform_loader,
            "pipeline_loader": self.pipeline_loader,
        }
