# ABOUTME: Pure analysis functions for NDBC wave data processing (WRK-316).
# ABOUTME: Parsing, scatter matrices, seasonal filtering, Weibull fits, wave roses.
"""
NDBC Analysis Functions

Pure functional helpers for NDBC buoy data:
- parse_stdmet_line: Parse one line from an NDBC stdmet text file.
- parse_stdmet_file: Parse a complete NDBC stdmet text file.
- build_scatter_matrix: Build an Hs/Tp scatter matrix.
- filter_by_season: Filter a DataFrame to specific calendar months.
- fit_weibull_hs: Fit a 2- or 3-parameter Weibull distribution to Hs data.
- wave_rose: Build a directional Hs breakdown from records.

No network I/O or database access is performed by any function in this module.
"""

from __future__ import annotations

import gzip
import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
from scipy.stats import weibull_min

from worldenergydata.metocean.constants import NDBC_MISSING_VALUES

logger = logging.getLogger(__name__)

# Default Hs and Tp bin edges for scatter matrices
_DEFAULT_HS_BINS: List[float] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
_DEFAULT_TP_BINS: List[float] = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
_MIN_WEIBULL_SAMPLES = 3


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_stdmet_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse one line from an NDBC standard meteorological text file.

    Comment lines (``#``) and lines with fewer than 5 tokens return ``None``.

    Column mapping (NDBC stdmet format):
        0: YY, 1: MM, 2: DD, 3: hh, 4: mm,
        5: WDIR, 6: WSPD, 7: GST, 8: WVHT (hs),
        9: DPD, 10: APD, 11: MWD, 12: PRES,
        13: ATMP, 14: WTMP, 15: DEWP, 16: VIS, 17: PTDY, 18: TIDE

    Returns:
        dict with keys ``observation_time``, ``hs``, ``dpd``, ``apd``,
        ``mwd``, ``wtmp``, ``wdir``, ``wspd``, ``gst``, ``pres``,
        ``atmp``, ``dewp``, ``vis``, ``ptdy``, ``tide``; values may
        be ``None`` for missing-value sentinels.
    """
    if not line or line.startswith("#"):
        return None

    parts = line.split()
    if len(parts) < 5:
        return None

    def _val(idx: int) -> Optional[float]:
        if idx >= len(parts):
            return None
        raw = parts[idx]
        if raw in NDBC_MISSING_VALUES:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = int(parts[3])
        minute = int(parts[4])
    except (ValueError, IndexError):
        return None

    if year < 100:
        year = 2000 + year if year < 50 else 1900 + year

    try:
        obs_time = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    return {
        "observation_time": obs_time,
        "wdir": _val(5),
        "wspd": _val(6),
        "gst": _val(7),
        "hs": _val(8),
        "dpd": _val(9),
        "apd": _val(10),
        "mwd": _val(11),
        "pres": _val(12),
        "atmp": _val(13),
        "wtmp": _val(14),
        "dewp": _val(15),
        "vis": _val(16),
        "ptdy": _val(17),
        "tide": _val(18),
    }


def parse_stdmet_file(
    path: Union[str, pathlib.Path],
) -> List[Dict[str, Any]]:
    """
    Parse a complete NDBC standard meteorological text file.

    Reads every non-comment line through :func:`parse_stdmet_line`.
    Supports plain ``.txt`` and gzip-compressed ``.txt.gz`` files.
    Returns an empty list when the file is absent (does not raise).

    Args:
        path: Filesystem path to the NDBC stdmet file.

    Returns:
        List of record dicts (may be empty).
    """
    file_path = pathlib.Path(path)
    if not file_path.exists():
        logger.warning("NDBC data file not found: %s", file_path)
        return []

    try:
        if file_path.suffix == ".gz":
            with gzip.open(file_path, "rt", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        else:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
    except OSError as exc:
        logger.error("Failed to read NDBC file %s: %s", file_path, exc)
        return []

    records: List[Dict[str, Any]] = []
    for line in lines:
        rec = parse_stdmet_line(line.rstrip("\n"))
        if rec is not None:
            records.append(rec)

    logger.debug("Parsed %d records from %s", len(records), file_path)
    return records


# ---------------------------------------------------------------------------
# Scatter matrix
# ---------------------------------------------------------------------------


def build_scatter_matrix(
    records: Sequence[Dict[str, Any]],
    hs_bins: Optional[Sequence[float]] = None,
    tp_bins: Optional[Sequence[float]] = None,
    normalize: bool = False,
) -> np.ndarray:
    """
    Build a 2-D Hs/Tp wave scatter matrix from record dicts.

    Records missing ``"hs"`` or ``"tp"`` keys (or with ``None`` values)
    are silently skipped.  Out-of-range values are also skipped.

    Args:
        records: Sequence of dicts with ``"hs"`` and ``"tp"`` floats.
        hs_bins: Bin edges for Hs (m). Defaults to 0–10 m in 1 m steps.
        tp_bins: Bin edges for Tp (s). Defaults to 0–20 s in 2 s steps.
        normalize: If True, divide counts by total so entries sum to 1.0.

    Returns:
        numpy.ndarray of shape ``(len(hs_bins)-1, len(tp_bins)-1)``.
    """
    hs_edges = np.asarray(hs_bins if hs_bins is not None else _DEFAULT_HS_BINS)
    tp_edges = np.asarray(tp_bins if tp_bins is not None else _DEFAULT_TP_BINS)

    n_hs = len(hs_edges) - 1
    n_tp = len(tp_edges) - 1
    matrix = np.zeros((n_hs, n_tp), dtype=float)

    for rec in records:
        hs = rec.get("hs")
        tp = rec.get("tp")
        if hs is None or tp is None:
            continue
        try:
            hs = float(hs)
            tp = float(tp)
        except (TypeError, ValueError):
            continue

        i_hs = int(np.searchsorted(hs_edges, hs, side="right")) - 1
        i_tp = int(np.searchsorted(tp_edges, tp, side="right")) - 1

        if 0 <= i_hs < n_hs and 0 <= i_tp < n_tp:
            matrix[i_hs, i_tp] += 1.0

    if normalize:
        total = matrix.sum()
        if total > 0:
            matrix = matrix / total

    return matrix


# ---------------------------------------------------------------------------
# Seasonal filtering
# ---------------------------------------------------------------------------


def filter_by_season(
    df: pd.DataFrame,
    months: List[int],
    time_col: str = "time",
) -> pd.DataFrame:
    """
    Filter a DataFrame to rows whose timestamp falls in the given months.

    Args:
        df: DataFrame containing a datetime column.
        months: Integer month numbers (1=Jan … 12=Dec).
        time_col: Datetime column name. Defaults to ``"time"``.

    Returns:
        Filtered DataFrame copy. Empty if ``months`` is empty.
    """
    if not months:
        return df.iloc[0:0].copy()

    mask = df[time_col].dt.month.isin(months)
    return df.loc[mask].copy()


# ---------------------------------------------------------------------------
# Weibull distribution fit
# ---------------------------------------------------------------------------


def fit_weibull_hs(
    hs_values: Sequence[float],
    n_params: int = 2,
) -> Dict[str, float]:
    """
    Fit a Weibull distribution to significant wave height data.

    Uses ``scipy.stats.weibull_min``.  For a 2-parameter fit the
    location is fixed at zero (``floc=0``).

    Args:
        hs_values: Sequence of positive Hs floats (metres).
        n_params: 2 for 2-parameter (shape, scale);
                  3 for 3-parameter (shape, loc, scale).

    Returns:
        Dict with keys ``"shape"``, ``"scale"`` (and ``"loc"`` for n_params=3).

    Raises:
        ValueError: Empty input, fewer than 3 samples, or invalid n_params.
    """
    if n_params not in (2, 3):
        raise ValueError(f"n_params must be 2 or 3, got {n_params!r}")

    data = [v for v in hs_values if v is not None]
    if len(data) == 0:
        raise ValueError("hs_values must not be empty")
    if len(data) < _MIN_WEIBULL_SAMPLES:
        raise ValueError(
            f"Need at least {_MIN_WEIBULL_SAMPLES} data points "
            f"for Weibull fit, got {len(data)}"
        )

    arr = np.asarray(data, dtype=float)
    if n_params == 2:
        shape, _loc, scale = weibull_min.fit(arr, floc=0)
        return {"shape": float(shape), "scale": float(scale)}
    else:
        shape, loc, scale = weibull_min.fit(arr)
        return {"shape": float(shape), "loc": float(loc), "scale": float(scale)}


# ---------------------------------------------------------------------------
# Directional wave rose
# ---------------------------------------------------------------------------


def _build_sector_labels(n_sectors: int) -> List[str]:
    """Build evenly-spaced directional sector labels (e.g. '0-45deg')."""
    width = 360.0 / n_sectors
    return [f"{i * width:.0f}-{(i + 1) * width:.0f}deg" for i in range(n_sectors)]


def wave_rose(
    records: Sequence[Dict[str, Any]],
    n_sectors: int = 8,
    direction_key: str = "mwd",
    hs_key: str = "hs",
) -> Dict[str, Any]:
    """
    Compute a directional wave rose from observation records.

    Groups records into ``n_sectors`` evenly-spaced sectors (0–360 deg)
    and computes mean Hs and occurrence frequency per sector.

    Args:
        records: Dicts with Hs and direction keys.
        n_sectors: Number of directional sectors (default 8).
        direction_key: Direction key name. Defaults to ``"mwd"``.
        hs_key: Wave height key name. Defaults to ``"hs"``.

    Returns:
        Dict with keys ``"sectors"``, ``"mean_hs"``, ``"frequency"``,
        ``"count"``, and ``"n_sectors"``.
    """
    width = 360.0 / n_sectors
    sector_labels = _build_sector_labels(n_sectors)
    sector_hs: Dict[str, List[float]] = {s: [] for s in sector_labels}

    valid_total = 0
    for rec in records:
        direction = rec.get(direction_key)
        hs = rec.get(hs_key)
        if direction is None or hs is None:
            continue
        try:
            direction = float(direction) % 360.0
            hs = float(hs)
        except (TypeError, ValueError):
            continue

        sector_idx = int(direction / width) % n_sectors
        sector_hs[sector_labels[sector_idx]].append(hs)
        valid_total += 1

    mean_hs: Dict[str, float] = {}
    frequency: Dict[str, float] = {}
    count: Dict[str, int] = {}

    for label in sector_labels:
        vals = sector_hs[label]
        count[label] = len(vals)
        mean_hs[label] = float(np.mean(vals)) if vals else 0.0
        frequency[label] = len(vals) / valid_total if valid_total > 0 else 0.0

    return {
        "sectors": sector_labels,
        "mean_hs": mean_hs,
        "frequency": frequency,
        "count": count,
        "n_sectors": n_sectors,
    }


__all__ = [
    "build_scatter_matrix",
    "filter_by_season",
    "fit_weibull_hs",
    "parse_stdmet_file",
    "parse_stdmet_line",
    "wave_rose",
]
