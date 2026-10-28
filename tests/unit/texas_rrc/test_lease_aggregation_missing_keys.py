"""Lease aggregation regressions with independent synthetic hand calculations.

Grouping contract: pandas 2.3 DataFrame.groupby, dropna parameter and Examples
(retrieved 2026-10-21), and issue #1634. Volumes below are chosen test inputs, not observations
or physical conversion factors; each expected sum is written out in its test.
"""

import pandas as pd
import pytest

from worldenergydata.texas_rrc.processors.production_processor import (
    ProductionProcessor,
)


@pytest.mark.parametrize("input_kind", ["records", "dataframe", "nullable"])
@pytest.mark.parametrize(
    "missing_key", ["lease_number", "district", "lease_name", "operator_name"]
)
@pytest.mark.parametrize(
    "missing", [None, float("nan"), pd.NA], ids=["none", "nan", "NA"]
)
def test_missing_key_preserves_repeated_lease_volumes(input_kind, missing_key, missing):
    """Hand calculation: missing rows sum oil 100+300=400, gas 10+30=40.

    Complete groups retain oil/gas 200/20 and 50/5. Overall oil is
    100+200+300+50=650 BBL; gas is 10+20+30+5=65 MCF. Other supplied
    columns sum water 1+2+3+5=11, condensate 2+4+6+10=22, BOE 4+8+12+20=44.
    BOE is supplied directly to test summation without a conversion coefficient.
    Three composite groups remain, including one shared incomplete group.
    """
    frame = pd.DataFrame(
        {
            "lease_number": ["L1", "L1", "L1", "L2"],
            "district": ["7B", "7B", "7B", "7B"],
            "lease_name": ["Lease A", "Lease A", "Lease A", "Lease B"],
            "operator_name": ["Operator A"] * 4,
            "oil_production": [100, 200, 300, 50],
            "gas_production": [10, 20, 30, 5],
            "water_production": [1, 2, 3, 5],
            "condensate": [2, 4, 6, 10],
            "boe_total": [4, 8, 12, 20],
        }
    )
    frame.loc[[0, 2], missing_key] = missing
    if input_kind == "nullable":
        frame[missing_key] = frame[missing_key].astype("string")
    original = frame.copy(deep=True)
    data = frame.to_dict("records") if input_kind == "records" else frame

    result = ProductionProcessor().aggregate_by_lease(data)

    expected_totals = {
        "oil_production": 650,
        "gas_production": 65,
        "water_production": 11,
        "condensate": 22,
        "boe_total": 44,
    }
    for column, expected in expected_totals.items():
        assert frame[column].sum() == expected
        assert result[column].sum() == expected
    assert len(result) == 3
    incomplete = result[result[missing_key].isna()]
    assert len(incomplete) == 1
    assert incomplete.iloc[0]["oil_production"] == 400
    assert incomplete.iloc[0]["gas_production"] == 40
    complete = result[result[missing_key].notna()]
    assert sorted(zip(complete["oil_production"], complete["gas_production"])) == [
        (50, 5),
        (200, 20),
    ]
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("as_records", [False, True], ids=["dataframe", "records"])
def test_all_keys_missing_retains_one_unidentified_group(as_records):
    """Two unidentified rows give oil 100+300=400 and gas 10+30=40.

    No complete key exists, so exactly one composite group remains. None, NaN
    and pd.NA represent missing keys, not different anonymous identities.
    """
    frame = pd.DataFrame(
        {
            "lease_number": [None, pd.NA],
            "district": [float("nan"), None],
            "lease_name": [pd.NA, None],
            "operator_name": [None, float("nan")],
            "oil_production": [100, 300],
            "gas_production": [10, 30],
        }
    )
    data = frame.to_dict("records") if as_records else frame
    result = ProductionProcessor().aggregate_by_lease(data)
    assert len(result) == 1
    assert result.iloc[0]["oil_production"] == 400
    assert result.iloc[0]["gas_production"] == 40
    for key in ["lease_number", "district", "lease_name", "operator_name"]:
        assert result[key].isna().all()


@pytest.mark.parametrize("as_records", [False, True], ids=["dataframe", "records"])
def test_process_then_aggregate_issue_example(as_records):
    """Issue #1634 inputs: blank/100, 7B/200, blank/300 BBL, distinct leases.

    Independent extension supplies 10,20,30 MCF. Hand totals are
    100+200+300=600 BBL and 10+20+30=60 MCF, across three distinct leases.
    The complete 7B lease retains 200 BBL and 20 MCF.
    """
    frame = pd.DataFrame(
        {
            "lease_number": ["L1", "L2", "L3"],
            "district": ["", "7B", ""],
            "lease_name": [None, "Lease B", "Lease C"],
            "operator_name": ["Operator A", "Operator A", None],
            "oil_production": [100, 200, 300],
            "gas_production": [10, 20, 30],
        }
    )
    data = frame.to_dict("records") if as_records else frame
    processor = ProductionProcessor()
    processed = processor.process(data, validate=False)
    processed_frame = pd.DataFrame(processed)
    result = processor.aggregate_by_lease(processed)

    assert len(processed) == 3
    assert len(result) == 3
    assert processed_frame["oil_production"].sum() == 600
    assert result["oil_production"].sum() == 600
    assert processed_frame["gas_production"].sum() == 60
    assert result["gas_production"].sum() == 60
    assigned = result[result["district"] == "7B"]
    assert assigned.iloc[0]["oil_production"] == 200
    assert assigned.iloc[0]["gas_production"] == 20


def test_complete_composite_keys_remain_distinct():
    """Hand sums: L1/A/X/7B gives oil 100+200=300, gas 10+20=30.

    Changing each key independently leaves singleton groups at 50/5, 60/6,
    70/7 and 80/8; totals are 560 BBL and 56 MCF. Empty names are literal
    values and remain distinct from missing names at 90/9 and 110/11.
    """
    records = [
        ["L1", "Lease A", "Operator A", "7B", 100, 10],
        ["L1", "Lease A", "Operator A", "7B", 200, 20],
        ["L2", "Lease A", "Operator A", "7B", 50, 5],
        ["L1", "Lease B", "Operator A", "7B", 60, 6],
        ["L1", "Lease A", "Operator B", "7B", 70, 7],
        ["L1", "Lease A", "Operator A", "7C", 80, 8],
        ["L1", "", "Operator A", "7B", 90, 9],
        ["L1", None, "Operator A", "7B", 110, 11],
    ]
    frame = pd.DataFrame(
        records,
        columns=[
            "lease_number",
            "lease_name",
            "operator_name",
            "district",
            "oil_production",
            "gas_production",
        ],
    )
    result = ProductionProcessor().aggregate_by_lease(frame)
    complete = result[result["lease_name"].notna() & result["lease_name"].ne("")]
    assert sorted(zip(complete["oil_production"], complete["gas_production"])) == [
        (50, 5),
        (60, 6),
        (70, 7),
        (80, 8),
        (300, 30),
    ]
    assert complete["oil_production"].sum() == 560
    assert complete["gas_production"].sum() == 56
    assert result.loc[result["lease_name"].eq(""), "oil_production"].item() == 90
    assert result.loc[result["lease_name"].isna(), "oil_production"].item() == 110
