"""Tests for safety analysis schema mapping and registry."""

import pytest

from worldenergydata.safety_analysis.core.schemas import (
    SchemaMapping,
    SchemaRegistry,
)
from worldenergydata.safety_analysis.exceptions import SafetyDataError


class TestSchemaMapping:
    def test_required_fields(self):
        m = SchemaMapping(
            name="test_mapping",
            asset_id_column="RIG_ID",
            datetime_column="OBS_DATE",
            description_column="DESCRIPTION",
        )
        assert m.name == "test_mapping"
        assert m.source_type == "observation"
        assert m.asset_id_column == "RIG_ID"

    def test_optional_defaults(self):
        m = SchemaMapping(
            name="test",
            asset_id_column="A",
            datetime_column="B",
            description_column="C",
        )
        assert m.type_column is None
        assert m.severity_column is None
        assert m.action_column is None
        assert m.type_mapping == {}
        assert m.severity_mapping == {}
        assert m.datetime_format is None
        assert m.id_extraction_regex is None
        assert m.extra_columns == {}

    def test_extract_asset_id_no_regex(self):
        m = SchemaMapping(
            name="test",
            asset_id_column="A",
            datetime_column="B",
            description_column="C",
        )
        assert m.extract_asset_id("RIG-001") == "RIG-001"

    def test_extract_asset_id_with_regex(self):
        m = SchemaMapping(
            name="test",
            asset_id_column="A",
            datetime_column="B",
            description_column="C",
            id_extraction_regex=r"RIG-\d+",
        )
        assert m.extract_asset_id("Unit: RIG-042 operated by CoA") == "RIG-042"

    def test_extract_asset_id_regex_no_match(self):
        m = SchemaMapping(
            name="test",
            asset_id_column="A",
            datetime_column="B",
            description_column="C",
            id_extraction_regex=r"RIG-\d+",
        )
        assert m.extract_asset_id("No match here") == "No match here"

    def test_with_mappings(self):
        m = SchemaMapping(
            name="custom",
            asset_id_column="FACILITY",
            datetime_column="DATE",
            description_column="DESC",
            source_type="incident",
            type_mapping={"INJ": "injury", "SPL": "spill"},
            severity_mapping={"HIGH": "severe", "LOW": "minor"},
        )
        assert m.source_type == "incident"
        assert m.type_mapping["INJ"] == "injury"
        assert m.severity_mapping["HIGH"] == "severe"


class TestSchemaRegistry:
    def _make_schema(self, name: str) -> SchemaMapping:
        return SchemaMapping(
            name=name,
            asset_id_column="ID",
            datetime_column="DT",
            description_column="DESC",
        )

    def test_register_and_get(self):
        reg = SchemaRegistry()
        schema = self._make_schema("test_schema")
        reg.register(schema)
        assert reg.get("test_schema") is schema

    def test_get_not_found(self):
        reg = SchemaRegistry()
        with pytest.raises(SafetyDataError):
            reg.get("nonexistent")

    def test_list_schemas_empty(self):
        reg = SchemaRegistry()
        assert reg.list_schemas() == []

    def test_list_schemas(self):
        reg = SchemaRegistry()
        reg.register(self._make_schema("a"))
        reg.register(self._make_schema("b"))
        names = reg.list_schemas()
        assert "a" in names
        assert "b" in names
        assert len(names) == 2

    def test_load_from_dict(self):
        reg = SchemaRegistry()
        reg.load_from_dict({
            "name": "from_dict",
            "asset_id_column": "ID",
            "datetime_column": "DT",
            "description_column": "DESC",
        })
        schema = reg.get("from_dict")
        assert schema.name == "from_dict"

    def test_register_overwrites(self):
        reg = SchemaRegistry()
        s1 = self._make_schema("test")
        s2 = SchemaMapping(
            name="test",
            asset_id_column="DIFFERENT",
            datetime_column="DT",
            description_column="DESC",
        )
        reg.register(s1)
        reg.register(s2)
        assert reg.get("test").asset_id_column == "DIFFERENT"

    def test_load_from_yaml(self, tmp_path):
        import yaml
        yaml_data = {
            "schemas": [
                {
                    "name": "yaml_schema",
                    "asset_id_column": "ASSET",
                    "datetime_column": "DATE",
                    "description_column": "TEXT",
                }
            ]
        }
        yaml_path = tmp_path / "schemas.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f)

        reg = SchemaRegistry()
        reg.load_from_yaml(yaml_path)
        schema = reg.get("yaml_schema")
        assert schema.asset_id_column == "ASSET"

    def test_load_from_yaml_list_format(self, tmp_path):
        import yaml
        yaml_data = [
            {
                "name": "list_schema",
                "asset_id_column": "ID",
                "datetime_column": "DT",
                "description_column": "DESC",
            }
        ]
        yaml_path = tmp_path / "list_schemas.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f)

        reg = SchemaRegistry()
        reg.load_from_yaml(yaml_path)
        assert "list_schema" in reg.list_schemas()
