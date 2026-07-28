"""Per-wellbore rig analysis for the API12 well pipeline.

Drilling and completion days are **not** derived here.  They come from
:mod:`worldenergydata.bsee.analysis.war_rig_days`, the single implementation
of the WAR activity-code basis (see #1063/#1075).  What remains in this
module is the part that is genuinely local to the API12 pipeline: attributing
WAR weeks to rig names, and shaping the result for ``well_api12``.

Two behaviours changed when this module was converged onto ``war_rig_days``
and both are deliberate:

Absent coverage is null, never zero
    A wellbore with no WAR activity used to report ``0`` drilling days, which
    is indistinguishable from a well that really did spend no time drilling.
    It now reports ``None`` alongside ``days_status == "no_war_activity"``.

The spud -> total-depth calendar span is no longer "drilling days"
    It measured elapsed time, so a suspended or batch-drilled well counted
    every day the rig was somewhere else.  The span is still emitted, but
    under the explicitly-labelled ``spud_to_td_calendar_days`` key, and it
    never feeds ``drilling_days``.
"""

from __future__ import annotations

import pandas as pd
from dateutil.parser import parse
from loguru import logger

from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM,
    STATUS_COVERED,
    STATUS_NO_ACTIVITY,
    Basis,
    rig_days_by_bore,
)


def _calendar_span_days(start, end):
    """Inclusive calendar days between two milestones, or ``None``.

    Explicitly *not* rig time -- it is reported under its own key so a
    consumer that wants elapsed time has to ask for it by name.
    """
    if start is None or end is None:
        return None
    try:
        return int((end - start).days) + 1
    except TypeError:  # pragma: no cover - defensive against odd date types
        return None


