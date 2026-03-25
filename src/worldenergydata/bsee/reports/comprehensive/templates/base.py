"""
Base template system for comprehensive reporting
Implements Jinja2-based template rendering with context validation
"""

from datetime import date, datetime
from enum import Enum
from pathlib import Path

# Import models dynamically to avoid dependency issues
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from jinja2 import DictLoader, Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateError, TemplateNotFound, TemplateRuntimeError

if TYPE_CHECKING:
    pass


class TemplateType(Enum):
    """Enum for supported template types"""

    ECONOMIC = "economic"
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class TemplateContext(Dict[str, Any]):
    """Extended dict for template context with validation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.required_fields = set()
        self.validated = False

    def require_field(self, field_name: str):
        """Mark field as required for validation"""
        self.required_fields.add(field_name)

    def require_fields(self, field_names: List[str]):
        """Mark multiple fields as required"""
        self.required_fields.update(field_names)

    def validate(self):
        """Validate that all required fields are present"""
        missing_fields = self.required_fields - set(self.keys())
        if missing_fields:
            raise ValueError(
                f"Missing required context fields: {', '.join(missing_fields)}"
            )
        self.validated = True


class BaseReportTemplate:
    """
    Base class for report templates with Jinja2 integration
    Provides template loading, context building, and rendering capabilities
    """

    # Supported template types
    SUPPORTED_TEMPLATE_TYPES = [t.value for t in TemplateType]

    def __init__(
        self,
        template_name: str,
        template_type: str,
        version: str = "1.0.0",
        template_path: Optional[Union[str, Path]] = None,
        parent_template: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize BaseReportTemplate

        Args:
            template_name: Name of the template
            template_type: Type of template (economic, operational, compliance, executive)
            version: Template version
            template_path: Path to template files directory
            parent_template: Name of parent template for inheritance
        """
        # Validate template type
        if template_type not in self.SUPPORTED_TEMPLATE_TYPES:
            raise ValueError(
                f"Invalid template type: {template_type}. "
                f"Supported types: {', '.join(self.SUPPORTED_TEMPLATE_TYPES)}"
            )

        self.template_name = template_name
        self.template_type = template_type
        self.version = version
        self.template_path = (
            Path(template_path) if template_path else self._get_default_template_path()
        )
        self.parent_template = parent_template

        # Template metadata
        self.metadata = {}
        self.creation_date = datetime.now()

        # Context and rendering
        self.context = TemplateContext()
        self._setup_context_requirements()

        # Jinja2 environment
        self.jinja_env = self._create_jinja_environment()

        # Template inheritance
        self.inheritance_chain = []
        self.block_overrides = {}

        # Store additional kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _get_default_template_path(self) -> Path:
        """Get default template path based on package structure"""
        current_dir = Path(__file__).parent
        return current_dir / "templates" / self.template_type

    def _create_jinja_environment(self) -> Environment:
        """Create and configure Jinja2 environment with custom filters"""

        # Create loader based on template path
        if self.template_path and self.template_path.exists():
            loader = FileSystemLoader(str(self.template_path))
        else:
            # Use empty dict loader as fallback
            loader = DictLoader({})

        # Create environment
        env = Environment(
            loader=loader,
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Register custom filters
        env.filters.update(self._get_custom_filters())

        # Register custom functions
        env.globals.update(self._get_custom_functions())

        return env

    def _get_custom_filters(self) -> Dict[str, callable]:
        """Get custom Jinja2 filters for formatting"""
        return {
            "currency": lambda x, symbol="$": (
                f"{symbol}{x:,.2f}" if x is not None else "N/A"
            ),
            "percentage": lambda x, decimals=1: (
                f"{x:.{decimals}f}%" if x is not None else "N/A"
            ),
            "number_format": lambda x, decimals=0: (
                f"{x:,.{decimals}f}" if x is not None else "N/A"
            ),
            "date_format": lambda x, fmt="%Y-%m-%d": x.strftime(fmt) if x else "N/A",
            "bbl_format": lambda x: f"{x:,.0f} bbl" if x is not None else "N/A",
            "mcf_format": lambda x: f"{x:,.0f} Mcf" if x is not None else "N/A",
            "days_format": lambda x: f"{x:,} days" if x is not None else "N/A",
        }

    def _get_custom_functions(self) -> Dict[str, callable]:
        """Get custom Jinja2 functions for templates"""
        return {
            "now": lambda: datetime.now(),
            "today": lambda: date.today(),
            "sum_list": lambda lst, key=None: sum(
                item[key] if key else item for item in lst if item is not None
            ),
            "avg_list": lambda lst, key=None: (
                sum(item[key] if key else item for item in lst if item is not None)
                / len([x for x in lst if x is not None])
                if lst
                else 0
            ),
        }

    def _setup_context_requirements(self):
        """Set up required context fields based on template type"""
        base_requirements = ["report_date", "entity_id"]

        type_requirements = {
            TemplateType.ECONOMIC.value: ["production_metrics", "financial_summary"],
            TemplateType.OPERATIONAL.value: ["production_metrics", "operational_kpis"],
            TemplateType.COMPLIANCE.value: ["compliance_metrics", "regulatory_status"],
            TemplateType.EXECUTIVE.value: ["executive_summary", "strategic_kpis"],
        }

        # Set base requirements
        self.context.require_fields(base_requirements)

        # Add type-specific requirements
        if self.template_type in type_requirements:
            self.context.require_fields(type_requirements[self.template_type])

    def set_context(self, context: Dict[str, Any]):
        """Set template context"""
        self.context.clear()
        self.context.update(context)
        self.context.require_fields(
            list(self.context.required_fields)
        )  # Preserve requirements

    def update_context(self, context: Dict[str, Any]):
        """Update template context with new values"""
        self.context.update(context)

    def get_context(self) -> TemplateContext:
        """Get current template context"""
        return self.context

    def get_default_context(self) -> Dict[str, Any]:
        """Get default context variables available to all templates"""
        return {
            "report_title": f"{self.template_type.title()} Report",
            "generation_date": datetime.now(),
            "template_version": self.version,
            "template_name": self.template_name,
            "organization_hierarchy": {
                "levels": ["well", "lease", "field", "block"],
                "current_level": "field",  # Default
            },
        }

    def validate_context(self, context: Optional[Dict[str, Any]] = None):
        """Validate template context has required fields"""
        context_to_validate = context if context is not None else self.context

        if isinstance(context_to_validate, TemplateContext):
            context_to_validate.validate()
        else:
            # Convert to TemplateContext for validation
            temp_context = TemplateContext(context_to_validate)
            temp_context.require_fields(list(self.context.required_fields))
            temp_context.validate()

    def build_context_from_production(self, production: Any) -> Dict[str, Any]:
        """Build template context from production metrics"""
        context = {
            "production_metrics": {
                "oil_bbls": production.oil_production_bbls,
                "gas_mcf": production.gas_production_mcf,
                "water_bbls": production.water_production_bbls,
                "daily_oil_rate": production.daily_oil_rate,
                "daily_gas_rate": production.daily_gas_rate,
                "period_start": production.period_start,
                "period_end": production.period_end,
                "days_in_period": production.days_in_period,
                "active_well_count": production.active_well_count,
            },
            "entity_info": {
                "entity_id": production.entity_id,
                "entity_type": production.entity_type,
            },
            "financial_summary": {
                "oil_revenue": production.oil_revenue(),
                "gas_revenue": production.gas_revenue(),
                "total_revenue": production.total_revenue(),
                "net_revenue": production.net_revenue(),
                "operating_margin": production.operating_margin(),
            },
        }

        return context

    def build_context_from_economics(self, economics: Any) -> Dict[str, Any]:
        """Build template context from economic metrics"""
        context = {
            "economic_metrics": {
                "revenue": economics.revenue,
                "operating_costs": economics.operating_costs,
                "capital_costs": economics.capital_costs,
                "royalties": economics.royalties,
                "net_income": economics.calculate_net_income(),
                "production_bbls": economics.production_bbls,
            },
            "financial_ratios": {
                "operating_cost_per_bbl": economics.operating_cost_per_bbl,
                "revenue_per_bbl": economics.revenue_per_bbl,
                "netback_per_bbl": economics.netback_per_bbl,
                "profit_margin": economics.profit_margin,
            },
            "profitability": {
                "npv": economics.calculate_npv(),
                "discount_rate": economics.discount_rate,
                "years_projection": economics.years_from_start,
            },
        }

        return context

    def set_metadata(self, key: str, value: Any):
        """Set template metadata"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get template metadata"""
        return self.metadata.get(key, default)

    def register_block_override(self, block_name: str, template_file: str):
        """Register template block override for inheritance"""
        self.block_overrides[block_name] = template_file

    def get_block_overrides(self) -> Dict[str, str]:
        """Get registered block overrides"""
        return self.block_overrides.copy()

    def get_template_blocks(self) -> List[str]:
        """Get available template blocks"""
        # This would analyze the template file to find blocks
        # For now, return common blocks
        return ["header", "content", "footer", "sidebar", "charts"]

    def load_template(self, template_file: Optional[str] = None) -> Template:
        """Load template from file"""
        if template_file is None:
            template_file = f"{self.template_name}.html"

        try:
            return self.jinja_env.get_template(template_file)
        except TemplateNotFound:
            # Create a basic template if not found
            basic_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ report_title }}</title>
            </head>
            <body>
                <h1>{{ report_title }}</h1>
                <p>Generated on: {{ generation_date | date_format }}</p>
                <div class="content">
                    {% block content %}
                    <p>Template content goes here</p>
                    {% endblock %}
                </div>
            </body>
            </html>
            """
            return self.jinja_env.from_string(basic_template)

    def render(
        self,
        template_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render template with context"""
        # Merge contexts
        render_context = self.get_default_context()
        render_context.update(self.context)
        if context:
            render_context.update(context)

        # Validate context
        self.validate_context(render_context)

        # Load and render template
        template = self.load_template(template_file)

        try:
            return template.render(**render_context)
        except TemplateRuntimeError as e:
            raise TemplateRuntimeError(
                f"Error rendering template {self.template_name}: {str(e)}"
            )
        except Exception as e:
            raise TemplateError(
                f"Unexpected error rendering template {self.template_name}: {str(e)}"
            )

    def __repr__(self) -> str:
        """String representation of template"""
        return f"BaseReportTemplate(name='{self.template_name}', type='{self.template_type}', version='{self.version}')"
