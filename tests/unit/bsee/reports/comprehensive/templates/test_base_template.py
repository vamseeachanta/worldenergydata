"""Tests for bsee.reports.comprehensive.templates.base module."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.base import (
    BaseReportTemplate,
    TemplateContext,
    TemplateType,
)


class TestTemplateType:
    def test_economic(self):
        assert TemplateType.ECONOMIC.value == "economic"

    def test_operational(self):
        assert TemplateType.OPERATIONAL.value == "operational"

    def test_compliance(self):
        assert TemplateType.COMPLIANCE.value == "compliance"

    def test_executive(self):
        assert TemplateType.EXECUTIVE.value == "executive"

    def test_custom(self):
        assert TemplateType.CUSTOM.value == "custom"


class TestTemplateContext:
    def test_init(self):
        ctx = TemplateContext()
        assert ctx.required_fields == set()
        assert ctx.validated is False

    def test_require_field(self):
        ctx = TemplateContext()
        ctx.require_field("name")
        assert "name" in ctx.required_fields

    def test_require_fields(self):
        ctx = TemplateContext()
        ctx.require_fields(["a", "b", "c"])
        assert ctx.required_fields == {"a", "b", "c"}

    def test_validate_success(self):
        ctx = TemplateContext({"a": 1, "b": 2})
        ctx.require_fields(["a", "b"])
        ctx.validate()
        assert ctx.validated is True

    def test_validate_missing_field(self):
        ctx = TemplateContext({"a": 1})
        ctx.require_fields(["a", "b"])
        with pytest.raises(ValueError, match="Missing required context fields"):
            ctx.validate()


class TestBaseReportTemplate:
    def test_init_economic(self):
        tmpl = BaseReportTemplate("test", "economic")
        assert tmpl.template_name == "test"
        assert tmpl.template_type == "economic"
        assert tmpl.version == "1.0.0"

    def test_init_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid template type"):
            BaseReportTemplate("test", "invalid_type")

    def test_supported_template_types(self):
        types = BaseReportTemplate.SUPPORTED_TEMPLATE_TYPES
        assert "economic" in types
        assert "operational" in types

    def test_set_metadata(self):
        tmpl = BaseReportTemplate("test", "economic")
        tmpl.set_metadata("author", "test_user")
        assert tmpl.get_metadata("author") == "test_user"

    def test_get_metadata_default(self):
        tmpl = BaseReportTemplate("test", "economic")
        assert tmpl.get_metadata("missing", "default") == "default"

    def test_update_context(self):
        tmpl = BaseReportTemplate("test", "economic")
        tmpl.update_context({"key": "value"})
        assert tmpl.context["key"] == "value"

    def test_set_context(self):
        tmpl = BaseReportTemplate("test", "economic")
        tmpl.set_context({"key": "value"})
        assert tmpl.context["key"] == "value"

    def test_get_context(self):
        tmpl = BaseReportTemplate("test", "economic")
        ctx = tmpl.get_context()
        assert isinstance(ctx, TemplateContext)

    def test_get_default_context(self):
        tmpl = BaseReportTemplate("test", "economic")
        ctx = tmpl.get_default_context()
        assert "report_title" in ctx
        assert "generation_date" in ctx
        assert "template_version" in ctx

    def test_register_block_override(self):
        tmpl = BaseReportTemplate("test", "economic")
        tmpl.register_block_override("header", "custom_header.html")
        overrides = tmpl.get_block_overrides()
        assert overrides["header"] == "custom_header.html"

    def test_get_template_blocks(self):
        tmpl = BaseReportTemplate("test", "economic")
        blocks = tmpl.get_template_blocks()
        assert "header" in blocks
        assert "content" in blocks

    def test_repr(self):
        tmpl = BaseReportTemplate("my_template", "economic", "2.0.0")
        r = repr(tmpl)
        assert "my_template" in r
        assert "economic" in r
        assert "2.0.0" in r

    def test_kwargs_stored(self):
        tmpl = BaseReportTemplate("test", "economic", custom_param="hello")
        assert tmpl.custom_param == "hello"

    def test_load_template_fallback(self):
        tmpl = BaseReportTemplate("test", "economic")
        template = tmpl.load_template("nonexistent.html")
        assert template is not None

    def test_validate_context_with_dict(self):
        tmpl = BaseReportTemplate("test", "custom")
        # custom type has no extra requirements beyond base
        ctx = {"report_date": "2024-01-01", "entity_id": "E001"}
        tmpl.validate_context(ctx)

    def test_validate_context_missing_raises(self):
        tmpl = BaseReportTemplate("test", "economic")
        with pytest.raises(ValueError):
            tmpl.validate_context({"report_date": "2024-01-01"})

    def test_render_basic(self):
        tmpl = BaseReportTemplate("test", "custom")
        tmpl.update_context(
            {
                "report_date": "2024-01-01",
                "entity_id": "E001",
            }
        )
        result = tmpl.render()
        assert isinstance(result, str)
        assert "Template content" in result

    def test_render_with_extra_context(self):
        tmpl = BaseReportTemplate("test", "custom")
        result = tmpl.render(
            context={
                "report_date": "2024-01-01",
                "entity_id": "E001",
            }
        )
        assert isinstance(result, str)

    def test_custom_filters(self):
        tmpl = BaseReportTemplate("test", "economic")
        filters = tmpl._get_custom_filters()
        assert "currency" in filters
        assert "percentage" in filters
        assert "bbl_format" in filters
        assert filters["currency"](1000) == "$1,000.00"
        assert filters["currency"](None) == "N/A"
        assert filters["bbl_format"](1000) == "1,000 bbl"
        assert filters["bbl_format"](None) == "N/A"

    def test_custom_functions(self):
        tmpl = BaseReportTemplate("test", "economic")
        funcs = tmpl._get_custom_functions()
        assert "now" in funcs
        assert "today" in funcs
        assert "sum_list" in funcs
