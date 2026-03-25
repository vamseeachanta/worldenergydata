"""Pipeline specification lookup against API 5L / ISO 3183 standard pipe schedule.

Provides OD/WT-based identification of standard pipe sizes for enriching
OrcaFlex line objects with NPS, schedule, grade range, and applicable standards.

Primary use-case: OrcaFlex .dat extraction pipeline (WRK-595) — converts
SI-unit OD/WT from extracted model files to canonical pipe spec entries,
replacing client object names with public engineering classification.

Database: data/modules/pipeline/api_5l_pipe_schedule.csv
Sources:  API 5L / ISO 3183, ASME B36.10M (publicly available standard tables)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "modules" / "pipeline"
_DEFAULT_FILE = "api_5l_pipe_schedule.csv"

# Default tolerances for OD/WT matching (SI units, meters)
_OD_TOLERANCE_M = 0.003  # 3 mm — covers measurement noise in .dat files
_WT_TOLERANCE_M = 0.003  # 3 mm


class PipelineSpecLookup:
    """Match extracted OrcaFlex OD/WT (SI) to the closest standard pipe spec.

    Loads the API 5L pipe schedule table and provides OD/WT-based fuzzy
    matching to identify the nominal pipe size, schedule, grade range, and
    applicable standard for a given line object.

    Usage::

        lookup = PipelineSpecLookup()
        spec = lookup.match_od_wt(od_m=0.2731, wt_m=0.012)
        # → {"nps_in": 10.0, "od_mm": 273.05, "schedule": "STD", ...}

        spec = lookup.match_od_wt(od_m=0.5334, wt_m=0.025)
        # → {"nps_in": 21.0, "od_mm": 533.40, "schedule": "RISER_BORE_HW", ...}
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _DATA_DIR
        self._df: Optional[pd.DataFrame] = None

    def load(self) -> pd.DataFrame:
        """Load API 5L pipe schedule table (lazy, cached)."""
        if self._df is not None:
            return self._df

        csv_path = self._data_dir / _DEFAULT_FILE
        if not csv_path.exists():
            logger.warning("Pipe schedule table not found: %s", csv_path)
            self._df = pd.DataFrame()
            return self._df

        self._df = pd.read_csv(csv_path)
        logger.info("Loaded %d pipe schedule entries", len(self._df))
        return self._df

    def match_od_wt(
        self,
        od_m: float,
        wt_m: float = 0.0,
        od_tolerance_m: float = _OD_TOLERANCE_M,
        wt_tolerance_m: float = _WT_TOLERANCE_M,
    ) -> Optional[dict]:
        """Match OD/WT (SI units) to closest standard pipe specification.

        Matching strategy:
          1. Filter rows where |od_mm - od_m*1000| <= od_tolerance_m*1000
          2. Among OD matches, prefer the row with the closest WT; if
             wt_m==0 or no WT match within tolerance, return the first
             OD-matching row (lowest NPS → lowest schedule preference).
          3. Return None if no OD match within tolerance.

        Args:
            od_m: Outer diameter in metres (e.g. 0.2731 for 10.75").
            wt_m: Wall thickness in metres (e.g. 0.012). Pass 0.0 to
                match by OD only.
            od_tolerance_m: OD matching tolerance in metres (default 3mm).
            wt_tolerance_m: WT matching tolerance in metres (default 3mm).

        Returns:
            Dict with keys: nps_in, od_mm, od_in, schedule, wt_mm, wt_in,
            weight_kgm, grade_range, standard, domain_hint, source.
            Returns None if no match within tolerance.
        """
        df = self.load()
        if df.empty:
            return None

        od_mm = od_m * 1000.0
        od_tol_mm = od_tolerance_m * 1000.0

        od_mask = (df["od_mm"] - od_mm).abs() <= od_tol_mm
        candidates = df[od_mask].copy()

        if candidates.empty:
            logger.debug(
                "PipelineSpecLookup: no match for OD=%.1fmm (tolerance=%.1fmm)",
                od_mm,
                od_tol_mm,
            )
            return None

        # Sort by OD closeness first, then WT closeness
        candidates["_od_diff"] = (candidates["od_mm"] - od_mm).abs()

        if wt_m > 0.0:
            wt_mm = wt_m * 1000.0
            wt_tol_mm = wt_tolerance_m * 1000.0
            candidates["_wt_diff"] = (candidates["wt_mm"] - wt_mm).abs()
            # Prefer rows within WT tolerance, then sort by WT diff
            wt_ok = candidates["_wt_diff"] <= wt_tol_mm
            if wt_ok.any():
                candidates = candidates[wt_ok]
            candidates = candidates.sort_values(["_od_diff", "_wt_diff"])
        else:
            candidates = candidates.sort_values("_od_diff")

        row = candidates.iloc[0]
        result = {
            "nps_in": float(row["nps_in"]),
            "od_mm": float(row["od_mm"]),
            "od_in": float(row["od_in"]),
            "schedule": str(row["schedule"]),
            "wt_mm": float(row["wt_mm"]),
            "wt_in": float(row["wt_in"]),
            "weight_kgm": (
                float(row["weight_kgm"]) if pd.notna(row["weight_kgm"]) else None
            ),
            "grade_range": (
                [g.strip() for g in str(row["grade_range"]).split("-")]
                if pd.notna(row["grade_range"])
                else []
            ),
            "standard": str(row["standard"]),
            "domain_hint": (
                str(row["domain_hint"]) if pd.notna(row["domain_hint"]) else None
            ),
            "source": "worldenergydata.bsee.pipeline.PipelineSpecLookup",
        }
        logger.debug(
            'PipelineSpecLookup: OD=%.1fmm → NPS %.1f" %s (%s)',
            od_mm,
            result["nps_in"],
            result["schedule"],
            result["domain_hint"],
        )
        return result

    def get_by_nps(self, nps_in: float) -> pd.DataFrame:
        """Return all schedule entries for a given NPS (inches)."""
        df = self.load()
        if df.empty:
            return df
        return df[df["nps_in"] == nps_in].copy()

    def get_all_nps_sizes(self) -> list[float]:
        """Return sorted list of all nominal pipe sizes in the table."""
        df = self.load()
        if df.empty:
            return []
        return sorted(df["nps_in"].unique().tolist())

    def nps_summary(self) -> dict[float, list[str]]:
        """Return {nps_in: [schedule, ...]} mapping."""
        df = self.load()
        if df.empty:
            return {}
        return {
            float(nps): df[df["nps_in"] == nps]["schedule"].tolist()
            for nps in sorted(df["nps_in"].unique())
        }
