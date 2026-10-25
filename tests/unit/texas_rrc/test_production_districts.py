"""Production labels qualified against the public RRC PDQ query, 2026-10-21."""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.texas_rrc.texas_rrc import TexasRRC
from worldenergydata.texas_rrc.validators import TexasDataValidator

# RRC PDQ, General Production Query, Geographic Region / District, undated,
# retrieved 2026-10-21: https://webapps.rrc.texas.gov/PDQ/generalReportAction.do
# These are visible labels; HTML option values are different identifiers.
EXPECTED_DISTRICTS = (
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "6E",
    "7B",
    "7C",
    "08",
    "8A",
    "09",
    "10",
)
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("code", EXPECTED_DISTRICTS)
def test_production_label_contract(code):
    """Expected labels are transcribed independently from the cited RRC control."""
    from worldenergydata.cli.commands.texas_rrc import VALID_DISTRICTS
    from worldenergydata.texas_rrc.endpoints import TEXAS_DISTRICTS

    validator = TexasDataValidator()
    assert validator.normalize_district(code) == code
    assert validator.validate_district(code) == (True, None)
    assert code in TexasRRC().get_valid_districts()
    assert code in VALID_DISTRICTS
    assert code in TEXAS_DISTRICTS
    config = yaml.safe_load(
        (REPO_ROOT / "config/texas_rrc.yml").read_text(encoding="utf-8")
    )
    assert code in config["districts"]
    TexasRRC()._validate_config({"districts": [code]})


def test_production_lists_have_no_unqualified_labels():
    """The complete label set is the cited RRC control, excluding UI selectors."""
    from worldenergydata.cli.commands.texas_rrc import VALID_DISTRICTS
    from worldenergydata.texas_rrc.endpoints import TEXAS_DISTRICTS

    assert set(TexasDataValidator.VALID_DISTRICTS) == set(EXPECTED_DISTRICTS)
    assert set(TexasRRC.VALID_DISTRICTS) == set(EXPECTED_DISTRICTS)
    assert set(VALID_DISTRICTS) == set(EXPECTED_DISTRICTS)
    assert set(TEXAS_DISTRICTS) == set(EXPECTED_DISTRICTS)
    config = yaml.safe_load(
        (REPO_ROOT / "config/texas_rrc.yml").read_text(encoding="utf-8")
    )
    assert set(config["districts"]) == set(EXPECTED_DISTRICTS)


@pytest.mark.parametrize("raw", ["6E", "6e", " 6e "])
def test_special_production_label_normalization(raw):
    """RRC label 6E accepts the existing case/space normalization convention."""
    assert TexasDataValidator().normalize_district(raw) == "6E"


@pytest.mark.parametrize(
    "raw, expected", [("3.0", "03"), ("10.00", "10"), ("3.5", None)]
)
def test_integral_numeric_csv_compatibility(raw, expected):
    """Hand calculation: 3.0 = 3, 10.00 = 10; 3.5 is not an integer label."""
    assert TexasDataValidator().normalize_district(raw) == expected


@pytest.mark.parametrize("code", ["6E", "7B", "7C", "8A"])
def test_csv_route_preserves_special_district_and_accounts_unknowns(tmp_path, code):
    """Independent hand sums of synthetic BBL and MCF inputs, no conversion.

    Special district: oil 100 + 25 = 125, gas 10 + 5 = 15; numeric 03:
    oil 50, gas 7. Invalid: oil 20, gas 3; blank: oil 10, gas 2.
    Overall: oil 125 + 50 + 20 + 10 = 205; gas 15 + 7 + 3 + 2 = 27.
    There are two assigned districts and two unassigned records. The repeated
    lease contributes two production rows but one distinct lease in its district.
    Codes are the labels in the RRC source cited above; fixture volumes are
    synthetic inputs, not observations or physical acceptance thresholds.
    """
    csv_path = tmp_path / "production.csv"
    csv_path.write_text(
        "district,lease_number,oil_production,gas_production\n"
        f"{code},1,100,10\n{code},1,25,5\n"
        "03,2,50,7\ninvalid,3,20,3\n,4,10,2\n",
        encoding="utf-8",
        newline="\n",
    )
    cfg = {
        "data_types": ["production"],
        "districts": [code, "03"],
        "data": {"source": "csv", "files": {"production": csv_path.as_posix()}},
        "Analysis": {
            "analysis_root_folder": tmp_path.as_posix(),
            "result_folder": (tmp_path / "results").as_posix(),
        },
    }
    result = TexasRRC().router(cfg)
    outputs = result["texas_rrc"]["outputs"]
    districts = pd.read_csv(outputs["districts_csv"], dtype={"district": str})
    special = districts.loc[districts["district"] == code].iloc[0]
    assert special["oil_production"] == 125
    assert special["gas_production"] == 15
    assert special["lease_count"] == 1
    unassigned = districts.loc[districts["district"].isna()].iloc[0]
    assert unassigned["oil_production"] == 30
    assert unassigned["gas_production"] == 5
    assert districts["oil_production"].sum() == 205
    assert districts["gas_production"].sum() == 27
    summary = json.loads(Path(outputs["summary_json"]).read_text(encoding="utf-8"))
    assert summary["total_records"] == 5
    assert summary["district_count"] == 2
    assert summary["oil_production_total"] == 205
    assert summary["gas_production_total"] == 27
    assert summary["unassigned_records"] == 2
    assert summary["unassigned_oil_production_total"] == 30
    assert summary["unassigned_gas_production_total"] == 5
    assert summary["invalid_district_records"] == 1
    assert summary["missing_district_records"] == 1
    assert summary["invalid_district_oil_production_total"] == 20
    assert summary["missing_district_oil_production_total"] == 10
    assert summary["invalid_district_gas_production_total"] == 3
    assert summary["missing_district_gas_production_total"] == 2


