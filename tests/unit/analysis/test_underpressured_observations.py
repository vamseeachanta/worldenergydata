"""Unit tests for under-pressured screen observation loading (#732)."""

import json

import pandas as pd

from worldenergydata.analysis.underpressured_screen.observations import (
    load_observations,
    normalize_observations,
)


def test_normalizes_texas_pressure_schema_to_screen_contract():
    frame = pd.DataFrame(
        [
            {
                "api14": "42127373050000",
                "field_name": "BRISCOE RANCH (EAGLEFORD)",
                "test_year": 2017,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 1046.7,
                "reference_depth_ft": 7394.0,
                "usable_for_virgin_pressure_proxy": True,
                "is_earliest_observation_for_well": True,
                "gradient_method": "surface_pressure_over_reference_depth_screening_only",
            }
        ]
    )

    result = normalize_observations(
        frame,
        {
            "name": "texas_rrc_completion_packets",
            "schema": "texas_rrc_pressure_v1",
            "state": "TX",
            "era": "completion_packet_screening",
            "require_usable_proxy": True,
        },
    )

    assert result.loc[0, "well_key"] == "42127373050000"
    assert result.loc[0, "field"] == "BRISCOE RANCH (EAGLEFORD)"
    assert result.loc[0, "state"] == "TX"
    assert result.loc[0, "source_name"] == "texas_rrc_completion_packets"
    assert result.loc[0, "era"] == "completion_packet_screening"
    assert result.loc[0, "pressure_kind"] == "WHP_shut_in"


def test_filters_texas_unusable_rows_when_required():
    frame = pd.DataFrame(
        [
            {
                "api14": "42127373050000",
                "field_name": "BRISCOE RANCH (EAGLEFORD)",
                "test_year": 2017,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 1046.7,
                "reference_depth_ft": 7394.0,
                "usable_for_virgin_pressure_proxy": True,
            },
            {
                "api14": "42127373100000",
                "field_name": "BRISCOE RANCH (EAGLEFORD)",
                "test_year": 2017,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 788.7,
                "reference_depth_ft": 12740.5,
                "usable_for_virgin_pressure_proxy": False,
            },
        ]
    )

    result = normalize_observations(
        frame,
        {
            "name": "texas_rrc_completion_packets",
            "schema": "texas_rrc_pressure_v1",
            "state": "TX",
            "era": "completion_packet_screening",
            "require_usable_proxy": True,
        },
    )

    assert list(result["well_key"]) == ["42127373050000"]


def test_normalizes_oklahoma_occ_completion_schema_to_screen_contract():
    frame = pd.DataFrame(
        [
            {
                "well_key": "3500323456",
                "formation_name": "MORROW",
                "test_year": 2024,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 139.7,
                "reference_depth_ft": 5100.0,
                "is_earliest_observation": True,
            },
            {
                "well_key": "3500323456",
                "formation_name": "MORROW",
                "test_year": 2025,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 120.0,
                "reference_depth_ft": 5100.0,
                "is_earliest_observation": False,
            },
        ]
    )

    result = normalize_observations(
        frame,
        {
            "name": "oklahoma_occ_completions",
            "schema": "oklahoma_occ_completion_v1",
            "state": "OK",
            "era": "completion_test_2010_present",
        },
    )

    assert list(result["well_key"]) == ["3500323456", "3500323456"]
    assert list(result["field"]) == ["MORROW", "MORROW"]
    assert list(result["state"]) == ["OK", "OK"]
    assert list(result["source_name"]) == [
        "oklahoma_occ_completions",
        "oklahoma_occ_completions",
    ]
    assert list(result["era"]) == [
        "completion_test_2010_present",
        "completion_test_2010_present",
    ]
    assert list(result["screen_observation_priority"]) == [0, 1]


def test_load_observations_collects_input_counts_and_quality_warnings(tmp_path):
    observations_path = tmp_path / "texas.parquet"
    quality_path = tmp_path / "quality.json"
    pd.DataFrame(
        [
            {
                "api14": "42127373050000",
                "field_name": "BRISCOE RANCH (EAGLEFORD)",
                "test_year": 2017,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 1046.7,
                "reference_depth_ft": 7394.0,
                "usable_for_virgin_pressure_proxy": True,
            }
        ]
    ).to_parquet(observations_path)
    quality_path.write_text(
        json.dumps(
            {
                "source_warnings": [
                    "raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z"
                ]
            }
        ),
        encoding="utf-8",
    )

    observations, summary = load_observations(
        [
            {
                "name": "texas_rrc_completion_packets",
                "path": str(observations_path),
                "quality_path": str(quality_path),
                "schema": "texas_rrc_pressure_v1",
                "state": "TX",
                "era": "completion_packet_screening",
                "require_usable_proxy": True,
            }
        ]
    )

    assert len(observations) == 1
    assert summary["input_row_counts"] == {"texas_rrc_completion_packets": 1}
    assert summary["loaded_row_counts"] == {"texas_rrc_completion_packets": 1}
    assert summary["source_warnings"] == {
        "texas_rrc_completion_packets": [
            "raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z"
        ]
    }
