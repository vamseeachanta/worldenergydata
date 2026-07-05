"""Job adapter implementations for the data collection scheduler.

The package initializer intentionally avoids importing concrete refresh job
adapters. Importing ``worldenergydata.scheduler.jobs.base`` is used by cheap
scheduler/no-op paths; eager imports here would pull in data-source clients and
heavy dependencies before a job is actually executed.
"""

from importlib import import_module
from typing import Any

from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)

_LAZY_EXPORTS = {
    "BrazilAnpRefreshJob": "worldenergydata.scheduler.jobs.brazil_anp_refresh",
    "BseeRefreshJob": "worldenergydata.scheduler.jobs.bsee_refresh",
    "EiaUsRefreshJob": "worldenergydata.scheduler.jobs.eia_us_refresh",
    "LngTerminalsRefreshJob": "worldenergydata.scheduler.jobs.lng_terminals_refresh",
    "MetoceanRefreshJob": "worldenergydata.scheduler.jobs.metocean_refresh",
    "SodirRefreshJob": "worldenergydata.scheduler.jobs.sodir_refresh",
    "SpainCoresRefreshJob": "worldenergydata.scheduler.jobs.spain_cores_refresh",
    "UkcsRefreshJob": "worldenergydata.scheduler.jobs.ukcs_refresh",
}


def __getattr__(name: str) -> Any:
    """Lazily import concrete job adapters on first attribute access."""
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "AbstractJob",
    "JobResult",
    "write_refresh_metadata",
    "BseeRefreshJob",
    "SodirRefreshJob",
    "EiaUsRefreshJob",
    "BrazilAnpRefreshJob",
    "UkcsRefreshJob",
    "MetoceanRefreshJob",
    "LngTerminalsRefreshJob",
    "SpainCoresRefreshJob",
]
