#!/usr/bin/env python3
import pandas as pd
import os
import sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

class BseeCustomAnalysis:

    def router(self, cfg):
        
        self.build_report(cfg)
        return cfg
    
    def load_clean(self,path):
        df = pd.read_pickle(path)
        for c in df.select_dtypes(include="object"):
            df[c] = df[c].str.strip().str.strip('"')
        return df

    def build_report(self,cfg):
        lease = cfg['data']['groups'][0]['lease']
        lease = lease.strip().upper()
        if not lease.startswith("G"):
            lease = "G" + lease

        # 1) main → SN_WAR & API
        main = self.load_clean("data/modules/bsee/bin/war/mv_war_main.bin")
        sub  = main[main["BOTM_LEASE_NUM"] == lease]
        if sub.empty:
            print(f"No records for lease {lease}")
            return
        sn_list  = sub["SN_WAR"].dropna().tolist()
        api_list = sub["API_WELL_NUMBER"].dropna().tolist()

        # 2) boreholes by API
        bore = self.load_clean("data/modules/bsee/bin/war/mv_war_boreholes_view.bin")
        bore = bore[bore["API_WELL_NUMBER"].isin(api_list)]
        bore = bore[[
            "API_WELL_NUMBER",
            "WELL_SPUD_DATE",
            "TOTAL_DEPTH_DATE",
            "BH_TOTAL_MD",
            "WELL_BORE_TVD"
        ]]

        # 3) prop for mud weight
        prop = self.load_clean("data/modules/bsee/bin/war/mv_war_main_prop.bin")
        prop = prop[prop["SN_WAR"].isin(sn_list)]
        prop = prop[["SN_WAR","DRILL_FLUID_WGT"]].rename(
            columns={"DRILL_FLUID_WGT":"Max Mud Weight (ppg)"}
        )

        # 4) merge & pick max mud weight
        df = sub[["SN_WAR","API_WELL_NUMBER"]].drop_duplicates()
        df = df.merge(bore, on="API_WELL_NUMBER", how="left")
        df = df.merge(prop, on="SN_WAR", how="left")
        df["Max Mud Weight (ppg)"] = pd.to_numeric(df["Max Mud Weight (ppg)"], errors="coerce")
        idx = df.groupby("API_WELL_NUMBER")["Max Mud Weight (ppg)"].idxmax()
        df = df.loc[idx].reset_index(drop=True)

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
            sn   = row[0]
            api  = row[1]
            spud = row[2]
            td   = row[3]
            tmd  = row[4]
            tvd  = row[5]
            mud  = row[6]

            ws.cell(r,1, sn)
            ws.cell(r,2, api)
            ws.cell(r,3, spud)
            ws.cell(r,4, td)
            ws.cell(r,5, f"=D{r}-C{r}")
            ws.cell(r,6, pd.to_numeric(tmd, errors="coerce"))
            ws.cell(r,7, pd.to_numeric(tvd, errors="coerce"))
            ws.cell(r,8, pd.to_numeric(mud, errors="coerce"))
            ws.cell(r,9, f"=H{r}*0.052*G{r}")

        # 7) formatting
        fmt_w = {
            1: ("@",           12),
            2: ("0",           14),
            3: ("mm/dd/yyyy",  12),
            4: ("mm/dd/yyyy",  12),
            5: ("0",           10),
            6: ("#,##0",       12),  # TMD with commas, no decimals
            7: ("#,##0",       12),  # TVD with commas, no decimals
            8: ("0.0",         15),
            9: ("#,##0",       12)   # BHP with commas, no decimals
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
        filename = f"{label}_summary_formulas.xlsx"

        wb.save(os.path.join(result_folder, filename))
        print(f"✅ Wrote fully formatted summary to {filename}")

# if __name__=="__main__":
#     if len(sys.argv) > 1:
#         lease = sys.argv[1]
#     else:
#         lease = input("Lease (e.g. G12345): ")
#     build_report(lease)
