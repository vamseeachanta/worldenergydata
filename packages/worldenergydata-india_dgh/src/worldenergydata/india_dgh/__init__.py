# ABOUTME: India upstream data from DGH (bid rounds, awarded blocks, basins) and PPAC
# ABOUTME: (monthly crude and gas production by company and onshore/offshore).

"""India upstream module for worldenergydata.

Three normalized tables ship with the package, each derived from a public
government file whose URL and SHA-256 are recorded in ``data/source_manifest.json``:

* ``load_awarded_blocks()`` - OALP and DSF blocks awarded by the Directorate
  General of Hydrocarbons (DGH);
* ``load_production()`` - crude oil and natural gas production by
  company group and onshore/offshore, from the Petroleum Planning & Analysis
  Cell (PPAC);
* ``load_basins()`` - the sedimentary basins of India with DGH category.

Unknown values stay missing (NaN); they are never imputed as zero. The National
Data Repository (ndrdgh.gov.in) requires registration and fees and is not used.
"""

from .basins import load_basins
from .blocks import load_awarded_blocks
from .production import load_production
from .sources import load_source_manifest

__all__ = [
    "load_awarded_blocks",
    "load_basins",
    "load_production",
    "load_source_manifest",
]
