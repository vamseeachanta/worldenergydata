"""
Template loader and configuration system
Handles template discovery, loading, and configuration management
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from jinja2 import DictLoader, Environment, FileSystemLoader, Template

from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)


class TemplateFormat(Enum):
    """Supported template formats"""

    HTML = "html"
    TEXT = "txt"
    MARKDOWN = "md"
    JSON = "json"
    XML = "xml"


@dataclass
class TemplateConfig:
    """Configuration for template system"""

    template_name: str
    template_type: str
    version: str = "1.0.0"
    format: TemplateFormat = TemplateFormat.HTML
    description: str = ""
    author: str = ""
    parent_template: Optional[str] = None
    required_context_fields: List[str] = field(default_factory=list)
    optional_context_fields: List[str] = field(default_factory=list)
    block_overrides: Dict[str, str] = field(default_factory=dict)
    custom_filters: Dict[str, str] = field(default_factory=dict)
    custom_functions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "TemplateConfig":
        """Load configuration from YAML or JSON file"""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Template config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yml", ".yaml"]:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == ".json":
                data = json.load(f)
            else:
                raise ValueError(
                    f"Unsupported config file format: {config_path.suffix}"
                )

        # Convert format string to enum
        if "format" in data:
            data["format"] = TemplateFormat(data["format"])

        return cls(**data)

    def to_file(self, config_path: Union[str, Path]):
        """Save configuration to YAML file"""
        config_path = Path(config_path)

        # Convert to serializable format
        data = {
            "template_name": self.template_name,
            "template_type": self.template_type,
            "version": self.version,
            "format": self.format.value,
            "description": self.description,
            "author": self.author,
            "parent_template": self.parent_template,
            "required_context_fields": self.required_context_fields,
            "optional_context_fields": self.optional_context_fields,
            "block_overrides": self.block_overrides,
            "custom_filters": self.custom_filters,
            "custom_functions": self.custom_functions,
            "metadata": self.metadata,
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)


class TemplateLoader:
    """
    Template loader and management system
    Handles template discovery, loading, and caching
    """

    def __init__(self, template_paths: Optional[List[Union[str, Path]]] = None):
        """
        Initialize template loader

        Args:
            template_paths: List of directories to search for templates
        """
        self.template_paths = []
        if template_paths:
            self.template_paths = [Path(p) for p in template_paths]
        else:
            self.template_paths = [self._get_default_template_path()]

        self.template_cache = {}
        self.config_cache = {}
        self.jinja_env = None
        self._setup_jinja_environment()

    def _get_default_template_path(self) -> Path:
        """Get default template path"""
        return Path(__file__).parent / "templates"

    def _setup_jinja_environment(self):
        """Setup Jinja2 environment with all template paths"""
        # Convert paths to strings for FileSystemLoader
        search_paths = [str(path) for path in self.template_paths if path.exists()]

        if search_paths:
            loader = FileSystemLoader(search_paths)
        else:
            # Fallback to empty dict loader
            loader = DictLoader({})

        self.jinja_env = Environment(
            loader=loader,
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Register default filters
        self.jinja_env.filters.update(self._get_default_filters())
        self.jinja_env.globals.update(self._get_default_functions())

    def _get_default_filters(self) -> Dict[str, callable]:
        """Get default Jinja2 filters"""
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

    def _get_default_functions(self) -> Dict[str, callable]:
        """Get default Jinja2 functions"""
        from datetime import date, datetime

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

    def add_template_path(self, path: Union[str, Path]):
        """Add additional template search path"""
        path = Path(path)
        if path not in self.template_paths:
            self.template_paths.append(path)
            # Recreate environment with new paths
            self._setup_jinja_environment()

    def discover_templates(self) -> List[Dict[str, Any]]:
        """
        Discover all available templates in search paths

        Returns:
            List of template information dictionaries
        """
        templates = []

        for search_path in self.template_paths:
            if not search_path.exists():
                continue

            # Find template files
            for template_file in search_path.rglob("*.html"):
                template_info = {
                    "name": template_file.stem,
                    "path": template_file,
                    "relative_path": template_file.relative_to(search_path),
                    "type": None,
                    "config": None,
                }

                # Look for corresponding config file
                config_file = template_file.with_suffix(".yml")
                if not config_file.exists():
                    config_file = template_file.with_suffix(".yaml")
                if not config_file.exists():
                    config_file = template_file.with_suffix(".json")

                if config_file.exists():
                    try:
                        config = TemplateConfig.from_file(config_file)
                        template_info["type"] = config.template_type
                        template_info["config"] = config
                    except Exception as e:
                        template_info["config_error"] = str(e)

                templates.append(template_info)

        return templates

    def load_template_config(self, template_name: str) -> Optional[TemplateConfig]:
        """
        Load configuration for a template

        Args:
            template_name: Name of template

        Returns:
            TemplateConfig object or None if not found
        """
        # Check cache first
        if template_name in self.config_cache:
            return self.config_cache[template_name]

        # Search for config file
        for search_path in self.template_paths:
            config_files = [
                search_path / f"{template_name}.yml",
                search_path / f"{template_name}.yaml",
                search_path / f"{template_name}.json",
            ]

            for config_file in config_files:
                if config_file.exists():
                    try:
                        config = TemplateConfig.from_file(config_file)
                        self.config_cache[template_name] = config
                        return config
                    except Exception as e:
                        logger.warning(
                            f"Warning: Failed to load config {config_file}: {e}"
                        )

        return None

    def load_template(
        self, template_name: str, template_type: Optional[str] = None
    ) -> Optional[Template]:
        """
        Load a template by name

        Args:
            template_name: Name of template
            template_type: Optional type filter

        Returns:
            Jinja2 Template object or None if not found
        """
        cache_key = f"{template_name}:{template_type}"

        # Check cache first
        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        # Try different file extensions and paths
        template_files = []

        for search_path in self.template_paths:
            if template_type:
                # Look in type-specific subdirectory first
                type_path = search_path / template_type
                if type_path.exists():
                    template_files.extend(
                        [
                            type_path / f"{template_name}.html",
                            type_path / f"{template_name}.txt",
                            type_path / f"{template_name}.md",
                        ]
                    )

            # Look in root path
            template_files.extend(
                [
                    search_path / f"{template_name}.html",
                    search_path / f"{template_name}.txt",
                    search_path / f"{template_name}.md",
                ]
            )

        # Try to load first existing template
        for template_file in template_files:
            if template_file.exists():
                try:
                    # Get relative path for Jinja2 loader
                    relative_path = None
                    for search_path in self.template_paths:
                        try:
                            relative_path = template_file.relative_to(search_path)
                            break
                        except ValueError:
                            continue

                    if relative_path:
                        template = self.jinja_env.get_template(str(relative_path))
                        self.template_cache[cache_key] = template
                        return template

                except Exception as e:
                    logger.warning(
                        f"Warning: Failed to load template {template_file}: {e}"
                    )

        return None

    def create_template_from_string(
        self, template_string: str, name: Optional[str] = None
    ) -> Template:
        """
        Create template from string content

        Args:
            template_string: Template content
            name: Optional name for template

        Returns:
            Jinja2 Template object
        """
        template = self.jinja_env.from_string(template_string)
        if name:
            # Cache the template
            self.template_cache[name] = template

        return template

    def get_template_list(self, template_type: Optional[str] = None) -> List[str]:
        """
        Get list of available template names

        Args:
            template_type: Optional type filter

        Returns:
            List of template names
        """
        templates = self.discover_templates()

        if template_type:
            templates = [t for t in templates if t.get("type") == template_type]

        return [t["name"] for t in templates]

    def validate_template(self, template_name: str) -> Dict[str, Any]:
        """
        Validate a template and its configuration

        Args:
            template_name: Name of template to validate

        Returns:
            Validation results dictionary
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "template_found": False,
            "config_found": False,
            "syntax_valid": False,
        }

        # Check if template exists
        template = self.load_template(template_name)
        if template:
            results["template_found"] = True

            # Test template syntax by trying to render with empty context
            try:
                template.render()
                results["syntax_valid"] = True
            except Exception as e:
                results["errors"].append(f"Template syntax error: {e}")
                results["valid"] = False
        else:
            results["errors"].append(f"Template '{template_name}' not found")
            results["valid"] = False

        # Check if config exists
        config = self.load_template_config(template_name)
        if config:
            results["config_found"] = True

            # Validate config
            if not config.template_name:
                results["warnings"].append("Template name not set in config")

            if not config.template_type:
                results["warnings"].append("Template type not set in config")
        else:
            results["warnings"].append(
                f"Configuration file not found for '{template_name}'"
            )

        return results

    def clear_cache(self):
        """Clear template and config caches"""
        self.template_cache.clear()
        self.config_cache.clear()

    def register_custom_filter(self, name: str, filter_func: callable):
        """Register custom Jinja2 filter"""
        self.jinja_env.filters[name] = filter_func

    def register_custom_function(self, name: str, function: callable):
        """Register custom Jinja2 global function"""
        self.jinja_env.globals[name] = function

    def __repr__(self) -> str:
        """String representation of loader"""
        return f"TemplateLoader(paths={len(self.template_paths)}, cached={len(self.template_cache)})"  # noqa: E501
