# Reader imports
import os
import pandas as pd

class DataFromFiles:
    
    def __init__(self):
        pass

    def router(self, cfg):

        if cfg['data_from_files']['production']:
            cfg = self.get_production_data_by_api12(cfg)

        return cfg
    
    def get_production_data_by_api12(self, cfg):

        folder_path = cfg['settings']['files_folder']  
        output_file = cfg['settings']['output_dir']
        api12 = cfg['settings']['api12']
        file_exists = os.path.exists(output_file)

        for file_name in os.listdir(folder_path):
            if file_name.endswith(".csv"):
                file_path = os.path.join(folder_path, file_name)
                try:
                    
                    df = pd.read_csv(file_path)
                    
                   
                    if 'API_WELL_NUMBER' not in df.columns:
                        print(f"Skipping {file_name}: 'api12' column not found.")
                        continue

                    
                    matching_rows = df[df['API_WELL_NUMBER'] == api12]
                    
                    if not matching_rows.empty:
                        # Move 'api12' column to the first position
                        columns = ['API_WELL_NUMBER'] + [col for col in matching_rows.columns if col != 'API_WELL_NUMBER']
                        matching_rows = matching_rows[columns]
                        
                        # Append or write to the output file
                        matching_rows.to_csv(output_file, mode='a' if file_exists else 'w', header=not file_exists, index=False)
                        file_exists = True 

                except FileNotFoundError:
                    print(f"File not found: {file_path}")
                except pd.errors.EmptyDataError:
                    print(f"Empty or corrupt CSV file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing {file_name}: {e}")

        return output_file
       