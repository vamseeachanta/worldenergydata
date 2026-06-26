"""Tests for BSEE field infrastructure bundle generation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _write_pickle(root: Path, rel: str, df: pd.DataFrame) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)


def _fixture_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "bsee" / "bin"

    _write_pickle(
        root,
        "deepqual/mv_deep_water_field_leases.bin",
        pd.DataFrame(
            {
                "FLD_NICK_NAME": ["Test Field", "Test Field"],
                "FIELD_NAME_CODE": ["TF001", "TF001"],
                "LEASE_NUMBER": ["G10001", "G10002"],
                "AREA_CODE": ["WR", "WR"],
                "BLOCK_NUMBER": [100, 101],
                "FLD_AVG_WTR_DPTH": [7000, 7000],
                "BUS_ASC_NAME": ["Test Operator", "Test Operator"],
                "FIRST_PROD_DATE": ["1/1/2020", "1/1/2020"],
            }
        ),
    )
    _write_pickle(
        root,
        "platstruc/mv_platstruc_structures.bin",
        pd.DataFrame(
            {
                "AREA_CODE": ["WR", "WR"],
                "BLOCK_NUMBER": [102, 999],
                "FIELD_NAME_CODE": ["TF001", "OTHER"],
                "STRUCTURE_NAME": ["A Test FPSO", "Other Platform"],
                "STRUCTURE_NUMBER": [1, 1],
                "STRUC_TYPE_CODE": ["FPSO", "FIXED"],
                "BUS_ASC_NAME": ["Test Operator", "Other Operator"],
                "COMPLEX_ID_NUM": [2500, 9999],
                "LEASE_NUMBER": ["G10003", "G99999"],
                "WATER_DEPTH": [7050, 100],
                "LATITUDE": [26.1, 27.0],
                "LONGITUDE": [-91.1, -90.0],
            }
        ),
    )
    _write_pickle(
        root,
        "permstruc/mv_subsea_boreholes.bin",
        pd.DataFrame(
            {
                "BUS_ASC_NAME": ["Test Operator", "Other Operator"],
                "AREA_CODE": ["WR", "WR"],
                "BLOCK_NUMBER": [100, 999],
                "WELL_NAME": ["SN001", "OTHER"],
                "WATER_DEPTH": [7020, 100],
            }
        ),
    )
    _write_pickle(
        root,
        "fmp/mv_fmp_meas_locations_all.bin",
        pd.DataFrame(
            {
                "SN_MEAS_LOC": [10, 20],
                "FMP_NUMBER": ["FMP-10", "FMP-20"],
                "FMP_NAME": ["Test FPSO Meter", "Other Meter"],
                "COMPLEX_ID_NUM": [2500, 9999],
                "AREA_CODE": ["WR", "WR"],
                "BLOCK_NUMBER": [102, 999],
                "FMP_LOC_NAME": ["WR 102 A", "Other"],
                "FMP_MEAS_TYP_CD": ["ACT", "GAS"],
                "BUS_ASC_NAME": ["Test Operator", "Other Operator"],
            }
        ),
    )
    _write_pickle(
        root,
        "fmp/mv_fmplist_all.bin",
        pd.DataFrame(
            {
                "SN_MEAS_LOC_FK": [10, 20],
                "LEASE_NUMBER": ["G10001", "G99999"],
                "UNIT_AGT_NUMBER": [123, 999],
                "UNIT_ALOC_SUFFIX": ["0", "0"],
                "REGION_CODE": ["G", "G"],
            }
        ),
    )
    _write_pickle(
        root,
        "mcpflow/mv_mcpflowleaseunits.bin",
        pd.DataFrame(
            {
                "LEASE_UNIT": ["G10001", "G99999"],
                "SN_MEAS_LOC_FK": [10, 20],
                "COMGL_SYS_NUM": ["SYS1", "SYS9"],
            }
        ),
    )
    _write_pickle(
        root,
        "mcpflow/mv_mcpflowareablock.bin",
        pd.DataFrame(
            {
                "AREA_CODE": ["WR", "WR"],
                "BLOCK_NUMBER": [100, 999],
                "LEASE_NUMBER": ["G10001", "G99999"],
                "BID_SYSTEM_CODE": ["RS9", "RS9"],
            }
        ),
    )
    _write_pickle(
        root,
        "mcpflow/mv_mcpflowsystems.bin",
        pd.DataFrame(
            {
                "COMGL_SYS_NUM": ["SYS1", "SYS9"],
                "COMGL_SYS_TYP_CD": ["M", "M"],
                "COMGL_SYS_NAME": ["Test Flow System", "Other System"],
                "COMGL_SYS_LOC": ["WR", "WR"],
                "COMGL_SYS_OPER": [123, 999],
                "SORT_NAME": ["Test Operator", "Other Operator"],
            }
        ),
    )
    _write_pickle(
        root,
        "scanneddocs/scan_pipeline_maps.bin",
        pd.DataFrame(
            {
                "DOC_ID": [501, 999],
                "SEGMENT_NUMBER": [7001, 9999],
                "ORIG_AREA_CODE": ["WR", "WR"],
                "ORIG_BLOCK_NUMBER": [100, 999],
                "ORIG_LEASE_NUMBER": ["G10001", "G99999"],
                "DEST_AREA_CODE": ["WR", "WR"],
                "DEST_BLOCK_NUMBER": [102, 999],
                "DEST_LEASE_NUMBER": ["G10003", "G99999"],
                "PPL_SIZE_CODE": ["08", "04"],
                "DOC_TYPE": ["As-built", "Other"],
                "DOC_DATE": ["1/1/2021", "1/1/2000"],
            }
        ),
    )
    _write_pickle(
        root,
        "scanneddocs/scan_row.bin",
        pd.DataFrame(
            {
                "DOC_ID": [601, 999],
                "ROW_NUMBER": ["ROW-1", "ROW-X"],
                "SEGMENT_NUMBER": [7001, 9999],
                "DOC_TYPE": ["ROW", "ROW"],
                "DOC_NOTES": ["Test ROW", "Other ROW"],
                "DOC_DATE": ["2/1/2021", "1/1/2000"],
            }
        ),
    )
    _write_pickle(
        root,
        "scanneddocs/scan_plans.bin",
        pd.DataFrame(
            {
                "DOC_ID": [701, 999],
                "LEASE_NUMBER": ["G10001", "G99999"],
                "AREA_BLOCK": ["WR 100", "WR 999"],
                "CONTROL_NUMBER": ["N-1", "N-X"],
                "DOC_TYPE": ["DOCD", "EP"],
                "DATE_RECEIVED": ["3/1/2021", "1/1/2000"],
            }
        ),
    )
    _write_pickle(
        root,
        "decomcost/mv_decom_cost_inst_pipe.bin",
        pd.DataFrame(
            {
                "SEGMENT_NUM": [7002, 9999],
                "ORIG_LSE_NUM": ["G10001", "G99999"],
                "ORIG_AR_CODE": ["WR", "WR"],
                "ORIG_BLK_NUM": [100, 999],
                "ORIG_ID_NAME": ["Test Well", "Other"],
                "DEST_LSE_NUM": ["G10001", "G99999"],
                "DEST_AR_CODE": ["WR", "WR"],
                "DEST_BLK_NUM": [100, 999],
                "DEST_ID_NAME": ["Test Manifold", "Other"],
                "PROD_CODE": ["BLKO", "GAS"],
                "PPL_SIZE_CODE": ["06", "04"],
                "STATUS_CODE": ["ACT", "ACT"],
            }
        ),
    )
    _write_pickle(
        root,
        "decomcost/mv_decom_cost_prop_pipe.bin",
        pd.DataFrame(
            columns=[
                "SEGMENT_NUM",
                "ORIG_LSE_NUM",
                "ORIG_AR_CODE",
                "ORIG_BLK_NUM",
                "ORIG_ID_NAME",
                "DEST_LSE_NUM",
                "DEST_AR_CODE",
                "DEST_BLK_NUM",
                "DEST_ID_NAME",
                "PROD_CODE",
                "PPL_SIZE_CODE",
                "STATUS_CODE",
            ]
        ),
    )
    _write_pickle(
        root,
        "pipeloc/mv_pipelinelocation.bin",
        pd.DataFrame(
            {
                "SEGMENT_NUM": [7001, 7001, 7002, 9999],
                "ASBUILT_SEQ_NUM": [1, 2, 1, 1],
                "LATITUDE": [26.10, 26.11, 26.12, 27.00],
                "LONGITUDE": [-91.10, -91.11, -91.12, -90.00],
                "NAD_YEAR_CD": [27, 27, 27, 27],
                "PROJ_CODE": ["G", "G", "G", "G"],
                "PPL_APURT_TYPE": ["RISER", "PIPELINE SLED", "SUBSEA MANIFOLD", ""],
            }
        ),
    )
    _write_pickle(
        root,
        "decomcost/mv_decom_cost_inst_plat.bin",
        pd.DataFrame(
            {
                "COMPLEX_ID_NUM": [2500, 9999],
                "STRUCTURE_NUMBER": [1, 1],
                "AREA_CODE": ["WR", "WR"],
                "BLOCK_NUMBER": [102, 999],
                "STRUCTURE_NAME": ["A Test FPSO", "Other Platform"],
                "EFFECTIVE_DATE": ["4/1/2021", "1/1/2000"],
            }
        ),
    )
    _write_pickle(
        root,
        "decomcost/mv_decom_cost_prop_plat.bin",
        pd.DataFrame(
            columns=[
                "COMPLEX_ID_NUM",
                "STRUCTURE_NUMBER",
                "AREA_CODE",
                "BLOCK_NUMBER",
                "STRUCTURE_NAME",
                "EFFECTIVE_DATE",
            ]
        ),
    )
    return root


def test_build_bundle_exports_product_ready_field_infrastructure(tmp_path: Path):
    from worldenergydata.bsee.pipeline.field_infrastructure import (
        build_field_infrastructure_bundle,
        write_field_infrastructure_bundle,
    )

    data_root = _fixture_data_root(tmp_path)
    bundle = build_field_infrastructure_bundle("Test Field", data_root=data_root)

    assert bundle.context["field_name"] == "Test Field"
    assert bundle.context["field_code"] == "TF001"
    assert bundle.context["leases"] == ["G10001", "G10002"]
    assert bundle.context["area_blocks"] == ["WR 100", "WR 101"]

    platform_rows = bundle.structures[
        bundle.structures["asset_type"] == "platform_structure"
    ]
    assert platform_rows["structure_name"].tolist() == ["A Test FPSO"]
    assert set(bundle.structures["asset_type"]) == {
        "platform_structure",
        "subsea_borehole",
        "fmp_measurement_location",
        "commingling_flow_system",
        "platform_decom_installed",
    }
    assert set(bundle.pipeline_segments["segment_number"].astype(int)) == {7001, 7002}
    assert set(bundle.pipeline_locations["segment_number"].astype(int)) == {7001, 7002}
    assert set(bundle.appurtenances["appurtenance_type"]) == {
        "RISER",
        "PIPELINE SLED",
        "SUBSEA MANIFOLD",
    }
    assert set(bundle.documents["document_family"]) == {
        "pipeline_map",
        "row",
        "plan",
    }

    summary = bundle.engineering_summary
    assert summary["field_name"] == "Test Field"
    assert summary["structure_count"] == 1
    assert summary["infrastructure_record_count"] == 5
    assert summary["pipeline_segment_count"] == 2
    assert summary["pipeline_location_row_count"] == 3
    assert summary["appurtenance_types"] == [
        "PIPELINE SLED",
        "RISER",
        "SUBSEA MANIFOLD",
    ]
    assert summary["document_count"] == 3

    out_dir = tmp_path / "bundle"
    paths = write_field_infrastructure_bundle(bundle, out_dir)

    assert set(paths) == {
        "field_context",
        "structures",
        "pipeline_segments",
        "pipeline_locations",
        "appurtenances",
        "documents",
        "engineering_summary",
    }
    assert (
        json.loads((out_dir / "engineering_summary.json").read_text())[
            "pipeline_segment_count"
        ]
        == 2
    )
    assert pd.read_csv(out_dir / "appurtenances.csv")["appurtenance_type"].tolist() == [
        "RISER",
        "PIPELINE SLED",
        "SUBSEA MANIFOLD",
    ]
