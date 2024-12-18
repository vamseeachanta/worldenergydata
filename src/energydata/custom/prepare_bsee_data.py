import os
import pandas as pd
import yaml

class PrepareBseeData:

    def router(self, cfg):

        data = self.merge_columns_from_files(cfg)

        return data
    
    def merge_columns_from_files(self, cfg):
  
        #config = load_yaml_config(config_path)
        dataframes = []
        
        # for file_info in config["files"]:
        #     file_name = file_info["name"]
        #     columns = file_info["columns"]
        #     file_path = os.path.join(data_dir, file_name)

            # if os.path.exists(file_path):
            #     df = pd.read_csv(file_path, usecols=columns)
            #     dataframes.append(df)
            # else:
            #     print(f"Warning: File not found - {file_name}")
        
        # merged_df = pd.concat(dataframes, axis=1)
        
        # # merged_df.to_csv(output_path, index=False)
        # return merged_df

if __name__ == "__main__":
    prepare_bsee_data = PrepareBseeData()
