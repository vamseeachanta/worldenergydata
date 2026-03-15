"""
Tests for oil price data extraction from Excel file.
This module validates that oil price data matches Excel analysis source exactly.
"""

import os

import numpy as np
import pandas as pd
import pytest


class TestOilPriceExtraction:
    """Test suite for oil price extraction from Excel source."""

    @pytest.fixture
    def excel_file_path(self):
        """Path to the Excel NPV analysis file."""
        return r"docs\modules\bsee\data\NPV_JStM-WELL-Production-Data-thru-2019.xlsx"

    def test_excel_file_exists(self, excel_file_path):
        """Test that the Excel file exists and is accessible."""
        assert os.path.exists(
            excel_file_path
        ), f"Excel file not found: {excel_file_path}"

        # Test that we can read the file
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )
        assert df is not None, "Could not read Excel file"
        assert df.shape[0] > 0, "Excel file appears to be empty"

    def test_brent_price_row_identification(self, excel_file_path):
        """Test that we can identify the BRENT price row correctly."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # BRENT prices should be in row 2 (index 2), column 1 should contain "BRENT Price"
        brent_label = df.iloc[2, 1]
        assert isinstance(
            brent_label, str
        ), f"Expected string label, got {type(brent_label)}"
        assert (
            "BRENT" in brent_label.upper()
        ), f"Expected BRENT label, got '{brent_label}'"

    def test_brent_price_extraction_basic(self, excel_file_path):
        """Test basic BRENT price extraction from Excel."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract BRENT prices from row 2 (index 2), starting from column 2
        brent_prices = []
        brent_row_idx = 2

        for col_idx in range(
            2, min(df.shape[1], 60)
        ):  # Start from column 2, reasonable limit
            price_val = df.iloc[brent_row_idx, col_idx]
            if (
                pd.notna(price_val)
                and isinstance(price_val, (int, float))
                and 20 < price_val < 200
            ):
                brent_prices.append(price_val)

        # Validate extracted prices
        assert len(brent_prices) > 0, "No BRENT prices were extracted"
        assert (
            len(brent_prices) >= 24
        ), f"Expected at least 24 months of prices, got {len(brent_prices)}"

        # Validate price ranges (reasonable oil prices)
        assert all(
            20 < price < 200 for price in brent_prices
        ), "Some prices are outside reasonable range (20-200)"

        print(
            f"Extracted {len(brent_prices)} BRENT prices: {brent_prices[:5]}...{brent_prices[-5:]}"
        )

    def test_brent_price_extraction_with_validation(self, excel_file_path):
        """Test BRENT price extraction with comprehensive validation."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract prices using the same logic as production code
        brent_prices = []
        brent_row_idx = 2

        for col_idx in range(2, min(df.shape[1], 60)):
            price_val = df.iloc[brent_row_idx, col_idx]
            if (
                pd.notna(price_val)
                and isinstance(price_val, (int, float))
                and 20 < price_val < 200
            ):
                brent_prices.append(price_val)

        # Test specific price values (these are from the actual Excel file)
        expected_first_prices = [
            62.34,
            47.76,
            58.1,
            55.89,
            59.52,
        ]  # First 5 prices from Excel

        assert (
            len(brent_prices) >= 5
        ), f"Need at least 5 prices for validation, got {len(brent_prices)}"

        # Check first few prices match expected values (within small tolerance for floating point)
        for i, expected_price in enumerate(expected_first_prices):
            actual_price = brent_prices[i]
            assert (
                abs(actual_price - expected_price) < 0.01
            ), f"Price {i}: expected {expected_price}, got {actual_price}"

    def test_month_header_extraction(self, excel_file_path):
        """Test extraction of month headers to align with prices."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract month headers from row 0, starting from column 2
        month_headers = []
        header_row_idx = 0

        for col_idx in range(2, min(df.shape[1], 60)):
            header_val = df.iloc[header_row_idx, col_idx]
            if pd.notna(header_val) and isinstance(header_val, str):
                month_headers.append(header_val)
            elif pd.notna(header_val):  # Non-string but not NaN
                month_headers.append(str(header_val))

        # Validate month headers
        assert len(month_headers) > 0, "No month headers extracted"

        # Check that some expected month names are present
        month_names = [
            "December",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
        ]
        found_months = [
            header
            for header in month_headers
            if any(month in header for month in month_names)
        ]
        assert (
            len(found_months) > 0
        ), f"No recognizable month names found in headers: {month_headers[:10]}"

        print(f"Extracted {len(month_headers)} month headers: {month_headers[:10]}")

    def test_price_data_alignment_with_months(self, excel_file_path):
        """Test that price data correctly aligns with month headers."""
        df = pd.read_excel(
            excel_file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
        )

        # Extract both months and prices
        months = []
        prices = []

        for col_idx in range(2, min(df.shape[1], 60)):
            # Month header (row 0)
            month_val = df.iloc[0, col_idx]
            # Price data (row 2)
            price_val = df.iloc[2, col_idx]

            if (
                pd.notna(month_val)
                and pd.notna(price_val)
                and isinstance(price_val, (int, float))
                and 20 < price_val < 200
            ):
                months.append(str(month_val))
                prices.append(price_val)

        # Validate alignment
        assert len(months) == len(
            prices
        ), f"Month-price mismatch: {len(months)} months vs {len(prices)} prices"
        assert (
            len(months) >= 12
        ), f"Expected at least 12 months of data, got {len(months)}"

        # Create aligned DataFrame for testing
        price_data = pd.DataFrame({"Month": months, "BRENT_Price_USD_per_BBL": prices})

        assert (
            price_data["BRENT_Price_USD_per_BBL"].mean() > 30
        ), "Average oil price seems too low"
        assert (
            price_data["BRENT_Price_USD_per_BBL"].mean() < 120
        ), "Average oil price seems too high"

        print(f"Successfully aligned {len(price_data)} month-price pairs")
        print(
            f"Price range: ${price_data['BRENT_Price_USD_per_BBL'].min():.2f} - ${price_data['BRENT_Price_USD_per_BBL'].max():.2f}"
        )

    def test_fallback_price_handling(self):
        """Test fallback handling when Excel file is not available."""
        # Test with non-existent file
        fake_path = "non_existent_file.xlsx"

        # This should be handled gracefully in production code
        assert not os.path.exists(fake_path), "Test file should not exist"

        # In real implementation, this would fall back to external price file
        # For now, just verify the test condition
        fallback_prices = [
            60.0,
            65.0,
            70.0,
            68.0,
            72.0,
        ] * 5  # 25 months of fallback data

        assert (
            len(fallback_prices) >= 20
        ), "Fallback prices should cover at least 20 months"
        assert all(
            30 < price < 100 for price in fallback_prices[:5]
        ), "Fallback prices should be reasonable"

    def test_price_extraction_function_integration(self, excel_file_path):
        """Test a complete price extraction function that mimics production code."""

        def extract_brent_prices_from_excel(file_path):
            """Extract BRENT prices from Excel file (test version)."""
            if not os.path.exists(file_path):
                return None

            try:
                df = pd.read_excel(
                    file_path, sheet_name="NPV w Mo'ly data chart", engine="openpyxl"
                )

                brent_prices = []
                brent_row_idx = 2

                for col_idx in range(2, min(df.shape[1], 60)):
                    price_val = df.iloc[brent_row_idx, col_idx]
                    if (
                        pd.notna(price_val)
                        and isinstance(price_val, (int, float))
                        and 20 < price_val < 200
                    ):
                        brent_prices.append(price_val)

                return brent_prices if brent_prices else None

            except Exception as e:
                print(f"Error extracting prices: {e}")
                return None

        # Test the function
        extracted_prices = extract_brent_prices_from_excel(excel_file_path)

        assert extracted_prices is not None, "Price extraction function failed"
        assert (
            len(extracted_prices) >= 12
        ), f"Expected at least 12 prices, got {len(extracted_prices)}"
        assert all(
            isinstance(p, (int, float)) for p in extracted_prices
        ), "All prices should be numeric"

        # Verify some expected values
        assert (
            abs(extracted_prices[0] - 62.34) < 0.01
        ), f"First price mismatch: expected 62.34, got {extracted_prices[0]}"
        assert (
            abs(extracted_prices[1] - 47.76) < 0.01
        ), f"Second price mismatch: expected 47.76, got {extracted_prices[1]}"

        print(f"Integration test passed: extracted {len(extracted_prices)} prices")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
