"""Regression coverage for district totals emitted by the local CSV route."""

import json

import pandas as pd
import pytest


def _run_csv_route(tmp_path, rows):
    from worldenergydata.texas_rrc.texas_rrc import TexasRRC

    source = tmp_path / "production.csv"
    source.write_text(
        "district,lease_number,oil_production,gas_production\n" + rows,
        encoding="utf-8",
    )
    cfg = {
        "module": "texas_rrc",
        "data_types": ["production"],
        "data": {"source": "csv", "files": {"production": source.name}},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(tmp_path / "results"),
        },
    }
    result = TexasRRC().router(cfg)
    assert result["texas_rrc"]["status"] == "completed"
    assert result["texas_rrc"]["data"]["errors"] == {}
    outputs = result["texas_rrc"]["outputs"]
    districts = pd.read_csv(outputs["districts_csv"], dtype={"district": "string"})
    with open(outputs["summary_json"], encoding="utf-8") as stream:
        summary = json.load(stream)
    return districts, summary


# Codes: validators.py, TexasDataValidator.VALID_DISTRICTS; issue #1246.
@pytest.mark.parametrize("district", ["7B", "7C", "8A"])
def test_alphanumeric_district_single_record(tmp_path, district):
    """Issue #1246 example: one 100 BBL record sums to 100 BBL, error 0 BBL.

    Each synthetic record has zero gas, one lease and one district. The
    expected total is the input itself, with no conversion or tolerance.
    """
    districts, summary = _run_csv_route(tmp_path, f"{district},1,100,0\n")
    assert districts["district"].tolist() == [district]
    assert districts["oil_production"].tolist() == [100.0]
    assert districts["lease_count"].tolist() == [1]
    assert summary == {
        "total_records": 1,
        "district_count": 1,
        "oil_production_total": 100.0,
        "gas_production_total": 0.0,
    }


@pytest.mark.parametrize("include_unknown", [False, True])
def test_csv_route_conserves_record_totals(tmp_path, include_unknown):
    """Hand calculation using synthetic records and exact integer sums.

    Codes follow validators.py, TexasDataValidator.VALID_DISTRICTS.
    Oil: 7B=100+50=150; 7C=200; 8A=300; 03=400; total=1050 BBL.
    Gas: 7B=10+5=15; 7C=20; 8A=30; 03=40; total=105 MCF.
    The repeated 7B lease counts once, so each district has one lease.
    With a blank and an invalid district, the unassigned group adds oil
    60+70=130 BBL and gas 6+7=13 MCF on two distinct leases. Totals then
    equal 1180 BBL and 118 MCF, with seven records and five groups rather
    than five records and four groups. No physical conversion is asserted.
    """
    rows = "7B,1,100,10\n7C,2,200,20\n8A,3,300,30\n03,4,400,40\n7B,1,50,5\n"
    if include_unknown:
        rows += ",5,60,6\ninvalid,6,70,7\n"
    districts, summary = _run_csv_route(tmp_path, rows)
    known = districts.loc[districts["district"].notna()].set_index("district")
    assert known["oil_production"].to_dict() == {
        "7B": 150.0,
        "7C": 200.0,
        "8A": 300.0,
        "03": 400.0,
    }
    assert known["gas_production"].to_dict() == {
        "7B": 15.0,
        "7C": 20.0,
        "8A": 30.0,
        "03": 40.0,
    }
    assert known["lease_count"].to_dict() == {"7B": 1, "7C": 1, "8A": 1, "03": 1}
    assert summary == {
        "total_records": 7 if include_unknown else 5,
        "district_count": 5 if include_unknown else 4,
        "oil_production_total": 1180.0 if include_unknown else 1050.0,
        "gas_production_total": 118.0 if include_unknown else 105.0,
    }
    assert districts["oil_production"].sum() == summary["oil_production_total"]
    assert districts["gas_production"].sum() == summary["gas_production_total"]
    missing = districts.loc[districts["district"].isna()]
    if include_unknown:
        assert missing["oil_production"].tolist() == [130.0]
        assert missing["gas_production"].tolist() == [13.0]
        assert missing["lease_count"].tolist() == [2]
    else:
        assert missing.empty
