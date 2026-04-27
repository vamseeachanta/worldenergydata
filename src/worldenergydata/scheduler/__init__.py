"""Worldenergydata data collection scheduler package.

Package-level exports are lazy so importing submodules such as
``worldenergydata.scheduler.cli`` does not pull in scheduler runtime,
monitoring, HTTP clients, or concrete refresh job adapters for no-op/help
paths.
"""

from importlib import import_module
from typing import Any

_LAZY_EXPORTS = {
    "SchedulerConfig": "worldenergydata.scheduler.config",
    "load_config": "worldenergydata.scheduler.config",
    "validate_config": "worldenergydata.scheduler.config",
    "DataScheduler": "worldenergydata.scheduler.scheduler",
}


def __getattr__(name: str) -> Any:
    """Lazily resolve package-level scheduler exports."""
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = ["DataScheduler", "SchedulerConfig", "load_config", "validate_config"]
