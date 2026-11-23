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
from worldenergydata.bsee.pipeline.document_retrieval import (
    DocumentRetrievalError,
    download_document_queue,
)
from worldenergydata.bsee.pipeline.field_cost_integration import (
    FieldPipelineCostIntegrator,
)
from worldenergydata.bsee.pipeline.field_infrastructure import (
    FieldInfrastructureBundle,
    FieldInfrastructureError,
    build_field_infrastructure_bundle,
    default_bsee_bin_root,
    write_field_infrastructure_bundle,
)
from worldenergydata.bsee.pipeline.field_package import (
    FIELD_PACKAGE_CONTRACT_VERSION,
    FieldPackageError,
    build_field_package,
    render_field_package_html,
)
from worldenergydata.bsee.pipeline.field_query import (
    FieldContext,
    FieldQueryError,
    resolve_field,
)
from worldenergydata.bsee.pipeline.field_report import render_html, save_report
from worldenergydata.bsee.pipeline.pipeline_runner import FieldReport, PipelineRunner
from worldenergydata.bsee.pipeline.reviewer_input_import import (
    ReviewerInputImportError,
    import_reviewer_ready_inputs,
)
from worldenergydata.bsee.pipeline.source_document_index import (
    SourceDocumentIndexError,
    build_source_document_index,
)
from worldenergydata.bsee.pipeline.source_document_ocr import (
    SourceDocumentOcrError,
    build_source_document_ocr_index,
)
from worldenergydata.bsee.pipeline.spec_lookup import PipelineSpecLookup

__all__ = [
    "CasingString",
    "casing_matrix",
    "DocumentRetrievalError",
    "FieldContext",
    "FieldInfrastructureBundle",
    "FieldInfrastructureError",
    "FIELD_PACKAGE_CONTRACT_VERSION",
    "FieldPackageError",
    "FieldPipelineCostIntegrator",
    "FieldQueryError",
    "FieldReport",
    "build_field_infrastructure_bundle",
    "build_field_package",
    "build_source_document_index",
    "build_source_document_ocr_index",
    "default_bsee_bin_root",
    "download_document_queue",
    "import_reviewer_ready_inputs",
    "load_well_casing",
    "PipelineRunner",
    "PipelineSpecLookup",
    "render_casing_svg",
    "render_field_package_html",
    "render_html",
    "resolve_field",
    "ReviewerInputImportError",
    "save_report",
    "SourceDocumentIndexError",
    "SourceDocumentOcrError",
    "write_field_infrastructure_bundle",
]
