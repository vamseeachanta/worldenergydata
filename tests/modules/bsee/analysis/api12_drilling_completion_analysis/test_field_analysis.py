"""
Test field-based analysis for API12 drilling completion comparison.

This module tests the functionality for analyzing wells grouped by field/lease name.
"""

from pathlib import Path

import pandas as pd
import pytest

from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
    load_and_prepare_data,
)
from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
    analyze_wells_by_field,
    generate_well_comparison_summary,
    get_wells_by_field,
)

_LEASE_FILE = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
_API12_FILE = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"


@pytest.mark.skipif(
    not Path(_LEASE_FILE).exists() or not Path(_API12_FILE).exists(),
    reason="Requires BSEE data files (run 'make data' first)",
)
class TestFieldAnalysis:
    """Test class for field-based analysis functionality."""

    def test_field_analysis_with_actual_data(self):
        """Test field analysis using actual lease and API12 data."""
        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)

        # Generate comprehensive summary
        summary = generate_well_comparison_summary(lease_df, api12_df)

        # Test summary structure
        assert "summary" in summary
        assert "field_analysis" in summary
        assert "representative_wells" in summary

        # Test basic counts
        assert summary["summary"]["total_wells"] == 122
        assert (
            summary["summary"]["total_fields"] > 5
        )  # We know there are multiple fields

        # Test that major fields are present
        expected_fields = ["Anchor", "Cascade", "Chinook", "Stones", "St Malo"]
        for field in expected_fields:
            if (
                field in summary["summary"]["fields"]
            ):  # Some fields might not be in this dataset
                assert field in summary["field_analysis"]

        print(f"Total wells analyzed: {summary['summary']['total_wells']}")
        print(f"Total fields: {summary['summary']['total_fields']}")
        print(f"Fields: {summary['summary']['fields']}")

        # Test field analysis details
        for field_name, field_data in summary["field_analysis"].items():
            print(f"\n{field_name}:")
            print(f"  Total wells: {field_data['total_wells']}")
            print(f"  Wells analyzed: {field_data['wells_analyzed']}")

            # Each field should have statistics
            assert "field_statistics" in field_data
            assert "selected_wells" in field_data

            # Should select up to 2 wells per field
            assert len(field_data["selected_wells"]) <= 2
            assert field_data["wells_analyzed"] <= 2

            # Print selected wells for this field
            for i, well in enumerate(field_data["selected_wells"]):
                print(
                    f"    Well {i+1}: API12 {well['api12']}, Total Diff: {well['total_diff']}"
                )

    def test_get_wells_by_specific_fields(self):
        """Test getting wells from specific fields like Anchor, Cascade, Chinook."""
        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)

        # Calculate differences
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
            calculate_differences,
        )

        comparison_df = calculate_differences(lease_df, api12_df)

        # Test specific fields mentioned in the task
        target_fields = ["Anchor", "Cascade", "Chinook"]

        for field_name in target_fields:
            field_wells = get_wells_by_field(comparison_df, field_name, n_wells=2)

            if not field_wells.empty:  # Field exists in dataset
                print(f"\n{field_name} Wells:")

                # Should get up to 2 wells
                assert len(field_wells) <= 2

                # All wells should be from the specified field
                assert all(field_wells["field_name"] == field_name)

                # Print well details
                for _, well in field_wells.iterrows():
                    print(f"  API12: {well['api12']}")
                    print(f"    Well Name: {well['well_name']}")
                    print(f"    Lease Drilling Days: {well['lease_drilling_days']}")
                    print(f"    API12 Drilling Days: {well['api12_drilling_days']}")
                    print(f"    Drilling Difference: {well['drilling_diff']}")
                    print(f"    Lease Completion Days: {well['lease_completion_days']}")
                    print(f"    API12 Completion Days: {well['api12_completion_days']}")
                    print(f"    Completion Difference: {well['completion_diff']}")
                    print(f"    Total Difference: {well['total_diff']}")
                    print()
            else:
                print(f"{field_name}: No wells found in dataset")

    def test_export_field_analysis(self):
        """Test exporting field analysis to CSV."""
        import os
        import tempfile

        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
            export_field_analysis_to_csv,
        )

        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)

        # Generate analysis
        summary = generate_well_comparison_summary(lease_df, api12_df)

        # Export to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            export_field_analysis_to_csv(summary["field_analysis"], tmp_file.name)

            # Verify file was created and has content
            assert os.path.exists(tmp_file.name)

            # Read back and verify
            exported_df = pd.read_csv(tmp_file.name)
            assert not exported_df.empty
            assert "field_name" in exported_df.columns
            assert "api12" in exported_df.columns
            assert "total_diff" in exported_df.columns

            print(f"Exported {len(exported_df)} well records to CSV")
            print(f"Fields covered: {exported_df['field_name'].unique()}")

        # Clean up
        os.unlink(tmp_file.name)


if __name__ == "__main__":
    test = TestFieldAnalysis()
    test.test_field_analysis_with_actual_data()
    test.test_get_wells_by_specific_fields()
    test.test_export_field_analysis()
