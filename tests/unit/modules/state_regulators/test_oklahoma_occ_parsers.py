"""Tests for Oklahoma OCC completion-pressure parsing (#740)."""

import pandas as pd
import pytest

from worldenergydata.modules.state_regulators.oklahoma_occ.parsers import (
    build_pressure_observations,
    build_quality_stats,
    read_completion_workbook,
)


SETTINGS = {
    "atmospheric_psi": 14.7,
    "test_type": "OCC Form 1002A initial completion test",
    "gradient_method": "completion_pressure_over_reference_depth_screening_only",
    "depth_priority": [
        "True_Vertical_Depth",
        "Formation_Depth",
        "Measured_Total_Depth",
        "Total_Depth",
    ],
}


def test_read_completion_workbook_preserves_required_occ_columns(tmp_path):
    workbook = tmp_path / "completions.xlsx"
    pd.DataFrame(
        [
            {
                "API_Number": "3500323456",
                "Completion_No": "01",
                "Well_Name": "PANHANDLE TEST",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "TEXAS",
                "Formation_Name": "MORROW",
                "Test_Date": "2024-01-15",
                "Shut_In_Pressure": "125",
                "Flow_Tubing_Pressure": "80",
                "True_Vertical_Depth": "5100",
                "Measured_Total_Depth": "5400",
            }
        ]
    ).to_excel(workbook, index=False)

    frame = read_completion_workbook(workbook)

    assert frame.loc[0, "API_Number"] == "3500323456"
    assert frame.loc[0, "Completion_No"] == "01"
    assert frame.loc[0, "Shut_In_Pressure"] == 125
    assert frame.loc[0, "True_Vertical_Depth"] == 5100


def test_build_pressure_observations_coerces_pressure_depth_and_test_year():
    completions = pd.DataFrame(
        [
            {
                "API_Number": "3500323456",
                "Completion_No": "01",
                "Well_Name": "PANHANDLE TEST",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "TEXAS",
                "Formation_Name": "MORROW",
                "Test_Date": "2024-01-15",
                "Shut_In_Pressure": "125",
                "Flow_Tubing_Pressure": "80",
                "Gas_MCF_Per_Day": "2500",
                "Oil_BBL_Per_Day": "12",
                "Water_BBL_Per_Day": "3",
                "True_Vertical_Depth": "5100",
                "Formation_Depth": "5050",
                "Measured_Total_Depth": "5400",
                "Total_Depth": "5450",
            }
        ]
    )

    observations = build_pressure_observations(completions, SETTINGS)

    assert len(observations) == 1
    row = observations.iloc[0]
    assert row["state"] == "OK"
    assert row["well_key"] == "3500323456"
    assert row["api_number"] == "3500323456"
    assert row["completion_no"] == "01"
    assert row["test_year"] == 2024
    assert row["pressure_kind"] == "WHP_shut_in"
    assert row["pressure_psig_reported"] == 125
    assert row["pressure_psia"] == pytest.approx(139.7)
    assert row["reference_depth_ft"] == 5100
    assert row["reference_depth_source"] == "True_Vertical_Depth"
    assert row["gas_mcf_per_day"] == 2500
    assert row["is_earliest_observation"] is True


def test_build_pressure_observations_uses_flowing_pressure_when_shut_in_missing():
    completions = pd.DataFrame(
        [
            {
                "API_Number": "3500323456",
                "Completion_No": "02",
                "Well_Name": "PANHANDLE TEST",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "TEXAS",
                "Formation_Name": "MORROW",
                "Test_Date": "2024-02-15",
                "Shut_In_Pressure": None,
                "Flow_Tubing_Pressure": "80",
                "True_Vertical_Depth": None,
                "Formation_Depth": "5050",
            }
        ]
    )

    observations = build_pressure_observations(completions, SETTINGS)

    assert len(observations) == 1
    row = observations.iloc[0]
    assert row["pressure_kind"] == "WHP_flowing_tubing"
    assert row["pressure_psig_reported"] == 80
    assert row["reference_depth_ft"] == 5050
    assert row["reference_depth_source"] == "Formation_Depth"


def test_build_pressure_observations_filters_unusable_rows_and_flags_earliest():
    completions = pd.DataFrame(
        [
            {
                "API_Number": "3500323456",
                "Completion_No": "02",
                "Well_Name": "SECOND",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "TEXAS",
                "Formation_Name": "MORROW",
                "Test_Date": "2024-02-15",
                "Shut_In_Pressure": "90",
                "True_Vertical_Depth": "5000",
            },
            {
                "API_Number": "3500323456",
                "Completion_No": "01",
                "Well_Name": "FIRST",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "TEXAS",
                "Formation_Name": "MORROW",
                "Test_Date": "2023-12-31",
                "Shut_In_Pressure": "100",
                "True_Vertical_Depth": "5000",
            },
            {
                "API_Number": "3509923456",
                "Completion_No": "01",
                "Well_Name": "NO PRESSURE",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "BEAVER",
                "Formation_Name": "MORROW",
                "Test_Date": "2024-01-01",
                "Shut_In_Pressure": None,
                "Flow_Tubing_Pressure": None,
                "True_Vertical_Depth": "5000",
            },
            {
                "API_Number": "3513923456",
                "Completion_No": "01",
                "Well_Name": "NO DEPTH",
                "Operator_Name": "DIRECT SOURCE ENERGY",
                "County": "TEXAS",
                "Formation_Name": "MORROW",
                "Test_Date": "2024-01-01",
                "Shut_In_Pressure": "100",
                "True_Vertical_Depth": None,
            },
        ]
    )

    observations = build_pressure_observations(completions, SETTINGS)
    quality = build_quality_stats(completions, observations)

    assert list(observations["completion_no"]) == ["02", "01"]
    assert list(observations["is_earliest_observation"]) == [False, True]
    assert quality["input_rows"] == 4
    assert quality["curated_count"] == 2
    assert quality["filtered_missing_pressure_count"] == 1
    assert quality["filtered_missing_depth_count"] == 1
    assert quality["wells_with_pressure_observation"] == 1
