import os
import pandas as pd

class PrepareBseeData:

    def router(self, cfg):

        output_dfs = {}
        config_data = cfg.get("config_data_map", [])

        for config in config_data:
            
            label = config["label"]
            files = config["files"]
            output_dfs[label] = self.merge_columns_from_files(cfg, files, label)
        
        return output_dfs
    
    def merge_columns_from_files(self, cfg, files, label):
        
        data_dir = cfg['input_path']['data_dir']
        dataframes = []
        
        for file_info in files:
            file_name = file_info["name"]
            columns = file_info["columns"]
            file_path = os.path.join(data_dir, file_name)

            if os.path.exists(file_path):
                df = pd.read_csv(file_path, usecols=columns)
                dataframes.append(df)
            else:
                print(f"Warning: File not found - {file_name}")
        
        merged_df = pd.concat(dataframes, axis=1)
        
        output_path = os.path.join("tests", "modules", "analysis", "data_for_analysis", f"{label}.csv")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)  
        merged_df.to_csv(output_path, index=False)

        return merged_df

if __name__ == "__main__": 
    prepare_bsee_data = PrepareBseeData()
