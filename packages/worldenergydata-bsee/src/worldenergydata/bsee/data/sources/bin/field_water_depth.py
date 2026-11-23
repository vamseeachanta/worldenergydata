"""Field-level water depth from materialized BSEE structure/lease ``.bin`` data.

Two on-disk pickled DataFrames carry water depth keyed by BOEM field code:

* PRIMARY: ``<bin>/platstruc/mv_platstruc_structures.bin`` — per-structure
  ``WATER_DEPTH`` (ft), averaged to one value per ``FIELD_NAME_CODE``.  This
  is the authoritative source for fields that have a fixed/floating structure.
* FALLBACK: ``<bin>/deepqual/mv_deep_water_field_leases.bin`` — per-lease
  ``FLD_AVG_WTR_DPTH`` (ft) for deep-water qualified leases.  Used only to
  FILL GAPS for field codes that platstruc does not cover (e.g. subsea
  tiebacks with no own structure).

The two are merged platstruc-wins; depths are real BSEE public values and
are never fabricated.  LFS stubs, missing files, and non-DataFrame pickles
are handled gracefully (a partial or empty dict is returned, never raised),
mirroring the guard pattern in :mod:`field_names`.
"""

from __future__ import annotations

import logging
import pickle  # nosec B403
from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_PLATSTRUC_REL = ("platstruc", "mv_platstruc_structures.bin")
_DEEPQUAL_REL = ("deepqual", "mv_deep_water_field_leases.bin")


def _load_pickle_safe(path: Path) -> Optional[pd.DataFrame]:
    """Load a pickled DataFrame, returning ``None`` for LFS stubs/errors."""
    if not path.exists():
        logger.warning("Water-depth source not found: %s", path)
        return None
    try:
        with open(path, "rb") as f:
            header = f.read(40)
        if b"version https://git-lfs" in header:
            logger.warning("LFS stub (not materialized): %s", path)
            return None
        with open(path, "rb") as f:
            obj = pickle.load(f)  # nosec B301
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error loading %s: %s", path, exc)
        return None
    if not isinstance(obj, pd.DataFrame):
        logger.warning("Not a DataFrame: %s", path)
        return None
    return obj


def _avg_by_field(
    df: Optional[pd.DataFrame], field_col: str, depth_col: str
) -> dict[str, float]:
    """Average a depth column by field code, dropping non-positive/blank rows."""
    if df is None or df.empty:
        return {}
    if field_col not in df.columns or depth_col not in df.columns:
        logger.warning(
            "Missing columns %s/%s in water-depth source", field_col, depth_col
        )
        return {}

    work = pd.DataFrame(
        {
            "field": df[field_col]
            .astype(str)
            .str.replace('"', "", regex=False)
            .str.strip(),
            "depth": pd.to_numeric(df[depth_col], errors="coerce"),
        }
    )
    work = work[(work["depth"] > 0) & (work["field"] != "")]
    if work.empty:
        return {}
    grouped = work.groupby("field")["depth"].mean().round()
    return {str(k): float(v) for k, v in grouped.items()}


def load_field_water_depth(data_dir: Optional[Path] = None) -> dict[str, float]:
    """Return ``{FIELD_NAME_CODE: avg_water_depth_ft}`` from BSEE bin data.

    Parameters
    ----------
    data_dir:
        Directory containing the ``platstruc/`` and ``deepqual/`` subdirs.
        Defaults to ``<bsee module>/bin`` (resolved via the repo data
        resolver, which follows the materialized-data symlink).

    Returns
    -------
    dict
        Field code -> average water depth (ft), rounded.  platstruc values
        take precedence; deepqual fills only the field codes platstruc
        lacks.  Empty when neither source is materialized.
    """
    if data_dir is None:
        data_dir = get_module_data_safe("bsee") / "bin"
    data_dir = Path(data_dir)

    platstruc = _avg_by_field(
        _load_pickle_safe(data_dir.joinpath(*_PLATSTRUC_REL)),
        "FIELD_NAME_CODE",
        "WATER_DEPTH",
    )
    deepqual = _avg_by_field(
        _load_pickle_safe(data_dir.joinpath(*_DEEPQUAL_REL)),
        "FIELD_NAME_CODE",
        "FLD_AVG_WTR_DPTH",
    )

    # platstruc wins for duplicate field codes; deepqual fills gaps only.
    merged = dict(deepqual)
    merged.update(platstruc)

    logger.info(
        "Field water depth: %d codes (platstruc=%d, deepqual-fill=%d)",
        len(merged),
        len(platstruc),
        len(merged) - len(platstruc),
    )
    return merged
