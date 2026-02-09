"""Shared pytest fixtures for intervention analysis tests (WRK-116 Phase 0b).

Provides synthetic DataFrames used across multiple test modules in the
intervention analysis test suite.  Each fixture returns a fresh copy so
tests never share mutable state.

Existing test files retain their own inline ``_make_*`` helpers -- these
shared fixtures are consumed by *new* test modules introduced in
Phases 2-7.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# war_df -- 15-row synthetic WAR DataFrame across 3 years
# ---------------------------------------------------------------------------


@pytest.fixture()
def war_df() -> pd.DataFrame:
    """Synthetic WAR DataFrame with 15 rows across 2020-2022.

    Covers drilling rigs, intervention equipment, and an unknown rig.
    Includes ``BUS_ASC_NAME`` and ``WATER_DEPTH`` columns required by
    downstream reports.
    """
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "DEEPWATER PATHFINDER",   # drillship (heuristic)
                "DEEPWATER PATHFINDER",   # drillship (heuristic)
                "OCEAN STAR",             # semi_submersible (heuristic)
                "OCEAN STAR",             # semi_submersible (heuristic)
                "ROWAN GORILLA V",        # jack_up (fleet)
                "ROWAN GORILLA V",        # jack_up (fleet)
                "ROWAN GORILLA V",        # jack_up (fleet) -- same well
                "WIRELINE UNIT 7",        # wireline_unit (fleet)
                "WIRELINE UNIT 7",        # wireline_unit (fleet)
                "COIL TUBING ALPHA",      # coil_tubing_unit (heuristic)
                "LIFT BOAT 99",           # lift_boat (heuristic)
                "LIFT BOAT 99",           # lift_boat (heuristic)
                "MYSTERY RIG",            # unknown
                "DEEPWATER PATHFINDER",   # drillship 2022
                "WIRELINE UNIT 7",        # wireline_unit 2022
            ],
            "WAR_START_DT": [
                "1/15/2020",
                "3/20/2020",
                "6/1/2020",
                "7/4/2020",
                "2/10/2021",
                "5/22/2021",
                "8/30/2021",
                "4/11/2021",
                "9/15/2021",
                "11/3/2021",
                "1/8/2020",
                "12/25/2020",
                "3/3/2021",
                "6/6/2022",
                "10/10/2022",
            ],
            "WAR_END_DT": [
                "1/21/2020",
                "3/26/2020",
                "6/7/2020",
                "7/10/2020",
                "2/16/2021",
                "5/28/2021",
                "9/5/2021",
                "4/17/2021",
                "9/21/2021",
                "11/9/2021",
                "1/14/2020",
                "12/31/2020",
                "3/9/2021",
                "6/12/2022",
                "10/16/2022",
            ],
            "API_WELL_NUMBER": [
                "W001", "W002", "W003", "W003",
                "W004", "W004", "W004", "W005",
                "W006", "W007", "W008", "W008",
                "W009", "W010", "W011",
            ],
            "BOTM_LEASE_NUM": [
                "L100", "L100", "L200", "L200",
                "L300", "L300", "L300", "L400",
                "L400", "L500", "L600", "L600",
                "L700", "L100", "L400",
            ],
            "AREA_CODE": [
                "GC", "GC", "WR", "WR",
                "HI", "HI", "HI", "GC",
                "GC", "MC", "ST", "ST",
                "VR", "GC", "GC",
            ],
            "BUS_ASC_NAME": [
                "SHELL OFFSHORE",
                "SHELL OFFSHORE",
                "BP EXPLORATION",
                "BP EXPLORATION",
                "CHEVRON USA",
                "CHEVRON USA",
                "CHEVRON USA",
                "TOTAL E&P USA",
                "TOTAL E&P USA",
                "SHELL OFFSHORE",
                "ENI PETROLEUM",
                "ENI PETROLEUM",
                "BP EXPLORATION",
                "SHELL OFFSHORE",
                "TOTAL E&P USA",
            ],
            "WATER_DEPTH": [
                4500.0, 4800.0, 7200.0, 7100.0,
                320.0, 310.0, 330.0, 3200.0,
                3100.0, np.nan, 85.0, 90.0,
                np.nan, 4600.0, 3300.0,
            ],
        }
    )


# ---------------------------------------------------------------------------
# fleet_df -- rig name to rig type mapping
# ---------------------------------------------------------------------------


@pytest.fixture()
def fleet_df() -> pd.DataFrame:
    """Synthetic fleet DataFrame with known rig types.

    Maps a subset of rigs from ``war_df`` to explicit types; the rest
    rely on heuristic classification.
    """
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "ROWAN GORILLA V",
                "WIRELINE UNIT 7",
                "SOME OTHER RIG",
                "LIFT BOAT 99",
                "COIL TUBING ALPHA",
            ],
            "RIG_TYPE": [
                "jack_up",
                "wireline_unit",
                "platform_rig",
                "lift_boat",
                "coil_tubing_unit",
            ],
        }
    )


# ---------------------------------------------------------------------------
# empty_war_df -- empty DataFrame with correct WAR columns
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_war_df() -> pd.DataFrame:
    """Empty WAR DataFrame preserving the full column schema."""
    return pd.DataFrame(
        columns=[
            "RIG_NAME",
            "WAR_START_DT",
            "WAR_END_DT",
            "API_WELL_NUMBER",
            "BOTM_LEASE_NUM",
            "AREA_CODE",
            "BUS_ASC_NAME",
            "WATER_DEPTH",
        ]
    )


# ---------------------------------------------------------------------------
# borehole_df -- synthetic borehole data for Phase 2 enrichment
# ---------------------------------------------------------------------------


@pytest.fixture()
def borehole_df() -> pd.DataFrame:
    """Synthetic borehole data matching a subset of ``war_df`` wells.

    Columns follow BSEE borehole schema conventions.  Wells W001-W008
    are present; W009-W011 are intentionally absent to test left-join
    behaviour in the enrichment engine.
    """
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "W001", "W002", "W003", "W004",
                "W005", "W006", "W007", "W008",
            ],
            "WELL_SPUD_DATE": [
                "2019-11-01", "2020-01-10", "2020-04-15", "2020-12-01",
                "2021-02-20", "2021-07-01", "2021-09-10", "2019-06-15",
            ],
            "TOTAL_DEPTH_DATE": [
                "2020-01-10", "2020-03-15", "2020-05-30", "2021-02-05",
                "2021-04-08", "2021-09-12", "2021-11-25", "2019-12-20",
            ],
            "BH_TOTAL_MD": [
                18500.0, 22000.0, 25000.0, 12000.0,
                15500.0, 9800.0, 8200.0, 21000.0,
            ],
            "WATER_DEPTH": [
                4500.0, 4800.0, 7200.0, 320.0,
                3200.0, 3100.0, 950.0, 85.0,
            ],
            "BOREHOLE_STAT_CD": [
                "COM", "COM", "PA", "DRL",
                "ST", "TA", "COM", "PA",
            ],
            "WELL_NAME_SUFFIX": [
                "ST00BP00", "ST00BP00", "ST00BP00", "ST00BP00",
                "ST00BP00", "ST00BP00", "ST00BP00", "ST00BP00",
            ],
        }
    )


# ---------------------------------------------------------------------------
# paleowells_era_map -- geological era mapping for a subset of wells
# ---------------------------------------------------------------------------


@pytest.fixture()
def paleowells_era_map() -> dict[str, str]:
    """Map API_WELL_NUMBER to geological era string.

    Only a subset of wells have era data -- mirrors real-world sparsity.
    """
    return {
        "W001": "Miocene",
        "W002": "Miocene",
        "W003": "Eocene",
        "W004": "Pleistocene",
        "W005": "Oligocene",
        "W007": "Pliocene",
    }


# ---------------------------------------------------------------------------
# enriched_df -- pre-built enriched DataFrame (Phase 2 output shape)
# ---------------------------------------------------------------------------


@pytest.fixture()
def enriched_df(
    war_df: pd.DataFrame,
    fleet_df: pd.DataFrame,
    borehole_df: pd.DataFrame,
    paleowells_era_map: dict[str, str],
) -> pd.DataFrame:
    """Pre-built enriched DataFrame simulating Phase 2 output.

    Combines WAR, fleet, borehole, and paleowells data with all derived
    columns that downstream analyzers and reports expect.
    """
    df = war_df.copy()

    # --- Rig type from fleet (left join) then heuristic fallback ---
    df = df.merge(
        fleet_df[["RIG_NAME", "RIG_TYPE"]],
        on="RIG_NAME",
        how="left",
    )
    _heuristic_map = {
        "DEEPWATER PATHFINDER": "drillship",
        "OCEAN STAR": "semi_submersible",
        "MYSTERY RIG": "unknown",
    }
    mask = df["RIG_TYPE"].isna()
    df.loc[mask, "RIG_TYPE"] = df.loc[mask, "RIG_NAME"].map(_heuristic_map)
    df["RIG_TYPE"] = df["RIG_TYPE"].fillna("unknown")

    # --- Activity category ---
    _drilling = frozenset(
        ["drillship", "semi_submersible", "jack_up", "platform_rig",
         "tender_assisted", "inland_barge", "submersible"]
    )
    _intervention = frozenset(
        ["wireline_unit", "coil_tubing_unit", "lift_boat", "snubbing_unit",
         "workover_rig", "support_vessel", "pumping_unit"]
    )

    def _classify(rt: str) -> str:
        if rt in _drilling:
            return "drilling"
        if rt in _intervention:
            return "intervention"
        return "unknown"

    df["ACTIVITY_CATEGORY"] = df["RIG_TYPE"].map(_classify)

    # --- Year from WAR_START_DT ---
    dt = pd.to_datetime(
        df["WAR_START_DT"], format="mixed", dayfirst=False, errors="coerce"
    )
    df["YEAR"] = dt.dt.year.astype("Int64")

    # --- Borehole enrichment (left join on API_WELL_NUMBER) ---
    bh = borehole_df.rename(columns={"WATER_DEPTH": "BH_WATER_DEPTH"}).copy()
    bh["WELL_SPUD_DATE"] = pd.to_datetime(bh["WELL_SPUD_DATE"])
    bh["TOTAL_DEPTH_DATE"] = pd.to_datetime(bh["TOTAL_DEPTH_DATE"])
    bh["DRILLING_DAYS"] = (
        bh["TOTAL_DEPTH_DATE"] - bh["WELL_SPUD_DATE"]
    ).dt.days.astype(float)

    df = df.merge(
        bh[["API_WELL_NUMBER", "WELL_SPUD_DATE", "TOTAL_DEPTH_DATE",
            "BH_TOTAL_MD", "BH_WATER_DEPTH", "BOREHOLE_STAT_CD",
            "WELL_NAME_SUFFIX", "DRILLING_DAYS"]],
        on="API_WELL_NUMBER",
        how="left",
    )

    # --- Well status (alias) ---
    df["WELL_STATUS"] = df["BOREHOLE_STAT_CD"]

    # --- Water depth classification ---
    def _classify_depth(depth: float) -> str:
        if pd.isna(depth):
            return "Unknown"
        if depth < 200:
            return "Shallow"
        if depth < 1000:
            return "Mid"
        if depth < 5000:
            return "Deep"
        return "Ultra-deep"

    df["WATER_DEPTH_CLASS"] = df["WATER_DEPTH"].map(_classify_depth)

    # --- Geological era from paleowells ---
    df["GEOLOGICAL_ERA"] = df["API_WELL_NUMBER"].map(paleowells_era_map)

    return df
