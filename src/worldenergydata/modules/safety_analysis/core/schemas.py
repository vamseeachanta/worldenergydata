"""
Schema Mapping for Safety Data Sources

Configurable column mappings to transform any safety data source
into the unified SafetyObservation/SafetyIncident models.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from worldenergydata.modules.safety_analysis.exceptions import SafetyDataError


class SchemaMapping(BaseModel):
    """Column mapping from a data source to the unified schema."""

    name: str = Field(..., description="Name of this schema mapping")
    source_type: str = Field(
        default="observation",
        description="Type of data: 'observation' or 'incident'",
    )
    asset_id_column: str = Field(
        ..., description="Column name for asset/rig/facility ID"
    )
    datetime_column: str = Field(..., description="Column name for datetime")
    description_column: str = Field(..., description="Column name for description text")
    type_column: Optional[str] = Field(
        default=None, description="Column for observation/incident type"
    )
    severity_column: Optional[str] = Field(
        default=None, description="Column for severity level"
    )
    potential_severity_column: Optional[str] = Field(
        default=None, description="Column for potential severity"
    )
    action_column: Optional[str] = Field(
        default=None, description="Column for action taken"
    )
    work_activity_column: Optional[str] = Field(
        default=None, description="Column for work activity"
    )
    type_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Map source type values to standard types",
    )
    severity_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Map source severity values to standard levels",
    )
    datetime_format: Optional[str] = Field(
        default=None, description="Date parsing format string"
    )
    id_extraction_regex: Optional[str] = Field(
        default=None,
        description="Regex to extract asset ID from column value",
    )
    extra_columns: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional columns to include in metadata",
    )

    def extract_asset_id(self, raw_value: str) -> str:
        """Extract asset ID using regex if configured, else return raw."""
        if self.id_extraction_regex:
            match = re.search(self.id_extraction_regex, raw_value)
            if match:
                return match.group(0)
        return raw_value


class SchemaRegistry:
    """Registry of schema mappings, loadable from YAML files."""

    def __init__(self) -> None:
        self._schemas: Dict[str, SchemaMapping] = {}

    def register(self, schema: SchemaMapping) -> None:
        """Register a schema mapping."""
        self._schemas[schema.name] = schema

    def get(self, name: str) -> SchemaMapping:
        """Get a schema mapping by name."""
        if name not in self._schemas:
            raise SafetyDataError(
                message=f"Schema mapping '{name}' not found",
                code="SAFETY_SCHEMA_NOT_FOUND",
                context={
                    "name": name,
                    "available": list(self._schemas.keys()),
                },
            )
        return self._schemas[name]

    def list_schemas(self) -> List[str]:
        """List all registered schema names."""
        return list(self._schemas.keys())

    def load_from_yaml(self, path: Path) -> None:
        """Load schema mappings from a YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise SafetyDataError.load_failed(
                str(path), "Failed to parse YAML", cause=e
            )

        schemas = data if isinstance(data, list) else data.get("schemas", [])
        for schema_data in schemas:
            schema = SchemaMapping(**schema_data)
            self.register(schema)

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Load a single schema mapping from a dictionary."""
        schema = SchemaMapping(**data)
        self.register(schema)
