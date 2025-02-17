import zipfile
import sqlite3
import pandas as pd

def load_into_database(zip_path):
    # Connect to an in-memory SQLite database
    conn = sqlite3.connect(':memory:')

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            file_names = [f for f in zip_file.namelist() if not f.endswith('/')]
            
            for file_name in file_names:
                with zip_file.open(file_name) as file:
                    # Read data into a Pandas DataFrame 
                    data = pd.read_csv(file) 
                    
                    table_name = file_name.split('/')[-1].split('.')[0]
                    
                    # Load DataFrame into the SQLite table
                    data.to_sql(table_name, conn, if_exists='replace', index=False)
                    print(f"Loaded data from {file_name} into table '{table_name}'")
                    
            for file_name in file_names:
                table_name = file_name.split('/')[-1].split('.')[0]
                print(f"\nData from table '{table_name}':")
                result = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5;", conn)
                print(result)

    except FileNotFoundError:
        print("Error: Zip file not found.")
    finally:
        conn.close()

load_into_database(r"data\bsee\APIRawData.zip")
