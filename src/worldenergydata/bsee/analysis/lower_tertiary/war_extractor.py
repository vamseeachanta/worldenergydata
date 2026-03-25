"""Extract WAR data for Lower Tertiary fields defined in YAML config.

Reuses ``load_war_from_zip`` from the buckskin extractor module.
Field definitions (area codes, block numbers, subsea/dry-tree grouping)
come from the ``LTConfig`` object, not hardcoded constants.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.bsee.analysis.buckskin.extractor import load_war_from_zip

from .config import LTConfig

logger = logging.getLogger(__name__)


class LTWarExtractor:
    """Extract and filter WAR data for all Lower Tertiary fields.

    Parameters
    ----------
    war_zip_path : Path
        Path to ``eWellWARRawData.zip``.
    config : LTConfig
        Loaded YAML configuration with field block mappings.
    """

    def __init__(self, war_zip_path: Path, config: LTConfig) -> None:
        self._df = load_war_from_zip(war_zip_path)
        self._config = config
        self._strip_strings()

    # -- public API -----------------------------------------------------------

    def extract_field(self, field_name: str) -> pd.DataFrame:
        """Filter WAR data to a single field using config block mappings.

        Parameters
        ----------
        field_name : str
            Field name as it appears in the YAML config (e.g. ``"Tiber"``).

        Returns
        -------
        pd.DataFrame
            WAR rows matching the field's area code and block numbers.

        Raises
        ------
        KeyError
            If *field_name* is not found in config.
        """
        area, blocks = self._config.field_blocks(field_name)
        block_set = self._block_set(blocks)
        mask = (self._df["BOTM_AREA_CODE"] == area) & (
            self._df["BOTM_BLOCK_NUM"].isin(block_set)
        )
        return self._df.loc[mask].reset_index(drop=True)

    def extract_all_fields(self) -> dict[str, pd.DataFrame]:
        """Extract WAR data for every field in config.

        Returns
        -------
        dict[str, pd.DataFrame]
            Mapping of field name to filtered DataFrame.
            Fields with zero records are omitted.
        """
        result: dict[str, pd.DataFrame] = {}
        for name in self._config.all_fields:
            df = self.extract_field(name)
            if not df.empty:
                result[name] = df
                logger.info("  %s: %d WAR records", name, len(df))
        return result

    def drilling_activity_by_year(self) -> pd.DataFrame:
        """Aggregate WAR record counts by field and year.

        Returns
        -------
        pd.DataFrame
            Columns: ``field``, ``year``, ``records``.
        """
        rows: list[dict[str, Any]] = []
        for name in self._config.all_fields:
            df = self.extract_field(name)
            if df.empty:
                continue
            df = df.copy()
            df["year"] = pd.to_datetime(
                df["WAR_START_DT"], format="mixed", errors="coerce"
            ).dt.year
            counts = df.groupby("year").size()
            for yr, cnt in counts.items():
                rows.append({"field": name, "year": int(yr), "records": int(cnt)})
        return pd.DataFrame(rows)

    def rig_utilization(self) -> pd.DataFrame:
        """Count WAR records per rig per field.

        Returns
        -------
        pd.DataFrame
            Columns: ``rig_name``, ``field``, ``records``.
        """
        rows: list[dict[str, Any]] = []
        for name in self._config.all_fields:
            df = self.extract_field(name)
            if df.empty or "RIG_NAME" not in df.columns:
                continue
            counts = df.groupby("RIG_NAME").size()
            for rig, cnt in counts.items():
                rows.append(
                    {"rig_name": rig, "field": name, "records": int(cnt)}
                )
        return pd.DataFrame(rows)

    def subsea_vs_drytree_activity(self) -> dict[str, pd.DataFrame]:
        """Group WAR records into subsea vs dry-tree categories.

        Returns
        -------
        dict[str, pd.DataFrame]
            Keys ``"subsea"`` and ``"dry_tree"``, each a DataFrame
            with an added ``"field"`` column.
        """
        subsea_frames: list[pd.DataFrame] = []
        dt_frames: list[pd.DataFrame] = []

        for name in self._config.subsea_fields:
            df = self.extract_field(name)
            if not df.empty:
                df = df.copy()
                df["field"] = name
                subsea_frames.append(df)

        for name in self._config.dry_tree_fields:
            df = self.extract_field(name)
            if not df.empty:
                df = df.copy()
                df["field"] = name
                dt_frames.append(df)

        return {
            "subsea": (
                pd.concat(subsea_frames, ignore_index=True)
                if subsea_frames
                else pd.DataFrame()
            ),
            "dry_tree": (
                pd.concat(dt_frames, ignore_index=True)
                if dt_frames
                else pd.DataFrame()
            ),
        }

    # -- private helpers ------------------------------------------------------

    def _strip_strings(self) -> None:
        """Strip whitespace and quotes from all object/string columns."""
        for col in self._df.select_dtypes(include=["object", "string"]):
            self._df[col] = self._df[col].str.strip().str.strip('"')

    @staticmethod
    def _block_set(blocks: list[int]) -> set[Any]:
        """Return blocks as a set containing both int and str forms.

        WAR data is loaded as dtype=str, but block numbers in YAML are
        ints. Including both forms ensures reliable matching.
        """
        result: set[Any] = set()
        for b in blocks:
            result.add(b)
            result.add(str(b))
        return result
