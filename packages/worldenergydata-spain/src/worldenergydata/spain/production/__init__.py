"""Spain production loaders."""

__all__ = [
    "DEFAULT_WORKBOOKS",
    "STATISTICS_PAGE_URL",
    "CoresFixtureProductionLoader",
    "CoresHttpResponse",
    "CoresLiveProductionLoader",
    "CoresProductionLoader",
    "CoresSourceError",
    "CoresWorkbook",
    "CoresWorkbookSource",
    "FixtureRefreshResult",
    "parse_cores_frame",
    "refresh_ayoluengo_fixture",
]


def __getattr__(name):
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
