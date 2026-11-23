"""Field-level geological era lifting from Paleowells data.

The base :class:`GeologicalEraClassifier` only credits a field with an era
when that field's *producing* wells appear in ``Paleowells.csv`` — which
leaves the vast majority of fields ``Unknown`` (~111/1390).

This module lifts paleo-well eras to the **field** level by joining *all*
paleo wells (producing or not) to their bottom-hole field code via the
``mv_api_list_all`` API->field table, then assigning each field its
dominant (most common) era.  The resulting field-level map is treated as
authoritative when applied over an all-fields atlas.

A Lower-Tertiary flag (Paleocene / Eocene / Oligocene) is also derived.
All inputs are real BSEE public data; missing/unmaterialized files degrade
gracefully to an empty map rather than fabricating eras.
"""

from __future__ import annotations

import logging
import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from worldenergydata.bsee.paleowells.era_classifier import GeologicalEraClassifier
from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

# Lower Tertiary plays of interest (Wilcox / pre-Miocene deepwater GoM).
LOWER_TERTIARY_ERAS = frozenset({"Paleocene", "Eocene", "Oligocene"})

_PALEO_RELPATH = ("paleowells", "Paleowells.csv")
_APIRAW_RELPATH = ("bin", "apiraw", "mv_api_list_all.bin")

_API_COL = "API_WELL_NUMBER"
_FIELD_COL = "BOTM_FLD_NAME_CD"


def is_lower_tertiary(era: Optional[str]) -> bool:
    """Return ``True`` iff ``era`` is one of the Lower Tertiary epochs."""
    return era in LOWER_TERTIARY_ERAS


def _load_apiraw_pickle(file_path: Path) -> pd.DataFrame:
    """Load the API->field pickle, degrading to empty on stub/missing/bad type.

    Mirrors the LFS-stub / missing-file / non-DataFrame guards used by
    :class:`worldenergydata.bsee.data.field_names.FieldNameResolver`.
    """
    if not file_path.exists():
        logger.warning("apiraw file not found: %s", file_path)
        return pd.DataFrame()

    try:
        with open(file_path, "rb") as f:
            header = f.read(40)
        if b"version https://git-lfs" in header:
            logger.warning("LFS stub detected (not materialized): %s", file_path)
            return pd.DataFrame()

        with open(file_path, "rb") as f:
            obj = pickle.load(f)  # nosec B301

        if isinstance(obj, pd.DataFrame):
            return obj

        logger.warning("apiraw file does not contain a DataFrame: %s", file_path)
        return pd.DataFrame()

    except Exception as e:  # pragma: no cover - defensive
        logger.error("Error loading apiraw %s: %s", file_path, e)
        return pd.DataFrame()


def _build_api_to_field(apiraw: pd.DataFrame) -> Dict[str, str]:
    """Build ``{API_WELL_NUMBER: BOTM_FLD_NAME_CD}`` from the apiraw frame."""
    if apiraw.empty:
        return {}
    if _API_COL not in apiraw.columns or _FIELD_COL not in apiraw.columns:
        logger.warning(
            "apiraw missing expected columns %s/%s (have: %s)",
            _API_COL,
            _FIELD_COL,
            list(apiraw.columns),
        )
        return {}

    api_to_field: Dict[str, str] = {}
    for api, field in zip(apiraw[_API_COL], apiraw[_FIELD_COL]):
        api_str = str(api).strip()
        field_str = str(field).strip()
        if api_str and field_str:
            api_to_field[api_str] = field_str
    return api_to_field


def build_field_era_map(data_dir: Optional[Path] = None) -> Dict[str, str]:
    """Build a ``{field_code: dominant_era}`` map from all paleo wells.

    Joins every paleo well that has an era to its bottom-hole field code,
    accumulates era votes per field, and assigns each field its most common
    era.  Returns an empty dict (never raises) when the apiraw join table is
    missing/unmaterialized.

    Args:
        data_dir: BSEE module data dir; defaults to
            ``get_module_data_safe("bsee")``.  The paleo CSV is expected at
            ``<data_dir>/paleowells/Paleowells.csv`` and the apiraw pickle at
            ``<data_dir>/bin/apiraw/mv_api_list_all.bin``.
    """
    base_dir = Path(data_dir) if data_dir is not None else get_module_data_safe("bsee")

    paleo_csv = base_dir.joinpath(*_PALEO_RELPATH)
    apiraw_bin = base_dir.joinpath(*_APIRAW_RELPATH)

    well_eras = GeologicalEraClassifier(paleowells_csv=paleo_csv).get_well_eras()
    if not well_eras:
        logger.warning("No well eras from %s", paleo_csv)
        return {}

    api_to_field = _build_api_to_field(_load_apiraw_pickle(apiraw_bin))
    if not api_to_field:
        return {}

    field_votes: Dict[str, Counter] = defaultdict(Counter)
    for api, era in well_eras.items():
        api_str = str(api).strip()
        field = api_to_field.get(api_str)
        if field and era:
            field_votes[field][era] += 1

    field_era: Dict[str, str] = {
        field: votes.most_common(1)[0][0] for field, votes in field_votes.items()
    }
    logger.info(
        "Built field-era map: %d fields from %d paleo wells",
        len(field_era),
        len(well_eras),
    )
    return field_era


def apply_field_era(
    result_df: pd.DataFrame, field_era_map: Dict[str, str]
) -> pd.DataFrame:
    """Override per-field era with the authoritative field-level map.

    Returns a copy of ``result_df`` where ``GEOLOGICAL_ERA`` is replaced by
    ``field_era_map[FIELD_CODE]`` for every field present in the map (the
    field-level map uses *all* paleo wells, so it is authoritative over the
    producing-well-only classifier).  Rows whose field is absent from the map
    keep their existing era (which may be ``"Unknown"``).

    Also adds/sets a boolean column ``IS_LOWER_TERTIARY`` derived from the
    (possibly overridden) ``GEOLOGICAL_ERA``.
    """
    out = result_df.copy()

    if out.empty:
        if "IS_LOWER_TERTIARY" not in out.columns:
            out["IS_LOWER_TERTIARY"] = pd.Series(dtype=bool)
        return out

    if "GEOLOGICAL_ERA" not in out.columns:
        out["GEOLOGICAL_ERA"] = "Unknown"

    if field_era_map and "FIELD_CODE" in out.columns:
        mapped = out["FIELD_CODE"].astype(str).str.strip().map(field_era_map)
        out["GEOLOGICAL_ERA"] = mapped.fillna(out["GEOLOGICAL_ERA"])

    out["IS_LOWER_TERTIARY"] = out["GEOLOGICAL_ERA"].apply(is_lower_tertiary)
    return out
