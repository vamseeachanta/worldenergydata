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

    csv_file = next((file for file in extracted_files if file.endswith('.csv')), None)
    if csv_file is None:
        raise FileNotFoundError("No .txt file found in the extracted ZIP file")
    
    os.makedirs(output_dir, exist_ok=True)
    z.extract(csv_file, output_dir)


urls = [
    # 'https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/BHPSRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/eWellAPDRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/eWellAPMRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/APDRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/APIRawData.zip',
    # 'https://www.data.bsee.gov/Well/Files/APIChangesRawData.zip',
    # 'https://www.data.bsee.gov/Company/Files/ApprovalsRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/AssignmentsRawData.zip',
    # 'https://www.data.bsee.gov/Company/Files/CompanyRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/DecomCostEstRawData.zip',
    # 'https://www.data.bsee.gov/Other/Files/DeepQualRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/FMPRawData.zip',
    # 'https://www.data.bsee.gov/Other/Files/FRSWellDataRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/FMPMetersRawData.zip',
    # 'https://www.data.bsee.gov/Other/Files/IncInvRawData.zip',
    # 'https://www.data.bsee.gov/Company/Files/INCSRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/LABRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/LeaseOwnerRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/NonReqRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/OffshoreStatsRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/OSFRRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/OCSProdRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/MCPFlowRawData.zip',
    # 'https://www.data.bsee.gov/Other/Files/PermStrucRawData.zip',
    # 'https://www.data.bsee.gov/Pipeline/Files/PipeLocRawData.zip',
    # 'https://www.data.bsee.gov/Pipeline/Files/PipePermRawData.zip',
    # 'https://www.data.bsee.gov/Plans/Files/PlansRawData.zip',
    # 'https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip',
    # 'https://www.data.bsee.gov/Production/Files/ProdPlanAreaRawData.zip',
    # 'https://www.data.bsee.gov/Other/Files/RoyaltyRefRawData.zip',
    # 'https://www.data.bsee.gov/Pipeline/Files/RowDescRawData.zip',
    # 'https://www.data.bsee.gov/Other/Files/ScannedDocsRawData.zip',
    # 'https://www.data.bsee.gov/Leasing/Files/SerialRegRawData.zip'
    'https://factpages.sodir.no/downloads/csv/afxAreaCurrent.zip',
    'https://factpages.sodir.no/downloads/csv/afxAreaSplitByBlock.zip',
    'https://factpages.sodir.no/downloads/csv/prlAreaCurrent.zip',
    'https://factpages.sodir.no/downloads/csv/prlAreaSplitByBlock.zip',
    'https://factpages.sodir.no/downloads/csv/apaAreaGross.zip',
    'https://factpages.sodir.no/downloads/csv/apaAreaNet.zip',
    'https://factpages.sodir.no/downloads/csv/wlbPoint.zip',
    'https://factpages.sodir.no/downloads/csv/baaAreaCurrent.zip',
    'https://factpages.sodir.no/downloads/csv/baaAreaSplitByBlock.zip',
    'https://factpages.sodir.no/downloads/csv/fldArea.zip',
    'https://factpages.sodir.no/downloads/csv/dscArea.zip',
    'https://factpages.sodir.no/downloads/csv/fclPoint.zip',
    'https://factpages.sodir.no/downloads/csv/seaArea.zip',
    'https://factpages.sodir.no/downloads/csv/pipLine.zip',
    'https://factpages.sodir.no/downloads/csv/blkArea.zip',
    'https://factpages.sodir.no/downloads/csv/qadArea.zip',
    'https://factpages.sodir.no/downloads/csv/subArea.zip'

]
output_dir = r'src\energydata\tests\test_data\bsee\results\Data\no_dir_data'
for url in urls:
    download_and_process_zip(url, output_dir)
