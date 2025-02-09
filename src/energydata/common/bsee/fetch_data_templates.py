# Reader imports
from assetutilities.common.data import AttributeDict
from assetutilities.common.yml_utilities import WorkingWithYAML

wwy = WorkingWithYAML()

class FetchDataTemplates:
    
    def __init__(self):
        pass

    def get_production_data_by_lease(self, custom_analysis_dict={}):

        library_name = "energydata"
        library_yaml_cfg = {
            'filename': 'base_configs/modules/bsee/production_data_by_lease.yml',
            'library_name': library_name
        }
        data_template = wwy.get_library_yaml_file(library_yaml_cfg)
        data_template['Analysis'] = custom_analysis_dict
        data_template = AttributeDict(data_template)

        return data_template
    
    def get_production_data_by_wellAPI(self, custom_analysis_dict={}):

        library_name = "energydata"
        library_yaml_cfg = {
            'filename': 'base_configs/modules/bsee/production_data_by_wellAPI.yml',
            'library_name': library_name
        }
        data_template = wwy.get_library_yaml_file(library_yaml_cfg)
        data_template['Analysis'] = custom_analysis_dict
        data_template = AttributeDict(data_template)

        return data_template

        
    