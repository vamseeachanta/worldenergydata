import pandas as pd
import sys
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import numbers

if len(sys.argv) < 2:
    print("Usage: python extract_api_details_to_excel.py <API_NUMBER>")
    sys.exit(1)

api_number = sys.argv[1].strip()
input_file = "mv_war_main.txt"
output_file = f"api_{api_number}_results_sorted.xlsx"

# Read and clean
df = pd.read_csv(input_file, dtype=str, low_memory=False)
df.columns = [col.strip() for col in df.columns]

# Filter
df_filtered = df[df["API_WELL_NUMBER"] == api_number].copy()

if not df_filtered.empty:
    # Confirmed date columns
    date_begin_col = "WAR_START_DT"
    date_complete_col = "WAR_END_DT"

    # Custom parser function
    def parse_date(val):
        if pd.isna(val):
            return None
        for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
            try:
                return datetime.strptime(val, fmt)
            except Exception:
                continue
        try:
            return pd.to_datetime(val, errors='coerce')
        except Exception:
            return None

    # Show raw values before parsing
    print("\nUnique RAW WAR_START_DT values:")
    print(df_filtered[date_begin_col].dropna().unique())
    print("\nUnique RAW WAR_END_DT values:")
    print(df_filtered[date_complete_col].dropna().unique())

    # Apply custom parsing
    df_filtered[date_begin_col] = df_filtered[date_begin_col].apply(parse_date)
    df_filtered[date_complete_col] = df_filtered[date_complete_col].apply(parse_date)

    # Report parsing success
    print("\nParsed WAR_START_DT (non-null):", df_filtered[date_begin_col].notna().sum())
    print("Parsed WAR_END_DT (non-null):", df_filtered[date_complete_col].notna().sum())

    # Drop specified columns
    df_filtered.drop(df_filtered.columns[[3, 4, 7, 8, 9, 10]], axis=1, inplace=True)

    # Sort by begin date
    df_filtered.sort_values(by=date_begin_col, inplace=True)

    # Create workbook manually
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
    for col_letter in ['B', 'C']:  # Assuming WAR_START_DT and WAR_END_DT are in B and C
        for cell in ws[col_letter][1:]:
            if isinstance(cell.value, datetime):
                cell.number_format = numbers.FORMAT_DATE_YYYYMMDD2

    wb.save(output_file)
    print(f"✅ Final fix applied with custom parsing. {len(df_filtered)} rows saved to {output_file}")
else:
    print(f"⚠️ No rows found for API number {api_number}")
