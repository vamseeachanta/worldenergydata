import requests
import zipfile
import io
import pandas as pd
import os
from urllib.parse import urlparse

def download_and_process_zip(url, output_dir):
    # Extract the name from the URL 
    base_name_csv = os.path.basename(urlparse(url).path).replace('.zip', '')

    r = requests.get(url)
    r.raise_for_status()  # Check if the download was successful

    z = zipfile.ZipFile(io.BytesIO(r.content))
    extracted_files = z.namelist()

    borehole_file = next((file for file in extracted_files if file.endswith('.txt')), None)
    if borehole_file is None:
        raise FileNotFoundError("No .txt file found in the extracted ZIP file")

    with z.open(borehole_file) as file:
        df = pd.read_csv(file, sep=',', encoding='ISO-8859-1')
    
    df = df.iloc[:100]
    
    os.makedirs(output_dir, exist_ok=True)
    csv_filename = f"{base_name_csv}.csv"
    df.to_csv(os.path.join(output_dir, csv_filename), index=False)

urls = [
    'https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip',
    'https://www.data.bsee.gov/Well/Files/BHPSRawData.zip',
    'https://www.data.bsee.gov/Well/Files/eWellAPDRawData.zip',
    'https://www.data.bsee.gov/Well/Files/eWellAPMRawData.zip',
    'https://www.data.bsee.gov/Well/Files/ProductionRawData.zip'
]
output_dir = r'src\energydata\tests\test_data\bsee\results\Data\by_zip'
for url in urls:
    download_and_process_zip(url, output_dir)
