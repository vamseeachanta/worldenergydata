"""Synthetic regressions for district-name and numeric-ID boundaries."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pandas as pd
import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.data.loaders.pdq_loader import PDQLoader
from worldenergydata.texas_rrc.data.texas_rrc_data import TexasRRCData
from worldenergydata.texas_rrc.processors.production_processor import (
    ProductionProcessor,
)
from worldenergydata.texas_rrc.production_atlas import (
    build_production_atlas,
    build_production_atlas_from_chunks,
    normalize_production_frame,
)
from worldenergydata.texas_rrc.production_atlas.sources import _read_pdq_text
from worldenergydata.texas_rrc.texas_rrc import TexasRRC


@pytest.mark.parametrize("district", ["01", "06", "08", "09", "10"])
def test_real_well_download_sends_explicit_numeric_parameter(district):
    output_dir = Path("unused")
    client = Mock()
    client.download_wellbore_data.return_value = output_dir / "wells.csv"
    result = TexasRRCData(client).download_well_data(
        {"districts": [district]}, output_dir
    )
    client.download_wellbore_data.assert_called_once_with(
        output_dir=output_dir, district=int(district), use_cache=True
    )
    assert result["results"][0]["status"] == "downloaded"


@pytest.mark.parametrize("district", ["6E", "7B", "7C", "8A"])
def test_unqualified_well_mapping_fails_before_any_request(district):
    client = Mock()
    with pytest.raises(ValueError, match="well.*mapping.*not qualified"):
        TexasRRCData(client).download_well_data(
            {"districts": ["10", district]}, Path("unused")
        )
    assert client.mock_calls == []


def test_default_cli_wells_uses_real_bulk_download_route(monkeypatch):
    output_dir = Path("unused")
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    client = Mock()
    client.download_pdq_dump.return_value = output_dir / "wells.zip"
    monkeypatch.setattr(TexasRRCData, "client", property(lambda self: client))
    result = CliRunner().invoke(
        app, ["collect", "--types", "wells", "--output", str(output_dir)]
    )
    assert result.exit_code == 0, result.output
    client.download_pdq_dump.assert_called_once_with(
        output_dir=output_dir, data_type="og_well", use_cache=True
    )
    client.download_wellbore_data.assert_not_called()


def test_cli_rejects_unqualified_well_mapping(monkeypatch):
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    client = Mock()
    monkeypatch.setattr(TexasRRCData, "client", property(lambda self: client))
    result = CliRunner().invoke(
        app,
        ["collect", "--types", "wells", "--districts", "6e", "--output", "unused"],
    )
    assert result.exit_code == 1
    assert "not qualified" in result.output
    assert client.mock_calls == []


@pytest.mark.parametrize("column", ["DISTRICT_NO", "OG_DIST_NO", "DIST_NO"])
def test_atlas_rejects_numeric_ids_before_assigning_names(column):
    frame = pd.DataFrame(
        {
            column: ["07", "08", "10"],
            "OG_CYCLE": ["202301"] * 3,
            "OG_OIL_PROD": [10, 20, 30],
        }
    )
    with pytest.raises(ValueError, match="numeric district IDs"):
        normalize_production_frame(frame)


@pytest.mark.parametrize(
    "column", ["DISTRICT_NO", "OG_DIST_NO", "DIST_NO", "district_no"]
)
@pytest.mark.parametrize("as_frame", [False, True])
def test_processor_rejects_numeric_id_records_and_frames(column, as_frame):
    records = [{column: value, "oil_production": 10} for value in ["07", "08", "10"]]
    data = pd.DataFrame(records) if as_frame else records
    with pytest.raises(ValueError, match="numeric district IDs"):
        ProductionProcessor().process(data, validate=False)


@pytest.mark.parametrize(
    "data_type,column", [("production", "OG_DIST_NO"), ("wells", "DIST_NO")]
)
def test_pdq_loader_preserves_numeric_id_as_separate_field(data_type, column):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("records.csv", f"{column}\n07\n08\n10\n")
    records = PDQLoader().load_from_bytes(buffer.getvalue(), data_type=data_type)
    assert [row["district_no"] for row in records] == ["07", "08", "10"]
    assert all("district" not in row for row in records)


def test_local_csv_route_rejects_numeric_ids(tmp_path):
    (tmp_path / "production.csv").write_text(
        "DISTRICT_NO,oil_production\n07,10\n08,20\n10,30\n", encoding="utf-8"
    )
    cfg = {
        "data_types": ["production"],
        "data": {"source": "csv", "files": {"production": "production.csv"}},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(tmp_path / "outputs"),
        },
    }
    with pytest.raises(ValueError, match="numeric district IDs"):
        TexasRRC().router(cfg)


def test_numeric_id_and_name_columns_are_not_silently_combined():
    frame = pd.DataFrame({"DISTRICT_NO": ["08"], "district": ["7B"]})
    result = normalize_production_frame(frame)
    assert result["district"].tolist() == ["7B"]
    assert result["district_no"].tolist() == ["08"]


def test_explicit_district_names_remain_supported_by_atlas():
    frame = pd.DataFrame({"DISTRICT_NAME": ["6E", "7B", "08"], "OIL_BBL": [10, 20, 30]})
    result = normalize_production_frame(frame, sort_rows=False)
    assert result["district"].tolist() == ["6E", "7B", "08"]
    assert result["oil_bbl"].sum() == 60


@pytest.mark.parametrize("separator", ["}", "|"])
def test_delimited_reader_preserves_names_and_pdq_metrics(separator):
    text = separator.join(["DISTRICT_NAME", "FIELD_NO", "OG_CYCLE", "OG_OIL_PROD"])
    text += "\n" + separator.join(["6E", "1", "202301", "10"]) + "\n"
    result = normalize_production_frame(_read_pdq_text(text))
    assert result["district"].tolist() == ["6E"]
    assert result["oil_bbl"].tolist() == [10]


@pytest.mark.parametrize("column", ["DISTRICT_NO", "OG_DIST_NO", "DIST_NO"])
def test_delimited_reader_cannot_discard_numeric_id_before_validation(column):
    text = (
        f"{column}}}FIELD_NO}}CYCLE_YEAR_MONTH}}LEASE_OIL_PROD_VOL\n08}}1}}202301}}10\n"
    )
    with pytest.raises(ValueError, match="numeric district IDs"):
        normalize_production_frame(_read_pdq_text(text))


@pytest.mark.parametrize("chunked", [False, True])
def test_pre_normalized_frame_cannot_bypass_numeric_id_check(chunked):
    frame = normalize_production_frame(
        pd.DataFrame({"district": ["08"], "OIL_BBL": [10]})
    )
    frame["district_no"] = "08"
    frame = frame.drop(columns="district")
    with pytest.raises(ValueError, match="numeric district IDs"):
        if chunked:
            build_production_atlas_from_chunks([frame])
        else:
            build_production_atlas(frame)
