import pandas as pd
import os

# Load CSV files
file1 = r'data\modules\bsee\full_data\BoreholeRawData_mv_boreholes_all.csv'
file2 = r'data\modules\bsee\full_data\eWellAPDRawData_mv_apd_main.csv'

df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

# Identify the join key (first column)
join_key = df1.columns[0]

# Merge on the first column (inner join to keep only matching rows)
merged_df = pd.merge(df1, df2, on=join_key, how="right")

merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_y')]
merged_df.columns = merged_df.columns.str.replace('_x', '', regex=True)

output_path = r'data\modules\bsee\well'
# Save to a new CSV file
merged_df.to_csv(os.path.join(output_path, 'Join_Borehole_APD.csv'), index=False)
