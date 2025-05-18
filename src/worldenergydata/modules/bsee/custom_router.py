from worldenergydata.modules.bsee.analysis.custom_scripts.build_lease_report_final import BseeCustomAnalysis 
from worldenergydata.modules.bsee.analysis.custom_scripts.finish_well_data_extraction import ExtractRemarksbyAPI

custom_anal = BseeCustomAnalysis()
extract_remarks = ExtractRemarksbyAPI()

class CustomRouter:

    def __init__(self):
        pass

    def router(self, cfg):
        
        custom_anal.router(cfg)
        extract_remarks.router(cfg)


        return cfg
