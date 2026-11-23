"""Resolve external contractor spec PDFs independently of repo YAML data."""

import os
from pathlib import Path

SPEC_PDF_ROOT_ENV = "WORLDENERGYDATA_SPEC_PDF_ROOT"
_DEFAULT_SPEC_PDF_ROOT = Path(
    "/mnt/ace/worldenergydata/data/modules/vessel_fleet/raw/spec_pdfs"
)


def resolve_spec_pdf_root() -> Path:
    """Use the environment override, or the shared external source directory.

    The root contains contractor subdirectories. Empty overrides use the default;
    relative paths are relative to the caller's cwd and home markers are expanded.
    This resolver never creates directories or changes the repo YAML data root.
    """
    override = os.environ.get(SPEC_PDF_ROOT_ENV)
    return Path(override).expanduser() if override else _DEFAULT_SPEC_PDF_ROOT
