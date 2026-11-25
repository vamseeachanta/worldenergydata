"""API10 inventory and dated well events from the BSEE eWell snapshot."""

import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BANDS = ["<100 m", "100–<500 m", "500–<1,500 m", "≥1,500 m"]
SNAPSHOT = pd.Timestamp("2026-11-23")
REPO_ROOT = Path(__file__).resolve().parents[3]
ARTICLE_CODE = Path("examples/bsee/interventions_by_depth/count_interventions.py")


def reference_module():
    path = REPO_ROOT / ARTICLE_CODE
    spec = importlib.util.spec_from_file_location("bsee_series_interventions", path)
    module = importlib.util.module_from_spec(spec)
    # The reference is a read-only checkout, including its imported normalizer.
    prev = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prev
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def calendar_dates(values):
    # Source dates are month/day/year with optional times. Both event definitions
    # here use whole calendar dates. Unrecognised formats are not silently truncated.
    dates = values.str.extract(
        r"^(\d{1,2}/\d{1,2}/\d{4})(?:\s+\d{1,2}:\d{2}:\d{2}(?:\s+[AP]M)?)?$",
        expand=False,
    )
    return pd.to_datetime(dates, format="%m/%d/%Y", errors="coerce")


def select(frame, stage, excludes, audit):
    """Apply disjoint, ordered dispositions while preserving record grain."""
    keep = pd.Series(True, index=frame.index)
    reasons = {}
    for reason, mask in excludes:
        if mask.isna().any():
            raise ValueError(f"{stage}: unresolved mask for {reason}")
        reasons[reason] = int((keep & mask).sum())
        keep &= ~mask
    audit(stage, len(frame), int(keep.sum()), reasons)
    return frame.loc[keep].copy()


def inventory(bore, ref, audit, check, notes):
    bore["api"] = ref.normalize_api(bore.API_WELL_NUMBER)
    bore["api10"] = bore.api.str[:10]
    bore = select(
        bore,
        "borehole API rows for inventory",
        [
            ("invalid API", bore.api.eq("")),
            ("duplicate borehole row", bore.duplicated()),
        ],
        audit,
    )
    check(
        "Borehole identifiers identify one inventory source row each",
        bore.api.is_unique,
        f"{len(bore):,} boreholes",
    )
    groups = bore.groupby("api10")
    statuses = groups.REGION_CODE.agg(set)
    current = pd.DataFrame(index=statuses.index)
    current["inventory_status"] = "outside_gulf"
    current.loc[statuses.map(lambda s: s == {""}), "inventory_status"] = "unknown_region"
    current.loc[statuses.map(lambda s: len(s) != 1), "inventory_status"] = "ambiguous_region"
    current.loc[statuses.map(lambda s: s == {"G"}), "inventory_status"] = "gulf"
    gulf_all = current.inventory_status.eq("gulf")
    cancelled = groups.BOREHOLE_STAT_CD.agg(lambda v: v.eq("CNL").all())
    current.loc[gulf_all & cancelled, "inventory_status"] = "cancelled_only"
    gulf = select(
        bore,
        "borehole rows for Gulf depth and spud",
        [
            ("region outside or unresolved", ~bore.api10.isin(current.index[gulf_all])),
            ("cancelled bore", bore.BOREHOLE_STAT_CD.eq("CNL")),
        ],
        audit,
    )
    gulf["spud"] = calendar_dates(gulf.WELL_SPUD_DATE)
    gulf["depth_ft"] = pd.to_numeric(gulf.WATER_DEPTH, errors="coerce")
    gulf["depth_ft"] = gulf.depth_ft.where(np.isfinite(gulf.depth_ft) & gulf.depth_ft.ge(0))
    # Match the inventory depth rule of the intervention series. Origin is the
    # bore's ST00BP00 designation, not an assumption about the last two API digits.
    original = gulf[gulf.WELL_NAME_SUFFIX.eq("ST00BP00")].copy()
    original["not_00"] = ~original.api.str.endswith("00")
    chosen = original.sort_values(["not_00", "spud", "api"], kind="stable").drop_duplicates("api10")
    source_depth = chosen.set_index("api10").depth_ft.combine_first(
        ref.unique_map(gulf, "api10", "depth_ft")
    )
    current["depth_ft"] = current.index.map(source_depth)
    current["band"] = pd.cut(
        current.depth_ft * 0.3048, [0, 100, 500, 1500, np.inf], right=False, labels=BANDS
    ).astype("string")
    current["first_spud"] = current.index.map(gulf.groupby("api10").spud.min())
    check(
        "Gulf inventory assigns each API10 at most one depth band",
        current.index.is_unique and current.loc[~current.inventory_status.eq("gulf"), "band"].isna().all(),
        f"{current.band.notna().sum():,} API10s with depth",
    )
    nd = gulf.groupby("api10").depth_ft.nunique()
    eligible = current[current.inventory_status.eq("gulf")]
    notes.append(
        f"Borehole REGION_CODE G identifies the Gulf. Of {len(eligible):,} distinct Gulf wells with a non-cancelled bore, {eligible.band.isna().sum():,} lack an assignable depth. "
        f"{nd.gt(1).sum():,} have differing reported depths across bores. The series inventory uses the ST00BP00 original hole, preferring an API ending in 00, then earliest spud and lowest API. "
        f"If its depth is absent, a single agreed nonnegative depth from the remaining bores is used. {eligible.depth_ft.eq(0).sum():,} selected depths are recorded as zero feet and fall in the shallowest band. "
        "The borehole dictionary defines WATER_DEPTH in feet. Metres = feet × 0.3048. Band lower limits are inclusive. The spud date is the earliest dated non-cancelled bore."
    )
    return current


