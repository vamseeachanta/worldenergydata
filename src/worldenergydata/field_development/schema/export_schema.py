# ABOUTME: Regenerates field_concept.schema.json from the Pydantic model.
# ABOUTME: Issue #568 — the model is the source of truth; JSON schema is derived.
"""
Regenerate ``field_concept.schema.json`` from :class:`FieldConcept`.

Run:  ``uv run python -m worldenergydata.field_development.schema.export_schema``

A unit test asserts the committed JSON matches the model output, so the two can
never silently drift. Re-run this script whenever the model changes.
"""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.field_development.models import FieldConcept

SCHEMA_PATH = Path(__file__).with_name("field_concept.schema.json")


def build_schema() -> dict:
    """Return the JSON Schema for :class:`FieldConcept`."""
    return FieldConcept.model_json_schema()


def write_schema() -> Path:
    """Write the JSON Schema to disk (pretty-printed, trailing newline)."""
    SCHEMA_PATH.write_text(
        json.dumps(build_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return SCHEMA_PATH


if __name__ == "__main__":
    path = write_schema()
    print(f"wrote {path}")
