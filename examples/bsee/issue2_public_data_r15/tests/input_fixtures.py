"""Small local archives with hand-countable APD, borehole, and APM records."""

from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile, ZipInfo


def write_synthetic_archives(directory):
    members = {
        "APDRawData.zip": {
            "mv_apddata_all": "SN_APD\n1\n",
            "mv_apd_main_all": (
                "SN_APD,API_WELL_NUMBER,REGION_CODE,PERMIT_TYPE,REQ_SPUD_DATE,RIG_TYPE_CODE,WATER_DEPTH\n"
                "1,001,G,New Well,1/1/2005,JACKUP,100\n"
                "2,001,G,New Well,1/1/2006,JACKUP,100\n"
            ),
        },
        "BoreholeRawData.zip": {
            "mv_boreholes_all": (
                "API_WELL_NUMBER,REGION_CODE,WELL_NAME_SUFFIX,BOREHOLE_STAT_CD,WELL_SPUD_DATE,"
                "TOTAL_DEPTH_DATE,WATER_DEPTH,SURF_LATITUDE,SURF_LONGITUDE\n"
                "001,G,ST00BP00,PA,1/1/2005,1/5/2005,100,28,-90\n"
                "002,G,ST00BP00,PA,1/1/2025,1/8/2025,6000,27,-91\n"
                "003,P,ST00BP00,PA,1/1/2025,1/8/2025,100,30,-92\n"
            ),
        },
        "eWellAPMRawData.zip": {
            "mv_apm_main": (
                "SN_APM,API_WELL_NUMBER,ACC_STATUS_DATE,APM_OP_CD,EST_OPERATION_DAYS,WATER_DEPTH\n"
                "1,001,1/1/2005,COMP,6,100\n"
                "2,003,1/1/2025,COMP,5,100\n"
            ),
            "mv_apm_suboperations": "SN_APM_FK,APM_SUBOP_CD\n1,ZONE\n",
            "mv_apm_primary_op_codes": "VALUE,DESCRIP\nCOMP,Completion\n",
            "mv_apm_suboperation_codes": "VALUE,DESCRIP\nZONE,Zone\n",
        },
    }
    for name, tables in members.items():
        with ZipFile(directory / name, "w") as archive:
            for member, contents in tables.items():
                archive.writestr(ZipInfo(member + ".txt"), contents)
    repo = Path(__file__).resolve().parents[4]
    copyfile(repo / "data" / "wti-monthly.csv", directory / "wti-monthly.csv")
