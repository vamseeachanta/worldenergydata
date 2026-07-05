# ABOUTME: Canada offshore production sub-package initialization.
# ABOUTME: Exports C-NLOER (Newfoundland & Labrador) production loaders.

"""Canada offshore production data loaders."""

from worldenergydata.canada.production.cnloer_loader import (
    CnloerFixtureLoader,
    CnloerProductionLoader,
    parse_cnloer_production_text,
)

__all__ = [
    "CnloerProductionLoader",
    "CnloerFixtureLoader",
    "parse_cnloer_production_text",
]
