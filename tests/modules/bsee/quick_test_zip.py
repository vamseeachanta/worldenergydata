import pandas as pd
import zipfile
import os

class ReadZipCsvNoHeader:
    
    def __init__(self):
        pass
    def read_zip_csv_no_header(zip_filepath, delimiter=',', column_names=None):
        with zipfile.ZipFile(zip_filepath, 'r') as zf:
            file_list = zf.namelist()
            
            # Identify CSV or TXT files
            csv_or_txt_files = [f for f in file_list if f.lower().endswith(('.csv', '.txt'))]
            if not csv_or_txt_files:
                raise ValueError("No CSV or TXT files found in the ZIP archive.")
            
            dataframes = {}
            for file_to_read in csv_or_txt_files:
                with zf.open(file_to_read) as txtf:
                    df = pd.read_csv(txtf, sep=delimiter)
                    
                    # If column names are provided and header row is missing, set column names
                    if column_names is not None:
                        df.columns = column_names
                    
                    print(f"Loaded file: {file_to_read}")
                    dataframes[file_to_read] = df
            
            return dataframes

    # Example usage:
    zip_file_path = r'data/modules/bsee/production/zip/ogora1996delimit.zip'
    column_names = ['LEASE_NUMBER', 'COMPLETION_NAME', 'PRODUCTION_DATE', 'DAYS_ON_PROD', 'PRODUCT_CODE', 'MON_O_PROD_VOL', 'MON_G_PROD_VOL', 'MON_WTR_PROD_VOL', 'API_WELL_NUMBER', 'WELL_STAT_CD', 'AREA_CODE_BLOCK_NUM', 'OPERATOR_NUM', 'SORT_NAME', 'BOEM_FIELD', 'INJECTION_VOLUME', 'PROD_INTERVAL_CD', 'FIRST_PROD_DATE', 'UNIT_AGT_NUMBER', 'UNIT_ALOC_SUFFIX']
    dataframes = read_zip_csv_no_header(zip_file_path, delimiter=',', column_names=column_names)
    print('Successfully loaded the zip file contents into dataframes.')