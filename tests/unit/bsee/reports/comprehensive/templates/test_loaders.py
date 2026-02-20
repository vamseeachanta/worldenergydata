"""Tests for template loader and configuration system."""

import json
from pathlib import Path

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.loaders import (
    TemplateConfig,
    TemplateFormat,
    TemplateLoader,
)


class TestTemplateFormat:
    def test_values(self):
        assert TemplateFormat.HTML.value == "html"
        assert TemplateFormat.TEXT.value == "txt"
        assert TemplateFormat.MARKDOWN.value == "md"
        assert TemplateFormat.JSON.value == "json"
        assert TemplateFormat.XML.value == "xml"

    def test_count(self):
        assert len(TemplateFormat) == 5


class TestTemplateConfig:
    def test_basic(self):
        tc = TemplateConfig(
            template_name="test_template",
            template_type="economic",
        )
        assert tc.template_name == "test_template"
        assert tc.template_type == "economic"
        assert tc.version == "1.0.0"
        assert tc.format == TemplateFormat.HTML
        assert tc.description == ""
        assert tc.author == ""
        assert tc.parent_template is None
        assert tc.required_context_fields == []
        assert tc.optional_context_fields == []
        assert tc.block_overrides == {}
        assert tc.custom_filters == {}
        assert tc.custom_functions == {}
        assert tc.metadata == {}

    def test_custom_fields(self):
        tc = TemplateConfig(
            template_name="test",
            template_type="operational",
            version="2.0.0",
            format=TemplateFormat.JSON,
            description="Test template",
            author="tester",
            parent_template="base",
            required_context_fields=["field1"],
            optional_context_fields=["field2"],
        )
        assert tc.version == "2.0.0"
        assert tc.format == TemplateFormat.JSON
        assert tc.description == "Test template"
        assert tc.author == "tester"
        assert tc.parent_template == "base"
        assert tc.required_context_fields == ["field1"]

    def test_from_json_file(self, tmp_path):
        config_data = {
            "template_name": "test_template",
            "template_type": "economic",
            "version": "1.0.0",
            "format": "html",
            "description": "A test template",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        tc = TemplateConfig.from_file(config_file)
        assert tc.template_name == "test_template"
        assert tc.template_type == "economic"
        assert tc.format == TemplateFormat.HTML

    def test_from_yaml_file(self, tmp_path):
        import yaml

        config_data = {
            "template_name": "yaml_template",
            "template_type": "compliance",
            "version": "1.0.0",
            "format": "json",
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))

        tc = TemplateConfig.from_file(config_file)
        assert tc.template_name == "yaml_template"
        assert tc.format == TemplateFormat.JSON

    def test_from_yml_file(self, tmp_path):
        import yaml

        config_data = {
            "template_name": "yml_template",
            "template_type": "operational",
        }
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(config_data))

        tc = TemplateConfig.from_file(config_file)
        assert tc.template_name == "yml_template"

    def test_from_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            TemplateConfig.from_file("/nonexistent/config.json")

    def test_from_file_unsupported_format(self, tmp_path):
        config_file = tmp_path / "config.txt"
        config_file.write_text("not a config")
        with pytest.raises(ValueError, match="Unsupported config file format"):
            TemplateConfig.from_file(config_file)

    def test_to_file(self, tmp_path):
        import yaml

        tc = TemplateConfig(
            template_name="save_test",
            template_type="executive",
            description="Saved template",
        )
        config_file = tmp_path / "output.yaml"
        tc.to_file(config_file)

        with open(config_file) as f:
            data = yaml.safe_load(f)

        assert data["template_name"] == "save_test"
        assert data["template_type"] == "executive"
        assert data["format"] == "html"
        assert data["description"] == "Saved template"

    def test_roundtrip_json(self, tmp_path):
        tc = TemplateConfig(
            template_name="roundtrip",
            template_type="economic",
            format=TemplateFormat.JSON,
            required_context_fields=["f1", "f2"],
        )
        out_file = tmp_path / "roundtrip.yaml"
        tc.to_file(out_file)

        # Read back (as yaml)
        import yaml

        with open(out_file) as f:
            data = yaml.safe_load(f)
        assert data["template_name"] == "roundtrip"
        assert data["required_context_fields"] == ["f1", "f2"]


