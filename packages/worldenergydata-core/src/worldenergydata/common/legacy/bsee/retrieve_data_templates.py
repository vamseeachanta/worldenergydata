from __future__ import annotations

from typing import Any

# Reader imports
from assetutilities.common.data import AttributeDict
from assetutilities.common.yml_utilities import WorkingWithYAML

wwy = WorkingWithYAML()


class RetrieveDataTemplates:

    def __init__(self) -> None:
        pass

    def get_production_data_by_lease(
        self, custom_analysis_dict: dict[str, Any] | None = None
    ) -> AttributeDict:
        if custom_analysis_dict is None:
            custom_analysis_dict = {}

        library_name = "energydata"
        library_yaml_cfg: dict[str, str] = {
            "filename": "base_configs/modules/bsee/production_data_by_lease.yml",
            "library_name": library_name,
        }
        data_template = wwy.get_library_yaml_file(library_yaml_cfg)
        data_template["Analysis"] = custom_analysis_dict
        data_template = AttributeDict(data_template)

        return data_template

    def get_production_data_by_wellAPI(
        self, custom_analysis_dict: dict[str, Any] | None = None
    ) -> AttributeDict:
        if custom_analysis_dict is None:
            custom_analysis_dict = {}

        library_name = "energydata"
        library_yaml_cfg: dict[str, str] = {
            "filename": "base_configs/modules/bsee/production_data_by_wellAPI.yml",
            "library_name": library_name,
        }
        data_template = wwy.get_library_yaml_file(library_yaml_cfg)
        data_template["Analysis"] = custom_analysis_dict
        data_template = AttributeDict(data_template)

        return data_template

    def get_data_from_existing_files(
        self, custom_analysis_dict: dict[str, Any] | None = None
    ) -> AttributeDict:
        if custom_analysis_dict is None:
            custom_analysis_dict = {}

        library_name = "energydata"
        library_yaml_cfg: dict[str, str] = {
            "filename": "base_configs/modules/bsee/retrieve_data_from_files.yml",
            "library_name": library_name,
        }
        data_template = wwy.get_library_yaml_file(library_yaml_cfg)
        data_template["Analysis"] = custom_analysis_dict
        data_template = AttributeDict(data_template)

        return data_template
