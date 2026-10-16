"""Record-count characterisation; no duration or production correlations."""

from __future__ import annotations

import io
import math
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.analysis.war_activity_codes import load_activity_codes
from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
from worldenergydata.bsee.data.utils.api_well_normalizer import (
    normalize_api_well_number,
)

UNKNOWN = "unknown"


@dataclass(frozen=True)
class Parameters:
    """Descriptive bins and count thresholds, independent of engineering limits."""

    depth_edges: tuple = (1000, 3000, 5000, 10000)
    era_edges: tuple = (2000, 2010, 2020)
    candidate_codes: tuple = ("PA", "REC", "ST", "TA", "WO")
    workover_codes: tuple = ("W",)
    outlier_quantiles: tuple = (0.05, 0.95)

    def __post_init__(self):
        for edges in (self.depth_edges, self.era_edges):
            if not edges or any(not math.isfinite(x) for x in edges):
                raise ValueError("finite bin edges are required")
            if any(a >= b for a, b in zip(edges, edges[1:])) or edges[0] <= 0:
                raise ValueError("bin edges must increase and be positive")
        low, high = self.outlier_quantiles
        if not 0 <= low < high <= 1:
            raise ValueError("outlier quantiles must increase within zero and one")
        if any(
            not isinstance(x, str) or not x
            for x in (*self.candidate_codes, *self.workover_codes)
        ):
            raise ValueError("activity selections require nonempty raw codes")


def depth_band(value, parameters):
    try:
        depth = float(value)
    except (TypeError, ValueError):
        return UNKNOWN
    if not math.isfinite(depth) or depth < 0:
        return UNKNOWN
    edges = parameters.depth_edges
    if depth < edges[0]:
        return f"below {edges[0]} ft"
    for left, right in zip(edges, edges[1:]):
        if left <= depth < right:
            return f"{left}-{right} ft"
    return f"at least {edges[-1]} ft"


def calendar_era(year, parameters):
    if year is None or pd.isna(year):
        return UNKNOWN
    edges = parameters.era_edges
    if year < edges[0]:
        return f"before {edges[0]}"
    for left, right in zip(edges, edges[1:]):
        if left <= year < right:
            return f"{left}-{right - 1}"
    return f"{edges[-1]} onwards"


