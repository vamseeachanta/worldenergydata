"""Tests for base template system for comprehensive reporting."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.base import (
    BaseReportTemplate,
    TemplateContext,
    TemplateType,
)


class TestTemplateType:
    def test_values(self):
        assert TemplateType.ECONOMIC.value == "economic"
        assert TemplateType.OPERATIONAL.value == "operational"
        assert TemplateType.COMPLIANCE.value == "compliance"
        assert TemplateType.EXECUTIVE.value == "executive"
        assert TemplateType.CUSTOM.value == "custom"

    def test_count(self):
        assert len(TemplateType) == 5


class TestTemplateContext:
    def test_init_empty(self):
        ctx = TemplateContext()
        assert ctx.required_fields == set()
        assert ctx.validated is False

    def test_init_with_data(self):
        ctx = TemplateContext({"key": "value"})
        assert ctx["key"] == "value"

    def test_require_field(self):
        ctx = TemplateContext()
        ctx.require_field("report_date")
        assert "report_date" in ctx.required_fields

    def test_require_fields(self):
        ctx = TemplateContext()
        ctx.require_fields(["report_date", "entity_id"])
        assert ctx.required_fields == {"report_date", "entity_id"}

    def test_validate_success(self):
        ctx = TemplateContext({"report_date": "2024-01-01", "entity_id": "W001"})
        ctx.require_fields(["report_date", "entity_id"])
        ctx.validate()
        assert ctx.validated is True

    def test_validate_missing_fields(self):
        ctx = TemplateContext({"report_date": "2024-01-01"})
        ctx.require_fields(["report_date", "entity_id"])
        with pytest.raises(ValueError, match="Missing required context fields"):
            ctx.validate()

    def test_validate_empty_context_with_requirements(self):
        ctx = TemplateContext()
        ctx.require_field("entity_id")
        with pytest.raises(ValueError, match="entity_id"):
            ctx.validate()

    def test_validate_no_requirements(self):
        ctx = TemplateContext()
        ctx.validate()
        assert ctx.validated is True


class TestBaseReportTemplateInit:
    def test_economic(self):
        t = BaseReportTemplate("test_report", "economic")
        assert t.template_name == "test_report"
        assert t.template_type == "economic"
        assert t.version == "1.0.0"
        assert t.parent_template is None
        assert t.metadata == {}
        assert t.block_overrides == {}

    def test_operational(self):
        t = BaseReportTemplate("ops_report", "operational")
        assert t.template_type == "operational"

    def test_compliance(self):
        t = BaseReportTemplate("compliance_report", "compliance")
        assert t.template_type == "compliance"

    def test_executive(self):
        t = BaseReportTemplate("exec_report", "executive")
        assert t.template_type == "executive"

    def test_custom(self):
        t = BaseReportTemplate("custom_report", "custom")
        assert t.template_type == "custom"

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid template type"):
            BaseReportTemplate("bad_report", "invalid_type")

    def test_custom_version(self):
        t = BaseReportTemplate("test", "economic", version="2.0.0")
        assert t.version == "2.0.0"

    def test_with_parent_template(self):
        t = BaseReportTemplate(
            "child", "economic", parent_template="parent_template"
        )
        assert t.parent_template == "parent_template"

    def test_supported_template_types(self):
        assert "economic" in BaseReportTemplate.SUPPORTED_TEMPLATE_TYPES
        assert "operational" in BaseReportTemplate.SUPPORTED_TEMPLATE_TYPES
        assert "compliance" in BaseReportTemplate.SUPPORTED_TEMPLATE_TYPES
        assert "executive" in BaseReportTemplate.SUPPORTED_TEMPLATE_TYPES
        assert "custom" in BaseReportTemplate.SUPPORTED_TEMPLATE_TYPES


class TestContextRequirements:
    def test_economic_requirements(self):
        t = BaseReportTemplate("test", "economic")
        required = t.context.required_fields
        assert "report_date" in required
        assert "entity_id" in required
        assert "production_metrics" in required
        assert "financial_summary" in required

    def test_operational_requirements(self):
        t = BaseReportTemplate("test", "operational")
        required = t.context.required_fields
        assert "report_date" in required
        assert "entity_id" in required
        assert "production_metrics" in required
        assert "operational_kpis" in required

    def test_compliance_requirements(self):
        t = BaseReportTemplate("test", "compliance")
        required = t.context.required_fields
        assert "compliance_metrics" in required
        assert "regulatory_status" in required

    def test_executive_requirements(self):
        t = BaseReportTemplate("test", "executive")
        required = t.context.required_fields
        assert "executive_summary" in required
        assert "strategic_kpis" in required

    def test_custom_has_base_requirements_only(self):
        t = BaseReportTemplate("test", "custom")
        required = t.context.required_fields
        assert "report_date" in required
        assert "entity_id" in required
        # Custom type should not have type-specific requirements
        assert "production_metrics" not in required


class TestContextManagement:
    def test_set_context(self):
        t = BaseReportTemplate("test", "economic")
        t.set_context({"report_date": "2024-01-01", "entity_id": "W001"})
        assert t.context["report_date"] == "2024-01-01"
        assert t.context["entity_id"] == "W001"

    def test_update_context(self):
        t = BaseReportTemplate("test", "economic")
        t.set_context({"report_date": "2024-01-01"})
        t.update_context({"entity_id": "W001"})
        assert t.context["report_date"] == "2024-01-01"
        assert t.context["entity_id"] == "W001"

    def test_get_context(self):
        t = BaseReportTemplate("test", "economic")
        ctx = t.get_context()
        assert isinstance(ctx, TemplateContext)

    def test_get_default_context(self):
        t = BaseReportTemplate("test", "economic")
        default = t.get_default_context()
        assert "report_title" in default
        assert "generation_date" in default
        assert "template_version" in default
        assert default["template_version"] == "1.0.0"
        assert default["template_name"] == "test"


class TestMetadata:
    def test_set_get(self):
        t = BaseReportTemplate("test", "economic")
        t.set_metadata("author", "tester")
        assert t.get_metadata("author") == "tester"

    def test_get_default(self):
        t = BaseReportTemplate("test", "economic")
        assert t.get_metadata("missing") is None
        assert t.get_metadata("missing", "default") == "default"


class TestBlockOverrides:
    def test_register(self):
        t = BaseReportTemplate("test", "economic")
        t.register_block_override("header", "custom_header.html")
        overrides = t.get_block_overrides()
        assert overrides["header"] == "custom_header.html"

    def test_get_returns_copy(self):
        t = BaseReportTemplate("test", "economic")
        t.register_block_override("header", "custom_header.html")
        overrides = t.get_block_overrides()
        overrides["footer"] = "new_footer.html"
        assert "footer" not in t.get_block_overrides()


class TestTemplateBlocks:
    def test_get_template_blocks(self):
        t = BaseReportTemplate("test", "economic")
        blocks = t.get_template_blocks()
        assert "header" in blocks
        assert "content" in blocks
        assert "footer" in blocks


class TestCustomFilters:
    def test_currency_filter(self):
        t = BaseReportTemplate("test", "economic")
        currency = t.jinja_env.filters["currency"]
        assert currency(1234.56) == "$1,234.56"
        assert currency(None) == "N/A"

    def test_percentage_filter(self):
        t = BaseReportTemplate("test", "economic")
        percentage = t.jinja_env.filters["percentage"]
        assert percentage(95.5) == "95.5%"
        assert percentage(None) == "N/A"

    def test_number_format_filter(self):
        t = BaseReportTemplate("test", "economic")
        number_format = t.jinja_env.filters["number_format"]
        assert number_format(1234567) == "1,234,567"
        assert number_format(None) == "N/A"

    def test_bbl_format_filter(self):
        t = BaseReportTemplate("test", "economic")
        bbl_format = t.jinja_env.filters["bbl_format"]
        assert bbl_format(1234) == "1,234 bbl"
        assert bbl_format(None) == "N/A"

    def test_mcf_format_filter(self):
        t = BaseReportTemplate("test", "economic")
        mcf_format = t.jinja_env.filters["mcf_format"]
        assert mcf_format(5678) == "5,678 Mcf"
        assert mcf_format(None) == "N/A"

    def test_days_format_filter(self):
        t = BaseReportTemplate("test", "economic")
        days_format = t.jinja_env.filters["days_format"]
        assert days_format(365) == "365 days"
        assert days_format(None) == "N/A"


class TestRepr:
    def test_repr(self):
        t = BaseReportTemplate("test_report", "economic", version="2.0.0")
        r = repr(t)
        assert "test_report" in r
        assert "economic" in r
        assert "2.0.0" in r


class TestCreateTemplateFromString:
    def test_basic(self):
        t = BaseReportTemplate("test", "economic")
        template = t.jinja_env.from_string("Hello {{ name }}")
        result = template.render(name="World")
        assert result == "Hello World"

    def test_with_filters(self):
        t = BaseReportTemplate("test", "economic")
        template = t.jinja_env.from_string("Revenue: {{ amount | currency }}")
        result = template.render(amount=1234.56)
        assert result == "Revenue: $1,234.56"
