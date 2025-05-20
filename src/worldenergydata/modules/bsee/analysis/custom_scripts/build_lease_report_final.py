#!/usr/bin/env python3
import pandas as pd
import os
import sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from datetime import datetime

class BseeCustomAnalysis:

    def router(self, cfg):
        self.build_report(cfg)
        return cfg

    def load_clean(self, path):
        df = pd.read_pickle(path)
        for c in df.select_dtypes(include="object"):
            df[c] = df[c].str.strip().str.strip('"')
        return df

    def build_report(self, cfg):
        lease = cfg['data']['groups']['lease']
        lease = lease.strip().upper()
        if not lease.startswith("G"):
            lease = "G" + lease

        # 1) main → SN_WAR & API
        war_path = cfg['data']['groups']['war']
        main = self.load_clean(war_path)
        sub = main[main["BOTM_LEASE_NUM"] == lease]
        if sub.empty:
            print(f"No records for lease {lease}")
            return
        sn_list = sub["SN_WAR"].dropna().tolist()
        api_list = sub["API_WELL_NUMBER"].dropna().tolist()

        # 2) boreholes by API
        boreholes_path = cfg['data']['groups']['boreholes']
        bore = self.load_clean(boreholes_path)
        bore = bore[bore["API_WELL_NUMBER"].isin(api_list)]
        bore = bore[[
            "API_WELL_NUMBER",
            "WELL_SPUD_DATE",
            "TOTAL_DEPTH_DATE",
            "BH_TOTAL_MD",
            "WELL_BORE_TVD"
        ]]

        # 3) prop for mud weight
        war_prop = cfg['data']['groups']['war_prop']
        prop = self.load_clean(war_prop)
        prop = prop[prop["SN_WAR"].isin(sn_list)]
        prop = prop[["SN_WAR", "DRILL_FLUID_WGT"]].rename(
            columns={"DRILL_FLUID_WGT": "Max Mud Weight (ppg)"}
        )

        # 4) merge & pick max mud weight
        df = sub[["SN_WAR", "API_WELL_NUMBER"]].drop_duplicates()
        df = df.merge(bore, on="API_WELL_NUMBER", how="left")
        df = df.merge(prop, on="SN_WAR", how="left")
        df["Max Mud Weight (ppg)"] = pd.to_numeric(df["Max Mud Weight (ppg)"], errors="coerce")
        idx = df.groupby("API_WELL_NUMBER")["Max Mud Weight (ppg)"].idxmax()
        df = df.loc[idx].reset_index(drop=True)

        # Convert date columns to datetime format
        df["WELL_SPUD_DATE"] = pd.to_datetime(df["WELL_SPUD_DATE"], errors='coerce')
        df["TOTAL_DEPTH_DATE"] = pd.to_datetime(df["TOTAL_DEPTH_DATE"], errors='coerce')

        # 5) build Excel
        wb = Workbook()
        ws = wb.active
        ws.title = lease

        headers = [
            "SN_WAR",
            "API_WELL_NUMBER",
            "Spud Date",
            "Total Depth Date",
            "Drilling Days",
            "TMD",
            "TVD",
            "Max Mud Weight (ppg)",
            "Bottom Hole Pressure"
        ]
        for i, h in enumerate(headers, 1):
            cell = ws.cell(1, i, h)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(wrap_text=True, horizontal="center")

        # 6) fill rows
        for r, row in enumerate(df.itertuples(index=False), start=2):
            sn = row[0]
            api = row[1]
            spud = row[2]
            td = row[3]
            tmd = row[4]
            tvd = row[5]
            mud = row[6]

            ws.cell(r, 1, sn)
            ws.cell(r, 2, api)
            
            # Handle dates - write as Excel datetime values
            if pd.notna(spud) and isinstance(spud, pd.Timestamp):
                ws.cell(r, 3, spud)
            else:
                ws.cell(r, 3, "")
                
            if pd.notna(td) and isinstance(td, pd.Timestamp):
                ws.cell(r, 4, td)
            else:
                ws.cell(r, 4, "")
            
            # Calculate drilling days only if both dates are valid
            if pd.notna(spud) and pd.notna(td) and isinstance(spud, pd.Timestamp) and isinstance(td, pd.Timestamp):
                ws.cell(r, 5, (td - spud).days)
            else:
                ws.cell(r, 5, "")
            
            ws.cell(r, 6, pd.to_numeric(tmd, errors="coerce"))
            ws.cell(r, 7, pd.to_numeric(tvd, errors="coerce"))
            ws.cell(r, 8, pd.to_numeric(mud, errors="coerce"))
            ws.cell(r, 9, f"=H{r}*0.052*G{r}")

        # 7) formatting
        fmt_w = {
            1: ("@", 12),
            2: ("0", 14),
            3: ("mm/dd/yyyy", 12),
            4: ("mm/dd/yyyy", 12),
            5: ("0", 10),
            6: ("#,##0", 12),  # TMD with commas, no decimals
            7: ("#,##0", 12),  # TVD with commas, no decimals
            8: ("0.0", 15),
            9: ("#,##0", 12)   # BHP with commas, no decimals
        }
        for col, (num_fmt, w) in fmt_w.items():
            letter = ws.cell(1, col).column_letter
            ws.column_dimensions[letter].width = w
            for cell in ws[letter]:
                cell.alignment = Alignment(wrap_text=True)
                if cell.row > 1 and num_fmt != "@":
                    cell.number_format = num_fmt

        result_folder = cfg['Analysis']['result_folder']
        label = cfg['meta']['label']
        filename = f"{label}_summary_{lease}.xlsx"

        wb.save(os.path.join(result_folder, filename))
        print(f"✅ Wrote fully formatted summary to {filename}")