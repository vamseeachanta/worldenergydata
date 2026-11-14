"""Per-well life cycle of Gulf of Mexico wells from the same BSEE archives.

One well is one API10. Its life runs from the first non-cancelled spud of any
of its bores to its permanent abandonment (the date the stock rule in
count_interventions.well_inventory removes it), or to the snapshot file date
while it still stands. Drilling events are bores: the original hole and each
sidetrack or bypass with a spud date. Interventions, temporary and permanent
abandonments are approved permits to modify, classified exactly as in
count_interventions.classified_permits, counted over the years of the
published permit tables (first full year through the snapshot file date).

Interventions are split light or heavy by the unit type the permit names
(RIG_TYPE_CODE through RIG_ID_NUM, the lookup the branch already uses):
light units work through the existing tubing without a rig; heavy units are a
rig or workover unit that can pull tubing. Only small aggregates are written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import count_interventions as ci
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DAYS_PER_YEAR = 365.25

# Light: no drilling or workover rig; wireline or coiled tubing through the
# tubing, from a platform, liftboat or vessel. NR is the regulator's recorded
# non-rig operation. LB (liftboat) and JU (jack-up rig) share the branch's
# "liftboat / jack-up" unit category; the split follows the two source codes.
LIGHT_CODES = {"WL", "CT", "WI", "LB", "NR"}
# Heavy: a rig or workover unit that can pull tubing.
HEAVY_CODES = {"HW", "SB", "PF", "JU", "DS", "SS", "SD"}
WEIGHTS = ["light", "heavy", "not established"]

# Stages in the order of a well's life.
STAGES = [
    "drilling",
    "sidetrack or bypass",
    "light intervention",
    "heavy intervention",
    "intervention, light or heavy not established",
    "temporary abandonment",
    "abandonment, type not stated",
    "permanent abandonment",
]
PERMIT_STAGES = STAGES[2:]
WELL_TYPES = {"D": "development", "E": "exploration"}
TYPE_ORDER = ["development", "exploration", "other or not stated"]
LIFE_BINS = list(range(0, 85, 5))
# The borehole columns count_interventions.run reads for region, depth and stock.
BORE_COLUMNS = [
    "API_WELL_NUMBER",
    "REGION_CODE",
    "WATER_DEPTH",
    "WELL_NAME_SUFFIX",
    "WELL_SPUD_DATE",
    "BOREHOLE_STAT_CD",
    "BOREHOLE_STAT_DT",
]


def intervention_weight(rig_type_code):
    """Light, heavy or not established, from the permit's unit type code."""
    if rig_type_code in LIGHT_CODES:
        return "light"
    if rig_type_code in HEAVY_CODES:
        return "heavy"
    return "not established"


def permit_stage(family, group, rig_type_code):
    """Life-cycle stage of one classified permit; None if excluded."""
    if family == "well work":
        weight = intervention_weight(rig_type_code)
        return (
            "intervention, light or heavy not established"
            if weight == "not established"
            else f"{weight} intervention"
        )
    if family == "abandonment":
        return {
            "temporary abandonment": "temporary abandonment",
            "permanent abandonment": "permanent abandonment",
            "abandonment unspecified": "abandonment, type not stated",
        }[group]
    return None


def gulf_bores(bore):
    """Non-cancelled Gulf bores with API10, spud date and kind."""
    b = bore[bore.REGION_CODE.eq("G") & bore.BOREHOLE_STAT_CD.ne("CNL")].copy()
    b["api12"] = ci.normalize_api(b.API_WELL_NUMBER)
    b["api10"] = b.api12.str[:10]
    b = b[b.api10.ne("")].sort_values("api12", kind="stable")
    b = b.drop_duplicates("api12")
    b["spud"] = ci.dates(b.WELL_SPUD_DATE)
    b["stage"] = np.where(
        b.WELL_NAME_SUFFIX.eq("ST00BP00"), "drilling", "sidetrack or bypass"
    )
    return b


