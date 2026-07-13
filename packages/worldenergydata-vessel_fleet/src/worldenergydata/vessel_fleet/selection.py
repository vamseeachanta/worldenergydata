"""Rig-selection queries over the contractor spec database (#998).

Loads the vendor-spec fleet (``_data/raw/spec_pdf_dimensions/*.parquet`` —
one file per contractor, built by ``scripts/vessel_fleet/
ingest_contractor_spec_pdfs.py``) into one DataFrame and answers the
questions a well planner asks when shortlisting rigs:

    from worldenergydata.vessel_fleet import selection
    fleet = selection.load_spec_fleet()
    deep = selection.filter_rigs(fleet, rig_type="drillship",
                                 min_water_depth_ft=10_000,
                                 min_hookload_kips=2_500)
    selection.compare_rigs(fleet, ["Deepwater Titan", "Noble Valiant"])

All dimension fields are vendor spec-sheet values
(``DIMENSION_CONFIDENCE = measured``); provenance URLs ride along.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

_DATA_DIR = Path(__file__).resolve().parent / "_data"

#: numeric criteria -> (column, comparison) applied by :func:`filter_rigs`
_MIN_CRITERIA = {
    "min_water_depth_ft": "WATER_DEPTH_RATING_FT",
    "min_drilling_depth_ft": "DRILLING_DEPTH_RATING_FT",
    "min_hookload_kips": "HOOKLOAD_RATING_KIPS",
    "min_vdl_st": "VARIABLE_DECK_LOAD_ST",
    "min_moonpool_length_m": "MOONPOOL_LENGTH_M",
    "min_moonpool_width_m": "MOONPOOL_WIDTH_M",
    "min_leg_length_ft": "LEG_LENGTH_FT",
    "min_cantilever_ft": "CANTILEVER_REACH_FT",
    "min_year_built": "YEAR_BUILT",
}

_DISPLAY_COLUMNS = [
    "VESSEL_NAME",
    "OWNER",
    "RIG_TYPE",
    "RIG_DESIGN",
    "YEAR_BUILT",
    "WATER_DEPTH_RATING_FT",
    "DRILLING_DEPTH_RATING_FT",
    "LOA_M",
    "BEAM_M",
    "DRAFT_M",
    "DISPLACEMENT_TONNES",
    "MOONPOOL_LENGTH_M",
    "MOONPOOL_WIDTH_M",
    "LEG_LENGTH_FT",
    "CANTILEVER_REACH_FT",
    "VARIABLE_DECK_LOAD_ST",
    "HOOKLOAD_RATING_KIPS",
    "SETBACK_CAPACITY_KIPS",
    "FLAG_STATE",
    "DATA_SOURCE_URL",
]


def load_spec_fleet(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load every contractor's vendor-spec records into one DataFrame."""
    base = Path(data_dir) if data_dir else _DATA_DIR
    spec_dir = base / "raw/spec_pdf_dimensions"
    frames = [pd.read_parquet(p) for p in sorted(spec_dir.glob("*.parquet"))]
    if not frames:
        raise FileNotFoundError(f"No spec parquets under {spec_dir}")
    fleet = pd.concat(frames, ignore_index=True)
    columns = [c for c in _DISPLAY_COLUMNS if c in fleet.columns]
    extras = [c for c in fleet.columns if c not in columns]
    return fleet[columns + extras]


def filter_rigs(
    fleet: pd.DataFrame,
    rig_type: Optional[str] = None,
    owner_contains: Optional[str] = None,
    design_contains: Optional[str] = None,
    **criteria: float,
) -> pd.DataFrame:
    """Shortlist rigs meeting every given criterion.

    Numeric criteria are ``min_*`` keywords (see ``_MIN_CRITERIA``); rigs
    with the field missing on their spec sheet are excluded by that
    criterion — a shortlist must be defensible, so unknown != qualified.
    """
    unknown = set(criteria) - set(_MIN_CRITERIA)
    if unknown:
        raise TypeError(f"Unknown criteria: {sorted(unknown)}")

    result = fleet
    if rig_type:
        result = result[result["RIG_TYPE"] == rig_type]
    if owner_contains:
        result = result[
            result["OWNER"].str.contains(owner_contains, case=False, na=False)
        ]
    if design_contains:
        result = result[
            result["RIG_DESIGN"].str.contains(design_contains, case=False, na=False)
        ]
    for key, minimum in criteria.items():
        column = _MIN_CRITERIA[key]
        result = result[result[column].notna() & (result[column] >= minimum)]
    return result.reset_index(drop=True)


def compare_rigs(fleet: pd.DataFrame, names: Sequence[str]) -> pd.DataFrame:
    """Side-by-side comparison (one column per rig), case-insensitive names."""
    wanted = {n.strip().upper() for n in names}
    subset = fleet[fleet["VESSEL_NAME"].str.upper().isin(wanted)]
    missing = wanted - set(subset["VESSEL_NAME"].str.upper())
    if missing:
        raise KeyError(f"Rigs not in the spec fleet: {sorted(missing)}")
    columns = [c for c in _DISPLAY_COLUMNS if c in subset.columns]
    return subset.set_index("VESSEL_NAME")[columns[1:]].T


def fleet_summary(fleet: pd.DataFrame) -> pd.DataFrame:
    """Per-contractor coverage summary (rig counts by type + key fields)."""
    grouped = fleet.groupby("OWNER", dropna=False)
    summary = pd.DataFrame(
        {
            "rigs": grouped.size(),
            "drillships": grouped.apply(
                lambda g: int((g["RIG_TYPE"] == "drillship").sum()),
                include_groups=False,
            ),
            "semis": grouped.apply(
                lambda g: int((g["RIG_TYPE"] == "semi_submersible").sum()),
                include_groups=False,
            ),
            "jackups": grouped.apply(
                lambda g: int((g["RIG_TYPE"] == "jack_up").sum()),
                include_groups=False,
            ),
            "with_moonpool": grouped.apply(
                lambda g: int(g["MOONPOOL_LENGTH_M"].notna().sum()),
                include_groups=False,
            ),
        }
    )
    return summary.sort_values("rigs", ascending=False)
