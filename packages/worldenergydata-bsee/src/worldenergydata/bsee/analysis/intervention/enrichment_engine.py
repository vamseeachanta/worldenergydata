"""Multi-source join engine for WAR data enrichment (WRK-116 Phase 2).

Joins WAR records with fleet, borehole, and paleowells data to produce
a row-level enriched DataFrame suitable for downstream analysis.

``DRILLING_DAYS`` is *not* derived here.  It comes from
:mod:`worldenergydata.bsee.analysis.war_rig_days`, the single implementation
of rig-days across the repo (#1063 / #1075).  This module previously computed
``TOTAL_DEPTH_DATE - WELL_SPUD_DATE``, a calendar span that for a suspended or
batch-drilled wellbore measures elapsed time rather than rig time and reached
3,980 days on this dataset.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    classify_activity,
)
from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM,
    STATUS_COVERED,
    STATUS_NO_ACTIVITY,
    Basis,
    rig_days_by_bore,
)
from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
    RigType,
    classify_rig_type,
)
from worldenergydata.bsee.data.utils.api_well_normalizer import (
    normalize_api_well_number,
)

_DEPTH_BINS: list[tuple[float, float, str]] = [
    (0, 200, "Shallow"),
    (200, 1000, "Mid"),
    (1000, 5000, "Deep"),
    (5000, float("inf"), "Ultra-deep"),
]

_CATEGORY_COLS: list[str] = [
    "RIG_TYPE",
    "ACTIVITY_CATEGORY",
    "AREA_CODE",
    "WATER_DEPTH_CLASS",
    # Few distinct values over the whole frame; category keeps the two
    # provenance columns from costing anything meaningful in memory.
    "DRILLING_DAYS_STATUS",
    "DRILLING_DAYS_BASIS",
]


# Columns ``war_rig_days.rig_days_by_bore`` needs on a single row.
_ACTIVITY_COLS = (
    "API_WELL_NUMBER",
    "WAR_START_DT",
    "WAR_END_DT",
    "WELL_ACTIVITY_CD",
)

# Reported by get_join_stats() so a null DRILLING_DAYS column is diagnosable
# rather than silently indistinguishable from "no wells matched".
SOURCE_DIRECT = "war_frame"
SOURCE_SN_WAR_JOIN = "sn_war_self_join"
SOURCE_UNAVAILABLE = "unavailable"

# A third state the shared module does not model: the bore *is* in WAR, but
# none of its weeks carry a drilling code, so drilling_days comes back 0.
# On the full BSEE corpus that is 14,657 of 27,033 covered bores (54%) --
# the WAR corpus is dominated by TA/PA/WO returns, and a bore drilled before
# WAR reporting began appears with only its later plugging weeks.  The 0 is
# kept (it is what the basis says) but is labelled distinctly so a consumer
# averaging DRILLING_DAYS can tell a real zero-day well from an unobserved
# one.  See the #1075 report: flipping these to null is a live question.
STATUS_NO_DRILLING = "no_drilling_activity"


def _resolve_war_activity(
    war_df: pd.DataFrame,
    explicit: pd.DataFrame | None,
) -> tuple[pd.DataFrame | None, str]:
    """Return WAR rows carrying all four rig-days columns, and their provenance.

    ``WARDataAcquirer.acquire_war_dataframe`` returns ``pd.concat`` of every
    member of the WAR zip, so ``WELL_ACTIVITY_CD`` (from mv_war_main_prop) and
    ``API_WELL_NUMBER``/``WAR_START_DT`` (from mv_war_main) land on *different*
    rows -- on the real dataset exactly zero rows carry all four.  The two
    tables still share ``SN_WAR``, so they can be re-joined here.  A caller
    that already holds a properly joined frame should pass it as ``explicit``.
    """
    if explicit is not None:
        return explicit, SOURCE_DIRECT

    if all(c in war_df.columns for c in _ACTIVITY_COLS):
        complete = war_df[list(_ACTIVITY_COLS)].notna().all(axis=1)
        if complete.any():
            return war_df.loc[complete], SOURCE_DIRECT

    if "SN_WAR" in war_df.columns and "WELL_ACTIVITY_CD" in war_df.columns:
        week_cols = ["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT"]
        if all(c in war_df.columns for c in week_cols):
            weeks = war_df.loc[
                war_df["SN_WAR"].notna()
                & war_df["API_WELL_NUMBER"].notna()
                & war_df["WAR_START_DT"].notna(),
                week_cols,
            ]
            codes = war_df.loc[
                war_df["SN_WAR"].notna() & war_df["WELL_ACTIVITY_CD"].notna(),
                ["SN_WAR", "WELL_ACTIVITY_CD"],
            ]
            if not weeks.empty and not codes.empty:
                joined = weeks.merge(codes, on="SN_WAR", how="inner")
                if not joined.empty:
                    return joined, SOURCE_SN_WAR_JOIN

    return None, SOURCE_UNAVAILABLE


def _classify_water_depth(depth: float) -> str:
    """Return water depth classification string."""
    if pd.isna(depth):
        return "Unknown"
    for low, high, label in _DEPTH_BINS:
        if low <= depth < high:
            return label
    return "Unknown"


class ActivityEnrichmentEngine:
    """Multi-source join engine for WAR data enrichment."""

    def __init__(
        self,
        war_df: pd.DataFrame,
        fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame | None = None,
        era_map: dict[str, str] | None = None,
        war_activity_df: pd.DataFrame | None = None,
        rig_days_basis: Basis = BASIS_DRL_COM,
    ) -> None:
        self._war_df = war_df.copy()
        self._fleet_df = fleet_df.copy()
        self._borehole_df = borehole_df.copy() if borehole_df is not None else None
        self._era_map = era_map
        self._war_activity_df = war_activity_df
        self._rig_days_basis = rig_days_basis
        self._rig_days_source = SOURCE_UNAVAILABLE
        self._result: pd.DataFrame | None = None

    # -- Step 1: WAR to Fleet join -------------------------------------------

    def _join_fleet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Left-join WAR to fleet, apply heuristic fallback, add category."""
        df = df.merge(
            self._fleet_df[["RIG_NAME", "RIG_TYPE"]],
            on="RIG_NAME",
            how="left",
        )
        # Track which rows came from fleet (before fallback fills them).
        df["_fleet_matched"] = df["RIG_TYPE"].notna()

        # Heuristic fallback for unmatched rigs.
        mask = df["RIG_TYPE"].isna()
        if mask.any():
            df.loc[mask, "RIG_TYPE"] = df.loc[mask, "RIG_NAME"].apply(
                lambda name: (
                    classify_rig_type(str(name)).value
                    if pd.notna(name)
                    else RigType.UNKNOWN.value
                )
            )

        df["ACTIVITY_CATEGORY"] = df["RIG_TYPE"].map(classify_activity)

        # Parse YEAR from WAR_START_DT with WAR_END_DT fallback.
        dt = pd.to_datetime(
            df["WAR_START_DT"],
            format="mixed",
            dayfirst=False,
            errors="coerce",
        )
        if "WAR_END_DT" in df.columns:
            fallback = pd.to_datetime(
                df["WAR_END_DT"],
                format="mixed",
                dayfirst=False,
                errors="coerce",
            )
            dt = dt.fillna(fallback)
        df["YEAR"] = dt.dt.year.astype("Int64")

        return df

    # -- Step 2: WAR to Borehole join ----------------------------------------

    # Columns that borehole join will introduce — drop WAR-side copies
    # to prevent pandas _x/_y suffix collision.  The WAR zip's
    # mv_war_boreholes_view.txt already contains these columns; the
    # borehole download is the authoritative source.
    _BH_JOIN_COLS = frozenset(
        {
            "WELL_SPUD_DATE",
            "TOTAL_DEPTH_DATE",
            "BH_TOTAL_MD",
            "WELL_NAME_SUFFIX",
            "DRILLING_DAYS",
            "DRILLING_DAYS_STATUS",
            "DRILLING_DAYS_BASIS",
            "BOREHOLE_STAT_CD",
            "WELL_BORE_TVD",
        }
    )

    def _rig_days_for_bores(self, bh: pd.DataFrame) -> pd.DataFrame:
        """Attach WAR rig-days to ``bh`` at its own API12 grain.

        The borehole frame is keyed on the 12-digit API -- the *wellbore*,
        each sidetrack its own suffix -- which is the grain
        ``rig_days_by_bore`` emits, so no roll-up is involved and
        ``rig_days_by_well`` would be the wrong function here.

        Bores with no WAR activity keep ``NaN``: absence of coverage is never
        rendered as a zero-day well.  A bore that *is* covered but logged no
        drilling week takes the basis at its word and is emitted as 0, tagged
        ``no_drilling_activity`` so the two cannot be conflated downstream.
        """
        api12 = normalize_api_well_number(bh["API_WELL_NUMBER"])
        bh["DRILLING_DAYS"] = float("nan")
        bh["DRILLING_DAYS_STATUS"] = STATUS_NO_ACTIVITY
        bh["DRILLING_DAYS_BASIS"] = self._rig_days_basis.describe()

        war, source = _resolve_war_activity(self._war_df, self._war_activity_df)
        self._rig_days_source = source
        if war is None:
            return bh

        population = sorted({a for a in api12.dropna().tolist() if a})
        if not population:
            return bh

        # Normalise the WAR-side API to the same form as the borehole side
        # before handing the frame over.  ``pd.concat`` over the WAR zip
        # members widens API_WELL_NUMBER to float64, so it stringifies as
        # "177084082200.0"; war_rig_days._prepare only does .astype(str)
        # .str.strip(), which leaves the ".0" on and drives the overlap with
        # the borehole population to exactly zero.
        war = war.assign(
            API_WELL_NUMBER=normalize_api_well_number(war["API_WELL_NUMBER"])
        ).dropna(subset=["API_WELL_NUMBER"])

        days = rig_days_by_bore(war, basis=self._rig_days_basis, population=population)
        covered = days[days["days_status"].eq(STATUS_COVERED)]

        # .map leaves NaN for every bore absent from the covered set, which is
        # exactly the "null, never 0" rule for uncovered bores.
        bh["DRILLING_DAYS"] = api12.map(
            dict(zip(covered["api12"], covered["drilling_days"]))
        ).astype(float)
        status = api12.map(dict(zip(days["api12"], days["days_status"]))).fillna(
            STATUS_NO_ACTIVITY
        )
        bh["DRILLING_DAYS_STATUS"] = status.mask(
            status.eq(STATUS_COVERED) & bh["DRILLING_DAYS"].eq(0),
            STATUS_NO_DRILLING,
        )
        return bh

    def _join_borehole(self, df: pd.DataFrame) -> pd.DataFrame:
        """Left-join borehole data, compute drilling days and coalesce depth."""
        if self._borehole_df is None:
            return df

        # Drop WAR-side columns that collide with borehole join columns.
        overlap = [c for c in self._BH_JOIN_COLS if c in df.columns]
        if overlap:
            df = df.drop(columns=overlap)

        bh = self._borehole_df.rename(
            columns={"WATER_DEPTH": "BH_WATER_DEPTH"},
        )
        bh["WELL_SPUD_DATE"] = pd.to_datetime(bh["WELL_SPUD_DATE"])
        bh["TOTAL_DEPTH_DATE"] = pd.to_datetime(bh["TOTAL_DEPTH_DATE"])

        # Drilling days come from the shared WAR rig-days module, never from
        # the spud/TD calendar span.  The old ".where(raw_days >= 0)" negative
        # clamp is not carried over because it is unreachable under this
        # basis: union_days drops intervals with end < start and returns
        # (end - start).days + 1, so the result is >= 0 by construction.
        # test_drilling_days_are_never_negative pins that.
        bh = self._rig_days_for_bores(bh)

        # Normalize API well numbers on both sides for robust join.
        df["_api_norm"] = normalize_api_well_number(df["API_WELL_NUMBER"])
        bh["_api_norm"] = normalize_api_well_number(bh["API_WELL_NUMBER"])

        bh_cols = [
            "_api_norm",
            "WELL_SPUD_DATE",
            "TOTAL_DEPTH_DATE",
            "BH_TOTAL_MD",
            "BH_WATER_DEPTH",
            "BOREHOLE_STAT_CD",
            "WELL_NAME_SUFFIX",
            "DRILLING_DAYS",
            "DRILLING_DAYS_STATUS",
            "DRILLING_DAYS_BASIS",
        ]
        bh_cols = [c for c in bh_cols if c in bh.columns]
        df = df.merge(bh[bh_cols], on="_api_norm", how="left")
        df.drop(columns=["_api_norm"], inplace=True)

        # Derived columns.
        df["WATER_DEPTH_FINAL"] = df["WATER_DEPTH"].fillna(df["BH_WATER_DEPTH"])
        # bh_cols is filtered to what the borehole frame actually carries, so
        # this optional column may legitimately be absent.
        if "BOREHOLE_STAT_CD" in df.columns:
            df["WELL_STATUS"] = df["BOREHOLE_STAT_CD"]

        return df

    # -- Step 3: Water depth classification ----------------------------------

    def _classify_depth(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add WATER_DEPTH_CLASS based on WATER_DEPTH_FINAL or WATER_DEPTH."""
        depth_col = (
            "WATER_DEPTH_FINAL" if "WATER_DEPTH_FINAL" in df.columns else "WATER_DEPTH"
        )
        df["WATER_DEPTH_CLASS"] = df[depth_col].map(_classify_water_depth)
        return df

    # -- Step 4: Paleowells era mapping --------------------------------------

    def _map_era(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map geological era from paleowells data (vectorized)."""
        if self._era_map is None:
            return df
        api_norm = normalize_api_well_number(df["API_WELL_NUMBER"])
        df["GEOLOGICAL_ERA"] = api_norm.map(self._era_map)
        return df

    # -- Step 5: Memory optimization -----------------------------------------

    @staticmethod
    def _optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """Cast string columns to category dtype for memory savings."""
        for col in _CATEGORY_COLS:
            if col in df.columns:
                df[col] = df[col].astype("category")
        if "WELL_STATUS" in df.columns:
            df["WELL_STATUS"] = df["WELL_STATUS"].astype("category")
        return df

    # -- Public API ----------------------------------------------------------

    def enrich(self) -> pd.DataFrame:
        """Run the full enrichment pipeline and return enriched DataFrame."""
        df = self._war_df.copy()
        if df.empty:
            return df

        df = self._join_fleet(df)
        df = self._join_borehole(df)
        df = self._classify_depth(df)
        df = self._map_era(df)
        df = self._optimize_dtypes(df)

        self._result = df
        return df

    def get_join_stats(self) -> dict:
        """Return join diagnostics after enrichment has been run."""
        if self._result is None:
            return {
                "total_war_records": 0,
                "fleet_match_rate": 0.0,
                "borehole_match_rate": 0.0,
                "era_match_rate": 0.0,
                "water_depth_fill_rate": 0.0,
                "rig_days_source": self._rig_days_source,
                "rig_days_basis": self._rig_days_basis.describe(),
                "rig_days_fill_rate": 0.0,
            }

        df = self._result
        n = len(df)

        fleet_rate = float(df["_fleet_matched"].sum() / n) if n else 0.0

        bh_rate = 0.0
        if "BH_TOTAL_MD" in df.columns and n:
            bh_rate = float(df["BH_TOTAL_MD"].notna().sum() / n)

        era_rate = 0.0
        if "GEOLOGICAL_ERA" in df.columns and n:
            era_rate = float(df["GEOLOGICAL_ERA"].notna().sum() / n)

        depth_col = (
            "WATER_DEPTH_FINAL" if "WATER_DEPTH_FINAL" in df.columns else "WATER_DEPTH"
        )
        depth_rate = float(df[depth_col].notna().sum() / n) if n else 0.0

        rig_days_rate = 0.0
        if "DRILLING_DAYS" in df.columns and n:
            rig_days_rate = float(df["DRILLING_DAYS"].notna().sum() / n)

        return {
            "total_war_records": n,
            "fleet_match_rate": fleet_rate,
            "borehole_match_rate": bh_rate,
            "era_match_rate": era_rate,
            "water_depth_fill_rate": depth_rate,
            # Where DRILLING_DAYS came from, so an all-null column is
            # diagnosable instead of looking like "no wells matched".
            "rig_days_source": self._rig_days_source,
            "rig_days_basis": self._rig_days_basis.describe(),
            "rig_days_fill_rate": rig_days_rate,
        }
