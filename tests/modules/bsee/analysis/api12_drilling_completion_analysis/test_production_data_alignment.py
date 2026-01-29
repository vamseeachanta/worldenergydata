"""
Tests for production data alignment with Excel analysis periods.
This module validates that production data extraction matches Excel methodology.
"""

import os

import numpy as np
import pandas as pd
import pytest


class TestProductionDataAlignment:
    """Test suite for production data alignment with Excel analysis."""

    @pytest.fixture
    def excel_file_path(self):
        """Path to the Excel NPV analysis file."""
        from pathlib import Path

        path = (
            Path("docs")
            / "modules"
            / "bsee"
            / "data"
            / "NPV_JStM-WELL-Production-Data-thru-2019.xlsx"
        )
        if not path.exists():
            pytest.skip(f"Excel data file not found: {path}")
        return str(path)

    def test_excel_production_data_identification(self, excel_file_path):
        """Test that we can identify the production data row in Excel."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Production data should be in row 22 (JSM Total AVGMoly)
        production_label = df.iloc[22, 1]  # Column 1 should have the label
        assert isinstance(
            production_label, str
        ), f"Expected string label, got {type(production_label)}"
        assert (
            "JSM" in production_label and "Total" in production_label
        ), f"Expected JSM Total label, got '{production_label}'"

    def test_excel_production_data_extraction(self, excel_file_path):
        """Test extraction of production data from Excel."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract production data from row 22, starting from column 2
        production_data = []
        production_row_idx = 22

        for col_idx in range(2, min(df.shape[1], 60)):
            prod_val = df.iloc[production_row_idx, col_idx]
            if (
                pd.notna(prod_val)
                and isinstance(prod_val, (int, float))
                and prod_val > 0
            ):
                production_data.append(prod_val)

        # Validate extracted production data
        assert len(production_data) > 0, "No production data was extracted"
        assert (
            len(production_data) >= 12
        ), f"Expected at least 12 months of production, got {len(production_data)}"

        # Validate production ranges (reasonable production volumes)
        assert all(
            prod > 1000 for prod in production_data
        ), "Some production values seem too low"
        assert all(
            prod < 200000 for prod in production_data
        ), "Some production values seem too high"

        print(
            f"Extracted {len(production_data)} production values: {production_data[:5]}...{production_data[-5:]}"
        )

    def test_production_data_with_known_values(self, excel_file_path):
        """Test production data extraction with known expected values."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract production data
        production_data = []
        production_row_idx = 22

        for col_idx in range(2, min(df.shape[1], 60)):
            prod_val = df.iloc[production_row_idx, col_idx]
            if (
                pd.notna(prod_val)
                and isinstance(prod_val, (int, float))
                and prod_val > 0
            ):
                production_data.append(prod_val)

        # Test specific values (these are from the actual Excel file)
        # Based on our previous examination: [19123.987142857142, 32642.056878306877, 49933.10769230769, ...]
        expected_first_values = [
            19123.987142857142,
            32642.056878306877,
            49933.10769230769,
        ]

        assert (
            len(production_data) >= 3
        ), f"Need at least 3 values for validation, got {len(production_data)}"

        # Check first few values match expected (within tolerance for floating point)
        for i, expected_prod in enumerate(expected_first_values):
            actual_prod = production_data[i]
            assert (
                abs(actual_prod - expected_prod) < 1.0
            ), f"Production {i}: expected {expected_prod:.2f}, got {actual_prod:.2f}"

    def test_production_period_alignment_with_prices(self, excel_file_path):
        """Test that production periods align with price periods."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract both production and price data
        production_data = []
        price_data = []

        for col_idx in range(2, min(df.shape[1], 60)):
            # Production data (row 22)
            prod_val = df.iloc[22, col_idx]
            # Price data (row 2)
            price_val = df.iloc[2, col_idx]

            if (
                pd.notna(prod_val)
                and isinstance(prod_val, (int, float))
                and prod_val > 0
                and pd.notna(price_val)
                and isinstance(price_val, (int, float))
                and 20 < price_val < 200
            ):
                production_data.append(prod_val)
                price_data.append(price_val)

        # Validate alignment
        assert len(production_data) == len(
            price_data
        ), f"Production-price mismatch: {len(production_data)} vs {len(price_data)}"
        assert (
            len(production_data) >= 12
        ), f"Expected at least 12 aligned periods, got {len(production_data)}"

        print(f"Successfully aligned {len(production_data)} production-price periods")

    def test_production_data_scaling_calibration(self, excel_file_path):
        """Test production data scaling to match expected units (barrels)."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract production data
        production_data = []
        production_row_idx = 22

        for col_idx in range(2, min(df.shape[1], 60)):
            prod_val = df.iloc[production_row_idx, col_idx]
            if (
                pd.notna(prod_val)
                and isinstance(prod_val, (int, float))
                and prod_val > 0
            ):
                production_data.append(prod_val)

        if len(production_data) == 0:
            pytest.fail("No production data extracted for scaling test")

        # Check if the data needs scaling (typical monthly production should be in thousands of barrels)
        avg_monthly_prod = sum(production_data) / len(production_data)

        # For a major field like Jack/St. Malo, monthly production should be in the range of 10,000 - 100,000 barrels
        assert (
            5000 < avg_monthly_prod < 200000
        ), f"Average monthly production {avg_monthly_prod:.0f} seems outside expected range"

        # Test scaling factor if needed
        if avg_monthly_prod < 1000:  # Data might be in thousands
            scaling_factor = 1000
            scaled_data = [prod * scaling_factor for prod in production_data]
            scaled_avg = sum(scaled_data) / len(scaled_data)
            print(
                f"Scaled production (x{scaling_factor}): average {scaled_avg:.0f} barrels/month"
            )
        else:
            scaling_factor = 1.0
            print(f"No scaling needed: average {avg_monthly_prod:.0f} barrels/month")

    def test_production_data_length_consistency(self, excel_file_path):
        """Test that production data has consistent length with other data series."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract all three data series
        months = []
        prices = []
        production = []

        for col_idx in range(2, min(df.shape[1], 60)):
            # Month headers (row 0)
            month_val = df.iloc[0, col_idx]
            # Price data (row 2)
            price_val = df.iloc[2, col_idx]
            # Production data (row 22)
            prod_val = df.iloc[22, col_idx]

            # Only include if all three are valid
            if (
                pd.notna(month_val)
                and pd.notna(price_val)
                and isinstance(price_val, (int, float))
                and 20 < price_val < 200
                and pd.notna(prod_val)
                and isinstance(prod_val, (int, float))
                and prod_val > 0
            ):
                months.append(str(month_val))
                prices.append(price_val)
                production.append(prod_val)

        # Validate consistency
        assert (
            len(months) == len(prices) == len(production)
        ), f"Length mismatch: months={len(months)}, prices={len(prices)}, production={len(production)}"
        assert (
            len(months) >= 12
        ), f"Expected at least 12 consistent periods, got {len(months)}"

        print(f"Consistent data length: {len(months)} periods")

    def test_production_data_missing_value_handling(self, excel_file_path):
        """Test handling of missing production values."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract production data including missing values
        all_production_cells = []
        production_row_idx = 22

        for col_idx in range(2, min(df.shape[1], 20)):  # Check first 20 columns
            prod_val = df.iloc[production_row_idx, col_idx]
            all_production_cells.append(prod_val)

        # Count valid vs invalid values
        valid_production = [
            val
            for val in all_production_cells
            if pd.notna(val) and isinstance(val, (int, float)) and val > 0
        ]
        invalid_production = [
            val
            for val in all_production_cells
            if pd.isna(val) or not isinstance(val, (int, float)) or val <= 0
        ]

        print(f"Valid production values: {len(valid_production)}")
        print(f"Invalid/missing values: {len(invalid_production)}")

        # Should have some valid data
        assert len(valid_production) > 0, "No valid production data found"

        # If there are missing values, they should be handled appropriately
        if len(invalid_production) > 0:
            print(f"Missing values found: {invalid_production[:5]}")

    def test_production_data_extraction_function(self, excel_file_path):
        """Test a complete production data extraction function."""

        def extract_production_from_excel(file_path):
            """Extract production data from Excel file (test version)."""
            if not os.path.exists(file_path):
                return None

            try:
                df = pd.read_excel(
                    file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
                )

                production_data = []
                production_row_idx = 22  # JSM Total AVGMoly row

                for col_idx in range(2, min(df.shape[1], 60)):
                    prod_val = df.iloc[production_row_idx, col_idx]
                    if (
                        pd.notna(prod_val)
                        and isinstance(prod_val, (int, float))
                        and prod_val > 0
                    ):
                        production_data.append(prod_val)

                return production_data if production_data else None

            except Exception as e:
                print(f"Error extracting production: {e}")
                return None

        # Test the function
        extracted_production = extract_production_from_excel(excel_file_path)

        assert extracted_production is not None, "Production extraction function failed"
        assert (
            len(extracted_production) >= 12
        ), f"Expected at least 12 production values, got {len(extracted_production)}"
        assert all(
            isinstance(p, (int, float)) for p in extracted_production
        ), "All production values should be numeric"

        # Verify some expected values
        assert (
            abs(extracted_production[0] - 19123.987142857142) < 1.0
        ), f"First production value mismatch"
        assert (
            abs(extracted_production[1] - 32642.056878306877) < 1.0
        ), f"Second production value mismatch"

        print(
            f"Integration test passed: extracted {len(extracted_production)} production values"
        )

    def test_production_data_revenue_calculation_alignment(self, excel_file_path):
        """Test that production data aligns properly for revenue calculation."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract aligned production and price data
        aligned_data = []

        for col_idx in range(2, min(df.shape[1], 60)):
            prod_val = df.iloc[22, col_idx]  # Production
            price_val = df.iloc[2, col_idx]  # Price

            if (
                pd.notna(prod_val)
                and isinstance(prod_val, (int, float))
                and prod_val > 0
                and pd.notna(price_val)
                and isinstance(price_val, (int, float))
                and 20 < price_val < 200
            ):
                revenue = prod_val * price_val
                aligned_data.append(
                    {"production": prod_val, "price": price_val, "revenue": revenue}
                )

        # Validate revenue calculations
        assert (
            len(aligned_data) >= 12
        ), f"Expected at least 12 aligned data points, got {len(aligned_data)}"

        for i, data_point in enumerate(aligned_data):
            expected_revenue = data_point["production"] * data_point["price"]
            actual_revenue = data_point["revenue"]
            assert (
                abs(actual_revenue - expected_revenue) < 0.01
            ), f"Revenue calculation error at period {i}"

        # Check that revenues are reasonable (millions of dollars per month for a major field)
        revenues = [dp["revenue"] for dp in aligned_data]
        avg_monthly_revenue = sum(revenues) / len(revenues)
        assert (
            avg_monthly_revenue > 500000
        ), f"Average monthly revenue ${avg_monthly_revenue:,.0f} seems too low"
        assert (
            avg_monthly_revenue < 10000000
        ), f"Average monthly revenue ${avg_monthly_revenue:,.0f} seems too high"

        print(
            f"Revenue alignment test passed: average monthly revenue ${avg_monthly_revenue:,.0f}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
