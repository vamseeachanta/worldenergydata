"""Router for rig fleet data queries."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from loguru import logger

from worldenergydata.modules.bsee.data.loaders.rig_fleet.rig_fleet_loader import (
    RigFleetLoader,
)


class RigFleetRouter:
    """Route rig fleet data queries based on configuration."""

    def __init__(self):
        self.rig_fleet_loader = RigFleetLoader()

    def router(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Route rig fleet data requests.

        When ``cfg["data"]["rig_fleet"]`` is truthy the loader is
        invoked and its result returned alongside the loader instance.
        Otherwise an empty dict is returned so callers can safely
        check for data presence.

        Args:
            cfg: Configuration dictionary.

        Returns:
            Tuple of (cfg, rig_fleet_data_dict).
        """
        rig_fleet_flag = cfg.get("data", {}).get("rig_fleet", False)

        if not rig_fleet_flag:
            logger.debug("Rig fleet data not requested in config")
            return cfg, {}

        logger.info("Loading rig fleet data")
        data = self.rig_fleet_loader._load_data(cfg)

        return cfg, {
            "rig_fleet_loader": self.rig_fleet_loader,
            "rig_fleet_data": data,
        }
