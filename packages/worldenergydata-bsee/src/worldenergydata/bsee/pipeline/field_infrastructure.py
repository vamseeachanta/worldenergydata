"""Field-level BSEE infrastructure joins for engineering products."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ACE_BSEE_BIN_ROOT = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin")


@dataclass(frozen=True)
class FieldInfrastructureBundle:
    """Product-ready field infrastructure data bundle."""

    context: dict[str, Any]
    structures: pd.DataFrame
    pipeline_segments: pd.DataFrame
    pipeline_locations: pd.DataFrame
    appurtenances: pd.DataFrame
    documents: pd.DataFrame
    engineering_summary: dict[str, Any]


class FieldInfrastructureError(ValueError):
    """Raised when a field infrastructure bundle cannot be built."""


def default_bsee_bin_root() -> Path:
    """Return the preferred local BSEE bin root.

    The mounted `/mnt/ace` tier is preferred because it carries the large
    downloaded BSEE binary tables. The repo-local data resolver remains the
    fallback for developer and CI environments.
    """
    if ACE_BSEE_BIN_ROOT.is_dir():
        return ACE_BSEE_BIN_ROOT
    project_candidate = Path("data/modules/bsee/bin")
    if project_candidate.is_dir():
        return project_candidate
    return project_candidate


def build_field_infrastructure_bundle(
    query: str,
    *,
    data_root: Path | str | None = None,
) -> FieldInfrastructureBundle:
    """Build engineering-ready field infrastructure joins for *query*.

    Args:
        query: Field name, field code, or lease number.
        data_root: Directory containing BSEE bin subdirectories. Defaults to
            `/mnt/ace/worldenergydata/data/modules/bsee/bin` when available.
    """
    root = Path(data_root) if data_root is not None else default_bsee_bin_root()
    deepqual = _read_table(root, "deepqual/mv_deep_water_field_leases.bin")
    if deepqual.empty:
        raise FieldInfrastructureError(f"Deepwater field table not found under {root}")

    anchor = _resolve_anchor(query, deepqual)
    context = _context_from_anchor(anchor)
    leases = set(context["leases"])
    area_blocks = _anchor_area_block_pairs(anchor)

    structures = _build_structures(root, context, leases, area_blocks)
    structures = _append_subsea_boreholes(root, structures, area_blocks)
    complex_ids = _values_as_strings(structures.get("complex_id"))
    fmp = _build_fmp_rows(root, leases, complex_ids)
    mcp = _build_mcp_rows(root, leases)

    pipeline_maps = _match_pipeline_maps(root, leases, area_blocks)
    decom_pipe = _match_pipeline_decom(root, leases, area_blocks)
    pipeline_segments = _build_pipeline_segments(pipeline_maps, decom_pipe)
    segment_numbers = set(pipeline_segments["segment_number"].dropna().astype(str))
    pipeline_locations = _match_pipeline_locations(root, segment_numbers)
    appurtenances = _build_appurtenances(pipeline_locations)

    documents = _build_documents(root, pipeline_maps, segment_numbers, leases)
    structures = _append_product_rows(structures, fmp, mcp)
    structures = _append_platform_decom(root, structures, area_blocks, complex_ids)

    summary = _engineering_summary(
        context,
        structures,
        pipeline_segments,
        pipeline_locations,
        appurtenances,
        documents,
    )

    return FieldInfrastructureBundle(
        context=context,
        structures=structures,
        pipeline_segments=pipeline_segments,
        pipeline_locations=pipeline_locations,
        appurtenances=appurtenances,
        documents=documents,
        engineering_summary=summary,
    )


def write_field_infrastructure_bundle(
    bundle: FieldInfrastructureBundle,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Write a field infrastructure bundle to product-facing files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "field_context": out / "field_context.json",
        "structures": out / "structures.csv",
        "pipeline_segments": out / "pipeline_segments.csv",
        "pipeline_locations": out / "pipeline_locations.csv",
        "appurtenances": out / "appurtenances.csv",
        "documents": out / "documents.csv",
        "engineering_summary": out / "engineering_summary.json",
    }
    paths["field_context"].write_text(
        json.dumps(bundle.context, indent=2, sort_keys=True), encoding="utf-8"
    )
    paths["engineering_summary"].write_text(
        json.dumps(bundle.engineering_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    bundle.structures.to_csv(paths["structures"], index=False)
    bundle.pipeline_segments.to_csv(paths["pipeline_segments"], index=False)
    bundle.pipeline_locations.to_csv(paths["pipeline_locations"], index=False)
    bundle.appurtenances.to_csv(paths["appurtenances"], index=False)
    bundle.documents.to_csv(paths["documents"], index=False)
    return paths


def _read_table(root: Path, rel: str) -> pd.DataFrame:
    path = root / rel
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_pickle(path)
    except Exception as exc:  # noqa: BLE001
        raise FieldInfrastructureError(f"Cannot read {path}: {exc}") from exc


def _norm(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _norm_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def _block_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64").astype("string")


def _resolve_anchor(query: str, deepqual: pd.DataFrame) -> pd.DataFrame:
    q = query.strip()
    q_upper = q.upper()
    masks: list[pd.Series] = []
    if "FIELD_NAME_CODE" in deepqual.columns:
        masks.append(_norm_series(deepqual["FIELD_NAME_CODE"]).str.upper().eq(q_upper))
    if "FLD_NICK_NAME" in deepqual.columns:
        masks.append(_norm_series(deepqual["FLD_NICK_NAME"]).str.upper().eq(q_upper))
    if "LEASE_NUMBER" in deepqual.columns:
        masks.append(_norm_series(deepqual["LEASE_NUMBER"]).str.upper().eq(q_upper))
    if "FLD_NICK_NAME" in deepqual.columns:
        masks.append(_norm_series(deepqual["FLD_NICK_NAME"]).str.upper().str.contains(q_upper, regex=False))
    if not masks:
        raise FieldInfrastructureError("Deepwater field table has no usable query columns")
    mask = masks[0].copy()
    for item in masks[1:]:
        mask |= item
    anchor = deepqual[mask].copy()
    if anchor.empty:
        raise FieldInfrastructureError(f"Cannot resolve field query: {query}")
    if "FIELD_NAME_CODE" in anchor.columns:
        field_code = _norm(anchor.iloc[0]["FIELD_NAME_CODE"])
        anchor = deepqual[_norm_series(deepqual["FIELD_NAME_CODE"]).eq(field_code)].copy()
    return anchor.reset_index(drop=True)


def _context_from_anchor(anchor: pd.DataFrame) -> dict[str, Any]:
    row = anchor.iloc[0]
    field_name = _norm(row.get("FLD_NICK_NAME", row.get("FIELD_NAME_CODE", "")))
    field_code = _norm(row.get("FIELD_NAME_CODE", field_name))
    leases = sorted(_norm_series(anchor["LEASE_NUMBER"]).replace("", pd.NA).dropna().unique())
    area_blocks = [f"{a} {b}" for a, b in _anchor_area_block_pairs(anchor)]
    water_depth = None
    if "FLD_AVG_WTR_DPTH" in anchor.columns:
        depths = pd.to_numeric(anchor["FLD_AVG_WTR_DPTH"], errors="coerce").dropna()
        if not depths.empty:
            water_depth = float(depths.iloc[0])
    operators = []
    if "BUS_ASC_NAME" in anchor.columns:
        operators = sorted(_norm_series(anchor["BUS_ASC_NAME"]).replace("", pd.NA).dropna().unique())
    return {
        "field_name": field_name,
        "field_code": field_code,
        "leases": leases,
        "area_blocks": area_blocks,
        "operator_names": operators,
        "average_water_depth_ft": water_depth,
        "source_table": "deepqual/mv_deep_water_field_leases.bin",
    }


def _anchor_area_block_pairs(anchor: pd.DataFrame) -> list[tuple[str, str]]:
    if "AREA_CODE" not in anchor.columns or "BLOCK_NUMBER" not in anchor.columns:
        return []
    pairs = sorted(
        {
            (_norm(area), _norm(block))
            for area, block in zip(anchor["AREA_CODE"], anchor["BLOCK_NUMBER"], strict=False)
            if _norm(area) and _norm(block)
        }
    )
    return pairs


def _match_lease(df: pd.DataFrame, cols: list[str], leases: set[str]) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for col in cols:
        if col in df.columns:
            mask |= _norm_series(df[col]).isin(leases)
    return mask


def _match_area_block(
    df: pd.DataFrame,
    area_cols: list[str],
    block_cols: list[str],
    pairs: list[tuple[str, str]],
) -> pd.Series:
    pair_set = {(area, str(int(float(block)))) for area, block in pairs if block}
    mask = pd.Series(False, index=df.index)
    for area_col in area_cols:
        for block_col in block_cols:
            if area_col not in df.columns or block_col not in df.columns:
                continue
            keys = zip(_norm_series(df[area_col]), _block_series(df[block_col]), strict=False)
            mask |= pd.Series([key in pair_set for key in keys], index=df.index)
    return mask


def _build_structures(
    root: Path,
    context: dict[str, Any],
    leases: set[str],
    area_blocks: list[tuple[str, str]],
) -> pd.DataFrame:
    df = _read_table(root, "platstruc/mv_platstruc_structures.bin")
    if df.empty:
        return _structure_frame()
    mask = pd.Series(False, index=df.index)
    if "FIELD_NAME_CODE" in df.columns:
        mask |= _norm_series(df["FIELD_NAME_CODE"]).eq(context["field_code"])
    mask |= _match_lease(df, ["LEASE_NUMBER"], leases)
    mask |= _match_area_block(df, ["AREA_CODE"], ["BLOCK_NUMBER"], area_blocks)
    rows = []
    for _, row in df[mask].iterrows():
        rows.append(
            {
                "asset_type": "platform_structure",
                "structure_name": _norm(row.get("STRUCTURE_NAME")),
                "structure_type": _norm(row.get("STRUC_TYPE_CODE")),
                "operator_name": _norm(row.get("BUS_ASC_NAME")),
                "area_code": _norm(row.get("AREA_CODE")),
                "block_number": _norm(row.get("BLOCK_NUMBER")),
                "lease_number": _norm(row.get("LEASE_NUMBER")),
                "complex_id": _norm(row.get("COMPLEX_ID_NUM")),
                "structure_number": _norm(row.get("STRUCTURE_NUMBER")),
                "water_depth_ft": _norm(row.get("WATER_DEPTH")),
                "latitude": _norm(row.get("LATITUDE")),
                "longitude": _norm(row.get("LONGITUDE")),
                "source_table": "platstruc/mv_platstruc_structures.bin",
                "join_key": "field_code|lease|area_block",
                "evidence_confidence": "direct",
            }
        )
    return pd.DataFrame(rows, columns=_structure_columns())


def _append_product_rows(
    structures: pd.DataFrame, fmp: pd.DataFrame, mcp: pd.DataFrame
) -> pd.DataFrame:
    frames = [structures]
    if not fmp.empty:
        frames.append(fmp)
    if not mcp.empty:
        frames.append(mcp)
    return pd.concat(frames, ignore_index=True) if frames else _structure_frame()


def _append_subsea_boreholes(
    root: Path,
    structures: pd.DataFrame,
    area_blocks: list[tuple[str, str]],
) -> pd.DataFrame:
    df = _read_table(root, "permstruc/mv_subsea_boreholes.bin")
    if df.empty:
        return structures
    matched = df[_match_area_block(df, ["AREA_CODE"], ["BLOCK_NUMBER"], area_blocks)]
    rows = []
    for _, row in matched.iterrows():
        rows.append(
            {
                "asset_type": "subsea_borehole",
                "structure_name": _norm(row.get("WELL_NAME")),
                "structure_type": "subsea_borehole",
                "operator_name": _norm(row.get("BUS_ASC_NAME")),
                "area_code": _norm(row.get("AREA_CODE")),
                "block_number": _norm(row.get("BLOCK_NUMBER")),
                "lease_number": "",
                "complex_id": "",
                "structure_number": _norm(row.get("WELL_NAME")),
                "water_depth_ft": _norm(row.get("WATER_DEPTH")),
                "latitude": "",
                "longitude": "",
                "source_table": "permstruc/mv_subsea_boreholes.bin",
                "join_key": "area_block",
                "evidence_confidence": "direct",
            }
        )
    if not rows:
        return structures
    return pd.concat(
        [structures, pd.DataFrame(rows, columns=_structure_columns())],
        ignore_index=True,
    )


def _build_fmp_rows(root: Path, leases: set[str], complex_ids: set[str]) -> pd.DataFrame:
    fmp_list = _read_table(root, "fmp/mv_fmplist_all.bin")
    fmp_locations = _read_table(root, "fmp/mv_fmp_meas_locations_all.bin")
    if fmp_list.empty or fmp_locations.empty:
        return _structure_frame()
    linked = fmp_list[_match_lease(fmp_list, ["LEASE_NUMBER"], leases)]
    meas_ids = set(_norm_series(linked["SN_MEAS_LOC_FK"])) if "SN_MEAS_LOC_FK" in linked else set()
    mask = pd.Series(False, index=fmp_locations.index)
    if "SN_MEAS_LOC" in fmp_locations.columns:
        mask |= _norm_series(fmp_locations["SN_MEAS_LOC"]).isin(meas_ids)
    if complex_ids and "COMPLEX_ID_NUM" in fmp_locations.columns:
        mask |= _norm_series(fmp_locations["COMPLEX_ID_NUM"]).isin(complex_ids)
    rows = []
    for _, row in fmp_locations[mask].iterrows():
        rows.append(
            {
                "asset_type": "fmp_measurement_location",
                "structure_name": _norm(row.get("FMP_NAME")) or _norm(row.get("FMP_LOC_NAME")),
                "structure_type": _norm(row.get("FMP_MEAS_TYP_CD")),
                "operator_name": _norm(row.get("BUS_ASC_NAME")),
                "area_code": _norm(row.get("AREA_CODE")),
                "block_number": _norm(row.get("BLOCK_NUMBER")),
                "lease_number": "",
                "complex_id": _norm(row.get("COMPLEX_ID_NUM")),
                "structure_number": _norm(row.get("SN_MEAS_LOC")),
                "water_depth_ft": "",
                "latitude": "",
                "longitude": "",
                "source_table": "fmp/mv_fmp_meas_locations_all.bin",
                "join_key": "lease|complex_id",
                "evidence_confidence": "direct",
            }
        )
    return pd.DataFrame(rows, columns=_structure_columns())


def _build_mcp_rows(root: Path, leases: set[str]) -> pd.DataFrame:
    lease_units = _read_table(root, "mcpflow/mv_mcpflowleaseunits.bin")
    systems = _read_table(root, "mcpflow/mv_mcpflowsystems.bin")
    if lease_units.empty or systems.empty:
        return _structure_frame()
    linked = lease_units[_match_lease(lease_units, ["LEASE_UNIT"], leases)]
    system_ids = set(_norm_series(linked["COMGL_SYS_NUM"])) if "COMGL_SYS_NUM" in linked else set()
    matched = systems[_norm_series(systems["COMGL_SYS_NUM"]).isin(system_ids)]
    rows = []
    for _, row in matched.iterrows():
        rows.append(
            {
                "asset_type": "commingling_flow_system",
                "structure_name": _norm(row.get("COMGL_SYS_NAME")),
                "structure_type": _norm(row.get("COMGL_SYS_TYP_CD")),
                "operator_name": _norm(row.get("SORT_NAME")),
                "area_code": _norm(row.get("COMGL_SYS_LOC")),
                "block_number": "",
                "lease_number": "",
                "complex_id": _norm(row.get("COMGL_SYS_NUM")),
                "structure_number": _norm(row.get("COMGL_SYS_NUM")),
                "water_depth_ft": "",
                "latitude": "",
                "longitude": "",
                "source_table": "mcpflow/mv_mcpflowsystems.bin",
                "join_key": "lease_unit",
                "evidence_confidence": "direct",
            }
        )
    return pd.DataFrame(rows, columns=_structure_columns())


def _match_pipeline_maps(
    root: Path, leases: set[str], area_blocks: list[tuple[str, str]]
) -> pd.DataFrame:
    df = _read_table(root, "scanneddocs/scan_pipeline_maps.bin")
    if df.empty:
        return pd.DataFrame()
    mask = _match_lease(df, ["ORIG_LEASE_NUMBER", "DEST_LEASE_NUMBER"], leases)
    mask |= _match_area_block(
        df,
        ["ORIG_AREA_CODE", "DEST_AREA_CODE"],
        ["ORIG_BLOCK_NUMBER", "DEST_BLOCK_NUMBER"],
        area_blocks,
    )
    return df[mask].copy()


def _match_pipeline_decom(
    root: Path, leases: set[str], area_blocks: list[tuple[str, str]]
) -> pd.DataFrame:
    frames = []
    for rel, status in (
        ("decomcost/mv_decom_cost_inst_pipe.bin", "installed"),
        ("decomcost/mv_decom_cost_prop_pipe.bin", "proposed"),
    ):
        df = _read_table(root, rel)
        if df.empty:
            continue
        mask = _match_lease(df, ["ORIG_LSE_NUM", "DEST_LSE_NUM", "AUTH_NUMBER"], leases)
        mask |= _match_area_block(
            df,
            ["ORIG_AR_CODE", "DEST_AR_CODE"],
            ["ORIG_BLK_NUM", "DEST_BLK_NUM"],
            area_blocks,
        )
        matched = df[mask].copy()
        matched["SOURCE_STATUS"] = status
        matched["SOURCE_TABLE"] = rel
        frames.append(matched)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _build_pipeline_segments(
    pipeline_maps: pd.DataFrame, decom_pipe: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for _, row in pipeline_maps.iterrows():
        rows.append(
            {
                "segment_number": _norm(row.get("SEGMENT_NUMBER")),
                "origin_lease": _norm(row.get("ORIG_LEASE_NUMBER")),
                "origin_area": _norm(row.get("ORIG_AREA_CODE")),
                "origin_block": _norm(row.get("ORIG_BLOCK_NUMBER")),
                "origin_name": "",
                "destination_lease": _norm(row.get("DEST_LEASE_NUMBER")),
                "destination_area": _norm(row.get("DEST_AREA_CODE")),
                "destination_block": _norm(row.get("DEST_BLOCK_NUMBER")),
                "destination_name": "",
                "product_code": "",
                "pipeline_size_code": _norm(row.get("PPL_SIZE_CODE")),
                "status": _norm(row.get("DOC_TYPE")),
                "source_table": "scanneddocs/scan_pipeline_maps.bin",
                "join_key": "lease|area_block",
                "evidence_confidence": "document_index",
            }
        )
    for _, row in decom_pipe.iterrows():
        rows.append(
            {
                "segment_number": _norm(row.get("SEGMENT_NUM")),
                "origin_lease": _norm(row.get("ORIG_LSE_NUM")),
                "origin_area": _norm(row.get("ORIG_AR_CODE")),
                "origin_block": _norm(row.get("ORIG_BLK_NUM")),
                "origin_name": _norm(row.get("ORIG_ID_NAME")),
                "destination_lease": _norm(row.get("DEST_LSE_NUM")),
                "destination_area": _norm(row.get("DEST_AR_CODE")),
                "destination_block": _norm(row.get("DEST_BLK_NUM")),
                "destination_name": _norm(row.get("DEST_ID_NAME")),
                "product_code": _norm(row.get("PROD_CODE")),
                "pipeline_size_code": _norm(row.get("PPL_SIZE_CODE")),
                "status": _norm(row.get("STATUS_CODE")) or _norm(row.get("SOURCE_STATUS")),
                "source_table": _norm(row.get("SOURCE_TABLE")),
                "join_key": "lease|area_block",
                "evidence_confidence": "inferred",
            }
        )
    if not rows:
        return pd.DataFrame(columns=_pipeline_segment_columns())
    frame = pd.DataFrame(rows, columns=_pipeline_segment_columns())
    return frame.drop_duplicates().reset_index(drop=True)


def _match_pipeline_locations(root: Path, segment_numbers: set[str]) -> pd.DataFrame:
    df = _read_table(root, "pipeloc/mv_pipelinelocation.bin")
    if df.empty or not segment_numbers:
        return pd.DataFrame(columns=_pipeline_location_columns())
    matched = df[_norm_series(df["SEGMENT_NUM"]).isin(segment_numbers)].copy()
    rows = []
    for _, row in matched.iterrows():
        rows.append(
            {
                "segment_number": _norm(row.get("SEGMENT_NUM")),
                "asbuilt_sequence": _norm(row.get("ASBUILT_SEQ_NUM")),
                "latitude": _norm(row.get("LATITUDE")),
                "longitude": _norm(row.get("LONGITUDE")),
                "nad_year": _norm(row.get("NAD_YEAR_CD")),
                "project_code": _norm(row.get("PROJ_CODE")),
                "appurtenance_type": _norm(row.get("PPL_APURT_TYPE")),
                "source_table": "pipeloc/mv_pipelinelocation.bin",
                "join_key": "segment_number",
                "evidence_confidence": "direct",
            }
        )
    return pd.DataFrame(rows, columns=_pipeline_location_columns())


def _build_appurtenances(pipeline_locations: pd.DataFrame) -> pd.DataFrame:
    if pipeline_locations.empty:
        return pd.DataFrame(columns=_appurtenance_columns())
    rows = []
    for _, row in pipeline_locations.iterrows():
        app_type = _norm(row.get("appurtenance_type"))
        if not app_type:
            continue
        rows.append(
            {
                "segment_number": _norm(row.get("segment_number")),
                "asbuilt_sequence": _norm(row.get("asbuilt_sequence")),
                "appurtenance_type": app_type,
                "latitude": _norm(row.get("latitude")),
                "longitude": _norm(row.get("longitude")),
                "source_table": _norm(row.get("source_table")),
                "join_key": "segment_number",
                "evidence_confidence": "direct",
            }
        )
    return pd.DataFrame(rows, columns=_appurtenance_columns())


def _build_documents(
    root: Path,
    pipeline_maps: pd.DataFrame,
    segment_numbers: set[str],
    leases: set[str],
) -> pd.DataFrame:
    rows = []
    for _, row in pipeline_maps.iterrows():
        rows.append(
            {
                "document_family": "pipeline_map",
                "document_id": _norm(row.get("DOC_ID")),
                "segment_number": _norm(row.get("SEGMENT_NUMBER")),
                "lease_number": "",
                "row_number": "",
                "control_number": "",
                "document_type": _norm(row.get("DOC_TYPE")),
                "document_date": _norm(row.get("DOC_DATE")),
                "source_table": "scanneddocs/scan_pipeline_maps.bin",
                "join_key": "lease|area_block",
                "evidence_confidence": "document_index",
            }
        )
    scan_row = _read_table(root, "scanneddocs/scan_row.bin")
    if not scan_row.empty and segment_numbers:
        matched = scan_row[_norm_series(scan_row["SEGMENT_NUMBER"]).isin(segment_numbers)]
        for _, row in matched.iterrows():
            rows.append(
                {
                    "document_family": "row",
                    "document_id": _norm(row.get("DOC_ID")),
                    "segment_number": _norm(row.get("SEGMENT_NUMBER")),
                    "lease_number": "",
                    "row_number": _norm(row.get("ROW_NUMBER")),
                    "control_number": "",
                    "document_type": _norm(row.get("DOC_TYPE")),
                    "document_date": _norm(row.get("DOC_DATE")),
                    "source_table": "scanneddocs/scan_row.bin",
                    "join_key": "segment_number",
                    "evidence_confidence": "document_index",
                }
            )
    plans = _read_table(root, "scanneddocs/scan_plans.bin")
    if not plans.empty:
        matched = plans[_match_lease(plans, ["LEASE_NUMBER"], leases)]
        for _, row in matched.iterrows():
            rows.append(
                {
                    "document_family": "plan",
                    "document_id": _norm(row.get("DOC_ID")),
                    "segment_number": "",
                    "lease_number": _norm(row.get("LEASE_NUMBER")),
                    "row_number": "",
                    "control_number": _norm(row.get("CONTROL_NUMBER")),
                    "document_type": _norm(row.get("DOC_TYPE")),
                    "document_date": _norm(row.get("DATE_RECEIVED")),
                    "source_table": "scanneddocs/scan_plans.bin",
                    "join_key": "lease",
                    "evidence_confidence": "document_index",
                }
            )
    return pd.DataFrame(rows, columns=_document_columns()).drop_duplicates().reset_index(drop=True)


def _append_platform_decom(
    root: Path,
    structures: pd.DataFrame,
    area_blocks: list[tuple[str, str]],
    complex_ids: set[str],
) -> pd.DataFrame:
    rows = []
    for rel, status in (
        ("decomcost/mv_decom_cost_inst_plat.bin", "installed"),
        ("decomcost/mv_decom_cost_prop_plat.bin", "proposed"),
    ):
        df = _read_table(root, rel)
        if df.empty:
            continue
        mask = _match_area_block(df, ["AREA_CODE"], ["BLOCK_NUMBER"], area_blocks)
        if complex_ids and "COMPLEX_ID_NUM" in df.columns:
            mask |= _norm_series(df["COMPLEX_ID_NUM"]).isin(complex_ids)
        for _, row in df[mask].iterrows():
            rows.append(
                {
                    "asset_type": f"platform_decom_{status}",
                    "structure_name": _norm(row.get("STRUCTURE_NAME")),
                    "structure_type": "decom",
                    "operator_name": "",
                    "area_code": _norm(row.get("AREA_CODE")),
                    "block_number": _norm(row.get("BLOCK_NUMBER")),
                    "lease_number": "",
                    "complex_id": _norm(row.get("COMPLEX_ID_NUM")),
                    "structure_number": _norm(row.get("STRUCTURE_NUMBER")),
                    "water_depth_ft": "",
                    "latitude": "",
                    "longitude": "",
                    "source_table": rel,
                    "join_key": "area_block|complex_id",
                    "evidence_confidence": "inferred",
                }
            )
    if not rows:
        return structures
    return pd.concat([structures, pd.DataFrame(rows, columns=_structure_columns())], ignore_index=True)


def _engineering_summary(
    context: dict[str, Any],
    structures: pd.DataFrame,
    pipeline_segments: pd.DataFrame,
    pipeline_locations: pd.DataFrame,
    appurtenances: pd.DataFrame,
    documents: pd.DataFrame,
) -> dict[str, Any]:
    appurtenance_types = []
    if not appurtenances.empty:
        appurtenance_types = sorted(_norm_series(appurtenances["appurtenance_type"]).unique())
    latitudes = pd.to_numeric(pipeline_locations.get("latitude"), errors="coerce")
    longitudes = pd.to_numeric(pipeline_locations.get("longitude"), errors="coerce")
    route_bounds = None
    if not latitudes.dropna().empty and not longitudes.dropna().empty:
        route_bounds = {
            "latitude_min": float(latitudes.min()),
            "latitude_max": float(latitudes.max()),
            "longitude_min": float(longitudes.min()),
            "longitude_max": float(longitudes.max()),
        }
    return {
        "field_name": context["field_name"],
        "field_code": context["field_code"],
        "lease_count": len(context["leases"]),
        "structure_count": int((structures["asset_type"] == "platform_structure").sum()) if "asset_type" in structures else 0,
        "infrastructure_record_count": len(structures),
        "pipeline_segment_count": pipeline_segments["segment_number"].nunique() if not pipeline_segments.empty else 0,
        "pipeline_location_row_count": len(pipeline_locations),
        "appurtenance_count": len(appurtenances),
        "appurtenance_types": appurtenance_types,
        "document_count": len(documents),
        "route_bounds": route_bounds,
        "product_contract_version": "field-infrastructure-bundle-v1",
    }


def _values_as_strings(series: pd.Series | None) -> set[str]:
    if series is None:
        return set()
    return set(_norm_series(series).replace("", pd.NA).dropna().unique())


def _structure_columns() -> list[str]:
    return [
        "asset_type",
        "structure_name",
        "structure_type",
        "operator_name",
        "area_code",
        "block_number",
        "lease_number",
        "complex_id",
        "structure_number",
        "water_depth_ft",
        "latitude",
        "longitude",
        "source_table",
        "join_key",
        "evidence_confidence",
    ]


def _structure_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=_structure_columns())


def _pipeline_segment_columns() -> list[str]:
    return [
        "segment_number",
        "origin_lease",
        "origin_area",
        "origin_block",
        "origin_name",
        "destination_lease",
        "destination_area",
        "destination_block",
        "destination_name",
        "product_code",
        "pipeline_size_code",
        "status",
        "source_table",
        "join_key",
        "evidence_confidence",
    ]


def _pipeline_location_columns() -> list[str]:
    return [
        "segment_number",
        "asbuilt_sequence",
        "latitude",
        "longitude",
        "nad_year",
        "project_code",
        "appurtenance_type",
        "source_table",
        "join_key",
        "evidence_confidence",
    ]


def _appurtenance_columns() -> list[str]:
    return [
        "segment_number",
        "asbuilt_sequence",
        "appurtenance_type",
        "latitude",
        "longitude",
        "source_table",
        "join_key",
        "evidence_confidence",
    ]


def _document_columns() -> list[str]:
    return [
        "document_family",
        "document_id",
        "segment_number",
        "lease_number",
        "row_number",
        "control_number",
        "document_type",
        "document_date",
        "source_table",
        "join_key",
        "evidence_confidence",
    ]
