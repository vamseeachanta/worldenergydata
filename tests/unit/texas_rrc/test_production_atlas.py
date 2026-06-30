"""Tests for Texas RRC production field atlas generation."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner


def _write_pdq_zip(
    path: Path,
    csv_text: str,
    *,
    member_name: str = "PDQ_DSV.csv",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member_name, csv_text)


def _pdq_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_LEASE_NO": "2001",
                "OG_LEASE_NAME": "MIDLAND UNIT",
                "OG_OPER_NO": "300001",
                "OG_OPER_NAME": "ALPHA ENERGY",
                "OG_CYCLE": "202301",
                "OG_OIL_PROD": "100",
                "OG_GAS_PROD": "1000",
                "OG_COND_PROD": "5",
                "OG_WATER_PROD": "20",
                "OG_WELL_CNT": "2",
            },
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_LEASE_NO": "2002",
                "OG_LEASE_NAME": "MIDLAND EAST",
                "OG_OPER_NO": "300002",
                "OG_OPER_NAME": "BETA ENERGY",
                "OG_CYCLE": "202302",
                "OG_OIL_PROD": "200",
                "OG_GAS_PROD": "500",
                "OG_COND_PROD": "10",
                "OG_WATER_PROD": "30",
                "OG_WELL_CNT": "3",
            },
            {
                "OG_DIST_NO": "7C",
                "OG_FIELD_NO": "1002",
                "OG_FIELD_NAME": "WOLFCAMP",
                "OG_LEASE_NO": "2003",
                "OG_LEASE_NAME": "REEVES UNIT",
                "OG_OPER_NO": "300001",
                "OG_OPER_NAME": "ALPHA ENERGY",
                "OG_CYCLE": "01/2023",
                "OG_OIL_PROD": "50",
                "OG_GAS_PROD": "0",
                "OG_COND_PROD": "0",
                "OG_WATER_PROD": "5",
                "OG_WELL_CNT": "1",
            },
        ]
    )


def test_normalize_production_frame_handles_official_pdq_aliases():
    from worldenergydata.texas_rrc.production_atlas import (
        normalize_production_frame,
    )

    normalized = normalize_production_frame(_pdq_frame())

    assert list(normalized["production_month"]) == [
        "2023-01",
        "2023-02",
        "2023-01",
    ]
    assert normalized.loc[0, "district"] == "08"
    assert normalized.loc[2, "district"] == "7C"
    assert normalized.loc[0, "field_number"] == "1001"
    assert normalized.loc[0, "lease_number"] == "2001"
    assert normalized.loc[0, "operator_number"] == "300001"
    assert normalized.loc[0, "oil_bbl"] == 100.0
    assert normalized.loc[0, "gas_mcf"] == 1000.0
    assert normalized.loc[0, "condensate_bbl"] == 5.0
    assert normalized.loc[0, "water_bbl"] == 20.0
    assert normalized.loc[0, "boe"] == pytest.approx(100.0 + 5.0 + 1000.0 * 0.1714)


def test_normalize_production_frame_handles_rrc_lease_cycle_dsv_aliases():
    from worldenergydata.texas_rrc.production_atlas import (
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "FIELD_NAME": "SPRABERRY",
                "LEASE_NO": "2001",
                "LEASE_NAME": "MIDLAND UNIT",
                "OPERATOR_NO": "300001",
                "OPERATOR_NAME": "ALPHA ENERGY",
                "CYCLE_YEAR_MONTH": "202301",
                "LEASE_OIL_PROD_VOL": "100",
                "LEASE_GAS_PROD_VOL": "1000",
                "LEASE_CSGD_PROD_VOL": "50",
                "LEASE_COND_PROD_VOL": "5",
            }
        ]
    )

    normalized = normalize_production_frame(frame)

    assert normalized.iloc[0]["production_month"] == "2023-01"
    assert normalized.iloc[0]["oil_bbl"] == 100.0
    assert normalized.iloc[0]["gas_mcf"] == 1050.0
    assert normalized.iloc[0]["condensate_bbl"] == 5.0
    assert normalized.iloc[0]["boe"] == pytest.approx(100.0 + 5.0 + 1050.0 * 0.1714)


def test_normalize_production_frame_marks_missing_official_metrics_unavailable():
    from worldenergydata.texas_rrc.production_atlas import (
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "PROD_REPORT_FILED_FLAG": "Y",
                "CYCLE_YEAR_MONTH": "202301",
                "LEASE_OIL_PROD_VOL": "100",
            }
        ]
    )

    normalized = normalize_production_frame(frame)

    assert normalized.iloc[0]["water_bbl"] == 0.0
    assert normalized.iloc[0]["water_available"] is False
    assert normalized.iloc[0]["well_count"] == 0.0
    assert normalized.iloc[0]["well_count_available"] is False
    assert normalized.iloc[0]["report_filed"] is True


def test_build_production_atlas_computes_field_metrics_deterministically():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    atlas = build_production_atlas(normalize_production_frame(_pdq_frame()))
    fields = atlas[atlas["aggregation_level"] == "field"].reset_index(drop=True)

    assert fields["field_number"].tolist() == ["1001", "1002"]
    spraberry = fields.iloc[0]
    assert spraberry["district"] == "08"
    assert spraberry["cumulative_oil_bbl"] == 300.0
    assert spraberry["cumulative_gas_mcf"] == 1500.0
    assert spraberry["cumulative_condensate_bbl"] == 15.0
    assert spraberry["cumulative_water_bbl"] == 50.0
    assert spraberry["cumulative_boe"] == pytest.approx(300.0 + 15.0 + 1500.0 * 0.1714)
    assert spraberry["first_production_month"] == "2023-01"
    assert spraberry["last_production_month"] == "2023-02"
    assert bool(spraberry["still_producing"]) is True
    assert spraberry["production_month_count"] == 2
    assert spraberry["production_span_months"] == 2
    assert spraberry["lease_count"] == 2
    assert spraberry["operator_count"] == 2
    assert spraberry["well_count_peak"] == 3
    assert spraberry["peak_oil_bbl"] == 200.0
    assert spraberry["peak_boe"] == pytest.approx(200.0 + 10.0 + 500.0 * 0.1714)
    assert spraberry["top_operator_number"] == "300002"
    assert spraberry["top_operator_share"] == pytest.approx(
        (200.0 + 10.0 + 500.0 * 0.1714) / (300.0 + 15.0 + 1500.0 * 0.1714)
    )


def test_build_production_atlas_marks_unavailable_metrics_as_null():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "PROD_REPORT_FILED_FLAG": "Y",
                "CYCLE_YEAR_MONTH": "202301",
                "LEASE_OIL_PROD_VOL": "100",
            }
        ]
    )

    atlas = build_production_atlas(normalize_production_frame(frame))
    field = atlas[atlas["aggregation_level"] == "field"].iloc[0]

    assert pd.isna(field["cumulative_water_bbl"])
    assert pd.isna(field["well_count_peak"])


def test_build_production_atlas_groups_on_stable_ids_not_display_names():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_LEASE_NO": "2001",
                "OG_LEASE_NAME": "MIDLAND UNIT",
                "OG_OPER_NO": "300001",
                "OG_OPER_NAME": "ALPHA ENERGY",
                "OG_CYCLE": "202301",
                "OG_OIL_PROD": "100",
                "OG_GAS_PROD": "1000",
            },
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY TREND AREA",
                "OG_LEASE_NO": "2001",
                "OG_LEASE_NAME": "MIDLAND UNIT A",
                "OG_OPER_NO": "300001",
                "OG_OPER_NAME": "ALPHA ENERGY LLC",
                "OG_CYCLE": "202302",
                "OG_OIL_PROD": "200",
                "OG_GAS_PROD": "500",
            },
        ]
    )

    atlas = build_production_atlas(normalize_production_frame(frame))

    field_rows = atlas[atlas["aggregation_level"] == "field"]
    lease_rows = atlas[atlas["aggregation_level"] == "lease"]
    operator_rows = atlas[atlas["aggregation_level"] == "operator"]
    assert len(field_rows) == 1
    assert len(lease_rows) == 1
    assert len(operator_rows) == 1
    assert field_rows.iloc[0]["field_name"] == "SPRABERRY TREND AREA"
    assert lease_rows.iloc[0]["lease_name"] == "MIDLAND UNIT A"
    assert operator_rows.iloc[0]["operator_name"] == "ALPHA ENERGY LLC"


def test_build_production_atlas_rolls_top_operator_up_by_number():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_LEASE_NO": "2001",
                "OG_OPER_NO": "300001",
                "OG_OPER_NAME": "ALPHA ENERGY",
                "OG_CYCLE": "202301",
                "OG_OIL_PROD": "100",
            },
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_LEASE_NO": "2002",
                "OG_OPER_NO": "300001",
                "OG_OPER_NAME": "ALPHA ENERGY LLC",
                "OG_CYCLE": "202302",
                "OG_OIL_PROD": "200",
            },
        ]
    )

    atlas = build_production_atlas(normalize_production_frame(frame))
    field = atlas[atlas["aggregation_level"] == "field"].iloc[0]
    operator = atlas[atlas["aggregation_level"] == "operator"].iloc[0]

    assert field["top_operator_number"] == "300001"
    assert field["top_operator_name"] == "ALPHA ENERGY LLC"
    assert field["top_operator_boe"] == 300.0
    assert field["top_operator_share"] == 1.0
    assert operator["top_operator_share"] == 1.0


def test_normalize_production_frame_handles_split_cycle_year_month():
    from worldenergydata.texas_rrc.production_atlas import normalize_production_frame

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "CYCLE_YEAR": "2023",
                "CYCLE_MONTH": "4",
                "OIL_BBL": "100",
            }
        ]
    )

    normalized = normalize_production_frame(frame)

    assert normalized.iloc[0]["production_month"] == "2023-04"


def test_build_production_atlas_uses_positive_months_for_active_window():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_CYCLE": "202301",
                "OG_OIL_PROD": "100",
                "OG_GAS_PROD": "0",
            },
            {
                "OG_DIST_NO": "08",
                "OG_FIELD_NO": "1001",
                "OG_FIELD_NAME": "SPRABERRY",
                "OG_CYCLE": "202302",
                "OG_OIL_PROD": "0",
                "OG_GAS_PROD": "0",
            },
        ]
    )

    atlas = build_production_atlas(normalize_production_frame(frame))
    field = atlas[atlas["aggregation_level"] == "field"].iloc[0]

    assert field["first_production_month"] == "2023-01"
    assert field["last_production_month"] == "2023-01"
    assert field["production_month_count"] == 1
    assert bool(field["still_producing"]) is False


def test_build_production_atlas_ignores_unfiled_future_cycles_for_currentness():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "PROD_REPORT_FILED_FLAG": "Y",
                "CYCLE_YEAR_MONTH": "202604",
                "LEASE_OIL_PROD_VOL": "100",
            },
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1002",
                "LEASE_NO": "2002",
                "OPERATOR_NO": "300002",
                "PROD_REPORT_FILED_FLAG": "N",
                "CYCLE_YEAR_MONTH": "202607",
                "LEASE_OIL_PROD_VOL": "0",
            },
        ]
    )

    atlas = build_production_atlas(normalize_production_frame(frame))
    field = atlas[
        (atlas["aggregation_level"] == "field") & (atlas["field_number"] == "1001")
    ].iloc[0]

    assert field["last_production_month"] == "2026-04"
    assert bool(field["still_producing"]) is True


def test_build_production_atlas_includes_required_aggregation_levels():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
    )

    atlas = build_production_atlas(normalize_production_frame(_pdq_frame()))

    assert atlas["aggregation_level"].tolist() == sorted(
        atlas["aggregation_level"].tolist(),
        key=["field", "lease", "district", "operator", "statewide"].index,
    )
    assert set(atlas["aggregation_level"]) == {
        "field",
        "lease",
        "district",
        "operator",
        "statewide",
    }
    assert len(atlas[atlas["aggregation_level"] == "statewide"]) == 1


def test_build_production_atlas_from_chunks_matches_in_memory_builder():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        build_production_atlas_from_chunks,
        normalize_production_frame,
    )

    frame = _pdq_frame()

    expected = build_production_atlas(normalize_production_frame(frame))
    actual = build_production_atlas_from_chunks([frame.iloc[:2], frame.iloc[2:]])

    pd.testing.assert_frame_equal(actual, expected)


def test_build_production_atlas_from_chunks_merges_boundary_duplicate_lease_months():
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        build_production_atlas_from_chunks,
        normalize_production_frame,
    )

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "PROD_REPORT_FILED_FLAG": "Y",
                "CYCLE_YEAR_MONTH": "202301",
                "LEASE_OIL_PROD_VOL": "100",
            },
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "PROD_REPORT_FILED_FLAG": "Y",
                "CYCLE_YEAR_MONTH": "202301",
                "LEASE_OIL_PROD_VOL": "50",
            },
        ]
    )

    expected = build_production_atlas(normalize_production_frame(frame))
    actual = build_production_atlas_from_chunks([frame.iloc[:1], frame.iloc[1:]])

    pd.testing.assert_frame_equal(actual, expected)


def test_build_production_atlas_empty_input_returns_stable_columns():
    from worldenergydata.texas_rrc.production_atlas import build_production_atlas

    atlas = build_production_atlas(pd.DataFrame())

    assert atlas.empty
    assert {
        "aggregation_level",
        "cumulative_oil_bbl",
        "cumulative_boe",
        "first_production_month",
        "top_operator_share",
    }.issubset(atlas.columns)


def test_load_production_inputs_reads_local_official_pdq_zip(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(
            [
                "OG_DIST_NO,OG_FIELD_NO,OG_FIELD_NAME,OG_LEASE_NO,OG_OPER_NO,OG_CYCLE,OG_OIL_PROD,OG_GAS_PROD",
                "08,1001,SPRABERRY,2001,300001,202301,100,1000",
            ]
        ),
    )

    inputs = load_production_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.input_paths == (tmp_path / "raw/production/pdq/PDQ_DSV.zip",)
    assert inputs.production.iloc[0]["field_number"] == "1001"
    assert inputs.production.iloc[0]["production_month"] == "2023-01"


def test_load_production_inputs_streams_preferred_pdq_member(tmp_path, monkeypatch):
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(
            [
                "DISTRICT_NO}FIELD_NO}FIELD_NAME}LEASE_NO}OPERATOR_NO}CYCLE_YEAR_MONTH}LEASE_OIL_PROD_VOL}LEASE_GAS_PROD_VOL",
                "08}1001}SPRABERRY}2001}300001}202301}100}1000",
            ]
        ),
        member_name="OG_LEASE_CYCLE_DATA_TABLE.dsv",
    )

    original_read = zipfile.ZipFile.read

    def fail_full_member_read(self, name, *args, **kwargs):
        if str(name).endswith("OG_LEASE_CYCLE_DATA_TABLE.dsv"):
            raise AssertionError("official PDQ production member must be streamed")
        return original_read(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "read", fail_full_member_read)

    inputs = load_production_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.production.iloc[0]["field_number"] == "1001"


def test_load_production_inputs_reads_pipe_delimited_pdq_members(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(
            [
                "OG_DIST_NO|OG_FIELD_NO|OG_FIELD_NAME|OG_LEASE_NO|OG_OPER_NO|OG_CYCLE|OG_OIL_PROD|OG_GAS_PROD",
                "08|1001|SPRABERRY|2001|300001|202301|100|1000",
            ]
        ),
    )

    inputs = load_production_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.production.iloc[0]["field_name"] == "SPRABERRY"
    assert inputs.production.iloc[0]["oil_bbl"] == 100.0


def test_iter_production_input_chunks_reads_pdq_in_bounded_chunks(tmp_path):
    from worldenergydata.texas_rrc.production_atlas.sources import (
        iter_production_input_chunks,
    )

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(
            [
                "DISTRICT_NO}FIELD_NO}FIELD_NAME}LEASE_NO}OPERATOR_NO}CYCLE_YEAR_MONTH}LEASE_OIL_PROD_VOL}LEASE_GAS_PROD_VOL",
                "08}1001}SPRABERRY}2001}300001}202301}100}1000",
                "08}1001}SPRABERRY}2001}300001}202302}50}500",
            ]
        ),
        member_name="OG_LEASE_CYCLE_DATA_TABLE.dsv",
    )

    inputs = iter_production_input_chunks(tmp_path, chunksize=1)
    chunks = list(inputs.chunks)

    assert inputs.source_gaps == ()
    assert len(chunks) == 2
    assert [len(chunk) for chunk in chunks] == [1, 1]
    assert chunks[0].iloc[0]["FIELD_NO"] == "1001"


def test_load_production_inputs_reads_tab_delimited_pdq_members(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(
            [
                "OG_DIST_NO\tOG_FIELD_NO\tOG_FIELD_NAME\tOG_LEASE_NO\tOG_OPER_NO\tOG_CYCLE\tOG_OIL_PROD",
                "08\t1001\tSPRABERRY\t2001\t300001\t202301\t100",
            ]
        ),
    )

    inputs = load_production_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.production.iloc[0]["field_name"] == "SPRABERRY"
    assert inputs.production.iloc[0]["oil_bbl"] == 100.0


def test_load_production_inputs_accepts_catalog_raw_path(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    raw_path = tmp_path / "raw/production/pdq"
    _write_pdq_zip(
        raw_path / "PDQ_DSV.zip",
        "\n".join(
            [
                "OG_DIST_NO,OG_FIELD_NO,OG_FIELD_NAME,OG_LEASE_NO,OG_OPER_NO,OG_CYCLE,OG_OIL_PROD",
                "08,1001,SPRABERRY,2001,300001,202301,100",
            ]
        ),
    )

    inputs = load_production_inputs(raw_path)

    assert inputs.source_gaps == ()
    assert inputs.input_paths == (raw_path / "PDQ_DSV.zip",)
    assert inputs.production.iloc[0]["field_number"] == "1001"


def test_load_production_inputs_rejects_unrecognized_pdq_members(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(["NOT_A_PDQ_COLUMN,OTHER", "x,y"]),
    )

    inputs = load_production_inputs(tmp_path)

    assert inputs.source_gaps == ("production_pdq",)
    assert inputs.production.empty


def test_load_production_inputs_rejects_url_like_roots():
    from worldenergydata.texas_rrc.production_atlas import load_production_inputs

    with pytest.raises(ValueError, match="local filesystem path"):
        load_production_inputs("https://www.rrc.texas.gov/pdq.zip")


def test_write_production_atlas_outputs_uses_ace_layout_and_manifest(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
        write_production_atlas_outputs,
    )

    atlas = build_production_atlas(normalize_production_frame(_pdq_frame()))
    raw_path = tmp_path / "raw/production/pdq/PDQ_DSV.zip"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(b"pdq")
    raw_manifest = tmp_path / "manifests/production_pdq-20260630T155507Z.json"
    raw_manifest.parent.mkdir(parents=True, exist_ok=True)
    raw_manifest.write_text(
        json.dumps(
            {
                "source_id": "production_pdq",
                "source_url": "https://www.rrc.texas.gov/media/ebxnoxbm/pdq-dump.zip",
                "download_url": "https://mft.rrc.texas.gov/link/example",
                "effective_url": "https://mft.rrc.texas.gov/link/godrivedownload",
                "raw_path": str(raw_path),
                "checksum_sha256": "abc123",
                "byte_size": 3,
                "retrieved_at": "2026-06-30T15:55:07Z",
                "refresh_cadence": "monthly_last_saturday",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = write_production_atlas_outputs(
        atlas,
        output_root=tmp_path,
        input_paths=[raw_path],
        generated_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
        source_gaps=(),
        allow_non_ace_root=True,
        command="worldenergydata texas-rrc build-production-atlas",
        code_revision="abcde",
    )

    assert manifest.csv_path == (
        tmp_path / "curated/production/field_atlas/production_field_atlas.csv"
    )
    assert manifest.parquet_path.exists()
    assert manifest.quality_path.exists()
    payload = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert payload["row_count"] == len(atlas)
    assert payload["source_ids"] == ["production_pdq"]
    assert payload["generated_at"] == "2026-06-30T00:00:00Z"
    assert payload["command"] == "worldenergydata texas-rrc build-production-atlas"
    assert payload["code_revision"] == "abcde"
    assert payload["sources"] == [
        {
            "byte_size": 3,
            "checksum_sha256": "abc123",
            "download_url": "https://mft.rrc.texas.gov/link/example",
            "effective_url": "https://mft.rrc.texas.gov/link/godrivedownload",
            "input_path": str(raw_path),
            "manifest_path": str(raw_manifest),
            "refresh_cadence": "monthly_last_saturday",
            "retrieved_at": "2026-06-30T15:55:07Z",
            "source_id": "production_pdq",
            "source_url": "https://www.rrc.texas.gov/media/ebxnoxbm/pdq-dump.zip",
        }
    ]


def test_write_production_atlas_outputs_reports_unavailable_metric_gaps(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import (
        build_production_atlas,
        normalize_production_frame,
        write_production_atlas_outputs,
    )

    frame = pd.DataFrame(
        [
            {
                "DISTRICT_NO": "08",
                "FIELD_NO": "1001",
                "LEASE_NO": "2001",
                "OPERATOR_NO": "300001",
                "PROD_REPORT_FILED_FLAG": "Y",
                "CYCLE_YEAR_MONTH": "202301",
                "LEASE_OIL_PROD_VOL": "100",
            }
        ]
    )
    atlas = build_production_atlas(normalize_production_frame(frame))

    manifest = write_production_atlas_outputs(
        atlas,
        output_root=tmp_path,
        generated_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
        allow_non_ace_root=True,
    )

    quality = json.loads(manifest.quality_path.read_text(encoding="utf-8"))
    assert quality["metric_gaps"] == ["water_bbl", "well_count"]


def test_write_production_atlas_outputs_rejects_non_ace_root_by_default(tmp_path):
    from worldenergydata.texas_rrc.production_atlas import (
        write_production_atlas_outputs,
    )

    with pytest.raises(ValueError, match="/mnt/ace"):
        write_production_atlas_outputs(pd.DataFrame(), output_root=tmp_path)


def test_build_production_atlas_cli_dry_run(monkeypatch, tmp_path):
    from worldenergydata.cli.commands.texas_rrc import app
    from worldenergydata.texas_rrc.production_atlas.sources import ProductionInputChunks

    def fake_iter_inputs(raw_root, chunksize):
        assert raw_root == tmp_path
        assert chunksize == 2
        return ProductionInputChunks(
            chunks=(normalize_fixture(),),
            input_paths=(tmp_path / "raw/production/pdq/PDQ_DSV.zip",),
            source_gaps=(),
        )

    def normalize_fixture():
        from worldenergydata.texas_rrc.production_atlas import (
            normalize_production_frame,
        )

        return normalize_production_frame(_pdq_frame())

    monkeypatch.setattr(
        "worldenergydata.texas_rrc.production_atlas.sources.iter_production_input_chunks",
        fake_iter_inputs,
    )

    result = CliRunner().invoke(
        app,
        [
            "build-production-atlas",
            "--dry-run",
            "--raw-root",
            str(tmp_path),
            "--chunksize",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "Production atlas rows" in result.output
    assert "Dry run" in result.output
    assert not any(tmp_path.rglob("curated"))


def test_build_production_atlas_cli_refuses_write_when_sources_missing(tmp_path):
    from worldenergydata.cli.commands.texas_rrc import app

    result = CliRunner().invoke(
        app,
        [
            "build-production-atlas",
            "--raw-root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
        ],
    )

    assert result.exit_code == 1
    assert "missing production sources: production_pdq" in result.output
    assert not any(tmp_path.rglob("curated"))


def test_build_production_atlas_cli_writes_outputs_with_non_ace_override(tmp_path):
    from worldenergydata.cli.commands.texas_rrc import app

    _write_pdq_zip(
        tmp_path / "raw/production/pdq/PDQ_DSV.zip",
        "\n".join(
            [
                "OG_DIST_NO,OG_FIELD_NO,OG_FIELD_NAME,OG_LEASE_NO,OG_OPER_NO,OG_CYCLE,OG_OIL_PROD",
                "08,1001,SPRABERRY,2001,300001,202301,100",
            ]
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "build-production-atlas",
            "--raw-root",
            str(tmp_path),
            "--output-root",
            str(tmp_path),
            "--allow-non-ace-output",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote production atlas" in result.output
    assert (
        tmp_path / "curated/production/field_atlas/production_field_atlas.csv"
    ).exists()
    assert (
        tmp_path / "curated/production/field_atlas/production_field_atlas.parquet"
    ).exists()
