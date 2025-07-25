import pandas as pd
import sys
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import numbers
import re

if len(sys.argv) < 2:
    print("Usage: python extract_api_details_to_excel.py <API_NUMBER>")
    sys.exit(1)

api_number = sys.argv[1].strip()
remark_file = "mv_war_main_prop_remark.txt"
output_file = f"api_{api_number}_remarks_parsed.xlsx"

# Read remarks file
remark_df = pd.read_csv(remark_file, dtype=str, encoding='ISO-8859-1', low_memory=False)
remark_df.columns = [col.strip() for col in remark_df.columns]

# Load SN_WAR list from a local file (already filtered)
snwar_file = f"api_{api_number}_results_sorted.xlsx"
snwar_df = pd.read_excel(snwar_file, dtype=str)
snwar_list = snwar_df['SN_WAR'].dropna().unique().tolist()

# Filter remark rows
df_snwar_remarks = remark_df[remark_df['SN_WAR'].isin(snwar_list)].copy()

# Extract the earliest date from TEXT_REMARK and clean text after colon

def extract_earliest_date_and_clean(text):
    if pd.isna(text):
        return None, text
    matches = re.findall(r"(\d{1,2}/\d{1,2}/\d{2,4})", text)
    dates = []
    for m in matches:
        for fmt in ["%m/%d/%Y", "%m/%d/%y"]:
            try:
                d = datetime.strptime(m, fmt)
                if d.year < 100:
                    d = d.replace(year=d.year + 2000)
                dates.append(d)
                break
            except:
                continue
    # Remove everything before and including the first colon from each line
    lines = text.splitlines()
    cleaned_lines = [line.split(":", 1)[-1].strip() if ":" in line else line.strip() for line in lines]
    cleaned_text = "\n".join(cleaned_lines).strip()
    return (min(dates) if dates else None), cleaned_text

parsed_rows = []
for _, row in df_snwar_remarks.iterrows():
    snwar = row['SN_WAR']
    remark = row['TEXT_REMARK']
    date, cleaned_remark = extract_earliest_date_and_clean(remark)
    parsed_rows.append((snwar, date, cleaned_remark))

# Write to single Excel file
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

wb.save(output_file)
print(f"📄 Final parsed remarks saved to: {output_file}")