def call_first_reports(raw, wells, ref, audit, check, notes):
    raw["api10"] = ref.normalize_api(raw.API_WELL_NUMBER).str[:10]
    raw["date"] = calendar_dates(raw.BOREHOLE_STAT_DT)
    raw = select(
        raw,
        "eWell EOR rows for first completion",
        [
            ("duplicate EOR row", raw.duplicated()),
            ("other EOR operation", raw.EOR_OPERATION_CD.ne("C")),
            ("invalid API", raw.api10.eq("")),
            (
                "outside eligible Gulf inventory",
                ~raw.api10.isin(wells.index[wells.inventory_status.eq("gulf")]),
            ),
            ("absent or unparseable status date", raw.date.isna()),
            ("status date after snapshot", raw.date.gt(SNAPSHOT)),
        ],
        audit,
    )
    check(
        "Eligible completion reports have distinct nonblank SN_EOR",
        raw.SN_EOR.ne("").all() and raw.SN_EOR.is_unique,
        f"{len(raw):,} reports",
    )
    first = raw.groupby("api10").date.min()
    wells["completion_date"] = wells.index.map(first)
    first_rows = raw[raw.date.eq(raw.api10.map(first))]
    flags = first_rows.groupby("api10").SUBSEA_COMPLETION_FLAG.agg(set)
    # Retain unknown for ties that give incompatible or missing flags.
    labels = flags.map(
        lambda s: "Subsea" if s == {"YES"} else ("No subsea flag (NO)" if s == {"NO"} else "Unknown")
    )
    wells["completion_type"] = wells.index.map(labels).fillna("Unknown")
    non_com = first_rows.loc[first_rows.BOREHOLE_STAT_CD.ne("COM"), "api10"].nunique()
    notes.append(
        f"The eWell code table mv_eor_operationcodes defines C as COMPLETION. The earliest C report's BOREHOLE_STAT_DT (effective status date) is selected across all bores and all years before applying the cohort dates. "
        f"{non_com:,} Gulf wells have a status other than COM on at least one earliest C report. eWell electronic EOR submissions start in April 2004 and may report earlier status dates. The earliest electronic report can describe later work on an older well. "
        "At the earliest dated C report only, SUBSEA_COMPLETION_FLAG records whether a subsea completion exists. YES identifies a subsea completion. Explicit NO is a reported negative for that flag and does not identify the design of a dry tree. "
        f"Blank, conflicting or absent evidence is unknown ({flags.map(lambda s: len(s) > 1).sum():,} earliest-date sets contain differing flag values). The undated borehole stub indicator is not used to infer historical completion type."
    )


def first_event(data, wells, ref, stage, date_col, audit, check, extra=()):
    data["api10"] = ref.normalize_api(data.API_WELL_NUMBER).str[:10]
    data["date"] = calendar_dates(data[date_col])
    data["completion"] = data.api10.map(wells.completion_date)
    data = select(
        data,
        stage,
        [
            *extra,
            ("invalid API", data.api10.eq("")),
            (
                "outside eligible Gulf inventory",
                ~data.api10.isin(wells.index[wells.inventory_status.eq("gulf")]),
            ),
            ("absent or unparseable event date", data.date.isna()),
            ("event after snapshot", data.date.gt(SNAPSHOT)),
            ("no dated C completion", data.completion.isna()),
            ("event on or before completion", data.date.le(data.completion)),
        ],
        audit,
    )
    result = data.groupby("api10").date.min()
    check(
        f"{stage}: first events occur strictly after completion",
        result.gt(wells.completion_date.reindex(result.index)).all(),
        f"{len(result):,} Gulf API10s",
    )
    return result


