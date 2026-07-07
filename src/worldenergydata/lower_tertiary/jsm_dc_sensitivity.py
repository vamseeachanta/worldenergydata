"""Rule-sensitivity helpers for the Jack St Malo D&C diagnostic."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd


def annotate_rule_sensitivity(sensitivity: pd.DataFrame) -> pd.DataFrame:
    out = sensitivity.copy()
    verdicts: dict[str, tuple[bool, str]] = {}
    for rule, grp in out.groupby("rule"):
        anchor = grp[grp["development"] == "Anchor"].iloc[0]
        buckskin = grp[grp["development"] == "Buckskin"].iloc[0]
        reasons = []
        if (
            int(anchor["drilling_days"]) != 821
            or int(anchor["completion_days"]) != 1004
        ):
            reasons.append(
                f"Anchor moved from 821/1004 to "
                f"{int(anchor['drilling_days'])}/{int(anchor['completion_days'])}"
            )
        if int(buckskin["d_and_c_days"]) != 2056:
            reasons.append(
                f"Buckskin moved from 2056 to {int(buckskin['d_and_c_days'])}"
            )
        verdicts[rule] = (not reasons, "; ".join(reasons) or "qualified")
    out["qualified_rule"] = out["rule"].map(lambda r: verdicts[r][0])
    out["disqualifier"] = out["rule"].map(lambda r: verdicts[r][1])
    return out


def rule_sensitivity(
    candidate: pd.DataFrame,
    *,
    extractor,
    leases: Path,
    war_main: Path,
    war_boreholes: Path,
    war_remarks: Path,
    norm_lease: Callable[[object], str],
    norm_api: Callable[[object], str],
) -> pd.DataFrame:
    base = _candidate_base(candidate, leases, norm_lease, norm_api)
    remarks = _remarks_frame(extractor, war_main, war_boreholes, war_remarks, norm_api)
    rules = [("current", None, False)] + [
        (f"gap_cap_{d}d", d, False) for d in [30, 60, 90, 180]
    ]
    rules.append(("keyword_only", None, True))
    out: list[dict] = []
    for rule, cap, keywords in rules:
        frame = base.copy()
        if rule != "current":
            comp_df = _completion_frame(
                frame, remarks, cap, keywords, extractor.is_completion_text
            )
            frame = frame.drop(columns=["COMPLETION_DAYS"]).merge(
                comp_df, on="API_WELL_NUMBER"
            )
        _add_development_totals(out, rule, frame)
    return annotate_rule_sensitivity(pd.DataFrame(out))


def _candidate_base(
    candidate: pd.DataFrame,
    leases: Path,
    norm_lease: Callable[[object], str],
    norm_api: Callable[[object], str],
) -> pd.DataFrame:
    lease_rows = pd.read_csv(leases)
    dev = lease_rows.assign(SURF_LEASE_NUM=lease_rows["LEASE_NUM"].map(norm_lease))[
        ["SURF_LEASE_NUM", "DEV_NAME"]
    ]
    base = candidate.copy()
    base["SURF_LEASE_NUM"] = base["SURF_LEASE_NUM"].map(norm_lease)
    base["API_WELL_NUMBER"] = base["API_WELL_NUMBER"].map(norm_api)
    return base.merge(dev, on="SURF_LEASE_NUM", how="left")


def _remarks_frame(
    extractor,
    war_main: Path,
    war_boreholes: Path,
    war_remarks: Path,
    norm_api: Callable[[object], str],
) -> pd.DataFrame:
    wm = extractor.load_war_main(war_main)
    bh = extractor.load_boreholes(war_boreholes)
    rk = extractor.load_remarks(war_remarks)
    sn = wm[["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT"]].dropna(
        subset=["SN_WAR"]
    )
    remarks = rk.merge(sn, on="SN_WAR", how="inner").merge(
        bh, on="API_WELL_NUMBER", how="left"
    )
    remarks["API_WELL_NUMBER"] = remarks["API_WELL_NUMBER"].map(norm_api)
    return remarks


def _completion_frame(
    frame: pd.DataFrame,
    remarks: pd.DataFrame,
    cap: int | None,
    keywords: bool,
    is_completion_text,
) -> pd.DataFrame:
    comps = []
    for api, grp in frame.groupby("API_WELL_NUMBER"):
        rows = remarks[remarks["API_WELL_NUMBER"] == api]
        td = grp["TOTAL_DEPTH_DATE"].iloc[0]
        days = _interval_days(
            rows, td, cap=cap, keywords=keywords, is_completion_text=is_completion_text
        )
        comps.append((api, days))
    return pd.DataFrame(comps, columns=["API_WELL_NUMBER", "COMPLETION_DAYS"])


def _interval_days(
    rows: pd.DataFrame,
    td,
    *,
    cap: int | None = None,
    keywords: bool = False,
    is_completion_text=None,
) -> int:
    if rows.empty or pd.isna(td):
        return 0
    dates = []
    ordered = rows.sort_values(["WAR_START_DT", "WAR_END_DT"])
    last_end = pd.NaT
    td_day = pd.to_datetime(td).normalize()
    for _, row in ordered.iterrows():
        if keywords and not is_completion_text(row.get("TEXT_REMARK", "")):
            continue
        start = pd.to_datetime(row["WAR_START_DT"], errors="coerce")
        end = pd.to_datetime(row["WAR_END_DT"], errors="coerce")
        if pd.isna(start) and pd.isna(end):
            continue
        if pd.isna(start):
            start = end
        if pd.isna(end):
            end = start
        if end.normalize() < td_day:
            continue
        if cap is not None and pd.notna(last_end) and (start - last_end).days > cap:
            break
        last_end = end
        dates.append(pd.date_range(start.normalize(), end.normalize(), freq="D"))
    if not dates:
        return 0
    all_days = pd.DatetimeIndex(
        pd.unique(pd.Index(pd.concat([pd.Series(d) for d in dates])))
    )
    return int(len(all_days[all_days >= td_day]))


def _add_development_totals(out: list[dict], rule: str, frame: pd.DataFrame) -> None:
    grp = frame.groupby("DEV_NAME", dropna=False)[
        ["DRILLING_DAYS", "COMPLETION_DAYS"]
    ].sum()
    for development, row in grp.iterrows():
        drill = int(row["DRILLING_DAYS"])
        compl = int(row["COMPLETION_DAYS"])
        out.append(
            {
                "rule": rule,
                "development": development,
                "drilling_days": drill,
                "completion_days": compl,
                "d_and_c_days": drill + compl,
            }
        )
