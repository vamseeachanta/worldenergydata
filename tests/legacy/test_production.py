from energydata.common.ymlInput import ymlInput
from energydata.common.legacy.data_models_components import DataModelsComponents

cfg_yaml = 'C:/GitHub/energydata/src/energydata/tests/legacy/data/bsee_yearly_production_data.yml'
cfg = ymlInput(cfg_yaml, None)

dm = DataModelsComponents(cfg)

