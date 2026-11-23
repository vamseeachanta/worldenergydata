"""Spain production loaders."""

from typing import Any

__all__ = [
    "DEFAULT_WORKBOOKS",
    "STATISTICS_PAGE_URL",
    "CoresFixtureProductionLoader",
    "CoresCrudeDensityFactor",
    "CoresDensityCoverageError",
    "CoresHttpResponse",
    "CoresLiveProductionLoader",
    "CoresOilConversionAudit",
    "CoresProductionLoader",
    "CoresSourceError",
    "CoresWorkbook",
    "CoresWorkbookSource",
    "FixtureRefreshResult",
    "bbl_per_tonne_from_api",
    "build_oil_conversion_audit",
    "load_crude_density_factors",
    "parse_cores_frame",
    "refresh_ayoluengo_fixture",
    "validate_crude_density_factor",
]


def __getattr__(name: str) -> Any:
    if name in {
        "CoresCrudeDensityFactor",
        "CoresDensityCoverageError",
        "CoresOilConversionAudit",
        "bbl_per_tonne_from_api",
        "build_oil_conversion_audit",
        "load_crude_density_factors",
        "validate_crude_density_factor",
    }:
        from worldenergydata.spain.production import cores_density

        return getattr(cores_density, name)
    if name in {
        "CoresFixtureProductionLoader",
        "CoresProductionLoader",
        "parse_cores_frame",
    }:
        from worldenergydata.spain.production import cores_loader

        return getattr(cores_loader, name)
    if name in {
        "DEFAULT_WORKBOOKS",
        "STATISTICS_PAGE_URL",
        "CoresHttpResponse",
        "CoresLiveProductionLoader",
        "CoresSourceError",
        "CoresWorkbook",
        "CoresWorkbookSource",
        "FixtureRefreshResult",
        "refresh_ayoluengo_fixture",
    }:
        from worldenergydata.spain.production import cores_live

        return getattr(cores_live, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
