import pandas as pd

prod_fp = "multi_year_lease_matrix_with_charts.xlsx"
xls = pd.ExcelFile(prod_fp)

# Print all sheet names in the workbook
print("Available sheets:", xls.sheet_names)

# Try previewing the first 6 rows of all sheets for inspection
for sh in xls.sheet_names:
    print(f"\n--- Sheet: {sh} ---")
    try:
        df = pd.read_excel(xls, sh, nrows=6)
        print(df.head())
    except Exception as e:
        print(f"Error reading sheet '{sh}': {e}")
