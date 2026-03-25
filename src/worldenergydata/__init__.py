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

# Activate backward-compatibility redirect for worldenergydata.X imports
from worldenergydata._compat import install_redirect as _install_redirect

_install_redirect()
del _install_redirect