class WellRigDays:
    """Rig attribution and rig-days for a single API12 wellbore."""

    def __init__(self):
        pass

    def rig_analysis(
        self,
        cfg,
        api12_df,
        api12_eWellWARRawData_mv_war_main,
        api12_eWellWARRawData_mv_war_main_prop,
        basis: Basis = BASIS_DRL_COM,
    ):

        war_data = pd.merge(
            api12_eWellWARRawData_mv_war_main,
            api12_eWellWARRawData_mv_war_main_prop,
            how="left",
            left_on=["SN_WAR"],
            right_on=["SN_WAR"],
        )

        spud_date = None
        if not api12_df["WELL_SPUD_DATE"].empty and pd.notna(
            api12_df["WELL_SPUD_DATE"].iloc[0]
        ):
            spud_value = str(api12_df["WELL_SPUD_DATE"].iloc[0]).strip()
            if spud_value and spud_value != "nan":
                spud_date = parse(spud_value)

        td_date = None
        if not api12_df["TOTAL_DEPTH_DATE"].empty and pd.notna(
            api12_df["TOTAL_DEPTH_DATE"].iloc[0]
        ):
            td_value = str(api12_df["TOTAL_DEPTH_DATE"].iloc[0]).strip()
            if td_value and td_value != "nan":
                td_date = parse(td_value)

        war_data["WAR_START_DT"] = [
            (
                parse(str(item))
                if item is not None and pd.notna(item) and str(item).strip() != ""
                else None
            )
            for item in war_data["WAR_START_DT"]
        ]
        war_data["WAR_END_DT"] = [
            (
                parse(str(item))
                if item is not None and pd.notna(item) and str(item).strip() != ""
                else None
            )
            for item in war_data["WAR_END_DT"]
        ]
        war_data.sort_values(by=["WAR_START_DT"], inplace=True)

        war_summary = self.get_war_days(cfg, war_data, td_date)
        bore = self.war_activity_days(war_data, basis=basis)

        rig_str = None
        api12_war_days = None
        rig_days_from_milestone = self.rig_days_from_milestone(
            cfg, spud_date, td_date, war_data, basis=basis, bore=bore
        )
        try:
            rig_str, api12_war_days = self.get_rig_info_and_rig_days_from_war(
                cfg, spud_date, td_date, war_summary, bore=bore
            )
        except Exception as e:
            logger.error(e)

        rig_analysis_dict = {
            "rig_str": rig_str,
            "api12_war_days": api12_war_days,
            "rig_days_from_milestone": rig_days_from_milestone,
        }

        return rig_analysis_dict

    def war_activity_days(self, war_data, basis: Basis = BASIS_DRL_COM):
        """The shared module's row for this wellbore, or ``None``.

        ``None`` means "WAR says nothing about this bore" -- it is the signal
        that days must be reported as null rather than zero.  A frame that
        somehow spans several API12s is collapsed additively at bore grain
        and flagged, because this pipeline is documented as per-wellbore.
        """
        if war_data is None:
            return None
        try:
            bores = rig_days_by_bore(war_data, basis=basis)
        except (ValueError, KeyError) as exc:
            logger.warning(f"WAR frame unusable for rig-days: {exc}")
            return None

        covered = bores[bores["days_status"].eq(STATUS_COVERED)]
        if covered.empty:
            return None
        if len(covered) > 1:
            logger.warning(
                "WAR frame spans "
                f"{len(covered)} wellbores ({', '.join(covered['api12'])}); "
                "rig-days summed additively at bore grain. Use "
                "war_rig_days.rig_days_by_well for an API10 roll-up."
            )
        return covered

    def rig_days_from_milestone(
        self,
        cfg,
        spud_date,
        td_date,
        war_data,
        basis: Basis = BASIS_DRL_COM,
        bore=None,
    ):
        """Drilling, completion and total rig-days for this wellbore.

        Sourced from :mod:`war_rig_days` on the WAR activity-code basis.  The
        historical keys ``drilling_days``, ``completion_days`` and
        ``rig_days`` are preserved; ``days_status``, ``basis``,
        ``war_days_total`` and ``spud_to_td_calendar_days`` are added so a
        consumer can tell what it is looking at.

        ``drilling_days`` and ``completion_days`` are ``None`` -- not ``0`` --
        when WAR reports no activity for the bore.
        """
        result = {
            "drilling_days": None,
            "completion_days": None,
            "rig_days": None,
            "war_days_total": None,
            "days_status": STATUS_NO_ACTIVITY,
            "basis": basis.describe(),
            "spud_to_td_calendar_days": _calendar_span_days(spud_date, td_date),
        }

        if bore is None:
            bore = self.war_activity_days(war_data, basis=basis)
        if bore is None or len(bore) == 0:
            return result

        drilling_days = int(bore["drilling_days"].sum())
        completion_days = int(bore["completion_days"].sum())
        result.update(
            {
                "drilling_days": drilling_days,
                "completion_days": completion_days,
                "rig_days": drilling_days + completion_days,
                "war_days_total": int(bore["war_days_total"].sum()),
                "days_status": STATUS_COVERED,
            }
        )
        return result

    def get_rig_info_and_rig_days_from_war(
        self, cfg, spud_date, td_date, war_summary, bore=None
    ):
        """Rig-name string plus days per activity code.

        Rig attribution is local to this module (``war_rig_days`` has no
        notion of ``RIG_NAME``); the day totals are not -- they come straight
        from the shared module's ``days_by_code``.

        Returns ``(rig_str, None)`` when WAR reports no activity, so the
        caller writes null rather than a fabricated zero.
        """
        try:
            rigs = list(war_summary.RIG_NAME.unique())

            rigs_for_string = [
                str(rig) if rig is not None and not pd.isna(rig) else "unknown rig"
                for rig in rigs
            ]
            rig_str = ", ".join(rigs_for_string)

        except Exception as e:
            logger.error(e)
            rig_str = {}

        if bore is None or len(bore) == 0:
            return rig_str, None

        api12_war_days_dict = {}
        for by_code in bore["days_by_code"]:
            for code, days in by_code.items():
                api12_war_days_dict[code] = api12_war_days_dict.get(code, 0) + int(days)
        api12_war_days_dict["total_rig_days"] = int(bore["war_days_total"].sum())

        return rig_str, api12_war_days_dict

    def get_war_days(self, cfg, war_data, td_date):
        """Per-WAR-row rig days, gaps and NPT, used for rig attribution.

        Note this is *not* the source of published drilling/completion days
        -- those come from ``war_rig_days`` via :meth:`war_activity_days`.
        """

        max_allowed_npt = cfg["parameters"]["max_allowed_npt"]
        columns = ["rig_days", "war_gap_days", "npt", "war_drilling_days_flag"]
        war_summary = pd.DataFrame(columns=columns, index=range(0, len(war_data)))
        war_summary["RIG_NAME"] = war_data["RIG_NAME"]
        war_summary["WELL_ACTIVITY_CD"] = war_data["WELL_ACTIVITY_CD"]

        for df_row in range(0, len(war_data)):
            war_drilling_days_flag = False
            rig_days = 0
            war_gap_days = 0
            npt = 0

            war_days = (
                war_data["WAR_END_DT"].iloc[df_row]
                - war_data["WAR_START_DT"].iloc[df_row]
            ).days

            rig_days = war_days + 1 if war_days > 0 else war_days

            if df_row > 0:
                gap_start_date = war_data["WAR_START_DT"].iloc[df_row]
                gap_end_date = war_data["WAR_END_DT"].iloc[df_row - 1]
                war_gap_days = (gap_start_date - gap_end_date).days - 1
                if war_gap_days > max_allowed_npt:
                    war_gap_days = 0
                elif td_date is not None and td_date > gap_start_date:
                    war_drilling_days_flag = True
                else:
                    war_drilling_days_flag = None

                if td_date is not None:
                    if (gap_end_date <= td_date) and (gap_start_date > td_date):
                        gap_end_date = td_date
                    npt = (gap_start_date - gap_end_date).days - 1

                    if (gap_start_date > td_date) and (npt <= max_allowed_npt):
                        if npt <= 0:
                            npt = 0

            values = [rig_days, war_gap_days, npt, war_drilling_days_flag]
            war_summary.loc[df_row, columns] = values

        return war_summary