@pytest.mark.parametrize("missing", ["NaN", ""])
def test_csv_route_missing_measurements_match_district_totals(tmp_path, missing):
    """Hand sums in BBL/MCF; missing measurements add no reported volume.

    Assigned 6E: oil 10, gas 2 + 1 = 3; assigned 03: both totals 0.
    Invalid: oil 1, gas 3; missing district: oil 4, gas 5.
    Unassigned: oil 1 + 4 = 5, gas 3 + 5 = 8.
    Overall: oil 10 + 1 + 4 = 15, gas 3 + 3 + 5 = 11; seven rows.
    """
    csv_path = tmp_path / "production.csv"
    csv_path.write_text(
        "district,oil_production,gas_production\n"
        f"6E,10,2\n6E,{missing},1\ninvalid,{missing},3\n"
        f"invalid,1,{missing}\n,{missing},5\n,4,{missing}\n"
        f"03,{missing},{missing}\n",
        encoding="utf-8",
        newline="\n",
    )
    cfg = {
        "data_types": ["production"],
        "data": {"source": "csv", "files": {"production": csv_path.as_posix()}},
        "Analysis": {
            "analysis_root_folder": tmp_path.as_posix(),
            "result_folder": (tmp_path / "results").as_posix(),
        },
    }
    outputs = TexasRRC().router(cfg)["texas_rrc"]["outputs"]

    def reject_nonfinite(value):
        raise ValueError("Non-finite summary JSON")

    summary = json.loads(
        Path(outputs["summary_json"]).read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite,
    )
    assert summary == {
        "total_records": 7,
        "district_count": 2,
        "oil_production_total": 15,
        "gas_production_total": 11,
        "invalid_district_records": 2,
        "invalid_district_oil_production_total": 1,
        "invalid_district_gas_production_total": 3,
        "missing_district_records": 2,
        "missing_district_oil_production_total": 4,
        "missing_district_gas_production_total": 5,
        "unassigned_records": 4,
        "unassigned_oil_production_total": 5,
        "unassigned_gas_production_total": 8,
    }
    districts = pd.read_csv(outputs["districts_csv"], dtype={"district": str})
    assert districts["oil_production"].sum() == 15
    assert districts["gas_production"].sum() == 11
    unassigned = districts.loc[districts["district"].isna()].iloc[0]
    assert unassigned["oil_production"] == 5
    assert unassigned["gas_production"] == 8
    all_missing = districts.loc[districts["district"] == "03"].iloc[0]
    assert all_missing["oil_production"] == 0
    assert all_missing["gas_production"] == 0


@pytest.mark.parametrize("district", ["6E", "invalid", ""])
@pytest.mark.parametrize("volume", ["oil_production", "gas_production"])
@pytest.mark.parametrize("nonfinite", ["inf", "-inf"])
def test_csv_route_rejects_nonfinite_summary(tmp_path, district, volume, nonfinite):
    """Infinity is invalid measurement data, not an absent volume or zero."""
    csv_path = tmp_path / "production.csv"
    csv_path.write_text(
        f"district,oil_production,gas_production\n{district},"
        + (f"{nonfinite},1\n" if volume == "oil_production" else f"1,{nonfinite}\n"),
        encoding="utf-8",
        newline="\n",
    )
    result_folder = tmp_path / "results"
    cfg = {
        "data_types": ["production"],
        "data": {"source": "csv", "files": {"production": csv_path.as_posix()}},
        "Analysis": {
            "analysis_root_folder": tmp_path.as_posix(),
            "result_folder": result_folder.as_posix(),
        },
    }
    with pytest.raises(ValueError, match="Out of range float values"):
        TexasRRC().router(cfg)
    assert not (result_folder / "texas_rrc_production_summary_summary.json").exists()


@pytest.mark.parametrize("as_dataframe", [False, True])
def test_processing_keeps_invalid_and_missing_status(as_dataframe):
    """Hand partitions: one assigned, one invalid, two missing; oil 4 + 3 + 3 = 10.

    Synthetic rows carry oil 1 (null), 2 (blank), 3 (invalid), 4 (6E).
    Unassigned oil = 1 + 2 + 3 = 6; assigned oil = 4; total oil = 10.
    """
    from worldenergydata.texas_rrc.processors.production_processor import (
        ProductionProcessor,
    )

    records = [
        {"district": None, "oil_production": 1},
        {"district": " ", "oil_production": 2},
        {"district": "bad", "oil_production": 3},
        {"district": "6e", "oil_production": 4},
    ]
    processor = ProductionProcessor()
    data = pd.DataFrame(records) if as_dataframe else records
    processed = processor.process(data, validate=False)
    normalized = pd.DataFrame(processed)
    assert normalized["district_status"].tolist() == [
        "missing",
        "missing",
        "invalid",
        "assigned",
    ]
    grouped = processor.aggregate_by_district(processed)
    assert grouped.loc[grouped["district"] == "6E", "oil_production"].item() == 4
    assert grouped.loc[grouped["district"].isna(), "oil_production"].item() == 6
    assert grouped["oil_production"].sum() == 10


@pytest.mark.parametrize("raw", ["07", "11", "13", "14", "Statewide", "None Selected"])
def test_query_identifiers_and_controls_are_not_district_labels(raw):
    """The RRC control's option values/selectors are not its display-label set."""
    assert TexasDataValidator().normalize_district(raw) is None


def test_unqualified_special_district_metadata_is_explicit():
    """The qualified PDQ selector supplies a label, no office or county count."""
    from worldenergydata.texas_rrc.endpoints import get_district_info

    info = get_district_info("6e")
    assert info["name"] == "District 6E"
    assert info["headquarters"] is None
    assert info["counties"] is None
