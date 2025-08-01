import pandas as pd

# --- Input and Output Files ---
input_file = "mv_war_main.txt"
output_file = "stones_producing_wells.csv"

# --- Load the WAR file ---
df = pd.read_csv(input_file, dtype=str, low_memory=False)

# --- Normalize column names ---
df.columns = [col.strip() for col in df.columns]

# --- Define filter criteria ---
shell_name = "Shell Offshore Inc."
stones_blocks = {"508", "509", "551", "552", "553", "596", "597", "598"}

# --- Apply filters for Shell-operated Stones wells ---
filtered_df = df[
    (df["BUS_ASC_NAME"].str.strip().str.lower() == shell_name.lower()) &
    (df["SURF_AREA_CODE"].str.strip() == "WR") &
    (df["SURF_BLOCK_NUM"].astype(str).str.strip().isin(stones_blocks))
]

# --- Get distinct wells with API numbers ---
result = filtered_df[["API_WELL_NUMBER", "WELL_NAME", "SURF_BLOCK_NUM"]].drop_duplicates()

# --- Save to CSV ---
result.to_csv(output_file, index=False)

print(f"✅ Found {len(result)} producing wells in Stones. Results saved to: {output_file}")
