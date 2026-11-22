"""District-name regressions against the RRC PDQ manual, printed page 26."""

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import VALID_DISTRICTS as CLI_DISTRICTS
from worldenergydata.cli.commands.texas_rrc import app
from worldenergydata.texas_rrc.endpoints import TEXAS_DISTRICTS, get_district_info
from worldenergydata.texas_rrc.production_atlas.atlas import (
    VALID_DISTRICTS as ATLAS_DISTRICTS,
)
from worldenergydata.texas_rrc.texas_rrc import TexasRRC
from worldenergydata.texas_rrc.validators import TexasDataValidator


@pytest.mark.parametrize("district", ["6E", "6e", " 6e "])
def test_east_texas_production_district_is_validated_and_normalized(district):
    validator = TexasDataValidator()
    assert validator.validate_district(district) == (True, None)
    assert validator.normalize_district(district) == "6E"


@pytest.mark.parametrize("district", ["07", "8B", "12", "20", "invalid", ""])
def test_nonproduction_district_names_remain_unassigned(district):
    validator = TexasDataValidator()
    assert validator.validate_district(district)[0] is False
    assert validator.normalize_district(district) is None


@pytest.mark.parametrize("district", ["6E", "6e", " 6e "])
def test_east_texas_district_lookup(district):
    assert get_district_info(district) == {"name": "District 6E"}


@pytest.mark.parametrize("unknown", ["", "invalid", "8B", "07", "12", "20"])
def test_csv_route_retains_qualified_districts_and_unassigned_totals(tmp_path, unknown):
    """Synthetic oil totals 1,150 BBL; gas totals 540 MCF, exactly.

    Assigned oil: 6E=125, 7B=200, 7C=300, 8A=400, 03=50 BBL.
    Unassigned oil=75 BBL and gas=30 MCF for each invalid/blank case.
    The repeated 6E lease contributes production once per row, one lease.
    """
    (tmp_path / "production.csv").write_text(
        "district,oil_production,gas_production,lease_number\n"
        "6E,100,0,1\n6e,25,0,1\n7B,200,100,2\n7C,300,150,3\n"
        f"8A,400,200,4\n03,50,60,5\n{unknown},75,30,6\n",
        encoding="utf-8",
    )
    cfg = {
        "basename": "texas_rrc",
        "data_types": ["production"],
        "districts": ["03", "6E", "7B", "7C", "8A"],
        "data": {"source": "csv", "files": {"production": "production.csv"}},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(tmp_path / "outputs"),
        },
    }
    result = TexasRRC().router(cfg)["texas_rrc"]
    assert result["status"] == "completed"
    assert result["data"]["errors"] == {}
    districts = pd.read_csv(result["outputs"]["districts_csv"], dtype={"district": str})
    assigned = districts.loc[districts["district"].notna()].set_index("district")
    assert assigned["oil_production"].to_dict() == {
        "03": 50,
        "6E": 125,
        "7B": 200,
        "7C": 300,
        "8A": 400,
    }
    assert assigned["gas_production"].to_dict() == {
        "03": 60,
        "6E": 0,
        "7B": 100,
        "7C": 150,
        "8A": 200,
    }
    assert assigned["lease_count"].to_dict() == {
        "03": 1,
        "6E": 1,
        "7B": 1,
        "7C": 1,
        "8A": 1,
    }
    unassigned = districts.loc[districts["district"].isna()]
    assert len(unassigned) == 1
    assert unassigned["oil_production"].tolist() == [75]
    assert unassigned["gas_production"].tolist() == [30]
    assert unassigned["lease_count"].tolist() == [1]
    assert districts["oil_production"].sum() == 1150
    assert districts["gas_production"].sum() == 540
    summary = json.loads(Path(result["outputs"]["summary_json"]).read_text())
    assert summary == {
        "total_records": 7,
        "district_count": 5,
        "unclassified_records": 1,
        "unclassified_oil_production": 75,
        "oil_production_total": 1150,
        "gas_production_total": 540,
    }


def test_router_accepts_all_qualified_production_district_names():
    TexasRRC()._validate_config(
        {
            "districts": [
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
            ],
        }
    )


@pytest.mark.parametrize("district", ["6E", "6e", " 6e "])
def test_cli_accepts_east_texas_production_district(monkeypatch, district):
    received = []
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)

    # Collection is replaced at the network boundary; CLI validation stays real.
    def collect_locally(self, cfg):
        received.append(cfg["districts"])
        self._validate_config(cfg)
        return {"texas_rrc": {"data_collected": ["production"]}}

    monkeypatch.setattr(TexasRRC, "router", collect_locally)
    result = CliRunner().invoke(
        app,
        ["collect", "--districts", district, "--output", "unused"],
    )
    assert result.exit_code == 0, result.output
    assert "Collected" in result.output
    assert received == [["6E"]]


def test_district_consumers_match_qualified_production_reference():
    # Independently transcribed from DISTRICT_NAME, RRC PDQ manual, p. 26.
    expected = {
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
    }
    for districts in (
        TexasDataValidator.VALID_DISTRICTS,
        TexasRRC.VALID_DISTRICTS,
        CLI_DISTRICTS,
        TEXAS_DISTRICTS,
        ATLAS_DISTRICTS,
    ):
        assert set(districts) == expected
        assert len(districts) == len(expected)


@pytest.mark.parametrize("district", ["07", "8B"])
def test_router_rejects_unqualified_district_names(district):
    with pytest.raises(ValueError, match="Invalid districts"):
        TexasRRC()._validate_config({"districts": [district]})


@pytest.mark.parametrize("district", ["07", "8B"])
def test_cli_rejects_unqualified_district_names(district, tmp_path, monkeypatch):
    def unexpected_collection(self, cfg):
        pytest.fail("Invalid CLI input reached collection")

    monkeypatch.setattr(TexasRRC, "router", unexpected_collection)
    result = CliRunner().invoke(
        app,
        ["collect", "--districts", district, "--output", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "Invalid district" in result.output
