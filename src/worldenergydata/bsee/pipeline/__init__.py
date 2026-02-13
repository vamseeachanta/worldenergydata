"""BSEE field analysis pipeline.

Orchestrates field data resolution, casing schematics, and reporting
for Bureau of Safety and Environmental Enforcement offshore data.
"""

from __future__ import annotations

from worldenergydata.bsee.pipeline.casing_schematic import (
    CasingString,
    casing_matrix,
    load_well_casing,
    render_casing_svg,
)
from worldenergydata.bsee.pipeline.field_query import (
    FieldContext,
    FieldQueryError,
    resolve_field,
)
from worldenergydata.bsee.pipeline.pipeline_runner import (
    FieldReport,
    PipelineRunner,
)
from worldenergydata.bsee.pipeline.field_report import (
    render_html,
    save_report,
)

__all__ = [
    "CasingString",
    "casing_matrix",
    "FieldContext",
    "FieldQueryError",
    "FieldReport",
    "load_well_casing",
    "PipelineRunner",
    "render_casing_svg",
    "render_html",
    "resolve_field",
    "save_report",
]
