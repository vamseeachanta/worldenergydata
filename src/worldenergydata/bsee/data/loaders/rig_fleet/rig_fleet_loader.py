"""Rig fleet data loader from binary files and WAR records."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from loguru import logger

from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
    classify_rig_type,
)
from worldenergydata.common.data_resolver import get_module_data_safe

_BSEE_DATA = get_module_data_safe("bsee")


class RigFleetLoader:
    """Load rig fleet data from binary files or build from WAR records."""

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self._bin_dir = str(_BSEE_DATA / "bin" / "rig_fleet")
        self._local_dir = str(_BSEE_DATA / ".local" / "rig_fleet")

    def _load_data(self, cfg: Optional[Dict] = None) -> Optional[pd.DataFrame]:
        """Load rig fleet data from binary file.

        Checks ``.local/`` directory first for full fleet data, then
        falls back to ``bin/`` for the committed sample.  The result
        is cached on ``self.data`` so subsequent calls are free.

        Args:
            cfg: Optional configuration dict.  When provided, a custom
                binary path can be supplied at
                ``cfg["parameters"]["filepath"]["rig_fleet"]["bin"]``.

        Returns:
            Concatenated DataFrame or None when no data is found.
        """
        if self.data is not None:
            return self.data
        try:
            # Config override takes absolute precedence
            if cfg:
                custom_path = (
                    cfg.get("parameters", {})
                    .get("filepath", {})
                    .get("rig_fleet", {})
                    .get("bin")
                )
                if custom_path:
                    return self._load_from_dir(Path(custom_path))

            # Try .local/ first (full fleet), then bin/ (sample)
            local_path = Path(self._local_dir)
            if local_path.exists():
                result = self._load_from_dir(local_path)
                if result is not None:
                    return result

            return self._load_from_dir(Path(self._bin_dir))

        except Exception as e:
            logger.error(f"Error loading rig fleet data: {str(e)}")
            return None

    def _load_from_dir(self, bin_path: Path) -> Optional[pd.DataFrame]:
        """Load and cache all .bin files from a directory."""
        bin_files = list(bin_path.glob("*.bin"))
        if not bin_files:
            logger.warning(f"No rig fleet binary files found in {bin_path}")
            return None

        frames = []
        for bf in bin_files:
            with open(bf, "rb") as f:
                df = pickle.load(f)  # nosec B301
                if isinstance(df, pd.DataFrame):
                    frames.append(df)

        if frames:
            self.data = pd.concat(frames, ignore_index=True)
            logger.info(f"Loaded {len(self.data)} rig fleet records")
            return self.data
        return None

    def build_fleet_from_war(
        self, war_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Extract unique rigs from WAR data and build fleet inventory.

        Args:
            war_df: DataFrame with at least a ``RIG_NAME`` column.
                Optionally ``WAR_END_DT``, ``WAR_START_DT``,
                ``AREA_CODE``, ``BLOCK_NUMBER``, ``API_WELL_NUMBER``,
                and ``WATER_DEPTH``.

        Returns:
            DataFrame with one row per unique rig and aggregated stats.
        """
        if "RIG_NAME" not in war_df.columns:
            logger.error("WAR DataFrame missing RIG_NAME column")
            return pd.DataFrame()

        # Filter out empty/null rig names and "NON RIG UNIT OPERATION"
        mask = (
            war_df["RIG_NAME"].notna()
            & (war_df["RIG_NAME"].str.strip() != "")
            & (~war_df["RIG_NAME"].str.upper().str.contains("NON RIG", na=False))
        )
        filtered = war_df[mask].copy()

        if filtered.empty:
            logger.warning("No valid rig names found in WAR data")
            return pd.DataFrame()

        # Normalise rig names
        filtered["RIG_NAME"] = filtered["RIG_NAME"].str.strip()

        # Build aggregation dict based on available columns
        agg_dict: Dict[str, Any] = {}
        if "API_WELL_NUMBER" in filtered.columns:
            agg_dict["API_WELL_NUMBER"] = "nunique"
        if "WAR_END_DT" in filtered.columns:
            agg_dict["WAR_END_DT"] = "max"
        if "WAR_START_DT" in filtered.columns:
            agg_dict["WAR_START_DT"] = "min"
        if "AREA_CODE" in filtered.columns:
            agg_dict["AREA_CODE"] = "last"
        if "BLOCK_NUMBER" in filtered.columns:
            agg_dict["BLOCK_NUMBER"] = "last"
        if "WATER_DEPTH" in filtered.columns:
            agg_dict["WATER_DEPTH"] = "max"

        if agg_dict:
            fleet_df = filtered.groupby("RIG_NAME", as_index=False).agg(agg_dict)
        else:
            fleet_df = (
                filtered[["RIG_NAME"]].drop_duplicates().reset_index(drop=True)
            )

        # Rename aggregated columns to domain-meaningful names
        rename_map = {
            "API_WELL_NUMBER": "WELLS_DRILLED_COUNT",
            "WAR_END_DT": "LAST_WAR_DATE",
            "WAR_START_DT": "FIRST_WAR_DATE",
            "AREA_CODE": "LAST_AREA_CODE",
            "BLOCK_NUMBER": "LAST_BLOCK_NUMBER",
            "WATER_DEPTH": "MAX_WATER_DEPTH_FT",
        }
        fleet_df.rename(
            columns={k: v for k, v in rename_map.items() if k in fleet_df.columns},
            inplace=True,
        )

        # Classify rig types from names
        fleet_df["RIG_TYPE"] = fleet_df["RIG_NAME"].apply(
            lambda name: classify_rig_type(name).value
        )

        # Mark all BSEE WAR rows as offshore with bsee_war source
        fleet_df["DATA_SOURCE"] = "bsee_war"
        fleet_df["IS_OFFSHORE"] = True

        logger.info(f"Built fleet of {len(fleet_df)} unique rigs from WAR data")
        return fleet_df

    def load_overrides(
        self, overrides_path: Path, fleet_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Apply manual rig type overrides from CSV.

        The CSV must have a ``RIG_NAME`` column.  All other columns are
        treated as override values and are merged into *fleet_df* where
        ``RIG_NAME`` matches.

        Args:
            overrides_path: Path to the overrides CSV file.
            fleet_df: Existing fleet DataFrame to update.

        Returns:
            Updated fleet DataFrame with overrides applied.
        """
        if not overrides_path.exists():
            logger.debug(f"No overrides file at {overrides_path}")
            return fleet_df

        try:
            overrides_df = pd.read_csv(overrides_path)
        except Exception as e:
            logger.error(f"Error reading overrides file: {e}")
            return fleet_df

        if "RIG_NAME" not in overrides_df.columns:
            logger.error("Overrides CSV missing RIG_NAME column")
            return fleet_df

        result = fleet_df.copy()
        override_cols = [c for c in overrides_df.columns if c != "RIG_NAME"]

        for _, override_row in overrides_df.iterrows():
            mask = result["RIG_NAME"] == override_row["RIG_NAME"]
            for col in override_cols:
                if pd.notna(override_row[col]):
                    if col not in result.columns:
                        result[col] = None
                    result.loc[mask, col] = override_row[col]

        logger.info(f"Applied {len(overrides_df)} rig type overrides")
        return result

    def get_rigs_by_type(
        self, rig_type: str, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get rigs filtered by type classification.

        Args:
            rig_type: RigType value string to filter on.
            cfg: Optional configuration dict passed to ``_load_data``.

        Returns:
            Filtered DataFrame or None when no matches are found.
        """
        df = self._load_data(cfg)
        if df is None:
            return None
        if "RIG_TYPE" not in df.columns:
            return None
        mask = df["RIG_TYPE"] == rig_type
        result = df[mask]
        logger.info(f"Found {len(result)} rigs of type {rig_type}")
        return result if not result.empty else None

    def get_rigs_by_offshore_status(
        self, is_offshore: bool, cfg: Optional[Dict] = None
    ) -> Optional[pd.DataFrame]:
        """Get rigs filtered by offshore/onshore status.

        Args:
            is_offshore: True for offshore, False for onshore.
            cfg: Optional configuration dict passed to ``_load_data``.

        Returns:
            Filtered DataFrame or None when no matches / missing column.
        """
        df = self._load_data(cfg)
        if df is None:
            return None
        if "IS_OFFSHORE" not in df.columns:
            return None
        mask = df["IS_OFFSHORE"] == is_offshore
        result = df[mask]
        return result if not result.empty else None

    def get_rig_well_history(
        self, rig_name: str, war_df: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """Get all WAR records for a specific rig.

        Matching is case-insensitive and strips leading/trailing spaces.

        Args:
            rig_name: The rig name to search for.
            war_df: Full WAR DataFrame.

        Returns:
            Filtered DataFrame or None if no records found.
        """
        if "RIG_NAME" not in war_df.columns:
            return None
        mask = (
            war_df["RIG_NAME"].str.strip().str.upper() == rig_name.strip().upper()
        )
        result = war_df[mask]
        return result if not result.empty else None
