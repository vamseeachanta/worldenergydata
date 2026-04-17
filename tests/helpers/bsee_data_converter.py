"""
Convert test data to match BSEE expected formats.
This bridges the gap between our test data and what the code expects.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


class BSEEDataConverter:
    """Convert generic test data to BSEE-specific formats"""

    @staticmethod
    def convert_to_bsee_production_format(df):
        """
        Convert generic production DataFrame to BSEE format.

        Expected BSEE columns:
        - API_WELL_NUMBER (or API12)
        - PRODUCTION_DATE (as YYYYMM integer)
        - MON_O_PROD_VOL (monthly oil production)
        - MON_G_PROD_VOL (monthly gas production)
        - MON_W_PROD_VOL (monthly water production)
        - DAYS_ON_PROD (days on production)
        - MER_YYYY (year)
        - MER_MM (month)
        """
        result = pd.DataFrame()

        # Handle API number
        if "API_WELL_NUMBER" in df.columns:
            result["API12"] = df["API_WELL_NUMBER"].astype(str)
        elif "API" in df.columns:
            result["API12"] = df["API"].astype(str)

        # Handle production date - convert to YYYYMM integer format
        if "PRODUCTION_DATE" in df.columns:
            dates = pd.to_datetime(df["PRODUCTION_DATE"])
            result["PRODUCTION_DATE"] = dates.dt.year * 100 + dates.dt.month
            result["MER_YYYY"] = dates.dt.year
            result["MER_MM"] = dates.dt.month
            result["PRODUCTION_DATETIME"] = dates

        # Handle production volumes
        if "OIL_VOLUME" in df.columns:
            result["MON_O_PROD_VOL"] = df["OIL_VOLUME"]
        elif "Oil_bbl" in df.columns:
            result["MON_O_PROD_VOL"] = df["Oil_bbl"]
        else:
            result["MON_O_PROD_VOL"] = np.random.uniform(1000, 10000, len(df))

        if "GAS_VOLUME" in df.columns:
            result["MON_G_PROD_VOL"] = df["GAS_VOLUME"]
        elif "Gas_MCF" in df.columns:
            result["MON_G_PROD_VOL"] = df["Gas_MCF"]
        else:
            result["MON_G_PROD_VOL"] = result["MON_O_PROD_VOL"] * 5

        if "WATER_VOLUME" in df.columns:
            result["MON_W_PROD_VOL"] = df["WATER_VOLUME"]
        elif "Water_bbl" in df.columns:
            result["MON_W_PROD_VOL"] = df["Water_bbl"]
        else:
            result["MON_W_PROD_VOL"] = result["MON_O_PROD_VOL"] * 0.3

        # Add other required fields
        result["DAYS_ON_PROD"] = df.get("DAYS_ON_PRODUCTION", 30)
        result["AVG_CHOKE_SIZE"] = df.get("CHOKE_SIZE", 32)
        result["AVG_WHP"] = df.get("AVG_WHP", 2500)
        result["AVG_WHT"] = df.get("AVG_WHT", 150)

        # Add liquid volumes (oil + water)
        result["Liquid_bbl"] = result["MON_O_PROD_VOL"] + result["MON_W_PROD_VOL"]
        result["Oil_bbl"] = result["MON_O_PROD_VOL"]
        result["Gas_MCF"] = result["MON_G_PROD_VOL"]
        result["Water_bbl"] = result["MON_W_PROD_VOL"]

        # Add calculated ratios
        result["Gor_scf_bbl"] = (
            result["MON_G_PROD_VOL"] * 1000 / result["MON_O_PROD_VOL"].replace(0, 1)
        )
        result["Wor_bbl_bbl"] = result["MON_W_PROD_VOL"] / result[
            "MON_O_PROD_VOL"
        ].replace(0, 1)

        # Add well info
        if "WELL_NAME" in df.columns:
            result["WELL_NAME"] = df["WELL_NAME"]
        else:
            result["WELL_NAME"] = "WELL_" + result["API12"].str[-4:]

        if "COMPLETION_NAME" in df.columns:
            result["COMPLETION_NAME"] = df["COMPLETION_NAME"]
        else:
            result["COMPLETION_NAME"] = "COMP_" + result["API12"].str[-4:] + "_01"

        # Add field and lease info
        result["FIELD_NAME"] = df.get("FIELD_NAME", "TEST_FIELD")
        result["LEASE_NUMBER"] = df.get("LEASE_NUMBER", "OCS-G-00000")

        # Add days on production
        result["days_on_production"] = result["DAYS_ON_PROD"]

        return result

    @staticmethod
    def load_and_convert_test_data():
        """Load our generated test data and convert it to BSEE format"""
        test_data_path = Path("tests/fixtures/bsee")

        if not test_data_path.exists():
            return None

        # Load production data
        prod_file = test_data_path / "production_data.csv"
        if prod_file.exists():
            df = pd.read_csv(prod_file)
            return BSEEDataConverter.convert_to_bsee_production_format(df)

        return None

    @staticmethod
    def create_minimal_bsee_data(num_wells=2, num_months=12):
        """Create minimal BSEE-format data for testing"""
        data = []
        apis = ["177154051100", "177154051200"][:num_wells]

        for api in apis:
            for i in range(num_months):
                year = 2022 + (i // 12)
                month = (i % 12) + 1
                data.append(
                    {
                        "API12": api,
                        "PRODUCTION_DATE": year * 100 + month,  # YYYYMM format
                        "MER_YYYY": year,
                        "MER_MM": month,
                        "MON_O_PROD_VOL": np.random.uniform(5000, 15000),
                        "MON_G_PROD_VOL": np.random.uniform(25000, 75000),
                        "MON_W_PROD_VOL": np.random.uniform(1500, 4500),
                        "DAYS_ON_PROD": 30,
                        "AVG_CHOKE_SIZE": np.random.uniform(20, 64),
                        "AVG_WHP": np.random.uniform(2000, 3000),
                        "AVG_WHT": np.random.uniform(120, 180),
                        "WELL_NAME": f"WELL_{api[-4:]}",
                        "COMPLETION_NAME": f"COMP_{api[-4:]}_01",
                        "FIELD_NAME": "ANCHOR" if api.endswith("1100") else "JULIA",
                        "LEASE_NUMBER": f"OCS-G-{api[-5:]}",
                    }
                )

        df = pd.DataFrame(data)

        # Add calculated fields
        df["Liquid_bbl"] = df["MON_O_PROD_VOL"] + df["MON_W_PROD_VOL"]
        df["Oil_bbl"] = df["MON_O_PROD_VOL"]
        df["Gas_MCF"] = df["MON_G_PROD_VOL"]
        df["Water_bbl"] = df["MON_W_PROD_VOL"]
        df["Gor_scf_bbl"] = df["MON_G_PROD_VOL"] * 1000 / df["MON_O_PROD_VOL"]
        df["Wor_bbl_bbl"] = df["MON_W_PROD_VOL"] / df["MON_O_PROD_VOL"]
        df["days_on_production"] = df["DAYS_ON_PROD"]

        # Add datetime for plotting
        df["PRODUCTION_DATETIME"] = pd.to_datetime(
            df["MER_YYYY"].astype(str)
            + "-"
            + df["MER_MM"].astype(str).str.zfill(2)
            + "-01"
        )

        return df


if __name__ == "__main__":
    # Test the converter
    converter = BSEEDataConverter()

    # Try to load and convert existing test data
    converted = converter.load_and_convert_test_data()
    if converted is not None:
        print(f"Converted {len(converted)} records")
        print("Columns:", list(converted.columns))
        converted.to_csv(
            "tests/fixtures/bsee/production_data_bsee_format.csv", index=False
        )

    # Create minimal BSEE data
    minimal = converter.create_minimal_bsee_data()
    print(f"\nCreated minimal BSEE data with {len(minimal)} records")
    print("Sample record:")
    print(minimal.iloc[0])
