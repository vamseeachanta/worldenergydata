"""Deprecated: import from activity_definitions or activity_registry directly."""
import warnings

warnings.warn(
    "activity_taxonomy is split; import from activity_definitions or activity_registry",
    DeprecationWarning,
    stacklevel=2,
)
from .activity_definitions import Activity, Subactivity  # noqa: F401, E402
from .activity_registry import ActivityTaxonomy  # noqa: F401, E402

__all__ = ["Subactivity", "Activity", "ActivityTaxonomy"]
