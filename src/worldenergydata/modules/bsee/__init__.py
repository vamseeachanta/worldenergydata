# ABOUTME: BSEE (Bureau of Safety and Environmental Enforcement) module initialization
# ABOUTME: Exports main BSEE data access, analysis, reporting, and verification classes

"""
BSEE Module - Gulf of Mexico Offshore Oil & Gas Data

This module provides comprehensive access to BSEE (Bureau of Safety and
Environmental Enforcement) data for Gulf of Mexico offshore oil and gas
operations.

Features:
    - Well and production data access (API10/API12 formats)
    - Production analysis and forecasting
    - Financial analysis (NPV, cash flow calculations)
    - Well data verification and quality assurance
    - Comprehensive reporting with multi-format export (Excel, JSON, HTML, PDF)
    - Paleontological well analysis

Data Structure:
    data/
        loaders/           Data loading strategies
            api/           API-based data access (by well API number)
            block/         Block-based data access (by OCS block)
            lease/         Lease-based data access (by lease number)
        sources/           Data source handlers
            bin/           Binary file sources (.bin format)
            zip/           ZIP file sources (compressed BSEE downloads)
    analysis/              Analysis tools
        well_api12.py      API12 well analysis
        well_api10.py      API10 well analysis
        financial/         Financial analysis (NPV, cash flow)
        well_data_verification/  Data quality verification
    reports/               Report generation
        comprehensive/     Multi-format comprehensive reports

Example usage:
    # Basic module usage
    from worldenergydata.modules.bsee import bsee, BSEEData, BSEEAnalysis

    # Data access
    from worldenergydata.modules.bsee import WellData, BlockRouter, LeaseRouter

    # Analysis
    from worldenergydata.modules.bsee import WellAPI12, ProductionAPI12Analysis

    # Initialize and run analysis
    cfg = {"data": {"block": "759"}}
    result_cfg = bsee.router(cfg)

CLI usage:
    worldenergydata bsee analyze --block 759
    worldenergydata bsee report --type field --id "Jack" --format excel
    worldenergydata bsee data --api 608114001200
    worldenergydata bsee refresh --type production

See Also:
    - docs/CLI.md: CLI command reference
    - docs/MIGRATION_GUIDE.md: Migration from old import paths
"""

from typing import Any, TYPE_CHECKING

__version__ = "1.0.0"
__all__ = [
    # Core
    "bsee",
    "BSEEData",
    "BSEEAnalysis",
    # Data layer
    "WellData",
    "ProductionRouter",
    "BlockRouter",
    "LeaseRouter",
    "DataRefresh",
    # Analysis - API12/API10
    "WellAPI12",
    "WellAPI10",
    "ProductionAPI12Analysis",
    "ProductionAPI10Analysis",
    # Verification (via submodule)
    "well_data_verification",
    # Financial (via submodule)
    "financial",
    # Reporting (via submodule)
    "comprehensive",
    # Paleowells
    "PaleowellsDataProcessor",
    "PaleowellsVisualizer",
]

# Type checking imports for IDE support
if TYPE_CHECKING:
    from worldenergydata.modules.bsee.bsee import bsee as bsee
    from worldenergydata.modules.bsee.data.bsee_data import BSEEData as BSEEData
    from worldenergydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis as BSEEAnalysis
    from worldenergydata.modules.bsee.data.loaders.api.well import WellData as WellData
    from worldenergydata.modules.bsee.data.production.router import ProductionRouter as ProductionRouter
    from worldenergydata.modules.bsee.data.loaders.block.router import BlockRouter as BlockRouter
    from worldenergydata.modules.bsee.data.loaders.lease.router import LeaseRouter as LeaseRouter
    from worldenergydata.modules.bsee.data.refresh.data_refresh import DataRefresh as DataRefresh
    from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12 as WellAPI12
    from worldenergydata.modules.bsee.analysis.well_api10 import WellAPI10 as WellAPI10
    from worldenergydata.modules.bsee.analysis.production_api12 import ProductionAPI12Analysis as ProductionAPI12Analysis
    from worldenergydata.modules.bsee.analysis.production_api10 import ProductionAPI10Analysis as ProductionAPI10Analysis
    from worldenergydata.modules.bsee.paleowells import PaleowellsDataProcessor as PaleowellsDataProcessor
    from worldenergydata.modules.bsee.paleowells import PaleowellsVisualizer as PaleowellsVisualizer


def __getattr__(name: str) -> Any:
    """Lazy import of module components to avoid circular imports."""

    # Core classes
    if name == "bsee":
        from worldenergydata.modules.bsee.bsee import bsee
        return bsee

    if name == "BSEEData":
        from worldenergydata.modules.bsee.data.bsee_data import BSEEData
        return BSEEData

    if name == "BSEEAnalysis":
        from worldenergydata.modules.bsee.analysis.bsee_analysis import BSEEAnalysis
        return BSEEAnalysis

    # Data layer
    if name == "WellData":
        from worldenergydata.modules.bsee.data.loaders.api.well import WellData
        return WellData

    if name == "ProductionRouter":
        from worldenergydata.modules.bsee.data.production.router import ProductionRouter
        return ProductionRouter

    if name == "BlockRouter":
        from worldenergydata.modules.bsee.data.loaders.block.router import BlockRouter
        return BlockRouter

    if name == "LeaseRouter":
        from worldenergydata.modules.bsee.data.loaders.lease.router import LeaseRouter
        return LeaseRouter

    if name == "DataRefresh":
        from worldenergydata.modules.bsee.data.refresh.data_refresh import DataRefresh
        return DataRefresh

    # Analysis layer
    if name == "WellAPI12":
        from worldenergydata.modules.bsee.analysis.well_api12 import WellAPI12
        return WellAPI12

    if name == "WellAPI10":
        from worldenergydata.modules.bsee.analysis.well_api10 import WellAPI10
        return WellAPI10

    if name == "ProductionAPI12Analysis":
        from worldenergydata.modules.bsee.analysis.production_api12 import ProductionAPI12Analysis
        return ProductionAPI12Analysis

    if name == "ProductionAPI10Analysis":
        from worldenergydata.modules.bsee.analysis.production_api10 import ProductionAPI10Analysis
        return ProductionAPI10Analysis

    # Submodules
    if name == "well_data_verification":
        from worldenergydata.modules.bsee.analysis import well_data_verification
        return well_data_verification

    if name == "financial":
        from worldenergydata.modules.bsee.analysis import financial
        return financial

    if name == "comprehensive":
        from worldenergydata.modules.bsee.reports import comprehensive
        return comprehensive

    # Paleowells
    if name == "PaleowellsDataProcessor":
        from worldenergydata.modules.bsee.paleowells import PaleowellsDataProcessor
        return PaleowellsDataProcessor

    if name == "PaleowellsVisualizer":
        from worldenergydata.modules.bsee.paleowells import PaleowellsVisualizer
        return PaleowellsVisualizer

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
