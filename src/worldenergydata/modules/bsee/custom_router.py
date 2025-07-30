# from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.build_lease_report_final import BuildLeaseReportFinal
# from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.extract_remarks_by_API import ExtractRemarksbyAPI

# from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.extract_api_details_to_excel_with_format import ExtractAPIDetails
# from worldenergydata.modules.bsee.analysis.custom_scripts.Roy.extract_api_remark_from_snwar import APIRemarksFromSNWAR

# build_report = BuildLeaseReportFinal()
# extract_remarks = ExtractRemarksbyAPI()

# api_details = ExtractAPIDetails()
# extract_remarks_snwar = APIRemarksFromSNWAR()

class CustomRouter:

    def __init__(self):
        pass

    def router(self, cfg):
        
        if 'custom_analysis' in cfg and cfg['custom_analysis']['flag']:
            # build_report.router(cfg)
            # extract_remarks.router(cfg)
            pass
            
        elif 'custom_remarks_analysis' in cfg and cfg['custom_remarks_analysis']['flag']:
            # api_details.router(cfg)
            # extract_remarks_snwar.router(cfg)
            pass

        return cfg
