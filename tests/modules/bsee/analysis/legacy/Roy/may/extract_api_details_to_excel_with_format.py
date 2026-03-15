import os
import re
import sys
from datetime import datetime

import pandas as pd
from loguru import logger
from openpyxl import Workbook
from openpyxl.styles import numbers


class ExtractAPIDetails:
    """
    Extracts Single API12 data from war data.
    Gets the API12 from the configuration.
    Reads the war data file, filters by API_WELL_NUMBER, and create an Excel file with formatted dates.
    """

    def router(self, cfg):
        self.extract_api_details(cfg)
        return cfg

    def extract_api_details(self, cfg):

        api_number = cfg["data"]["groups"]["api12"]
        input_file = cfg["data"]["groups"]["war"]

        df = pd.read_pickle(input_file)
        df.columns = [col.strip() for col in df.columns]

        df_filtered = df[df["API_WELL_NUMBER"] == api_number].copy()

        if not df_filtered.empty:
            self.format_and_sort_api_data(df_filtered)

            result_folder = cfg["Analysis"]["result_folder"]
            output_file = f"api_{api_number}_results_sorted.xlsx"
            self.write_to_excel(result_folder, output_file, df_filtered)
            logger.info(
                f"✅ Final fix applied with custom parsing. {len(df_filtered)} rows saved to {output_file}"
            )
        else:
            logger.error(f"⚠️ No rows found for API number {api_number}")

    def format_and_sort_api_data(self, df_filtered):
        date_begin_col = "WAR_START_DT"
        date_complete_col = "WAR_END_DT"

        logger.debug("\nUnique RAW WAR_START_DT values:")
        logger.debug(df_filtered[date_begin_col].dropna().unique())
        logger.debug("\nUnique RAW WAR_END_DT values:")
        logger.debug(df_filtered[date_complete_col].dropna().unique())

        df_filtered[date_begin_col] = df_filtered[date_begin_col].apply(self.parse_date)
        df_filtered[date_complete_col] = df_filtered[date_complete_col].apply(
            self.parse_date
        )

        logger.debug(
            "\nParsed WAR_START_DT (non-null):",
            df_filtered[date_begin_col].notna().sum(),
        )
        logger.debug(
            "Parsed WAR_END_DT (non-null):",
            df_filtered[date_complete_col].notna().sum(),
        )

        df_filtered.drop(df_filtered.columns[[3, 4, 7, 8, 9, 10]], axis=1, inplace=True)

        df_filtered.sort_values(by=date_begin_col, inplace=True)

    def write_to_excel(self, result_folder, output_file, df_filtered):
        wb = Workbook()
        ws = wb.active
        ws.title = "API Data"

        # Write header
        ws.append(df_filtered.columns.tolist())

        # Write rows with true datetime values
        for _, row in df_filtered.iterrows():
            excel_row = []
            for col in df_filtered.columns:
                val = row[col]
                excel_row.append(val)
            ws.append(excel_row)

            # Format date columns
        for col_letter in [
            "B",
            "C",
        ]:  # Assuming WAR_START_DT and WAR_END_DT are in B and C
            for cell in ws[col_letter][1:]:
                if isinstance(cell.value, datetime):
                    cell.number_format = numbers.FORMAT_DATE_YYYYMMDD2

        wb.save(os.path.join(result_folder, output_file))

    def parse_date(self, val):
        if pd.isna(val):
            return None

        if isinstance(val, datetime):
            return val

        val_str = str(val).strip()

        match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})", val_str)
        if match:
            try:
                month, day, year = map(int, match.groups())
                if year < 50:
                    year += 2000
                elif year < 100:
                    year += 1900
                return datetime(year, month, day)
            except:
                pass

        try:
            return pd.to_datetime(val_str, errors="coerce")
        except:
            return None
