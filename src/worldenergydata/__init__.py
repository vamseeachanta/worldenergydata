# ABOUTME: Root package for worldenergydata - energy market data platform.
# ABOUTME: Registers backward-compatibility redirect for old modules.X imports.

"""World Energy Data - Global energy market data aggregation and analysis.

See https://github.com/vamseeachanta/worldenergydata/ for more information.

Module catalog (flat namespace, WRK-096):

  Regulatory & Safety:
    worldenergydata.bsee           - Bureau of Safety and Environmental Enforcement
    worldenergydata.hse            - Health, Safety & Environment data
    worldenergydata.marine_safety  - Marine safety incident analysis
    worldenergydata.pipeline_safety - Pipeline safety data and analysis
    worldenergydata.safety_analysis - Safety analysis utilities
    worldenergydata.fdas           - Facility data analysis

  Production & Markets:
    worldenergydata.sodir          - Norwegian Shelf Directorate data
    worldenergydata.texas_rrc      - Texas Railroad Commission data
    worldenergydata.mexico_cnh     - Mexico CNH hydrocarbon data
    worldenergydata.canada         - Canadian energy data
    worldenergydata.well_production_dashboard - Well production dashboards

  Infrastructure:
    worldenergydata.lng_terminals  - LNG terminal data
    worldenergydata.landman        - Land management data
    worldenergydata.vessel_hull_models - Vessel hull model data

  Metocean & Environment:
    worldenergydata.metocean       - Meteorological and oceanographic data

  Reporting:
    worldenergydata.reporting      - Report generation

  Analysis:
    worldenergydata.lower_tertiary - Lower tertiary geological analysis

Backward compatibility:
    Old imports (worldenergydata.X) still work but emit
    DeprecationWarning. Migrate to worldenergydata.X.
"""

# Version of package
__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Namespace extensibility (ADR 0001 — domain-package split, Phase 1)
# ---------------------------------------------------------------------------
# Extend this package's ``__path__`` so the ``worldenergydata`` namespace can
# later be contributed to by multiple independently-built/-versioned
# distributions (uv workspace members) that each ship ``worldenergydata/<domain>/``.
# A plain regular-package ``__init__.py`` pins ``__path__`` to a single
# location and blocks distributed extension (ADR POC 3 Case B); adopting
# ``pkgutil.extend_path`` lets the namespace span every install location while
# preserving this module's ``__version__``, the ``_compat`` legacy redirect,
# and the lazy ``__getattr__`` below (ADR POC 3 Case C / POC 4).
# This is a no-op today (single distribution) and introduces no behavior change.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Activate backward-compatibility redirect for worldenergydata.X imports
from worldenergydata._compat import install_redirect as _install_redirect

_install_redirect()
del _install_redirect


# ---------------------------------------------------------------------------
# Lazy attribute access for query API modules
# ---------------------------------------------------------------------------
# Keeps ``import worldenergydata`` fast by deferring heavy sub-module
# imports until first attribute access.


def __getattr__(name: str):
    """Lazy import of top-level query API namespaces.

    Supported attributes:

    * ``marine_safety_api`` — :mod:`worldenergydata.marine_safety.api` (incidents)

    Note: ``bsee`` and ``fdas`` are real subpackages whose ``__init__.py``
    files expose query API singletons (``production``, ``wells``,
    ``companies``, ``economics``) via their own ``__getattr__``.

    Examples
    --------
    >>> import worldenergydata as wed
    >>> df = wed.bsee.production.query(year=2022)
    >>> npv = wed.fdas.economics.npv([-1000, 100, 200], 0.10)
    >>> df = wed.marine_safety_api.incidents.query(source="maib")
    """
    if name == "marine_safety_api":
        from worldenergydata.marine_safety import api as _ms_api

        return _ms_api
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
