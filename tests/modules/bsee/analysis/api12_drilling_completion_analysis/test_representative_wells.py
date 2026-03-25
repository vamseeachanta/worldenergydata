"""
Test representative well selection for API12 drilling completion analysis.

This module tests the selection of one high-difference and one low-difference well
for detailed methodology comparison.
"""

import pandas as pd
import pytest

from tests.modules.bsee.analysis.api12_drilling_completion_analysis.data_loader import (
    calculate_differences,
    load_and_prepare_data,
)
from tests.modules.bsee.analysis.api12_drilling_completion_analysis.well_selector import (
    generate_well_comparison_summary,
    get_well_details,
    select_representative_wells,
)


class TestRepresentativeWells:
    """Test class for representative well selection."""

    def test_select_high_and_low_difference_wells(self):
        """Test selection of one high-difference and one low-difference well."""
        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)
        comparison_df = calculate_differences(lease_df, api12_df)

        # Select representative wells
        high_well, low_well = select_representative_wells(comparison_df)

        # Verify they are different wells
        assert high_well["api12"] != low_well["api12"]

        # High well should have higher total difference than low well
        assert high_well["total_diff"] > low_well["total_diff"]

        print("HIGH DIFFERENCE WELL SELECTED FOR ANALYSIS:")
        print("=" * 50)
        print(f"API12: {high_well['api12']}")
        print(f"Field: {high_well['field_name']}")
        print(f"Well Name: {high_well['well_name']}")
        print(f"Lease Drilling Days: {high_well['lease_drilling_days']}")
        print(f"API12 Drilling Days: {high_well['api12_drilling_days']}")
        print(f"Drilling Difference: {high_well['drilling_diff']} days")
        print(f"Lease Completion Days: {high_well['lease_completion_days']}")
        print(f"API12 Completion Days: {high_well['api12_completion_days']}")
        print(f"Completion Difference: {high_well['completion_diff']} days")
        print(f"TOTAL DIFFERENCE: {high_well['total_diff']} days")

        print("\nLOW DIFFERENCE WELL SELECTED FOR ANALYSIS:")
        print("=" * 50)
        print(f"API12: {low_well['api12']}")
        print(f"Field: {low_well['field_name']}")
        print(f"Well Name: {low_well['well_name']}")
        print(f"Lease Drilling Days: {low_well['lease_drilling_days']}")
        print(f"API12 Drilling Days: {low_well['api12_drilling_days']}")
        print(f"Drilling Difference: {low_well['drilling_diff']} days")
        print(f"Lease Completion Days: {low_well['lease_completion_days']}")
        print(f"API12 Completion Days: {low_well['api12_completion_days']}")
        print(f"Completion Difference: {low_well['completion_diff']} days")
        print(f"TOTAL DIFFERENCE: {low_well['total_diff']} days")

        # Store these wells for future analysis
        return {
            "high_difference_well": {
                "api12": int(high_well["api12"]),
                "field_name": high_well["field_name"],
                "well_name": high_well["well_name"],
                "total_diff": float(high_well["total_diff"]),
            },
            "low_difference_well": {
                "api12": int(low_well["api12"]),
                "field_name": low_well["field_name"],
                "well_name": low_well["well_name"],
                "total_diff": float(low_well["total_diff"]),
            },
        }

    def test_detailed_well_comparison(self):
        """Test detailed comparison of selected wells."""
        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)
        comparison_df = calculate_differences(lease_df, api12_df)

        # Select representative wells
        high_well, low_well = select_representative_wells(comparison_df)

        # Get detailed information
        high_details = get_well_details(comparison_df, high_well["api12"])
        low_details = get_well_details(comparison_df, low_well["api12"])

        print("\nDETAILED COMPARISON:")
        print("=" * 60)

        print("\nHIGH DIFFERENCE WELL DETAILS:")
        print("-" * 30)
        for key, value in high_details.items():
            print(f"{key}: {value}")

        print("\nLOW DIFFERENCE WELL DETAILS:")
        print("-" * 30)
        for key, value in low_details.items():
            print(f"{key}: {value}")

        # Verify details match
        assert high_details["api12"] == high_well["api12"]
        assert low_details["api12"] == low_well["api12"]

        return high_details, low_details

    def test_comprehensive_summary_generation(self):
        """Test generation of comprehensive well comparison summary."""
        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)

        # Generate comprehensive summary
        summary = generate_well_comparison_summary(lease_df, api12_df)

        print("\nCOMPREHENSIVE ANALYSIS SUMMARY:")
        print("=" * 50)
        print(f"Total Wells: {summary['summary']['total_wells']}")
        print(f"Total Fields: {summary['summary']['total_fields']}")
        print(f"Fields: {', '.join(summary['summary']['fields'])}")

        # Overall statistics
        print(f"\nOVERALL DRILLING DIFFERENCE STATISTICS:")
        drilling_stats = summary["overall_statistics"]["drilling_diff"]
        print(f"  Mean: {drilling_stats['mean']:.2f} days")
        print(f"  Std Dev: {drilling_stats['std']:.2f} days")
        print(
            f"  Range: {drilling_stats['min']:.1f} to {drilling_stats['max']:.1f} days"
        )
        print(f"  Median: {drilling_stats['median']:.1f} days")

        print(f"\nOVERALL COMPLETION DIFFERENCE STATISTICS:")
        completion_stats = summary["overall_statistics"]["completion_diff"]
        print(f"  Mean: {completion_stats['mean']:.2f} days")
        print(f"  Std Dev: {completion_stats['std']:.2f} days")
        print(
            f"  Range: {completion_stats['min']:.1f} to {completion_stats['max']:.1f} days"
        )
        print(f"  Median: {completion_stats['median']:.1f} days")

        print(f"\nOVERALL TOTAL DIFFERENCE STATISTICS:")
        total_stats = summary["overall_statistics"]["total_diff"]
        print(f"  Mean: {total_stats['mean']:.2f} days")
        print(f"  Std Dev: {total_stats['std']:.2f} days")
        print(f"  Range: {total_stats['min']:.1f} to {total_stats['max']:.1f} days")
        print(f"  Median: {total_stats['median']:.1f} days")

        # Representative wells
        print(f"\nREPRESENTATIVE WELLS SELECTED:")
        high_rep = summary["representative_wells"]["high_difference"]
        low_rep = summary["representative_wells"]["low_difference"]

        print(f"\nHigh Difference Well:")
        print(f"  API12: {high_rep['api12']}")
        print(f"  Field: {high_rep['field_name']}")
        print(f"  Well Name: {high_rep['well_name']}")
        print(f"  Total Difference: {high_rep['total_diff']} days")

        print(f"\nLow Difference Well:")
        print(f"  API12: {low_rep['api12']}")
        print(f"  Field: {low_rep['field_name']}")
        print(f"  Well Name: {low_rep['well_name']}")
        print(f"  Total Difference: {low_rep['total_diff']} days")

        return summary

    def test_save_selected_wells_info(self):
        """Save the selected wells information to a file for later analysis."""
        import json

        lease_file = "tests/modules/bsee/analysis/results/drilling_and_completion_days_by_api_validation_20250805_191100.xlsx"
        api12_file = "tests/modules/bsee/analysis/results/well_summ_multiple_wells.csv"

        # Load and prepare data
        lease_df, api12_df = load_and_prepare_data(lease_file, api12_file)

        # Generate comprehensive summary
        summary = generate_well_comparison_summary(lease_df, api12_df)

        # Create selected wells info
        selected_wells_info = {
            "analysis_date": "2025-08-06",
            "total_wells_analyzed": summary["summary"]["total_wells"],
            "selected_wells": {
                "high_difference_well": {
                    "api12": int(
                        summary["representative_wells"]["high_difference"]["api12"]
                    ),
                    "field_name": summary["representative_wells"]["high_difference"][
                        "field_name"
                    ],
                    "well_name": summary["representative_wells"]["high_difference"][
                        "well_name"
                    ],
                    "total_difference": float(
                        summary["representative_wells"]["high_difference"]["total_diff"]
                    ),
                    "drilling_difference": float(
                        summary["representative_wells"]["high_difference"][
                            "drilling_diff"
                        ]
                    ),
                    "completion_difference": float(
                        summary["representative_wells"]["high_difference"][
                            "completion_diff"
                        ]
                    ),
                },
                "low_difference_well": {
                    "api12": int(
                        summary["representative_wells"]["low_difference"]["api12"]
                    ),
                    "field_name": summary["representative_wells"]["low_difference"][
                        "field_name"
                    ],
                    "well_name": summary["representative_wells"]["low_difference"][
                        "well_name"
                    ],
                    "total_difference": float(
                        summary["representative_wells"]["low_difference"]["total_diff"]
                    ),
                    "drilling_difference": float(
                        summary["representative_wells"]["low_difference"][
                            "drilling_diff"
                        ]
                    ),
                    "completion_difference": float(
                        summary["representative_wells"]["low_difference"][
                            "completion_diff"
                        ]
                    ),
                },
            },
            "analysis_summary": {
                "mean_drilling_diff": summary["overall_statistics"]["drilling_diff"][
                    "mean"
                ],
                "mean_completion_diff": summary["overall_statistics"][
                    "completion_diff"
                ]["mean"],
                "mean_total_diff": summary["overall_statistics"]["total_diff"]["mean"],
            },
        }

        # Save to results directory
        output_file = "tests/modules/bsee/analysis/api12_drilling_completion_analysis/results/selected_wells_info.json"
        with open(output_file, "w") as f:
            json.dump(selected_wells_info, f, indent=2)

        print(f"\nSelected wells information saved to: {output_file}")

        return selected_wells_info


if __name__ == "__main__":
    test = TestRepresentativeWells()
    test.test_select_high_and_low_difference_wells()
    test.test_detailed_well_comparison()
    test.test_comprehensive_summary_generation()
    test.test_save_selected_wells_info()