def read_archive(path, members):
    """Select named members, then delegate CSV decoding to the existing loader.

    Main and property tables retain their individual grains. Large narrative
    members are not parsed when they are not analysis inputs.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(buffer, "w") as selected:
        for member in members:
            matches = [n for n in source.namelist() if Path(n).name == member + ".txt"]
            if len(matches) != 1:
                raise ValueError(f"expected exactly one archive member: {member}")
            selected.writestr(member + ".txt", source.read(matches[0]))
    data = MemoryProcessor(use_optimized=False).process_zip_in_memory(buffer.getvalue())
    if set(data) != {m + ".txt" for m in members}:
        raise ValueError("existing processor did not return every selected member")
    return {m: data[m + ".txt"] for m in members}


def _columns(frame, columns):
    result = frame.reindex(columns=columns).copy()
    for column in columns:
        result[column] = result[column].fillna("").astype(str).str.strip()
    if "API_WELL_NUMBER" in columns:
        api = normalize_api_well_number(result["API_WELL_NUMBER"])
        result["API_WELL_NUMBER"] = api.where(
            api.str.fullmatch(r"\d{12}", na=False), ""
        )
    for column in columns:
        if column.startswith("SN_"):
            result[column] = result[column].str.replace(r"\.0$", "", regex=True)
    return result


def _unique(frame, keys, name, quality):
    exact = frame.drop_duplicates().reset_index(drop=True)
    quality[name + "_duplicate_rows_removed"] = len(frame) - len(exact)
    if exact.duplicated(keys, keep=False).any():
        raise ValueError(f"conflicting {name} keys; refusing a multiplying join")
    if exact[keys].eq("").any(axis=None):
        raise ValueError(f"missing {name} report key")
    return exact


def _mapping(frame, column, quality, quality_key, numeric=False):
    values = frame[["API_WELL_NUMBER", column]].copy()
    values = values[values["API_WELL_NUMBER"] != ""]
    if numeric:
        values[column] = pd.to_numeric(values[column], errors="coerce")
        values.loc[~values[column].ge(0) | ~values[column].lt(float("inf")), column] = (
            pd.NA
        )
    else:
        values[column] = values[column].replace("", pd.NA)
    groups = values.groupby("API_WELL_NUMBER")[column]
    sizes = groups.nunique()
    quality[quality_key] = int((sizes > 1).sum())
    return groups.first().where(sizes == 1).to_dict()


def _year(frame, column):
    parsed = pd.to_datetime(
        frame[column], format="mixed", dayfirst=False, errors="coerce"
    )
    return parsed.dt.year.map(lambda x: str(int(x)) if pd.notna(x) else UNKNOWN)


def _enrich(frame, fields, depths, date_column, parameters):
    result = frame.copy()
    result["field"] = result["API_WELL_NUMBER"].map(fields).fillna(UNKNOWN)
    result["water_depth_band"] = (
        result["API_WELL_NUMBER"].map(depths).map(lambda x: depth_band(x, parameters))
    )
    result["year"] = _year(result, date_column)
    result["era"] = result["year"].map(
        lambda x: calendar_era(int(x) if x != UNKNOWN else None, parameters)
    )
    return result


def _counts(frame, dimensions):
    return (
        frame.groupby(dimensions, dropna=False)
        .size()
        .rename("records")
        .reset_index()
        .sort_values(dimensions)
        .to_dict("records")
    )


def _annual(frame, code):
    result = frame.copy()
    result["code"] = result[code].replace("", UNKNOWN)
    result["valid_api"] = result["API_WELL_NUMBER"].replace("", pd.NA)
    return (
        result.groupby(["year", "code"])
        .agg(records=("code", "size"), wells=("valid_api", "nunique"))
        .reset_index()
        .sort_values(["year", "code"])
        .to_dict("records")
    )


def outlier_flags(values, quantiles):
    """Strict linear empirical quantiles; equal values are never flagged."""
    if not values:
        return {"thresholds": None, "flags": []}
    low, high = pd.Series(values, dtype=float).quantile(list(quantiles)).tolist()
    return {
        "thresholds": [low, high],
        "flags": ["low" if x < low else "high" if x > high else "" for x in values],
    }


def _well_frequencies(eor, war, parameters):
    valid = eor[eor["API_WELL_NUMBER"] != ""].copy()
    valid["workover"] = (
        valid["EOR_OPERATION_CD"].isin(parameters.workover_codes).astype(int)
    )
    groups = valid.groupby("API_WELL_NUMBER")
    wells = groups.agg(
        eor_records=("SN_EOR", "size"),
        workover_records=("workover", "sum"),
        field=("field", "first"),
    )
    candidate = war[war["WELL_ACTIVITY_CD"].isin(parameters.candidate_codes)]
    wells["candidate_war_records"] = (
        candidate.groupby("API_WELL_NUMBER").size().reindex(wells.index, fill_value=0)
    )
    wells = (
        wells.reset_index()
        .rename(columns={"API_WELL_NUMBER": "api12"})
        .sort_values("api12")
    )
    flags = outlier_flags(
        wells["workover_records"].tolist(), parameters.outlier_quantiles
    )
    wells["outlier"] = flags["flags"]
    return wells, flags["thresholds"]


def _field_frequencies(wells, parameters):
    known = wells[wells["field"] != UNKNOWN]
    fields = (
        known.groupby("field")
        .agg(
            recorded_wells=("api12", "size"),
            workover_records=("workover_records", "sum"),
        )
        .reset_index()
    )
    fields["workover_records_per_recorded_well"] = (
        fields["workover_records"] / fields["recorded_wells"]
    )
    flags = outlier_flags(
        fields["workover_records_per_recorded_well"].tolist(),
        parameters.outlier_quantiles,
    )
    fields["outlier"] = flags["flags"]
    return fields.to_dict("records"), flags["thresholds"]


def _war_frequencies(war, parameters):
    valid = war[war["API_WELL_NUMBER"] != ""].copy()
    valid["candidate"] = (
        valid["WELL_ACTIVITY_CD"].isin(parameters.candidate_codes).astype(int)
    )
    return (
        valid.groupby("API_WELL_NUMBER")
        .agg(
            war_records=("SN_WAR", "size"),
            candidate_war_records=("candidate", "sum"),
            field=("field", "first"),
        )
        .reset_index()
        .rename(columns={"API_WELL_NUMBER": "api12"})
        .sort_values("api12")
        .to_dict("records")
    )


def _validate_tables(tables):
    essential = {
        "mv_war_main": ["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT"],
        "mv_war_main_prop": ["SN_WAR", "WELL_ACTIVITY_CD"],
        "mv_eor_mainquery": [
            "SN_EOR",
            "API_WELL_NUMBER",
            "EOR_OPERATION_CD",
            "BOREHOLE_STAT_DT",
        ],
        "mv_eor_completions": ["SN_EOR_FK", "SN_EOR_WELL_COMP"],
        "mv_api_wellcomps_all": [
            "API_WELL_NUMBER",
            "COMPLETION_DATE",
            "COMP_STATUS_CD",
        ],
        "mv_api_list_all": ["API_WELL_NUMBER"],
        "mv_boreholes_all": ["API_WELL_NUMBER"],
    }
    for name, columns in essential.items():
        if name not in tables or set(columns) - set(tables[name].columns):
            raise ValueError(f"missing essential columns or table: {name}")


def _war_frame(tables, fields, depths, parameters, quality):
    columns = ["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT"]
    main = _unique(_columns(tables["mv_war_main"], columns), ["SN_WAR"], "war", quality)
    prop = _unique(
        _columns(tables["mv_war_main_prop"], ["SN_WAR", "WELL_ACTIVITY_CD"]),
        ["SN_WAR"],
        "war_property",
        quality,
    )
    quality["war_property_missing_main"] = int(
        (~prop["SN_WAR"].isin(main["SN_WAR"])).sum()
    )
    quality["war_missing_property"] = int((~main["SN_WAR"].isin(prop["SN_WAR"])).sum())
    war = main.merge(prop, on="SN_WAR", how="left", validate="one_to_one")
    war["WELL_ACTIVITY_CD"] = war["WELL_ACTIVITY_CD"].fillna("")
    return _enrich(war, fields, depths, "WAR_START_DT", parameters)


def _eor_frames(tables, fields, depths, parameters, quality):
    columns = [
        "SN_EOR",
        "API_WELL_NUMBER",
        "EOR_OPERATION_CD",
        "BOREHOLE_STAT_DT",
        "SUBSEA_COMPLETION_FLAG",
    ]
    eor = _unique(
        _columns(tables["mv_eor_mainquery"], columns), ["SN_EOR"], "eor", quality
    )
    eor = _enrich(eor, fields, depths, "BOREHOLE_STAT_DT", parameters)
    comp = _unique(
        _columns(
            tables["mv_eor_completions"],
            ["SN_EOR_FK", "SN_EOR_WELL_COMP", "COMP_STATUS_CD"],
        ),
        ["SN_EOR_FK", "SN_EOR_WELL_COMP"],
        "eor_completion",
        quality,
    )
    quality["eor_completion_missing_parent"] = int(
        (~comp["SN_EOR_FK"].isin(eor["SN_EOR"])).sum()
    )
    comp = comp.merge(
        eor, left_on="SN_EOR_FK", right_on="SN_EOR", how="left", validate="many_to_one"
    )
    comp["subsea_flag"] = (
        comp["SUBSEA_COMPLETION_FLAG"].replace("", UNKNOWN).fillna(UNKNOWN)
    )
    comp[["field", "water_depth_band", "era"]] = comp[
        ["field", "water_depth_band", "era"]
    ].fillna(UNKNOWN)
    return eor, comp


def analyse(tables, parameters=None):
    """Reconcile reporting grains and return JSON-compatible characterisation."""
    p = parameters or Parameters()
    _validate_tables(tables)
    quality = {}
    api = _columns(tables["mv_api_list_all"], ["API_WELL_NUMBER", "BOTM_FLD_NAME_CD"])
    bore = _columns(tables["mv_boreholes_all"], ["API_WELL_NUMBER", "WATER_DEPTH"])
    fields = _mapping(api, "BOTM_FLD_NAME_CD", quality, "conflicting_field_apis")
    depths = _mapping(
        bore, "WATER_DEPTH", quality, "conflicting_borehole_depth_apis", numeric=True
    )
    war = _war_frame(tables, fields, depths, p, quality)
    eor, eor_comp = _eor_frames(tables, fields, depths, p, quality)
    comp = _columns(
        tables["mv_api_wellcomps_all"],
        [
            "API_WELL_NUMBER",
            "COMPLETION_DATE",
            "PROD_INTERVAL_CD",
            "COMP_STATUS_CD",
            "COMP_UNIT_CODE",
            "UNIT_NUMBER",
        ],
    )
    comp = _enrich(comp, fields, depths, "COMPLETION_DATE", p)
    comp["status"] = comp["COMP_STATUS_CD"].replace("", UNKNOWN)
    for name, frame in [("war", war), ("eor", eor), ("completion", comp)]:
        quality[name + "_missing_api"] = int(frame["API_WELL_NUMBER"].eq("").sum())
        for dimension in ["year", "field", "water_depth_band"]:
            quality[name + "_unknown_" + dimension] = int(
                frame[dimension].eq(UNKNOWN).sum()
            )
    wells, well_thresholds = _well_frequencies(eor, war, p)
    fields_result, field_thresholds = _field_frequencies(wells, p)
    return _results(
        war,
        eor,
        comp,
        eor_comp,
        wells,
        fields_result,
        well_thresholds,
        field_thresholds,
        quality,
        p,
    )


def _summary_statistics(war, eor, comp, eor_comp, wells, parameters):
    records = int(eor["EOR_OPERATION_CD"].isin(parameters.workover_codes).sum())
    valid_records = int(wells["workover_records"].sum())
    return {
        "completion_records": len(comp),
        "eor_completion_records": len(eor_comp),
        "eor_records": len(eor),
        "eor_recorded_wells": len(wells),
        "workover_records": records,
        "workover_records_with_api": valid_records,
        "workover_records_per_recorded_well": (
            valid_records / len(wells) if len(wells) else None
        ),
        "war_records": len(war),
        "candidate_war_records": int(
            war["WELL_ACTIVITY_CD"].isin(parameters.candidate_codes).sum()
        ),
        "high_count_wells": int(wells["outlier"].eq("high").sum()),
        "low_count_wells": int(wells["outlier"].eq("low").sum()),
    }


def _method():
    return {
        "frequency_basis": "records per recorded API12; no exposure-time denominator",
        "completion_era_basis": "API Lookup COMPLETION_DATE",
        "eor_year_basis": "BOREHOLE_STAT_DT; not intervention event date",
        "war_year_basis": "WAR_START_DT; not an intervention start",
        "depth_basis": "unique nonnegative borehole WATER_DEPTH, in feet",
        "field_basis": "unique API Lookup BOTM_FLD_NAME_CD; ambiguous and unmatched are unknown",
        "bin_basis": "descriptive water-depth boundaries and calendar cohorts; no design criterion",
        "candidate_basis": "legacy intervention selection in lower_tertiary.ops_timeline; raw codes only",
        "outlier_basis": "strict below lower or above upper linear empirical quantile; ties excluded; flags use unrounded values; observed records only",
    }


def _limits():
    return [
        "Completion status and reported subsea flag are characterised separately; general completion design types are not supplied by these tables.",
        "API completion rows may describe production intervals or repeated historical listings; counts do not establish unique completion installations.",
        "EOR years use borehole-status dates and cannot establish workover event timing. Completion years use recorded completion dates, not spud dates.",
        "WAR rows are weekly reporting records, not separate interventions. Missing properties and unknown activity-code meanings remain explicit.",
        "Workover selection uses EOR operation code W, whose source code table labels it WORKOVER. WAR candidate selection is an interpretation, not a published WAR classification.",
        "Plug-back classification and intervention triggers are not established by the selected structured data; narrative text is not interpreted.",
        "Recorded zero workovers indicate no W reports in this archive for an observed API12, not absence of interventions over the well life. Observation exposure and well-age effects are not established.",
        "Field and depth attribution use a current snapshot; ambiguous metadata stays unknown. Historical reassignment is not reconstructed.",
        "Rates, durations, production correlations and exposure-normalised outliers wait for issue #1063. Completion-type, well-age and field correlations are not computed here.",
        "Coverage is the supplied snapshot, not a census of all operations. Calendar changes can reflect reporting coverage and cannot establish changes in engineering practice.",
    ]


def _results(
    war,
    eor,
    comp,
    eor_comp,
    wells,
    fields,
    well_thresholds,
    field_thresholds,
    quality,
    parameters,
):
    vocabulary = {
        str(x["code"]): x
        for x in load_activity_codes()["codes"]
        if x["code"] is not None
    }
    observed = sorted(set(war["WELL_ACTIVITY_CD"].replace("", UNKNOWN)))
    return {
        "summary": _summary_statistics(war, eor, comp, eor_comp, wells, parameters),
        "parameters": asdict(parameters),
        "method": _method(),
        "completion_design_types": None,
        "quality": quality,
        "completion_strata": _counts(
            comp, ["field", "water_depth_band", "era", "status"]
        ),
        "completions_by_year": _counts(comp, ["year", "status"]),
        "eor_completion_strata": _counts(
            eor_comp, ["field", "water_depth_band", "era", "subsea_flag"]
        ),
        "eor_by_year_type": _annual(eor, "EOR_OPERATION_CD"),
        "war_by_year_type": _annual(war, "WELL_ACTIVITY_CD"),
        "war_vocabulary": [
            {
                "code": c,
                "label": vocabulary.get(c, {}).get("label"),
                "provenance": vocabulary.get(c, {}).get("provenance", "unknown"),
            }
            for c in observed
        ],
        "per_well": wells.to_dict("records"),
        "war_per_well": _war_frequencies(war, parameters),
        "per_field": fields,
        "outliers": {
            "well_thresholds": well_thresholds,
            "field_thresholds": field_thresholds,
        },
        "limits": _limits(),
    }
