from worldenergydata.modules.bsee.analysis.custom_scripts.build_lease_report_final import BseeCustomAnalysis 

custom_anal = BseeCustomAnalysis()

class CustomRouter:

    def __init__(self):
        pass

    def router(self, cfg):
    
        
        custom_anal.router(cfg)

        return cfg
