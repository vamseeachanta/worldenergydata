"""Regression coverage for district data loss on the local CSV route."""

import json
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.texas_rrc.data.loaders.csv_loader import CSVLoader
from worldenergydata.texas_rrc.processors.production_processor import (
    ProductionProcessor,
)
from worldenergydata.texas_rrc.texas_rrc import TexasRRC


# Source: validators.py, TexasDataValidator.VALID_DISTRICTS and
# normalize_district; repository district contract at the regression baseline.
@pytest.mark.parametrize(
    "district", ["01", "02", "03", "04", "05", "06", "7B", "7C", "08", "8A", "09", "10"]
)
@pytest.mark.parametrize("route", ["string", "file", "stream"])
def test_csv_preserves_district_codes(district, route, tmp_path):
    """A district is a text identifier; exact equality is the criterion."""
    content = f"DISTRICT_NO\n{district}\n"
    mapping = {"DISTRICT_NO": "district"}
    loader = CSVLoader()
    if route == "string":
        records = loader.load_from_string(content, field_mapping=mapping)
    else:
        path = tmp_path / "production.csv"
        path.write_text(content, encoding="utf-8")
        if route == "file":
            records = loader.load(path, field_mapping=mapping)
        else:
            records = list(loader.iter_records(path, field_mapping=mapping))
    assert [record["district"] for record in records] == [district]


@pytest.mark.parametrize("district", [" 7b ", "7c", "8a"])
def test_csv_district_normalization_stays_in_processor(district):
    """Source: validators.py, normalize_district strips and uppercases codes."""
    records = CSVLoader().load_from_string(f"district\n{district}\n")
    result = ProductionProcessor().process(records, validate=False)
    assert result[0]["district"] == district.strip().upper()


@pytest.mark.parametrize("district", ["7B", "7C", "8A"])
def test_csv_single_district_retains_production(district):
    """Issue 1246 example: one 100 BBL row gives 100 BBL, zero BBL error.

    The same synthetic case is extended to each affected district; total
    record oil = 100 BBL = district oil, with no conversion or tolerance.
    """
    records = CSVLoader().load_from_string(f"district,oil_production\n{district},100\n")
    processor = ProductionProcessor()
    result = processor.aggregate_by_district(processor.process(records, validate=False))
    assert result["district"].tolist() == [district]
    assert result["oil_production"].tolist() == [100]
    assert result["oil_production"].sum() == sum(
        record["oil_production"] for record in records
    )


@pytest.mark.parametrize(
    "field",
    ["oil_production", "gas_production", "water_production", "condensate", "boe_total"],
)
@pytest.mark.parametrize("as_dataframe", [False, True])
def test_all_missing_districts_retain_each_volume(field, as_dataframe):
    """Synthetic sum: 100 + 25 = 125 in each input column's own units.

    Oil, water and condensate are BBL, gas is MCF and boe_total is BOE.
    Inputs are already processed; no physical conversion is performed.
    pandas 2.3.3 (2025), DataFrame.groupby, dropna=False retains NA keys.
    """
    records = [{"district": None, field: 100}, {"district": None, field: 25}]
    data = pd.DataFrame(records) if as_dataframe else records
    result = ProductionProcessor().aggregate_by_district(data)
    assert result["district"].isna().all()
    assert result[field].tolist() == [125]


@pytest.mark.parametrize("unknown", [None, "", "invalid", float("nan")])
@pytest.mark.parametrize("as_dataframe", [False, True])
@pytest.mark.parametrize("with_leases", [False, True])
def test_missing_district_retains_volumes_and_lease_counts(
    unknown, as_dataframe, with_leases
):
    """Synthetic hand calculation, independent of the implementation.

    Known oil = 100 BBL; unclassified oil = 200 + 50 + 25 = 275 BBL;
    total oil = 100 + 275 = 375 BBL. The unclassified leases are A, A, B,
    so their distinct count is 2; the known group contains one lease C.
    Gas is zero MCF in every record, so BOE equals oil without conversion.
    Retention basis: pandas 2.3.3 (2025), DataFrame.groupby, dropna=False.
    """
    records = [
        {"district": "03", "oil_production": 100, "gas_production": 0},
        {"district": unknown, "oil_production": 200, "gas_production": 0},
        {"district": unknown, "oil_production": 50, "gas_production": 0},
        {"district": unknown, "oil_production": 25, "gas_production": 0},
    ]
    if with_leases:
        for record, lease in zip(records, ["C", "A", "A", "B"]):
            record["lease_number"] = lease
    data = pd.DataFrame(records) if as_dataframe else records
    processor = ProductionProcessor()
    processed = processor.process(data, validate=False)
    result = processor.aggregate_by_district(processed)
    known = result.loc[result["district"] == "03"].iloc[0]
    missing = result.loc[result["district"].isna()].iloc[0]
    assert known["oil_production"] == 100
    assert missing["oil_production"] == 275
    assert result["oil_production"].sum() == 375
    assert missing["boe_total"] == 275
    assert missing["gas_production"] == 0
    if with_leases:
        assert known["lease_count"] == 1
        assert missing["lease_count"] == 2
    else:
        assert "lease_count" not in result.columns


@pytest.mark.parametrize("unknown", [None, "", "invalid"])
def test_csv_router_outputs_conserve_district_totals(tmp_path, unknown):
    """Synthetic hand calculation for the complete local CSV route.
    Source case: issue 1246 requires 7B oil of 100 BBL with zero error.
    Oil by district: 7B = 100 + 25 = 125, 7C = 200, 8A = 300, 03 = 40 BBL.
    Total = 125 + 200 + 300 + 40 = 665 BBL from five records, four groups.
    An optional unknown adds 50 BBL: total = 715 BBL, six records, five
    groups. Gas is zero MCF throughout. Exact equality is required because
    these integer sums are exactly representable. No measured data is used.
    """
    content = (
        "district,oil_production,gas_production,lease_number\n"
        "7B,100,0,1\n7C,200,0,2\n8A,300,0,3\n03,40,0,4\n7B,25,0,1\n"
    )
    if unknown is not None:
        content += f"{unknown},50,0,5\n"
    (tmp_path / "production.csv").write_text(content, encoding="utf-8")
    cfg = {
        "basename": "texas_rrc",
        "data_types": ["production"],
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
    summary = json.loads(Path(result["outputs"]["summary_json"]).read_text())
    known = districts.loc[districts["district"].notna()].set_index("district")
    assert known["oil_production"].to_dict() == {
        "03": 40,
        "7B": 125,
        "7C": 200,
        "8A": 300,
    }
    assert known["lease_count"].to_dict() == {"03": 1, "7B": 1, "7C": 1, "8A": 1}
    if unknown is not None:
        missing = districts.loc[districts["district"].isna()].iloc[0]
        assert missing["oil_production"] == 50
        assert missing["lease_count"] == 1
    expected_total = 665 if unknown is None else 715
    assert districts["oil_production"].sum() == expected_total
    assert summary == {
        "total_records": 5 if unknown is None else 6,
        "district_count": 4 if unknown is None else 5,
        "oil_production_total": expected_total,
        "gas_production_total": 0,
    }
