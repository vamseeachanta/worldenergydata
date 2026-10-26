"""Match pipe dimensions against validated, caller-supplied reference data.

The distributed CSV is an empty compatibility template. Supply a data directory
containing that CSV and a per-row sources.yml; no standards table is bundled.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# Phase 2 batch-3 carve (#529): this file is now 2 levels deeper under
# packages/worldenergydata-bsee/, so the repo root is parents[6] (was [4]).
# The data/ tree stays at the repo root (not moved by the carve).
_DATA_DIR = Path(__file__).resolve().parents[6] / "data" / "modules" / "pipeline"
_DEFAULT_FILE = "api_5l_pipe_schedule.csv"

# Default tolerances for OD/WT matching (SI units, meters)
_OD_TOLERANCE_M = 0.003  # 3 mm — covers measurement noise in .dat files
_WT_TOLERANCE_M = 0.003  # 3 mm


_COLUMNS = (
    "nps_in",
    "od_mm",
    "od_in",
    "schedule",
    "wt_mm",
    "wt_in",
    "weight_kgm",
    "grade_range",
    "standard",
    "domain_hint",
)
_STANDARD_SOURCE = re.compile(
    r"\b(?:API|ASME|ISO|ASTM|ANSI|BSI|DIN|IEC|NACE|DNV)\b"
    r"|\bBS\s+(?:EN|\d)|\bEN\s+\d"
    r"|American Petroleum Institute|American Society of Mechanical Engineers"
    r"|International Organi[sz]ation for Standardi[sz]ation"
    r"|American Society for Testing and Materials|British Standards Institution",
    re.IGNORECASE,
)


def validate_source_label(label: str) -> None:
    """Reject standards-attributed source labels; this is not a rights review."""
    if _STANDARD_SOURCE.search(str(label)):
        raise ValueError("Pipe input must not use a standard as its data source")


class _UniqueSourceLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently replacing provenance."""


def _unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("Source manifest keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueSourceLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def _load_sources(path: Path, row_count: int, allow_synthetic: bool) -> dict:
    try:
        loader = _UniqueSourceLoader(path.read_text())
        try:
            manifest = loader.get_single_data()
        finally:
            loader.dispose()
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError("A valid sources.yml beside the pipe CSV is required") from exc
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("version")) is not int
        or manifest["version"] != 1
        or not isinstance(manifest.get("rows"), list)
    ):
        raise ValueError("Source manifest requires version 1 and a rows list")
    sources = {}
    for entry in manifest["rows"]:
        if not isinstance(entry, dict):
            raise ValueError("Each pipe source must be a mapping")
        number = entry.get("row")
        if type(number) is not int or number in sources or not 1 <= number <= row_count:
            raise ValueError("Source rows must uniquely identify CSV data rows")
        for field in ("kind", "title", "publisher", "revision", "date"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"Source row {number} requires {field}")
        if entry["kind"] not in {
            "manufacturer",
            "public_paper",
            "design_basis",
            "synthetic",
        }:
            raise ValueError("Pipe sources must be independent of standards tables")
        if entry["kind"] == "synthetic" and not allow_synthetic:
            raise ValueError(
                "synthetic pipe inputs require allow_synthetic=True for tests"
            )
        try:
            if date.fromisoformat(entry["date"]).isoformat() != entry["date"]:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Source date must use YYYY-MM-DD") from exc
        url = entry.get("url", "")
        catalogue = entry.get("catalogue_number", "")
        if not isinstance(url, str) or not isinstance(catalogue, str):
            raise ValueError("Source URL and catalogue number must be strings")
        if not url.strip() and not catalogue.strip():
            raise ValueError("Source requires a URL or catalogue number")
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Source URL must be a public HTTP(S) address")
        for field in ("title", "publisher", "url", "catalogue_number"):
            validate_source_label(entry.get(field, ""))
        sources[number] = entry.copy()
    if set(sources) != set(range(1, row_count + 1)):
        raise ValueError("Every pipe CSV data row requires exactly one source record")
    return sources


