### Well , Production and block data

basic analysis for single and multiple well apis:

Gathering_data:

  Initially gets the data from respective website

  Create groups in cfg and store required data ( fileames , dfs) for analysis in cfg 

Analysis:
   Pass all data to analysis class and play with it.

### Code for future purposes on how to store data in cfg and use it

```
from energydata.modules.bsee.data.bsee_data import BSEEData
from energydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis

bsee_data = BSEEData()
bsee_analysis = BSEEAnalysis()


class BSEE:
    def __init__(self):
        pass

    def router(self, cfg):
        cfg[cfg['basename']] = {}
        cfg, data = bsee_data.router(cfg)
        cfg = bsee_analysis.router(cfg, data)
        return cfg


class BSEEDATA:
    def router(self, cfg):
        well_data_flag = cfg['data'].get('well_data', False)
        well_data_groups = None
        if well_data_flag:
            cfg, well_data_groups = well_data.get_well_data_all_wells(cfg)

        production_data_flag = cfg['data'].get('production', False)
        production_from_zip_flag = cfg['well_production'].get('flag', False)
        production_data_groups = None
        if production_data_flag or production_from_zip_flag:
            cfg, production_data_groups = production_from_website.get_data(cfg)

        data = {
            'well_data': well_data_groups,
            'production_data': production_data_groups
        }
        return cfg, data


class WellData:
    def __init__(self):
        pass

    def get_well_data_all_wells(self, cfg):
        Borehole_apd_df = self.get_Borehole_apd_for_all_wells(cfg)
        cfg = self.get_well_data_from_website(cfg)

        well_data_groups = []
        for group in cfg[cfg['basename']]['well_data']['groups']:
            well_data_group = group.copy()
            api12_array = group['api12']
            api12_array_well_data = []
            for api12 in api12_array:
                api12_df = self.get_api12_data_from_all_sources(cfg, Borehole_apd_df, group, api12)
            
            well_data_group.update({'api12_df': api12_df})
            api12_array_well_data.append(well_data_group)

        well_data_groups.append(api12_array_well_data)
        return cfg, well_data_groups

    def get_api12_data_from_all_sources(self, cfg, Borehole_apd_df, group, api12):
        api12_well_data = pd.read_csv(group['file_name'])
        api12_Borehole_apd = self.get_Borehole_apd_for_api12(cfg, Borehole_apd_df, api12)
        api12_df = pd.merge(
            api12_Borehole_apd, api12_well_data, how='inner',
            left_on=['API_WELL_NUMBER'], right_on=['API Well Number']
        )
        return api12_df

    def get_Borehole_apd_for_all_wells(self, cfg):
        BoreholeRawData_df = self.get_BoreholeRawData_from_csv(cfg)
        eWellAPDRawData_df = self.get_eWellAPDRawData_from_csv(cfg)
        self.Borehole_apd_df = self.get_merged_data(BoreholeRawData_df, eWellAPDRawData_df)
        return self.Borehole_apd_df

    def get_Borehole_apd_for_api12(self, cfg, Borehole_apd_df, api12):
        api12_Borehole_apd = Borehole_apd_df[Borehole_apd_df['API_WELL_NUMBER'] == api12].copy()
        return api12_Borehole_apd

    def get_well_data_from_website(self, cfg):
        output_data = []
        if cfg['data']['by'] == 'API12':
            website_data = self.get_well_data_by_api12(cfg, output_data)
        elif cfg['data']['by'] == 'block':
            website_data = self.get_well_data_by_block(cfg, output_data)
        
        well_data = {'type': 'csv', 'groups': output_data}
        cfg[cfg['basename']].update({'well_data': well_data})
        return cfg

    def get_well_data_by_api12(self, cfg, output_data):
        input_items = cfg['data']['groups']
        scrapy_runner_api = ScrapyRunnerAPI()

        for input_item in input_items:
            api_num = str(input_item['api12'][0])
            api_label = api_num
            if 'label' in input_item and input_item['label'][0] is not None:
                api_label = input_item['label'][0]
            input_item.update({'label': api_label})

            api12_data = scrapy_runner_api.run_spider(cfg, input_item)
            output_data = self.generate_output_item(cfg, output_data, input_item)

        return output_data, api12_data

    def generate_output_item(self, cfg, output_data, input_item):
        label = input_item['label']
        output_path = os.path.join(cfg['Analysis']['result_folder'], 'Data')
        if output_path is None:
            result_folder = cfg['Analysis']['result_folder']
            output_path = os.path.join(result_folder, 'Data')

        analysis_root_folder = cfg['Analysis']['analysis_root_folder']
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + '.csv')
        input_item_csv_cfg = deepcopy(input_item)
        input_item_csv_cfg.update({'label': label, 'file_name': output_file})
        output_data.append(input_item_csv_cfg)
        return output_data

```