# Standard library imports
import io
import os
import zipfile
from urllib.parse import urlparse

# Third party imports
import requests
import pandas as pd

class DownloadFromZipUrl:
    
    def __init__(self):
        pass

    def router(self,cfg):
        
        urls = cfg['input']['urls']
        
        for url in urls:
            self.download_and_process_zip(url ,cfg)

        return cfg
    
    def download_and_process_zip(self, url ,cfg):

        nrows = None

        # Extract the name from the URL
        base_name = os.path.basename(urlparse(url).path).replace('.zip', '')

        try:
            r = requests.get(url)
            r.raise_for_status()  # Check if the download was successful

            z = zipfile.ZipFile(io.BytesIO(r.content))
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return
        except zipfile.BadZipFile as e:
            print(f"Failed to unzip file: {e}")
            return

        extracted_files = z.namelist()

        output_dir = cfg['input']['out_directory']

        for file in extracted_files:
            if file.endswith('/'):
                continue
            csv_filename = f"{base_name}_{os.path.splitext(os.path.basename(file))[0]}"+'.csv'
            with z.open(file) as file:   
                try:
                    if nrows is None:
                        df = pd.read_csv(file, sep=',', encoding='ISO-8859-1', low_memory=False)
                    else:
                        df = pd.read_csv(file, sep=',', encoding='ISO-8859-1', low_memory=False, nrows=100)
                        
                except Exception as e:
                    print(f"Could not read {file} as CSV: {e}")
                    continue

                df.to_csv(os.path.join(output_dir, csv_filename), index=False)
    
        