def well_types(bore):
    """Development or exploration from the canonical original hole's type code.

    The original hole (ST00BP00) is chosen as in the inventory depth rule:
    API12 ending 00 first, then the earliest spud, then the API12.
    """
    b = gulf_bores(bore)
    o = b[b.stage.eq("drilling")].copy()
    o["not_suffix00"] = ~o.api12.str.endswith("00")
    o = o.sort_values(["not_suffix00", "spud", "api12"], kind="stable")
    o = o.drop_duplicates("api10")
    return o.set_index("api10").WELL_TYPE_CODE.map(WELL_TYPES)


def permit_events(apm, rigs, window):
    """One row per included permit in the window, with api10, date and stage."""
    lookup = rigs[["RIG_ID_NUM", "RIG_TYPE_CODE"]].drop_duplicates()
    if lookup.RIG_ID_NUM.duplicated().any():
        raise ValueError("conflicting rig lookup keys")
    a = apm[apm.year.isin(window)].merge(
        lookup, on="RIG_ID_NUM", how="left", validate="many_to_one"
    )
    a["RIG_TYPE_CODE"] = a.RIG_TYPE_CODE.fillna("")
    a["stage"] = [
        permit_stage(r.family, r.group, r.RIG_TYPE_CODE) for r in a.itertuples()
    ]
    a = a[a.stage.notna()].copy()
    a["api10"] = a.API_WELL_NUMBER.str[:10]
    a["date"] = ci.dates(a.ACC_STATUS_DATE)
    return a[["SN_APM", "api10", "year", "band", "group", "family", "stage", "date"]]


