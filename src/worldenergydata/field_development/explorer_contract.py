"""Tooling contract for the existing composite Explorer sidecar.

Only envelope objects and field identity are checked. Panel bodies, metadata
contents and the inner wells contract remain opaque and retain their original
values. This module is not part of the standard-library publication path.
"""

from typing import Any, cast

from pydantic import BaseModel, ConfigDict, model_validator


class ExplorerField(BaseModel):
    """Identity supplied by the poster producer, plus additive panel content."""

    model_config = ConfigDict(strict=True, extra="allow")

    id: str
    name: str


class ExplorerPanels(BaseModel):
    """Composite envelope for the field Explorer.

    Nested panel bodies are not validated. Map-key/id equality is a procedural
    check in the typed validator, not a guarantee of JSON Schema alone.
    """

    model_config = ConfigDict(
        strict=True,
        extra="allow",
        json_schema_extra={"$schema": "https://json-schema.org/draft/2020-12/schema"},
    )

    meta: dict[str, Any]
    fields: dict[str, ExplorerField]
    wells: dict[str, Any]

    @model_validator(mode="after")
    def check_field_keys(self) -> "ExplorerPanels":
        for key, record in self.fields.items():
            if key != record.id:
                raise ValueError("map key must match field id")
        return self


def validate_explorer_payload(payload: object) -> dict[str, Any]:
    """Validate a parsed JSON object and return that same, unmodified object.

    Raises Pydantic ValidationError on an invalid envelope or field identity.
    No defaults, unit conversions, panel normalization or file writes occur.
    """
    ExplorerPanels.model_validate(payload)
    return cast(dict[str, Any], payload)


def explorer_panel_schema() -> dict[str, Any]:
    """Emit the structural schema from the same model used for validation."""
    return ExplorerPanels.model_json_schema()
