##-*- coding: utf-8 -*-


import zipfile

import wget

# Define  URL to download
##URL = 'https://www.data.boem.gov//Leasing//Files//LeaseOwnerRawData.zip'
##URL2 = 'https://www.data.boem.gov//Company//Files//CompanyRawData.zip'
URL3 = 'https://www.data.boem.gov/Well/Files/BoreholeRawData.zip' 

fileName = wget.download(URL3)
path = "C://Users//AceEngineer-04//Dropbox//0119 Programming//008 GoM Wells//"
wget -O /path/CODE/test/BoreholeRawData.zip
with zipfile.ZipFile(fileName) as zf:
			zf.extractall()
