import os
import pandas as pd

# Define the path to the CSV files
directory = "tests/modules/bsee/data/well_production_yearly"

# Define the column names
column_names = [
    "LEASE_NUMBER", "COMPLETION_NAME", "PRODUCTION_DATE", "DAYS_ON_PROD", "PRODUCT_CODE", 
    "MON_O_PROD_VOL", "MON_G_PROD_VOL", "MON_WTR_PROD_VOL", "API_WELL_NUMBER", 
    "WELL_STAT_CD", "AREA_CODE_BLOCK_NUM", "OPERATOR_NUM", "SORT_NAME", "BOEM_FIELD", 
    "INJECTION_VOLUME", "PROD_INTERVAL_CD", "FIRST_PROD_DATE", "UNIT_AGT_NUMBER", 
    "UNIT_ALOC_SUFFIX"
]

# Iterate over all CSV files in the specified directory
for filename in os.listdir(directory):
    if filename.endswith(".csv"):
        file_path = os.path.join(directory, filename)
        
        # Read the CSV file
        df = pd.read_csv(file_path, header=None)  # Assume the files may have no header
        
        # Add column names to the DataFrame
        df.columns = column_names
        
        # Save the updated CSV file (overwrite the original file)
        df.to_csv(file_path, index=False)
        
        print(f"Updated columns for: {filename}")

print("Column names added to all CSV files successfully.")
