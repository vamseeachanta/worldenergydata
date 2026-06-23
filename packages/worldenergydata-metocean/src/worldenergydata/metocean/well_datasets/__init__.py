# ABOUTME: well_datasets sub-package — optional The Well (Polymathic AI) dataset integrations.
# ABOUTME: All imports are guarded; this sub-package does not break if the_well is absent.

"""
well_datasets: Optional integrations with The Well physics simulation datasets.

The Well dataset — CC BY 4.0, Polymathic AI
https://github.com/PolymathicAI/the_well

Available loaders
-----------------
PlanetsweLoader
    Streams the ``planetswe`` (Shallow Water Equations on rotating sphere) dataset.
    Requires: ``pip install the_well>=1.2.0``
"""

from worldenergydata.metocean.well_datasets.planetswe_loader import (
    THE_WELL_ATTRIBUTION,
    WELL_AVAILABLE,
    PlanetsweLoader,
)

__all__ = [
    "PlanetsweLoader",
    "THE_WELL_ATTRIBUTION",
    "WELL_AVAILABLE",
]