class TestTemplateLoader:
    def test_init_default(self):
        loader = TemplateLoader()
        assert len(loader.template_paths) == 1
        assert loader.template_cache == {}
        assert loader.config_cache == {}
        assert loader.jinja_env is not None

    def test_init_custom_paths(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        assert len(loader.template_paths) == 1
        assert loader.template_paths[0] == tmp_path

    def test_add_template_path(self, tmp_path):
        loader = TemplateLoader()
        initial_count = len(loader.template_paths)
        loader.add_template_path(tmp_path)
        assert len(loader.template_paths) == initial_count + 1

    def test_add_duplicate_path(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        loader.add_template_path(tmp_path)
        assert len(loader.template_paths) == 1

    def test_discover_templates_empty(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        templates = loader.discover_templates()
        assert templates == []

    def test_discover_templates_with_files(self, tmp_path):
        # Create a template file
        tmpl = tmp_path / "test_template.html"
        tmpl.write_text("<h1>{{ title }}</h1>")

        loader = TemplateLoader(template_paths=[str(tmp_path)])
        templates = loader.discover_templates()
        assert len(templates) == 1
        assert templates[0]["name"] == "test_template"

    def test_create_template_from_string(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        template = loader.create_template_from_string("Hello {{ name }}")
        result = template.render(name="World")
        assert result == "Hello World"

    def test_create_template_from_string_cached(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        loader.create_template_from_string("Hi {{ x }}", name="test_tmpl")
        assert "test_tmpl" in loader.template_cache

    def test_clear_cache(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        loader.template_cache["key"] = "value"
        loader.config_cache["key"] = "value"
        loader.clear_cache()
        assert loader.template_cache == {}
        assert loader.config_cache == {}

    def test_register_custom_filter(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        loader.register_custom_filter("upper_first", lambda s: s[0].upper() + s[1:])
        tmpl = loader.create_template_from_string("{{ name | upper_first }}")
        result = tmpl.render(name="hello")
        assert result == "Hello"

    def test_register_custom_function(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        loader.register_custom_function("greet", lambda n: f"Hi {n}")
        tmpl = loader.create_template_from_string("{{ greet('Bob') }}")
        result = tmpl.render()
        assert result == "Hi Bob"

    def test_default_filters(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        filters = loader._get_default_filters()
        assert "currency" in filters
        assert "percentage" in filters
        assert "number_format" in filters
        assert "bbl_format" in filters
        assert "mcf_format" in filters
        assert "days_format" in filters

    def test_repr(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        r = repr(loader)
        assert "TemplateLoader" in r
        assert "paths=1" in r

    def test_load_template_not_found(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        result = loader.load_template("nonexistent")
        assert result is None

    def test_load_template_found(self, tmp_path):
        tmpl_file = tmp_path / "test.html"
        tmpl_file.write_text("<p>{{ content }}</p>")
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        tmpl = loader.load_template("test")
        assert tmpl is not None
        result = tmpl.render(content="hello")
        assert "hello" in result

    def test_load_template_cached(self, tmp_path):
        tmpl_file = tmp_path / "test.html"
        tmpl_file.write_text("<p>{{ content }}</p>")
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        tmpl1 = loader.load_template("test")
        tmpl2 = loader.load_template("test")
        assert tmpl1 is tmpl2

    def test_get_template_list_empty(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        result = loader.get_template_list()
        assert result == []

    def test_get_template_list_with_templates(self, tmp_path):
        (tmp_path / "report.html").write_text("<h1>Report</h1>")
        (tmp_path / "summary.html").write_text("<h1>Summary</h1>")
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        result = loader.get_template_list()
        assert len(result) == 2

    def test_load_template_config_not_found(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        result = loader.load_template_config("nonexistent")
        assert result is None

    def test_load_template_config_found(self, tmp_path):
        import yaml

        config_data = {
            "template_name": "test",
            "template_type": "economic",
        }
        (tmp_path / "test.yaml").write_text(yaml.dump(config_data))
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        config = loader.load_template_config("test")
        assert config is not None
        assert config.template_name == "test"

    def test_load_template_config_cached(self, tmp_path):
        import yaml

        config_data = {
            "template_name": "test",
            "template_type": "economic",
        }
        (tmp_path / "test.yaml").write_text(yaml.dump(config_data))
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        config1 = loader.load_template_config("test")
        config2 = loader.load_template_config("test")
        assert config1 is config2

    def test_validate_template_not_found(self, tmp_path):
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        result = loader.validate_template("nonexistent")
        assert result["valid"] is False
        assert result["template_found"] is False

    def test_validate_template_found(self, tmp_path):
        (tmp_path / "test.html").write_text("<p>{{ content }}</p>")
        loader = TemplateLoader(template_paths=[str(tmp_path)])
        result = loader.validate_template("test")
        assert result["template_found"] is True
        assert result["syntax_valid"] is True