def load_wells(well_dir, audit, check):
    """Return all resolvable API10 identities, Gulf fields and provenance notes."""
    ref, reference_hash = reference_module()
    notes = [
        (
            f"Reference code: worldenergydata/{ARTICLE_CODE}, SHA-256 {reference_hash}. Its read_table, API normalizer, unique-depth mapping, permit identity and operation classifier are reused. "
            "Field documentation: docs/knowledge-base/bsee/data-dictionaries/wells/borehole-fields.md and docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md. "
        )
    ]

    def read(archive, member, columns, encoding="latin1"):
        return ref.read_table(well_dir, archive + ".zip", member, columns, encoding=encoding)

    bore = read(
        "BoreholeRawData",
        "mv_boreholes_all",
        [
            "API_WELL_NUMBER",
            "REGION_CODE",
            "WELL_NAME_SUFFIX",
            "WELL_SPUD_DATE",
            "WATER_DEPTH",
            "BOREHOLE_STAT_CD",
        ],
    )
    wells = inventory(bore, ref, audit, check, notes)
    codes = read("eWellEORRawData", "mv_eor_operationcodes", ["VALUE", "ABBREVIATION"])
    audit("eWell EOR operation code dictionary", len(codes), len(codes), {})
    check(
        "BSEE operation code C means COMPLETION",
        codes.loc[codes.VALUE.eq("C"), "ABBREVIATION"].tolist() == ["COMPLETION"],
    )
    eor = read(
        "eWellEORRawData",
        "mv_eor_mainquery",
        [
            "SN_EOR",
            "API_WELL_NUMBER",
            "EOR_OPERATION_CD",
            "BOREHOLE_STAT_DT",
            "BOREHOLE_STAT_CD",
            "SUBSEA_COMPLETION_FLAG",
        ],
    )
    call_first_reports(eor, wells, ref, audit, check, notes)
    war = read("eWellWARRawData", "mv_war_main", ["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT"])
    check(
        "WAR identifiers are nonblank and identify one API and start date",
        war.SN_WAR.ne("").all() and war.drop_duplicates().SN_WAR.is_unique,
    )
    war_dates = first_event(
        war,
        wells,
        ref,
        "eWell WAR rows for observed work",
        "WAR_START_DT",
        audit,
        check,
        [("duplicate WAR row", war.duplicated())],
    )
    wells["war_date"] = wells.index.map(war_dates)
    # The independent permit comparator uses the series classifier without copying
    # its new-hole exclusion regex or assigning meanings to undocumented WAR codes.
    apm = read(
        "eWellAPMRawData", "mv_apm_main", ["SN_APM", "API_WELL_NUMBER", "ACC_STATUS_DATE", "APM_OP_CD"]
    )
    permits = ref.dedupe_permits(apm)
    audit(
        "eWell APM permit identities", len(apm), len(permits), {"repeated permit": len(apm) - len(permits)}
    )
    eligible = wells.index[wells.inventory_status.eq("gulf")]
    permits = select(
        permits,
        "eWell APM permits for series classification",
        [
            (
                "outside eligible Gulf inventory",
                ~ref.normalize_api(permits.API_WELL_NUMBER).str[:10].isin(eligible),
            ),
        ],
        audit,
    )
    sub = read("eWellAPMRawData", "mv_apm_suboperations", ["SN_APM_FK", "APM_SUBOP_CD"])
    sub = select(
        sub,
        "eWell APM suboperation rows",
        [
            ("no selected permit", ~sub.SN_APM_FK.isin(permits.SN_APM)),
        ],
        audit,
    )
    subcodes = sub.groupby("SN_APM_FK").APM_SUBOP_CD.agg(set)
    prop = read("eWellAPMRawData", "mv_apm_main_prop", ["SN_APM", "APM_OP_DESC"])
    prop = select(
        prop,
        "eWell APM descriptions",
        [
            ("no selected permit", ~prop.SN_APM.isin(permits.SN_APM)),
        ],
        audit,
    )
    descriptions = prop.groupby("SN_APM").APM_OP_DESC.agg(lambda s: "\n\n".join(sorted(set(s))))
    permits["group"] = [
        ref.classify_operation(r.APM_OP_CD, subcodes.get(r.SN_APM, set()), descriptions.get(r.SN_APM, ""))
        for r in permits.itertuples()
    ]
    permit_dates = first_event(
        permits,
        wells,
        ref,
        "eWell APM approvals for classified well work",
        "ACC_STATUS_DATE",
        audit,
        check,
        [("outside series well-work groups", ~permits.group.isin(ref.WELL_WORK))],
    )
    wells["permit_date"] = wells.index.map(permit_dates)
    notes.append(
        "One WAR event marks the first WAR_START_DT strictly after the well's C status date. The WAR clock uses whole calendar dates; later reports on the same completion day are excluded. "
        "WAR covers work of several kinds, and the local field definitions do not establish a complete WAR activity-code vocabulary. A later WAR is a proxy for reported activity and cannot establish a confirmed intervention. "
        "The interventions article counts approved APM permits. Its comparator here uses the first post-completion ACC_STATUS_DATE classified as workover/recompletion, production enhancement or other well work by the article's code. "
        "This removes abandonments, new-hole preparations and initial completions. An approval records permission for work; it cannot establish the day the work took place."
    )
    return wells.reset_index(), notes