def well_table(inventory, bores, events, types, file_date):
    """One row per dated well: life, status, type and counts by stage."""
    w = inventory[inventory.spud.notna()].copy()
    end = w.abandoned.fillna(pd.Timestamp(file_date))
    w["status"] = np.where(w.abandoned.notna(), "permanently abandoned", "standing")
    w["life_years"] = (end - w.spud).dt.days / DAYS_PER_YEAR
    w["life_not_established"] = w.life_years.lt(0)
    w.loc[w.life_not_established, "life_years"] = np.nan
    w["spud_year"] = w.spud.dt.year.astype(int)
    w["well_type"] = w.api10.map(types).fillna("other or not stated")
    counts = pd.concat(
        [
            bores[bores.spud.notna()][["api10", "stage"]],
            events[["api10", "stage"]],
        ]
    )
    table = (
        counts.groupby(["api10", "stage"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=STAGES, fill_value=0)
    )
    w = w.merge(table, left_on="api10", right_index=True, how="left")
    w[STAGES] = w[STAGES].fillna(0).astype(int)
    return w.reset_index(drop=True)


def event_ages(bores, events, wells):
    """Age of the well, in years after first spud, at each dated event."""
    spud = wells.set_index("api10").spud
    rows = pd.concat(
        [
            bores[bores.spud.notna() & bores.stage.eq("sidetrack or bypass")].rename(
                columns={"spud": "date"}
            )[["api10", "stage", "date"]],
            events[["api10", "stage", "date"]],
        ]
    )
    rows = rows[rows.api10.isin(spud.index)].copy()
    rows["age_years"] = (rows.date - rows.api10.map(spud)).dt.days / DAYS_PER_YEAR
    rows["well_type"] = rows.api10.map(wells.set_index("api10").well_type)
    return rows


def age_summary(ages):
    """Quartiles of well age at each event, by well type and in total."""
    out = []
    for well_type in ["all wells"] + TYPE_ORDER:
        part = ages if well_type == "all wells" else ages[ages.well_type.eq(well_type)]
        for stage in STAGES[1:]:
            g = part[part.stage.eq(stage)].age_years
            valid = g[g.ge(0)]
            q = valid.quantile([0.25, 0.5, 0.75]) if len(valid) else None
            out.append(
                dict(
                    well_type=well_type,
                    stage=stage,
                    events=len(g),
                    before_first_spud=int(g.lt(0).sum()),
                    q25_years=q.loc[0.25] if q is not None else np.nan,
                    median_years=q.loc[0.5] if q is not None else np.nan,
                    q75_years=q.loc[0.75] if q is not None else np.nan,
                )
            )
    return pd.DataFrame(out)


def cohorts(wells, first_year, last_year):
    """Wells whose whole life lies inside the published permit years.

    A well first drilled in or after the first full permit year has every
    approval of its life in the window; older wells do not, so they are not
    used for per-well counts.
    """
    drilled = wells.spud_year.between(first_year, last_year)
    return {
        f"{kind} wells first drilled {first_year}-{last_year}": drilled
        & wells.well_type.eq(kind)
        for kind in TYPE_ORDER[:2]
    }


def stage_reach(wells, groups):
    """Share of wells with at least one event of each stage, per group."""
    rows = []
    for name, mask in groups.items():
        g = wells[mask]
        n = len(g)
        for stage in STAGES:
            reached = int(g[stage].gt(0).sum())
            rows.append(
                dict(
                    group=name,
                    wells=n,
                    stage=stage,
                    wells_reaching=reached,
                    share_percent=reached / n * 100 if n else np.nan,
                    events=int(g[stage].sum()),
                    events_per_well=g[stage].sum() / n if n else np.nan,
                )
            )
        reached = int(g.status.eq("permanently abandoned").sum())
        rows.append(
            dict(
                group=name,
                wells=n,
                stage="permanently abandoned (bore status)",
                wells_reaching=reached,
                share_percent=reached / n * 100 if n else np.nan,
                events=reached,
                events_per_well=reached / n if n else np.nan,
            )
        )
    return pd.DataFrame(rows)


def life_summary(wells, groups):
    """Life in years by group and status: count and quartiles."""
    rows = []
    named = {"all dated wells": pd.Series(True, index=wells.index)}
    named.update({f"{t} wells": wells.well_type.eq(t) for t in TYPE_ORDER[:2]})
    named.update(groups)
    for name, mask in named.items():
        for status in ["permanently abandoned", "standing"]:
            g = wells[mask & wells.status.eq(status)].life_years
            valid = g.dropna()
            q = valid.quantile([0.25, 0.5, 0.75]) if len(valid) else None
            rows.append(
                dict(
                    group=name,
                    status=status,
                    wells=len(g),
                    life_not_established=int(g.isna().sum()),
                    q25_years=q.loc[0.25] if q is not None else np.nan,
                    median_years=q.loc[0.5] if q is not None else np.nan,
                    q75_years=q.loc[0.75] if q is not None else np.nan,
                    under_1_year=int(valid.lt(1).sum()),
                )
            )
    return pd.DataFrame(rows)


def life_histogram(wells):
    """Wells by 5-year life bin, well type and status."""
    w = wells[wells.life_years.notna()]
    bins = pd.cut(
        w.life_years,
        LIFE_BINS + [np.inf],
        right=False,
        labels=[f"{a}" for a in LIFE_BINS],
    )
    table = (
        w.assign(bin_start_years=bins)
        .groupby(["well_type", "status", "bin_start_years"], observed=False)
        .size()
        .rename("wells")
        .reset_index()
    )
    table["bin_start_years"] = table.bin_start_years.astype(int)
    return table


def reconcile(wells, events, counts, window):
    """Per-well permit counts plus unmatched permits equal the published counts.

    Returns one row per stage with the published total (counts_by_year_band
    _group.csv over the window), the count assigned to dated wells and the
    count not assigned (no API10 match to a dated well).
    """
    groups = {
        "temporary abandonment": ["temporary abandonment"],
        "permanent abandonment": ["permanent abandonment"],
        "abandonment, type not stated": ["abandonment unspecified"],
        "intervention, all": [
            "workover and recompletion",
            "production enhancement",
            "other well work",
        ],
    }
    c = counts[counts.year.isin(window)]
    interventions = PERMIT_STAGES[:3]
    rows = []
    for stage, source in groups.items():
        stages = interventions if stage == "intervention, all" else [stage]
        published = int(c.loc[c.group.isin(source), "permits"].sum())
        assigned = int(wells[stages].to_numpy().sum())
        found = int(events.stage.isin(stages).sum())
        rows.append(
            dict(
                stage=stage,
                published_permits=published,
                permits_in_events=found,
                assigned_to_dated_wells=assigned,
                not_assigned=found - assigned,
            )
        )
    table = pd.DataFrame(rows)
    if not table.published_permits.eq(table.permits_in_events).all():
        raise ValueError("life-cycle permits do not reconcile with published counts")
    return table


def weight_by_year(events, standing, window):
    """Intervention approvals by year and light/heavy, per 100 standing wells."""
    e = events[events.stage.isin(PERMIT_STAGES[:3])].copy()
    e["weight"] = e.stage.map(
        {
            "light intervention": "light",
            "heavy intervention": "heavy",
            "intervention, light or heavy not established": "not established",
        }
    )
    table = (
        e.groupby(["year", "weight"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=window, columns=WEIGHTS, fill_value=0)
    )
    stock = standing.groupby("year").standing_wells.sum().reindex(window)
    rows = []
    for year in window:
        for weight in WEIGHTS:
            n = int(table.loc[year, weight])
            rows.append(
                dict(
                    year=year,
                    weight=weight,
                    approvals=n,
                    standing_wells=int(stock.loc[year]),
                    per_100_standing_wells=n / stock.loc[year] * 100,
                )
            )
    return pd.DataFrame(rows)


def write_csv(frame, out, name):
    frame.to_csv(
        out / (name + ".csv"), index=False, float_format="%.6f", lineterminator="\n"
    )


def run(data_dir, out):
    data_dir, out = Path(data_dir), Path(out)
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    saved = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if manifest != saved:
        raise ValueError("raw-data manifest differs from the published output set")
    file_date = pd.Timestamp(summary["file_date"])
    first, last = int(summary["first_full_year"]), int(summary["last_full_year"])
    window = list(range(first, int(summary["partial_year"]) + 1))
    bore = ci.read_table(
        data_dir, "BoreholeRawData.zip", "mv_boreholes_all", BORE_COLUMNS
    )
    _, apm, _, _ = ci.classified_permits(data_dir, bore)
    rigs = ci.read_table(data_dir, "eWellAPMRawData.zip", "mv_apm_rig_view")
    events = permit_events(apm, rigs, window)
    typed = ci.read_table(
        data_dir,
        "BoreholeRawData.zip",
        "mv_boreholes_all",
        [
            "API_WELL_NUMBER",
            "REGION_CODE",
            "WELL_NAME_SUFFIX",
            "WELL_SPUD_DATE",
            "BOREHOLE_STAT_CD",
            "WELL_TYPE_CODE",
        ],
    )
    bores = gulf_bores(typed)
    inventory = ci.well_inventory(bore)
    wells = well_table(inventory, bores, events, well_types(typed), file_date)
    counts = pd.read_csv(out / "counts_by_year_band_group.csv")
    checks = reconcile(wells, events, counts, window)
    groups = cohorts(wells, first, last)
    standing = pd.read_csv(out / "standing_wells.csv")
    write_csv(checks, out, "life_cycle_reconciliation")
    write_csv(life_summary(wells, groups), out, "life_cycle_life_years")
    write_csv(life_histogram(wells), out, "life_cycle_life_histogram")
    write_csv(stage_reach(wells, groups), out, "life_cycle_stage_reach")
    write_csv(
        age_summary(event_ages(bores, events, wells)), out, "life_cycle_event_ages"
    )
    write_csv(
        weight_by_year(events, standing, window), out, "intervention_weight_by_year"
    )
    rules = [
        dict(raw_value=k, unit_category=ci.UNIT_TYPES[k], weight=intervention_weight(k))
        for k in ci.UNIT_TYPES
    ] + [
        dict(
            raw_value="blank or unmatched",
            unit_category="none named / other",
            weight="not established",
        )
    ]
    write_csv(pd.DataFrame(rules), out, "intervention_weight_mapping")
    record = dict(
        snapshot=summary["snapshot"],
        file_date=summary["file_date"],
        window=f"{window[0]}-{window[-1]}",
        dated_wells=len(wells),
        wells_without_first_spud=int(inventory.spud.isna().sum()),
        life_not_established=int(wells.life_not_established.sum()),
        permanently_abandoned=int(wells.status.eq("permanently abandoned").sum()),
        standing=int(wells.status.eq("standing").sum()),
        bores_with_spud=int(bores.spud.notna().sum()),
        bores_without_spud=int(bores.spud.isna().sum()),
        bores_not_in_dated_wells=int(
            (~bores[bores.spud.notna()].api10.isin(wells.api10)).sum()
        ),
        group_sizes={k: int(v.sum()) for k, v in groups.items()},
    )
    (out / "life_cycle_summary.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    print(json.dumps(run(args.data_dir, args.out), indent=2))
