# ABOUTME: Equipment failure table: incidents by equipment class, failure mode and stated cause.
# ABOUTME: Feeds the HSE and safety report appendix; see docs/hse/equipment-failure-table.md.

"""Equipment failure taxonomy, table and report section."""

from worldenergydata.safety_analysis.equipment.cases import PublicCase, load_cases
from worldenergydata.safety_analysis.equipment.classify import (
    EquipmentFailureRow,
    classify_records,
)
from worldenergydata.safety_analysis.equipment.report_section import (
    HseSection,
    build_section,
    render_markdown,
)
from worldenergydata.safety_analysis.equipment.table import (
    SourceFile,
    build_table,
    coverage,
    query,
    summarise,
)
from worldenergydata.safety_analysis.equipment.taxonomy import (
    EQUIPMENT_CLASSES,
    FAILURE_MECHANISMS,
    FAILURE_MODES,
)

__all__ = [
    "EQUIPMENT_CLASSES",
    "FAILURE_MECHANISMS",
    "FAILURE_MODES",
    "EquipmentFailureRow",
    "HseSection",
    "PublicCase",
    "SourceFile",
    "build_section",
    "build_table",
    "classify_records",
    "coverage",
    "load_cases",
    "query",
    "render_markdown",
    "summarise",
]
