import requests 
import zipfile 
import io
import pandas as pd
import os

url = 'https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip'

r = requests.get(url)
z = zipfile.ZipFile(io.BytesIO(r.content))
z.extractall()

extracted_files = z.namelist()

borehole_file = None
for file in extracted_files:
    if 'mv_boreholes_all.txt' in file:
        borehole_file = file
        break

if borehole_file is None:
    raise FileNotFoundError("borehole.txt not found in the extracted ZIP file")

df = pd.read_csv(borehole_file, sep=',')
dir_path = r'src\energydata\tests\test_data\bsee\results\Data'
df.to_csv(os.path.join(dir_path, 'borehole_data.csv'), index=False)