"""Load hull data from the curated rig fleet with hull form enrichment.

Provides query interface by rig name, rig type, or hull form type,
joining curated fleet data with hull classification and estimates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.vessel_hull_models.rig_hulls.hull_estimator import (
    populate_estimated_dimensions,
)
from worldenergydata.vessel_hull_models.rig_hulls.hull_form_mapper import (
    populate_hull_forms,
)

logger = logging.getLogger(__name__)

_DEFAULT_FILE = "drilling_rigs.parquet"


def _default_curated_dir() -> Path:
    """Resolve the vessel_fleet curated dataset directory.

    The curated rig fleet (``drilling_rigs.parquet``) is owned by the
    ``worldenergydata-vessel_fleet`` member, which (ADR 0001 Phase 2 batch 4,
    #529 — option (i)) now ships that dataset as package data under
    ``worldenergydata/vessel_fleet/_data/curated/``. Resolve it from the
    INSTALLED vessel_fleet package rather than a repo-root walk, so it works
    from an editable workspace install or the built wheel regardless of where
    vessel_hull_models lands. Falls back to a (likely non-existent) path on
    import error; the loader's caller can always inject ``data_dir`` explicitly.
    """
    try:
        from importlib.resources import files

        return Path(str(files("worldenergydata.vessel_fleet"))) / "_data" / "curated"
    except (ImportError, ModuleNotFoundError, TypeError):  # pragma: no cover
        return Path(__file__).resolve().parent / "_missing_vessel_fleet_data"


class HullDataLoader:
    """Query hull data from the enriched curated fleet."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _default_curated_dir()
        self._df: Optional[pd.DataFrame] = None

    def _load(self) -> pd.DataFrame:
        """Load and enrich curated fleet data (lazy, cached)."""
        if self._df is not None:
            return self._df

        pq = self._data_dir / _DEFAULT_FILE
        if not pq.exists():
            logger.warning("Curated fleet not found: %s", pq)
            self._df = pd.DataFrame()
            return self._df

        df = pd.read_parquet(pq)
        df = populate_hull_forms(df)
        df = populate_estimated_dimensions(df)
        self._df = df
        logger.info("Loaded %d rigs with hull data", len(df))
        return self._df

    def get_by_name(self, rig_name: str) -> Optional[dict]:
        """Look up hull data by rig name (case-insensitive)."""
        df = self._load()
        if df.empty:
            return None
        mask = df["VESSEL_NAME"].str.upper() == rig_name.upper()
        if not mask.any():
            # Try RIG_NAME if VESSEL_NAME didn't match
            if "RIG_NAME" in df.columns:
                mask = df["RIG_NAME"].str.upper() == rig_name.upper()
        matches = df[mask]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    def get_by_hull_form(self, hull_form_type: str) -> pd.DataFrame:
        """Get all rigs with a specific hull form type."""
        df = self._load()
        if df.empty:
            return df
        mask = df["HULL_FORM_TYPE"] == hull_form_type
        return df[mask].copy()

    def get_by_rig_type(self, rig_type: str) -> pd.DataFrame:
        """Get all rigs with a specific operational rig type."""
        df = self._load()
        if df.empty:
            return df
        mask = df["RIG_TYPE"] == rig_type
        return df[mask].copy()

    def hull_form_summary(self) -> dict[str, int]:
        """Return count of rigs per hull form type."""
        df = self._load()
        if df.empty:
            return {}
        return df["HULL_FORM_TYPE"].value_counts(dropna=False).to_dict()

    def dimension_coverage(self) -> dict[str, dict]:
        """Report dimension coverage by hull form type."""
        df = self._load()
        if df.empty:
            return {}
        result = {}
        for form in df["HULL_FORM_TYPE"].dropna().unique():
            subset = df[df["HULL_FORM_TYPE"] == form]
            result[form] = {
                "total": len(subset),
                "loa_m": int(subset["LOA_M"].notna().sum()),
                "beam_m": int(subset["BEAM_M"].notna().sum()),
                "draft_m": int(subset["DRAFT_M"].notna().sum()),
                "measured": (
                    int((subset["DIMENSION_CONFIDENCE"] == "measured").sum())
                    if "DIMENSION_CONFIDENCE" in subset.columns
                    else 0
                ),
                "estimated": (
                    int((subset["DIMENSION_CONFIDENCE"] == "estimated").sum())
                    if "DIMENSION_CONFIDENCE" in subset.columns
                    else 0
                ),
                "generic": (
                    int((subset["DIMENSION_CONFIDENCE"] == "generic").sum())
                    if "DIMENSION_CONFIDENCE" in subset.columns
                    else 0
                ),
            }
        return result
