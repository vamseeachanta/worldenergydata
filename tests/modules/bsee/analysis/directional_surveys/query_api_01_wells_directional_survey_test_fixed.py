#!/usr/bin/env python3
"""
Fixed version of query_api_01_wells_directional_survey_test.py

This test runs the directional surveys functionality without external dependencies.
It simulates the same workflow as the original YAML-based test but using direct method calls.
"""

import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12


def create_test_data_from_yaml():
    """
    Create test data that matches the YAML configuration:
    - API12: [608124000400]
    - Simulates real BSEE directional survey data
    """

    # Create realistic directional survey data for API12 608124000400
    # This simulates what would come from BSEE database
    directional_surveys = pd.DataFrame(
        {
            "API12": [608124000400] * 10,
            "API_WELL_NUMBER": [608124000400] * 10,
            "SURVEY_POINT_MD": [
                0,
                1000,
                2000,
                3000,
                4000,
                5000,
                6000,
                7000,
                8000,
                9000,
            ],
            "INCL_ANG_DEG_VAL": [0, 3, 8, 15, 22, 28, 35, 40, 45, 48],
            "INCL_ANG_MIN_VAL": [0, 15, 30, 0, 45, 15, 0, 30, 15, 0],
            "DIR_DEG_VAL": [0, 30, 75, 120, 150, 180, 210, 240, 270, 300],
            "DIR_MINS_VAL": [0, 0, 15, 30, 0, 15, 30, 0, 15, 30],
            "WELL_N_S_CODE": ["N"] * 10,
            "WELL_E_W_CODE": ["E"] * 10,
            "SURVEY_POINT_TVD": [
                0,
                999.5,
                1996.8,
                2988.1,
                3970.2,
                4940.5,
                5896.8,
                6837.2,
                7759.8,
                8662.5,
            ],
        }
    )

    # Create well data structure (this would come from BSEE well data)
    well_data = {
        "merged_api12_df": pd.DataFrame(
            {
                "API12": [608124000400],
                "API10": [6081240004],
                "Well Name": ["ST MALO A-001"],
                "Sidetrack and Bypass": ["ST01"],
                "SURF_x_rel": [2847.6],  # Surface position X relative to field center
                "SURF_y_rel": [1923.8],  # Surface position Y relative to field center
                "Water Depth (feet)": [4000],
                "Total Measured Depth": [18750],
                "Total Depth Date": ["2023-06-15"],
                "Spud Date": ["2023-04-10"],
            }
        )
    }

    return directional_surveys, well_data


def run_application_fixed():
    """
    Fixed version of run_application that doesn't require external engine.
    Simulates the same workflow as the YAML-based test.
    """

    print("Running directional survey analysis for API12: 608124000400")
    print("Simulating query_api_01_wells_directional_survey.yml workflow")
    print("=" * 70)

    # Create temporary directory for outputs
    temp_dir = tempfile.mkdtemp()

    try:
        # Configuration matching the YAML file
        cfg = {
            "meta": {
                "library": "worldenergydata",
                "basename": "bsee",
                "label": "goa_stmalo",
            },
            "basename": "bsee",
            "data": {
                "production_data": True,
                "groups": [
                    {
                        "bottom_block": None,
                        "bottom_lease": None,
                        "api12": [608124000400],
                    }
                ],
            },
            "analysis": {"flag": True},
            "Analysis": {
                "result_folder": f"{temp_dir}/",
                "file_name_for_overwrite": "query_api_01_wells_directional_survey",
            },
            "custom_parameters": {"field_nickname": "StMalo"},
        }

        # Create test data
        directional_surveys, well_data = create_test_data_from_yaml()

        # Initialize WellAPI12 instance
        well_api12 = WellAPI12()
        well_api12.cfg = cfg
        well_api12.output_data_api12_df = well_data["merged_api12_df"].copy()
        well_api12.output_data_api12_df["xyz"] = None

        print(f"Processing {len(directional_surveys)} directional survey points...")

        # Run the directional surveys workflow
        well_api12.prepare_well_paths(directional_surveys, well_data)

        # Verify results
        assert hasattr(
            well_api12, "output_data_well_path"
        ), "output_data_well_path not created"
        assert len(well_api12.output_data_well_path) > 0, "No well path data generated"
        assert (
            608124000400 in well_api12.output_data_well_path
        ), "API12 608124000400 not processed"

        well_path_data = well_api12.output_data_well_path[608124000400]

        print(f"✓ Well path generated: {len(well_path_data)} survey points")
        print(f"✓ XYZ coordinates calculated successfully")

        # Print coordinate summary
        x_range = well_path_data["x_coor"].max() - well_path_data["x_coor"].min()
        y_range = well_path_data["y_coor"].max() - well_path_data["y_coor"].min()
        z_range = well_path_data["z_coor"].max() - well_path_data["z_coor"].min()

        print(
            f"✓ X (Easting) range: {well_path_data['x_coor'].min():.1f} to {well_path_data['x_coor'].max():.1f} ft"
        )
        print(
            f"✓ Y (Northing) range: {well_path_data['y_coor'].min():.1f} to {well_path_data['y_coor'].max():.1f} ft"
        )
        print(
            f"✓ Z (TVD) range: {well_path_data['z_coor'].min():.1f} to {well_path_data['z_coor'].max():.1f} ft"
        )

        # Verify data was stored correctly
        xyz_data = well_api12.output_data_api12_df["xyz"].iloc[0]
        assert xyz_data is not None, "XYZ data not stored in output_data_api12_df"

        import json

        stored_data = json.loads(xyz_data)
        print(
            f"✓ Data stored: {len(stored_data['data'])} points with label '{stored_data['label']}'"
        )

        # Test 3D plotting (with mock to avoid display issues)
        from unittest.mock import Mock, patch

        with patch("matplotlib.pyplot.figure") as mock_figure, patch(
            "matplotlib.pyplot.close"
        ) as mock_close:

            mock_fig = Mock()
            mock_ax = Mock()
            mock_figure.return_value = mock_fig
            mock_fig.add_subplot.return_value = mock_ax
            mock_ax.get_xlim.return_value = (0, 5000)
            mock_ax.get_ylim.return_value = (0, 5000)

            well_api12.plot_field_wells()

            # Verify plotting was called
            mock_figure.assert_called_once()
            mock_ax.plot3D.assert_called()

            print("✓ 3D visualization generated successfully")

        print("=" * 70)
        print("🎉 DIRECTIONAL SURVEY TEST PASSED! 🎉")
        print("All four methods working correctly:")
        print("  ✓ prepare_well_paths")
        print("  ✓ process_survey_xyz")
        print("  ✓ add_relative_WH_positions")
        print("  ✓ plot_field_wells")

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_application():
    """Main test function that can be run by pytest"""

    print("\nExecuting fixed directional survey test...")
    print("This replaces the original engine-based test with direct method testing.")

    success = run_application_fixed()
    assert success, "Directional survey test failed"

    print("Test completed successfully!")


if __name__ == "__main__":
    """Run test when executed directly"""
    test_application()
