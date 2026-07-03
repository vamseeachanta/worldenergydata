"""Tests for Colorado ECMC production and wells parsing (#745)."""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
import shapefile

from worldenergydata.modules.state_regulators.colorado_ecmc.parsers import (
    normalize_api_parts,
    read_production_csv,
    read_wells_shapefile,
)

PRODUCTION_COLUMNS = [
    "DocNum",
    "ReportMonth",
    "ReportYear",
    "DaysProduced",
    "AcceptedDate",
    "Revised",
    "OpName",
    "OpNumber",
    "FacilityId",
    "ApiCountyCode",
    "ApiSequenceNumber",
    "ApiSidetrack",
    "Well",
    "WellStatus",
    "FormationCode",
    "OilProduced",
    "OilSales",
    "OilAdjustment",
    "OilGravity",
    "GasProduced",
    "GasSales",
    "GasBtuSales",
    "GasUsedOnLease",
    "GasSrinkage",
    "GasPressureTubing",
    "GasPressureCasing",
    "FlaredVented",
    "WaterProduced",
    "WaterPressureTubing",
    "WaterPressureCasing",
    "BOMInvent",
    "EOMInvent",
]


def test_normalize_api_parts_builds_colorado_api10_and_api12():
    frame = pd.DataFrame(
        {
            "ApiCountyCode": [123, "5"],
            "ApiSequenceNumber": [32498, "77"],
            "ApiSidetrack": [0, "3"],
        }
    )

    result = normalize_api_parts(frame)

    assert list(result["api10"]) == ["0512332498", "0500500077"]
    assert list(result["api12"]) == ["051233249800", "050050007703"]


def test_read_production_csv_coerces_pressures_and_report_dates(tmp_path):
    path = tmp_path / "2025_prod_reports.csv"
    _production_frame(
        [
            {
                "DocNum": 1,
                "ReportMonth": "1",
                "ReportYear": "2025",
                "FacilityId": "420193",
                "ApiCountyCode": "123",
                "ApiSequenceNumber": "32498",
                "ApiSidetrack": "0",
                "Well": "WATTENBERG TEST",
                "FormationCode": "J SAND",
                "GasPressureTubing": "85",
                "GasPressureCasing": "120",
                "WaterPressureTubing": "10",
                "WaterPressureCasing": "",
                "GasProduced": "1500",
                "DaysProduced": "20",
            }
        ]
    ).to_csv(path, index=False)

    frame = read_production_csv(path, {"source_name": "production_2025"})

    assert frame.loc[0, "api12"] == "051233249800"
    assert frame.loc[0, "api10"] == "0512332498"
    assert frame.loc[0, "facility_id"] == "420193"
    assert frame.loc[0, "report_year"] == 2025
    assert frame.loc[0, "report_month"] == 1
    assert frame.loc[0, "test_date"] == pd.Timestamp("2025-01-31")
    assert frame.loc[0, "gas_pressure_tubing_psig"] == 85
    assert frame.loc[0, "gas_pressure_casing_psig"] == 120
    assert frame.loc[0, "water_pressure_tubing_psig"] == 10


def test_read_production_csv_fails_closed_on_missing_required_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"DocNum": [1], "ReportYear": [2025]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing required ECMC production columns"):
        read_production_csv(path, {})


def test_read_wells_shapefile_extracts_join_fields_depth_and_field(tmp_path):
    zip_path = _write_wells_shapefile(
        tmp_path,
        {
            "API": "051233249800",
            "API_County": "123",
            "API_Seq": "32498",
            "API_Label": "05-123-32498",
            "Field_Code": "401",
            "Field_Name": "WATTENBERG",
            "Facil_Id": "420193",
            "Max_MD": 8150,
            "Max_TVD": 7994,
            "Latitude": 40.123,
            "Longitude": -104.456,
        },
    )

    frame = read_wells_shapefile(zip_path)

    assert frame.loc[0, "api12"] == "051233249800"
    assert frame.loc[0, "api10"] == "0512332498"
    assert frame.loc[0, "facility_id"] == "420193"
    assert frame.loc[0, "field"] == "WATTENBERG"
    assert frame.loc[0, "max_md_ft"] == 8150
    assert frame.loc[0, "max_tvd_ft"] == 7994
    assert frame.loc[0, "latitude"] == pytest.approx(40.123)
    assert frame.loc[0, "longitude"] == pytest.approx(-104.456)


def test_read_wells_shapefile_fails_closed_on_missing_join_columns(tmp_path):
    zip_path = _write_wells_shapefile(tmp_path, {"API": "051233249800"})

    with pytest.raises(ValueError, match="missing required ECMC wells columns"):
        read_wells_shapefile(zip_path)


def _production_frame(rows):
    return pd.DataFrame(
        [{column: row.get(column) for column in PRODUCTION_COLUMNS} for row in rows]
    )


def _write_wells_shapefile(tmp_path: Path, record: dict) -> Path:
    shp_base = tmp_path / "Wells"
    writer = shapefile.Writer(str(shp_base), shapeType=shapefile.POINT)
    for name, field_type, size, decimal in [
        ("API", "C", 20, 0),
        ("API_County", "C", 10, 0),
        ("API_Seq", "C", 10, 0),
        ("API_Label", "C", 20, 0),
        ("Field_Code", "C", 10, 0),
        ("Field_Name", "C", 40, 0),
        ("Facil_Id", "C", 20, 0),
        ("Max_MD", "N", 12, 2),
        ("Max_TVD", "N", 12, 2),
        ("Latitude", "N", 16, 8),
        ("Longitude", "N", 16, 8),
    ]:
        if name in record:
            writer.field(name, field_type, size=size, decimal=decimal)
    writer.point(
        float(record.get("Longitude", -104.0)), float(record.get("Latitude", 40.0))
    )
    writer.record(*[record[name] for name in record])
    writer.close()
    (tmp_path / "Wells.prj").write_text("GEOGCS[]", encoding="utf-8")

    zip_path = tmp_path / "WELLS_SHP.ZIP"
    with ZipFile(zip_path, "w") as archive:
        for suffix in [".shp", ".shx", ".dbf", ".prj"]:
            candidate = shp_base.with_suffix(suffix)
            if candidate.exists():
                archive.write(candidate, candidate.name)
    return zip_path
