import requests
import zipfile
import io
import pandas as pd
import os

url = 'https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip'

r = requests.get(url)
r.raise_for_status()  # Check if the download was successful

z = zipfile.ZipFile(io.BytesIO(r.content))

extracted_files = z.namelist()

borehole_file = next((file for file in extracted_files if file.endswith('.txt')), None)

if borehole_file is None:
    raise FileNotFoundError("No .txt file found in the extracted ZIP file")

with z.open(borehole_file) as file:
    df = pd.read_csv(file, sep=',')

df = df.iloc[:100]

dir_path = r'src\energydata\tests\test_data\bsee\results\Data'
os.makedirs(dir_path, exist_ok=True)
df.to_csv(os.path.join(dir_path, 'boreholes_all.csv'), index=False)
