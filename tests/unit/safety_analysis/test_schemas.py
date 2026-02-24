"""Tests for schema mapping and registry."""

import pytest
import yaml

from worldenergydata.safety_analysis.core.schemas import (
    SchemaMapping,
    SchemaRegistry,
)
from worldenergydata.safety_analysis.exceptions import SafetyDataError


class TestSchemaMapping:
    def test_create_minimal(self):
        schema = SchemaMapping(
            name="test",
            asset_id_column="rig_id",
            datetime_column="date",
            description_column="desc",
        )
        assert schema.name == "test"
        assert schema.source_type == "observation"

    def test_extract_asset_id_no_regex(self):
        schema = SchemaMapping(
            name="test",
            asset_id_column="rig_id",
            datetime_column="date",
            description_column="desc",
        )
        assert schema.extract_asset_id("RIG-001") == "RIG-001"

    def test_extract_asset_id_with_regex(self):
        schema = SchemaMapping(
            name="test",
            asset_id_column="rig_id",
            datetime_column="date",
            description_column="desc",
            id_extraction_regex=r"RIG-\d+",
        )
        assert schema.extract_asset_id("PREFIX_RIG-001_SUFFIX") == "RIG-001"

    def test_extract_asset_id_regex_no_match(self):
        schema = SchemaMapping(
            name="test",
            asset_id_column="rig_id",
            datetime_column="date",
            description_column="desc",
            id_extraction_regex=r"RIG-\d+",
        )
        assert schema.extract_asset_id("NORIG") == "NORIG"


class TestSchemaRegistry:
    def test_register_and_get(self):
        registry = SchemaRegistry()
        schema = SchemaMapping(
            name="test_schema",
            asset_id_column="rig_id",
            datetime_column="date",
            description_column="desc",
        )
        registry.register(schema)
        retrieved = registry.get("test_schema")
        assert retrieved.name == "test_schema"

    def test_get_missing_raises(self):
        registry = SchemaRegistry()
        with pytest.raises(SafetyDataError, match="not found"):
            registry.get("nonexistent")

    def test_list_schemas(self):
        registry = SchemaRegistry()
        schema = SchemaMapping(
            name="schema_a",
            asset_id_column="id",
            datetime_column="dt",
            description_column="d",
        )
        registry.register(schema)
        assert "schema_a" in registry.list_schemas()

    def test_load_from_yaml(self, tmp_path):
        yaml_data = {
            "schemas": [
                {
                    "name": "yaml_schema",
                    "asset_id_column": "rig_id",
                    "datetime_column": "date",
                    "description_column": "desc",
                }
            ]
        }
        yaml_path = tmp_path / "schemas.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f)

        registry = SchemaRegistry()
        registry.load_from_yaml(yaml_path)
        schema = registry.get("yaml_schema")
        assert schema.asset_id_column == "rig_id"

    def test_load_from_dict(self):
        registry = SchemaRegistry()
        registry.load_from_dict(
            {
                "name": "dict_schema",
                "asset_id_column": "facility_id",
                "datetime_column": "timestamp",
                "description_column": "notes",
            }
        )
        schema = registry.get("dict_schema")
        assert schema.asset_id_column == "facility_id"
