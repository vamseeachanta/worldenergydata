# ABOUTME: India upstream data from DGH (bid rounds, awarded blocks, basins) and PPAC
# ABOUTME: (historical crude by company, condensate totals and monthly gas by location).

"""India upstream module for worldenergydata.

Three normalized tables ship with the package, each derived from a public
government file whose URL and SHA-256 are recorded in ``data/source_manifest.json``:

* ``load_awarded_blocks()`` - OALP I-IX and Special CBM 2022 blocks awarded by the Directorate
  General of Hydrocarbons (DGH);
* ``load_production()`` - annual crude oil by company (FY1998-99 to FY2021-22),
  annual condensate totals (FY2006-07 to FY2021-22), both also monthly for
  April-May 2022; monthly gas by state and onshore/offshore location for
  FY2012-13 to FY2018-19 and FY2021-22, from the Petroleum Planning & Analysis
  Cell (PPAC). Crude has no onshore/offshore split; condensate has no company split;
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
