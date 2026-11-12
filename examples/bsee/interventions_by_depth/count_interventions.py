"""Count BSEE approved APM submissions; retain unknowns and audit exclusions.

Read zipped CSV members directly, without extracting raw files. All aggregations
are deterministic. The retained manifest is required and verified before use.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import zipfile
from pathlib import Path

import pandas as pd

# Load the existing leaf utility without executing the data package's eager
# imports of unrelated scrapers and assetutilities. This example is repo-local.
_utility = (
    Path(__file__).resolve().parents[3]
    / "packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py"
)
_spec = importlib.util.spec_from_file_location("interventions_api_normalizer", _utility)
_normalizer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_normalizer)
normalize_api_well_number = _normalizer.normalize_api_well_number

BANDS = [
    "under 100 m",
    "100 to 500 m",
    "500 to 1500 m",
    "1500 m and deeper",
    "no depth",
]
GROUPS = [
    "workover and recompletion",
    "production enhancement",
    "temporary abandonment",
    "permanent abandonment",
    "other well work",
    "abandonment unspecified",
    "new hole excluded",
    "initial completion excluded",
]
WELL_WORK = {GROUPS[0], GROUPS[1], GROUPS[4]}
ABANDONMENT = {GROUPS[2], GROUPS[3], GROUPS[5]}


def normalize_api(series):
    result = normalize_api_well_number(series).fillna("")
    return result.where(result.str.fullmatch(r"\d{10}(?:\d{2})?"), "")


def band_from_feet(value):
    try:
        depth = float(value) * 0.3048
    except (TypeError, ValueError):
        return BANDS[-1]
    if not math.isfinite(depth) or depth < 0:
        return BANDS[-1]
    return BANDS[sum(depth >= edge for edge in (100, 500, 1500))]


def dates(series):
    return pd.to_datetime(series, format="mixed", errors="coerce")


def read_table(data_dir, archive, member, columns=None, encoding="cp1252"):
    with zipfile.ZipFile(Path(data_dir) / archive) as z:
        names = [n for n in z.namelist() if Path(n).name == member + ".txt"]
        if len(names) != 1:
            raise ValueError(f"expected one member: {member}")
        return pd.read_csv(
            z.open(names[0]),
            dtype=str,
            encoding=encoding,
            usecols=columns,
            keep_default_na=False,
        ).apply(lambda s: s.str.strip())


def unique_map(frame, key, value):
    usable = frame[(frame[key] != "") & frame[value].notna()]
    groups = usable.groupby(key)[value]
    return groups.first().where(groups.nunique() == 1).dropna()


def attach_depth(events, bore):
    result = events.copy()
    result["API_WELL_NUMBER"] = normalize_api(result.API_WELL_NUMBER)
    b = bore.copy()
    b["API_WELL_NUMBER"] = normalize_api(b.API_WELL_NUMBER)
    b["api10"] = b.API_WELL_NUMBER.str[:10]
    b["depth_ft"] = pd.to_numeric(b.WATER_DEPTH, errors="coerce")
    b["depth_ft"] = b.depth_ft.where(b.depth_ft.ge(0) & b.depth_ft.lt(float("inf")))
    exact = result.API_WELL_NUMBER.map(unique_map(b, "API_WELL_NUMBER", "depth_ft"))
    fallback = result.API_WELL_NUMBER.str[:10].map(unique_map(b, "api10", "depth_ft"))
    result["depth_ft"] = exact.fillna(fallback)
    result["depth_join"] = "missing"
    result.loc[fallback.notna(), "depth_join"] = "api10"
    result.loc[exact.notna(), "depth_join"] = "api12"
    result["band"] = result.depth_ft.map(band_from_feet)
    return result


def gulf_only(frame, bore):
    """Use authoritative borehole region; G lease fallback only if unmatched."""
    result = frame.copy()
    result["API_WELL_NUMBER"] = normalize_api(result.API_WELL_NUMBER)
    b = bore.copy()
    b["API_WELL_NUMBER"] = normalize_api(b.API_WELL_NUMBER)
    b["api10"] = b.API_WELL_NUMBER.str[:10]
    region = result.API_WELL_NUMBER.map(unique_map(b, "API_WELL_NUMBER", "REGION_CODE"))
    region = region.fillna(
        result.API_WELL_NUMBER.str[:10].map(unique_map(b, "api10", "REGION_CODE"))
    )
    lease = next(
        (c for c in ["SURF_LEASE_NUM", "SURF_LEASE_NUMBER"] if c in result), None
    )
    if lease:
        region = region.fillna(
            result[lease].map(lambda x: "G" if x.startswith("G") else pd.NA)
        )
    result["region"] = region.fillna("unknown")
    return result


def dedupe_permits(frame):
    keys = ["SN_APM", "API_WELL_NUMBER", "ACC_STATUS_DATE", "APM_OP_CD"]
    core = frame[keys].drop_duplicates()
    if core.SN_APM.eq("").any() or core.SN_APM.duplicated().any():
        raise ValueError("missing or conflicting APM identity")
    return frame.sort_values(keys, kind="stable").drop_duplicates("SN_APM").copy()


def narrative_new_hole(code, text):
    """Narrow literal screen; future plans and flow-path bypasses are retained.

    OTHER/deepen covers legacy paper deepening approvals entered through APM.
    No current borehole status is used to classify historic permits.
    """
    if code == "OTHER" and re.search(r"\bdeepen(?:ing)?\b", text, re.I):
        return True
    return bool(
        re.search(
            r"\bdrill(?:ing)?\s+(?:a\s+)?(?:new\s+)?(?:sidetrack|bypass)\b"
            r"|\bAPM for (?:Bypass|Sidetrack)\b|\binadvertently sidetrack\b"
            r"|\bAPM.*?in lieu of.*?\bto sidetrack\b",
            text,
            re.I | re.S,
        )
    )


def classify_operation(code, subcodes, narrative=""):
    # Precedence is deliberate: a permanent abandonment may also contain a
    # temporary stage; new-hole preparation is excluded even within ABANDON.
    if (
        code in {"SIDETRACK", "BYPASS", "DEEPEN"}
        or "PLUGBACK" in subcodes
        or narrative_new_hole(code, narrative)
    ):
        return GROUPS[6]
    if code == "ABANDON":
        if "PERMABAN" in subcodes:
            return GROUPS[3]
        if "TEMPABAN" in subcodes:
            return GROUPS[2]
        return GROUPS[5]
    if code == "WORKOVER" or (code == "COMP" and "ZONE" in subcodes):
        return GROUPS[0]
    if code == "ENHANCE":
        return GROUPS[1]
    if code == "COMP":
        return GROUPS[7]
    if code in {"OTHER", "INFORM", "UTIL"}:
        return GROUPS[4]
    raise ValueError(f"unmapped primary operation {code!r}")


def well_inventory(bore):
    """One API10, all non-cancelled bores; current statuses are a history proxy."""
    b = bore[bore.REGION_CODE.eq("G") & bore.BOREHOLE_STAT_CD.ne("CNL")].copy()
    b["api10"] = normalize_api(b.API_WELL_NUMBER).str[:10]
    b = b[b.api10.ne("")].drop_duplicates()
    b["spud"] = dates(b.WELL_SPUD_DATE)
    b["status_date"] = dates(b.BOREHOLE_STAT_DT)
    b["depth_ft"] = pd.to_numeric(b.WATER_DEPTH, errors="coerce")
    b["depth_ft"] = b.depth_ft.where(b.depth_ft.ge(0) & b.depth_ft.lt(float("inf")))
    depths = unique_map(b, "api10", "depth_ft")
    # The inventory is a stock of wells, so use a stable surface/original-hole
    # depth where supplied. Bore depths can differ within an API10. Preserve
    # the previous canonical-original tie break; status/spud still use ALL bores.
    originals = b[b.WELL_NAME_SUFFIX.eq("ST00BP00")].copy()
    originals["not_suffix00"] = ~originals.API_WELL_NUMBER.str.endswith("00")
    originals = originals.sort_values(
        ["not_suffix00", "spud", "API_WELL_NUMBER"], kind="stable"
    ).drop_duplicates("api10")
    depths = originals.set_index("api10").depth_ft.combine_first(depths)
    rows = []
    for api, g in b.groupby("api10", sort=True):
        terminal = g[~g.BOREHOLE_STAT_CD.isin(["ST", "BP"])]
        missing_date = terminal.status_date.isna().any()
        all_pa = len(terminal) > 0 and terminal.BOREHOLE_STAT_CD.eq("PA").all()
        rows.append(
            dict(
                api10=api,
                spud=g.spud.min(),
                abandoned=(
                    terminal.status_date.max()
                    if all_pa and not missing_date
                    else pd.NaT
                ),
                assumed_standing=bool(len(terminal) == 0 or missing_date),
                no_non_superseded_bore=bool(len(terminal) == 0),
                missing_terminal_status_date=bool(missing_date),
                band=band_from_feet(depths.get(api)),
            )
        )
    return pd.DataFrame(
        rows,
        columns=[
            "api10",
            "spud",
            "abandoned",
            "assumed_standing",
            "no_non_superseded_bore",
            "missing_terminal_status_date",
            "band",
        ],
    )


def standing_wells(bore, years, as_of=None, at="start"):
    if at not in {"start", "year_end"}:
        raise ValueError("inventory date must be start or year_end")
    b = well_inventory(bore)
    rows = []
    for year in years:
        end = (
            pd.Timestamp(year=year, month=1, day=1)
            if at == "start"
            else pd.Timestamp(year=year, month=12, day=31)
        )
        if as_of is not None:
            end = min(end, pd.Timestamp(as_of).normalize())
        active = b[b.spud.le(end) & ~(b.abandoned.notna() & b.abandoned.le(end))]
        for band in BANDS:
            g = active[active.band.eq(band)]
            rows.append(
                dict(
                    year=year,
                    band=band,
                    stock_date=str(end.date()),
                    standing_wells=len(g),
                    assumed_standing=int(g.assumed_standing.sum()),
                    no_non_superseded_bore=int(g.no_non_superseded_bore.sum()),
                    missing_terminal_status_date=int(
                        g.missing_terminal_status_date.sum()
                    ),
                )
            )
    return pd.DataFrame(rows)


UNIT_TYPES = {
    "WL": "wireline unit",
    "CT": "coiled tubing",
    "HW": "hydraulic workover / snubbing",
    "SB": "hydraulic workover / snubbing",
    "PF": "platform rig",
    "LB": "liftboat / jack-up",
    "JU": "liftboat / jack-up",
    "WI": "intervention vessel",
    "DS": "drillship / semisubmersible",
    "SS": "drillship / semisubmersible",
    "SD": "drillship / semisubmersible",
    "NR": "none named",
    "BG": "other",
    "BR": "other",
    "PL": "other",
    "SU": "other",
}
UNIT_CATEGORIES = list(dict.fromkeys(UNIT_TYPES.values()))


def unit_category(code, name, rig_id):
    """Use supplied type codes; names do not prove deployed equipment."""
    if code in UNIT_TYPES:
        return UNIT_TYPES[code]
    return "none named" if not code and not name and not rig_id else "other"


def access_outputs(apm, data_dir, out, last_full_year):
    rigs = read_table(data_dir, "eWellAPMRawData.zip", "mv_apm_rig_view")
    fields = ["RIG_ID_NUM", "RIG_NAME", "RIG_TYPE_CODE"]
    rigs = rigs[fields].drop_duplicates()
    if rigs.RIG_ID_NUM.duplicated().any():
        raise ValueError("conflicting rig lookup keys")
    rigs["unit_category"] = [
        unit_category(r.RIG_TYPE_CODE, r.RIG_NAME, r.RIG_ID_NUM)
        for r in rigs.itertuples()
    ]
    write_csv(rigs, out, "unit_type_lookup")
    rules = [
        dict(
            source_field="RIG_TYPE_CODE",
            raw_value=k,
            unit_category=v,
            rule="exact type code; joined via RIG_ID_NUM; no name inference",
        )
        for k, v in UNIT_TYPES.items()
    ]
    rules.extend(
        [
            dict(
                source_field="RIG_ID_NUM / RIG_NAME / RIG_TYPE_CODE",
                raw_value="all blank",
                unit_category="none named",
                rule="no unit information",
            ),
            dict(
                source_field="RIG_ID_NUM / RIG_TYPE_CODE",
                raw_value="unmatched ID or unmapped code",
                unit_category="other",
                rule="retained unresolved unit; SU is submersible, not a semisubmersible",
            ),
        ]
    )
    write_csv(pd.DataFrame(rules), out, "unit_type_mapping")
    a = apm.merge(rigs, on="RIG_ID_NUM", how="left", validate="many_to_one").fillna(
        {"RIG_NAME": "", "RIG_TYPE_CODE": ""}
    )
    a["unit_category"] = [
        unit_category(r.RIG_TYPE_CODE, r.RIG_NAME, r.RIG_ID_NUM) for r in a.itertuples()
    ]
    eor = read_table(
        data_dir,
        "eWellEORRawData.zip",
        "mv_eor_mainquery",
        ["API_WELL_NUMBER", "SUBSEA_COMPLETION_FLAG"],
    )
    eor["api10"] = normalize_api(eor.API_WELL_NUMBER).str[:10]
    # Ever flagged YES at API10 in the retained EOR snapshot. A missing YES is
    # not evidence of a dry-tree completion; preserve unknown/no distinctions.
    flags = eor[eor.api10.ne("")].groupby("api10").SUBSEA_COMPLETION_FLAG.agg(set)
    a["api10"] = a.API_WELL_NUMBER.str[:10]
    a["subsea_flag"] = a.api10.map(flags).map(
        lambda x: (
            "yes"
            if isinstance(x, set) and "YES" in x
            else "no" if isinstance(x, set) and "NO" in x else "unknown"
        )
    )
    a["event"] = a["family"].where(a.family.eq("well work"), a["group"])
    rows, shares, estimates = [], [], []
    for period, first in [
        (str(last_full_year), last_full_year),
        (f"{last_full_year-4}-{last_full_year}", last_full_year - 4),
    ]:
        for band in BANDS:
            for event in ["well work", "permanent abandonment"]:
                g = a[
                    a.year.between(first, last_full_year)
                    & a.band.eq(band)
                    & a.event.eq(event)
                ]
                for category in UNIT_CATEGORIES:
                    n = int(g.unit_category.eq(category).sum())
                    rows.append(
                        dict(
                            period=period,
                            band=band,
                            event=event,
                            unit_category=category,
                            approvals=n,
                            total_approvals=len(g),
                            share_percent=n / len(g) * 100 if len(g) else float("nan"),
                        )
                    )
                shares.append(
                    dict(
                        period=period,
                        band=band,
                        event=event,
                        approvals=len(g),
                        subsea_flag_yes=int(g.subsea_flag.eq("yes").sum()),
                        subsea_flag_no=int(g.subsea_flag.eq("no").sum()),
                        subsea_flag_unknown=int(g.subsea_flag.eq("unknown").sum()),
                        subsea_share_percent=g.subsea_flag.eq("yes").mean() * 100,
                    )
                )
                if first == last_full_year:
                    days = pd.to_numeric(g.EST_OPERATION_DAYS, errors="coerce")
                    valid = days[days.gt(0) & days.lt(float("inf"))]
                    estimates.append(
                        dict(
                            year=last_full_year,
                            band=band,
                            event=event,
                            approvals=len(g),
                            estimates=len(valid),
                            missing_or_nonpositive=len(g) - len(valid),
                            median_est_operation_days=valid.median(),
                        )
                    )
    write_csv(pd.DataFrame(rows), out, "unit_type_shares")
    write_csv(pd.DataFrame(shares), out, "subsea_completion_shares")
    write_csv(pd.DataFrame(estimates), out, "permit_duration_estimates")
    ratios = []
    for band in BANDS:
        for family in ["well work", "abandonment"]:
            g = a[a.year.eq(last_full_year) & a.band.eq(band) & a.family.eq(family)]
            wells = g.loc[g.api10.ne(""), "api10"].nunique()
            ratios.append(
                dict(
                    year=last_full_year,
                    band=band,
                    family=family,
                    approvals=len(g),
                    distinct_wells=wells,
                    approvals_per_well=len(g) / wells if wells else float("nan"),
                    missing_api10=int(g.api10.eq("").sum()),
                )
            )
    write_csv(pd.DataFrame(ratios), out, "approvals_per_distinct_well")


def rate_per_100(events, wells):
    return events / wells * 100 if wells > 0 else float("nan")


def full_year_average(frame, column, last_full_year):
    return frame.loc[frame.year.le(last_full_year), column].mean()


def write_csv(frame, out, name):
    frame.to_csv(
        out / (name + ".csv"), index=False, float_format="%.6f", lineterminator="\n"
    )


def grid_counts(frame, value, groups, years):
    index = pd.MultiIndex.from_product(
        [years, BANDS, groups], names=["year", "band", "group"]
    )
    return (
        frame.groupby(["year", "band", "group"])
        .size()
        .reindex(index, fill_value=0)
        .rename(value)
        .reset_index()
    )


def war_crosscheck(data_dir, bore, out, first_year, last_full_year):
    main = read_table(
        data_dir,
        "eWellWARRawData.zip",
        "mv_war_main",
        [
            "SN_WAR",
            "API_WELL_NUMBER",
            "WAR_START_DT",
            "WAR_END_DT",
            "RIG_NAME",
            "SURF_LEASE_NUM",
        ],
    )
    prop = read_table(
        data_dir,
        "eWellWARRawData.zip",
        "mv_war_main_prop",
        ["SN_WAR", "WELL_ACTIVITY_CD"],
    )
    prop = prop.drop_duplicates()
    if prop.SN_WAR.duplicated().any():
        raise ValueError("conflicting WAR property keys")
    main = main.drop_duplicates()
    if main.SN_WAR.duplicated().any():
        raise ValueError("conflicting WAR main keys")
    war = gulf_only(
        main.merge(prop, on="SN_WAR", how="left", validate="one_to_one"), bore
    )
    war = attach_depth(war[war.region.eq("G")], bore)
    war["start"] = dates(war.WAR_START_DT)
    war["end"] = dates(war.WAR_END_DT)
    war["days"] = (war.end - war.start).dt.days + 1
    in_years = war.start.dt.year.between(first_year, last_full_year)
    # Token subset is an interpretation, not an official WAR code definition.
    selected = war.WELL_ACTIVITY_CD.isin(["WO", "REC", "TA", "PA"])
    rig = ~war.RIG_NAME.str.upper().isin(
        ["", "N/A", "NA", "NONE", "NO RIG", "WIRELINE", "CT"]
    )
    valid = war.days.between(1, 90) & war.API_WELL_NUMBER.ne("")
    f = war[in_years & selected & rig & valid].sort_values(
        ["API_WELL_NUMBER", "RIG_NAME", "WELL_ACTIVITY_CD", "start", "end"]
    )
    # Union overlapping/adjacent report intervals per bore, named unit and raw
    # code. A gap or a changed code/unit starts a new proxy episode.
    episodes = []
    for (api, asset, code), g in f.groupby(
        ["API_WELL_NUMBER", "RIG_NAME", "WELL_ACTIVITY_CD"]
    ):
        start = end = band = None
        for r in g.itertuples():
            if start is not None and r.start > end + pd.Timedelta(days=1):
                episodes.append(dict(band=band, code=code, days=(end - start).days + 1))
                start = None
            if start is None:
                start, end, band = r.start, r.end, r.band
            else:
                end = max(end, r.end)
        if start is not None:
            episodes.append(dict(band=band, code=code, days=(end - start).days + 1))
    e = pd.DataFrame(episodes, columns=["band", "code", "days"])
    rows = []
    for (band, code), g in e.groupby(["band", "code"]):
        q = g.days.quantile([0.25, 0.5, 0.75])
        rows.append(
            dict(
                band=band,
                raw_war_code=code,
                episodes=len(g),
                q25_days=q.loc[0.25],
                median_days=q.loc[0.5],
                q75_days=q.loc[0.75],
            )
        )
    for band, g in e.groupby("band"):
        q = g.days.quantile([0.25, 0.5, 0.75])
        rows.append(
            dict(
                band=band,
                raw_war_code="selected tokens combined",
                episodes=len(g),
                q25_days=q.loc[0.25],
                median_days=q.loc[0.5],
                q75_days=q.loc[0.75],
            )
        )
    write_csv(pd.DataFrame(rows), out, "war_duration_crosscheck")
    return dict(
        war_rows=len(war),
        selected_valid_rows=len(f),
        proxy_episodes=len(e),
        invalid_selected_spans=int((in_years & selected & ~valid).sum()),
    )


def run(data_dir, out, last_full_year):
    data_dir, out = Path(data_dir), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    for receipt in manifest["files"]:
        if receipt["status"] == "downloaded":
            path = data_dir / receipt["name"]
            if (
                path.stat().st_size != receipt["bytes"]
                or hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]
            ):
                raise ValueError(f"archive digest mismatch: {path.name}")
    available = {r["name"] for r in manifest["files"] if r["status"] == "downloaded"}
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if not {"BoreholeRawData.zip", "eWellAPMRawData.zip"}.issubset(available):
        summary = dict(
            status="insufficient inputs",
            unavailable=sorted(
                {"BoreholeRawData.zip", "eWellAPMRawData.zip"} - available
            ),
        )
        (out / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        return summary
    bore = read_table(
        data_dir,
        "BoreholeRawData.zip",
        "mv_boreholes_all",
        [
            "API_WELL_NUMBER",
            "REGION_CODE",
            "WATER_DEPTH",
            "WELL_NAME_SUFFIX",
            "WELL_SPUD_DATE",
            "BOREHOLE_STAT_CD",
            "BOREHOLE_STAT_DT",
        ],
    )
    raw = read_table(data_dir, "eWellAPMRawData.zip", "mv_apm_main")
    apm = dedupe_permits(raw)
    apm = gulf_only(apm, bore)
    region_counts = apm.region.value_counts().to_dict()
    apm = attach_depth(apm[apm.region.eq("G")], bore)
    apm["year"] = dates(apm.ACC_STATUS_DATE).dt.year
    sub = read_table(data_dir, "eWellAPMRawData.zip", "mv_apm_suboperations")
    subcodes = sub.groupby("SN_APM_FK").APM_SUBOP_CD.agg(set).to_dict()
    # Latin-1 preserves every source byte; some narrative bytes are undefined
    # in cp1252. The screen uses ASCII words only; narratives are never exported.
    prop = read_table(
        data_dir, "eWellAPMRawData.zip", "mv_apm_main_prop", encoding="latin1"
    )
    narratives = (
        prop.groupby("SN_APM")
        .APM_OP_DESC.agg(lambda s: "\n".join(sorted(set(s))))
        .to_dict()
    )
    apm["group"] = [
        classify_operation(
            r.APM_OP_CD, subcodes.get(r.SN_APM, set()), narratives.get(r.SN_APM, "")
        )
        for r in apm.itertuples()
    ]
    apm["exclusion_basis"] = [
        (
            "PLUGBACK subcode"
            if "PLUGBACK" in subcodes.get(r.SN_APM, set())
            else (
                "explicit new-hole narrative"
                if narrative_new_hole(r.APM_OP_CD, narratives.get(r.SN_APM, ""))
                else "completion without ZONE" if r.group == GROUPS[7] else "included"
            )
        )
        for r in apm.itertuples()
    ]
    apm["family"] = apm.group.map(
        lambda g: (
            "well work"
            if g in WELL_WORK
            else "abandonment" if g in ABANDONMENT else "excluded"
        )
    )
    # 2004 begins in April and ramps sharply; 2005 is the first full calendar
    # year represented. No claim of complete regulatory capture is made.
    first_year = 2005
    years = list(range(first_year, last_full_year + 2))
    quality = dict(
        raw_apm_rows=len(raw),
        unique_apm=len(dedupe_permits(raw)),
        duplicate_apm_rows_removed=len(raw) - len(dedupe_permits(raw)),
        region_counts=region_counts,
        invalid_approval_dates=int(apm.year.isna().sum()),
        first_full_year=first_year,
        last_full_year=last_full_year,
        partial_year=last_full_year + 1,
        original_holes_missing_spud=int(
            (
                bore.REGION_CODE.eq("G")
                & bore.WELL_NAME_SUFFIX.eq("ST00BP00")
                & dates(bore.WELL_SPUD_DATE).isna()
            ).sum()
        ),
        original_holes_pa_without_date=int(
            (
                bore.REGION_CODE.eq("G")
                & bore.WELL_NAME_SUFFIX.eq("ST00BP00")
                & bore.BOREHOLE_STAT_CD.eq("PA")
                & dates(bore.BOREHOLE_STAT_DT).isna()
            ).sum()
        ),
    )
    monthly = (
        apm.assign(month=dates(apm.ACC_STATUS_DATE).dt.strftime("%Y-%m"))
        .groupby("month")
        .size()
        .rename("approved_permits")
        .reset_index()
    )
    write_csv(monthly, out, "coverage_by_month")
    raw_2025 = raw[dates(raw.ACC_STATUS_DATE).dt.year.eq(last_full_year)]
    quality["checkpoint_raw_last_full_year"] = (
        raw_2025.APM_OP_CD.value_counts().to_dict()
    )
    apm = apm[apm.year.isin(years)].copy()
    apm["year"] = apm.year.astype(int)
    access_outputs(apm, data_dir, out, last_full_year)
    write_csv(
        apm.groupby(["year", "APM_OP_CD"]).size().rename("approvals").reset_index(),
        out,
        "primary_code_by_year",
    )
    quality["depth_join"] = (
        apm[apm.family.ne("excluded")].depth_join.value_counts().to_dict()
    )
    quality["events_with_depth_fraction"] = float(
        apm.loc[apm.family.ne("excluded"), "band"].ne("no depth").mean()
    )
    counts = grid_counts(apm, "permits", GROUPS, years)
    counts["partial_year"] = counts.year.gt(last_full_year)
    write_csv(counts, out, "counts_by_year_band_group")
    write_csv(
        apm.groupby(["year", "exclusion_basis"]).size().rename("permits").reset_index(),
        out,
        "exclusion_audit",
    )
    primary = read_table(
        data_dir, "eWellAPMRawData.zip", "mv_apm_primary_op_codes"
    ).rename(columns={"VALUE": "primary_code", "DESCRIP": "description"})
    mapping = (
        apm.groupby(["APM_OP_CD", "group"])
        .size()
        .rename("permits")
        .reset_index()
        .rename(columns={"APM_OP_CD": "primary_code"})
        .merge(primary, on="primary_code", how="left")
    )
    last_counts = (
        apm[apm.year.eq(last_full_year)].groupby(["APM_OP_CD", "group"]).size()
    )
    mapping["last_full_year_permits"] = [
        int(last_counts.get((r.primary_code, r.group), 0)) for r in mapping.itertuples()
    ]
    write_csv(mapping, out, "code_mapping")
    submap = read_table(data_dir, "eWellAPMRawData.zip", "mv_apm_suboperation_codes")
    submap["occurrences_in_selected_permits"] = (
        submap.VALUE.map(
            sub[sub.SN_APM_FK.isin(apm.SN_APM)].APM_SUBOP_CD.value_counts()
        )
        .fillna(0)
        .astype(int)
    )
    write_csv(submap, out, "suboperation_mapping")
    file_date = max(
        pd.Timestamp(r["page_last_updated"]).date()
        for r in manifest["files"]
        if r["status"] == "downloaded"
    )
    quality["file_date"] = str(file_date)
    standing = standing_wells(bore, years, as_of=file_date)
    standing["partial_year"] = standing.year.gt(last_full_year)
    write_csv(standing, out, "standing_wells")
    write_csv(
        standing_wells(bore, years, as_of=file_date, at="year_end"),
        out,
        "standing_wells_year_end",
    )
    inventory = well_inventory(bore)
    quality["inventory_missing_first_spud"] = int(inventory.spud.isna().sum())
    quality["inventory_basis"] = (
        "all non-cancelled bores per API10; stock on 1 January, inclusive dates"
    )
    quality["assumed_standing_last_full_year"] = int(
        standing.loc[standing.year.eq(last_full_year), "assumed_standing"].sum()
    )
    rates = []
    for r in standing.itertuples():
        for family, selected in [
            ("well work", WELL_WORK),
            ("abandonment", ABANDONMENT),
        ]:
            n = int(
                counts.loc[
                    counts.year.eq(r.year)
                    & counts.band.eq(r.band)
                    & counts.group.isin(selected),
                    "permits",
                ].sum()
            )
            rates.append(
                dict(
                    year=r.year,
                    band=r.band,
                    family=family,
                    permits=n,
                    standing_wells=r.standing_wells,
                    stock_date=r.stock_date,
                    per_100_standing_wells=rate_per_100(n, r.standing_wells),
                    partial_year=r.partial_year,
                )
            )
    rates = pd.DataFrame(rates)
    write_csv(rates, out, "rates")
    averages = (
        rates[rates.year.le(last_full_year)]
        .groupby(["band", "family"])
        .agg(
            mean_annual_permits=("permits", "mean"),
            mean_annual_rate=("per_100_standing_wells", "mean"),
        )
        .reset_index()
    )
    write_csv(averages, out, "full_year_averages")
    if "eWellEORRawData.zip" in available:
        eor = read_table(
            data_dir,
            "eWellEORRawData.zip",
            "mv_eor_mainquery",
            [
                "SN_EOR",
                "API_WELL_NUMBER",
                "EOR_OPERATION_CD",
                "BOREHOLE_STAT_DT",
                "SURF_LEASE_NUMBER",
            ],
        )
        eor = eor.drop_duplicates()
        if eor.SN_EOR.duplicated().any():
            raise ValueError("conflicting EOR keys")
        eor = gulf_only(eor, bore)
        eor = attach_depth(eor[eor.region.eq("G")], bore)
        eor["year"] = dates(eor.BOREHOLE_STAT_DT).dt.year
        quality["eor_invalid_status_dates"] = int(eor.year.isna().sum())
        quality["checkpoint_eor_last_full_year"] = (
            eor[eor.year.eq(last_full_year)].EOR_OPERATION_CD.value_counts().to_dict()
        )
        eor["group"] = eor.EOR_OPERATION_CD.map(
            {"W": "workover", "A": "abandonment", "C": "completion"}
        )
        ec = grid_counts(
            eor[eor.year.isin(years)],
            "reports",
            ["workover", "abandonment", "completion"],
            years,
        )
        ec["partial_year"] = ec.year.gt(last_full_year)
        write_csv(ec, out, "eor_by_year_band")
        ratios = []
        for band in BANDS:
            for kind, codes in [
                ("workover", {"WORKOVER"}),
                ("abandonment", {"ABANDON"}),
            ]:
                n = int(
                    ec.loc[
                        ec.year.eq(last_full_year)
                        & ec.band.eq(band)
                        & ec.group.eq(kind),
                        "reports",
                    ].sum()
                )
                p = int(
                    (
                        apm.year.eq(last_full_year)
                        & apm.band.eq(band)
                        & apm.APM_OP_CD.isin(codes)
                        & apm.family.ne("excluded")
                    ).sum()
                )
                ratios.append(
                    dict(
                        year=last_full_year,
                        band=band,
                        type=kind,
                        reports=n,
                        permits=p,
                        reports_per_permit=n / p if p else float("nan"),
                    )
                )
        write_csv(pd.DataFrame(ratios), out, "eor_permit_ratios")
    if "eWellWARRawData.zip" in available:
        quality.update(war_crosscheck(data_dir, bore, out, first_year, last_full_year))
    headline = rates[rates.year.eq(last_full_year)].astype(object)
    quality["headline"] = headline.where(headline.notna(), None).to_dict("records")
    (out / "summary.json").write_text(
        json.dumps(quality, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        k: quality[k]
        for k in [
            "raw_apm_rows",
            "duplicate_apm_rows_removed",
            "events_with_depth_fraction",
            "checkpoint_raw_last_full_year",
            "checkpoint_eor_last_full_year",
        ]
        if k in quality
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--last-full-year", type=int, default=2025)
    args = parser.parse_args()
    print(json.dumps(run(args.data_dir, args.out, args.last_full_year), sort_keys=True))
