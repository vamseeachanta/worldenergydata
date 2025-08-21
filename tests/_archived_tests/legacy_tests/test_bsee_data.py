# Standard library imports
import os
from pathlib import Path

# Third party imports
from assetutilities.common.data import GetData


get_data = GetData()


def GetData_download_file_from_url(cfg):

    get_data.download_file_from_url(cfg)


# API Data
cfg = {
    'url': 'https://www.data.bsee.gov/Well/Files/APIRawData.zip',
    'download_to': os.path.abspath(Path("./data/bsee"))
}
GetData_download_file_from_url(cfg)

# eWell APD
cfg = {
    'url': 'https://www.data.bsee.gov/Well/Files/eWellAPDRawData.zip',
    'download_to': os.path.abspath(Path("./data/bsee"))
}
GetData_download_file_from_url(cfg)

