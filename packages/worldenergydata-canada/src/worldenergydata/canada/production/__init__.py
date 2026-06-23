# ABOUTME: Canada offshore production sub-package initialization.
# ABOUTME: Exports C-NLOER (Newfoundland & Labrador) production loader.

"""Canada offshore production data loaders."""

from worldenergydata.canada.production.cnloer_loader import (
    CnloerLoader,
    CnloerProductionRecord,
)

__all__ = [
    "CnloerLoader",
    "CnloerProductionRecord",
]