def _validate_dimensions(df: pd.DataFrame) -> None:
    if set(_COLUMNS) - set(df.columns):
        raise ValueError("Pipe CSV is missing required columns")
    for column in ("nps_in", "od_mm", "od_in", "wt_mm", "wt_in", "weight_kgm"):
        try:
            values = pd.to_numeric(df[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Pipe column {column} must be numeric") from exc
        if column == "weight_kgm":
            valid = values.isna() | (values.map(math.isfinite) & (values > 0))
        else:
            valid = values.map(math.isfinite) & (values > 0)
        if not valid.all():
            raise ValueError(
                f"Pipe column {column} must contain finite positive values"
            )
        df[column] = values
    if (2 * df["wt_mm"] >= df["od_mm"]).any():
        raise ValueError("Pipe wall thickness must leave a positive internal diameter")
    for prefix in ("od", "wt"):
        # Inch conversion only, with a 0.02 mm allowance for rounded input.
        if ((df[f"{prefix}_in"] * 25.4 - df[f"{prefix}_mm"]).abs() > 0.02).any():
            raise ValueError("Pipe inch and millimetre dimensions must agree")
    if df["schedule"].isna().any() or not df["schedule"].astype(str).str.strip().all():
        raise ValueError("Each pipe row requires a schedule label")
    for label in df["standard"].dropna():
        validate_source_label(label)


class PipelineSpecLookup:
    """Match SI dimensions to caller data with independently recorded provenance.

    Existing no-argument calls return empty results until data is supplied.
    Use ``data_dir`` for a CSV plus sources.yml. Synthetic inputs require an
    explicit test-only opt-in. Result keys and matching tolerances are retained;
    ``provenance`` additionally identifies the matched row's source record.
    """

    def __init__(
        self, data_dir: Optional[Path] = None, *, allow_synthetic: bool = False
    ) -> None:
        self._data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._allow_synthetic = allow_synthetic
        self._df: Optional[pd.DataFrame] = None
        self._sources: dict = {}

    def load(self) -> pd.DataFrame:
        """Load and validate caller dimensions and row sources (lazy, cached)."""
        if self._df is not None:
            return self._df
        csv_path = self._data_dir / _DEFAULT_FILE
        if not csv_path.exists():
            logger.warning("Pipe schedule table not found")
            self._df = pd.DataFrame(columns=_COLUMNS)
            return self._df
        try:
            df = pd.read_csv(csv_path)
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise ValueError("Pipe CSV must contain the compatibility header") from exc
        _validate_dimensions(df)
        sources = _load_sources(
            self._data_dir / "sources.yml", len(df), self._allow_synthetic
        )
        self._sources = sources
        self._df = df
        logger.info("Loaded %d caller-supplied pipe entries", len(df))
        return self._df

    def match_od_wt(
        self,
        od_m: float,
        wt_m: float = 0.0,
        od_tolerance_m: float = _OD_TOLERANCE_M,
        wt_tolerance_m: float = _WT_TOLERANCE_M,
    ) -> Optional[dict]:
        """Match OD/WT (SI units) to closest caller-supplied pipe entry.

        Matching strategy:
          1. Filter rows where |od_mm - od_m*1000| <= od_tolerance_m*1000
          2. Among OD matches, prefer the row with the closest WT; if
             wt_m==0 or no WT match within tolerance, return the first
             OD-matching row (lowest NPS → lowest schedule preference).
          3. Return None if no OD match within tolerance.

        Args:
            od_m: Outer diameter in metres.
            wt_m: Wall thickness in metres. Pass 0.0 to
                match by OD only.
            od_tolerance_m: OD matching tolerance in metres (default 3mm).
            wt_tolerance_m: WT matching tolerance in metres (default 3mm).

        Returns:
            Dict with keys: nps_in, od_mm, od_in, schedule, wt_mm, wt_in,
            weight_kgm, grade_range, standard, domain_hint, source, provenance.
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
            "provenance": self._sources[int(row.name) + 1].copy(),
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
