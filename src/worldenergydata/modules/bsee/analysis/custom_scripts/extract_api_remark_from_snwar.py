import pandas as pd
import re

import os
import sys
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import numbers

class APIRemarksFromSNWAR:

    def router(self, cfg):
        self.extract_remarks(cfg)
        return cfg

    def extract_remarks(self, cfg):   

        api_number = cfg['data']['groups']['api12']
        remark_file = cfg['data']['groups']['war_remarks']

        # Read remarks file
        remark_df = pd.read_pickle(remark_file)
        remark_df.columns = [col.strip() for col in remark_df.columns]

        # Load SN_WAR list from a local file (already filtered)
        result_folder = cfg['Analysis']['result_folder']
        snwar_file = f"api_{api_number}_results_sorted.xlsx"
        snwar_file = os.path.join(result_folder, snwar_file)
        snwar_df = pd.read_excel(snwar_file, dtype=str)
        snwar_list = snwar_df['SN_WAR'].dropna().unique().tolist()

        # Filter remark rows
        parsed_rows = self.get_snwar_remarks_with_dates(remark_df, snwar_list)

        result_folder = cfg['Analysis']['result_folder']
        output_file = f"api_{api_number}_remarks_parsed.xlsx"
        self.write_to_excel(result_folder, output_file, parsed_rows)

    def get_snwar_remarks_with_dates(self, remark_df, snwar_list):
        remark_df['SN_WAR'] = remark_df['SN_WAR'].astype(str)
        df_snwar_remarks = remark_df[remark_df['SN_WAR'].isin(snwar_list)].copy()

        parsed_rows = []
        for _, row in df_snwar_remarks.iterrows():
            snwar = row['SN_WAR']
            remark = row['TEXT_REMARK']
            date, cleaned_remark = self.extract_earliest_date_and_clean(remark)
            parsed_rows.append((snwar, date, cleaned_remark))
        return parsed_rows

    def write_to_excel(self, result_folder, output_file, parsed_rows):

        wb = Workbook()
        ws = wb.active
        ws.title = "Parsed Remarks"
        ws.column_dimensions['B'].width = 12
        ws.append(["SN_WAR", "DATE", "TEXT_REMARK"])
        for snwar, date, remark in parsed_rows:
            ws.append([snwar, date, remark])

        for cell in ws["B"][1:]:
            if isinstance(cell.value, datetime):
                cell.number_format = numbers.FORMAT_DATE_YYYYMMDD2

        wb.save(os.path.join(result_folder, output_file))
        print(f"📄 Final parsed remarks saved to: {output_file}")

    def extract_earliest_date_and_clean(self, text):
        if pd.isna(text):
            return None, text

        matches = re.findall(r"(\d{1,2}/\d{1,2}/\d{2,4})", text)
        dates = []

        for date_str in matches:
            try:
                m, d, y = map(int, date_str.split("/"))
                if y < 50:
                    y += 2000
                elif y < 100:
                    y += 1900
                dates.append(datetime(y, m, d))
            except:
                continue

        lines = text.splitlines()
        cleaned_lines = [line.split(":", 1)[-1].strip() if ":" in line else line.strip() for line in lines]
        cleaned_text = "\n".join(cleaned_lines).strip()

        return (min(dates) if dates else None), cleaned_text

