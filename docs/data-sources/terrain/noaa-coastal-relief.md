# NOAA Coastal Relief Model subset planning

The existing terrain catalog records NOAA NCEI Coastal Relief Model access
endpoints. `worldenergydata.field_development.coastal_relief` discovers the
numbered volumes from saved THREDDS catalog XML and plans small OPeNDAP ASCII
requests. It performs no network access and writes no raster data.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Document discovery and bounded index planning for coastal data access. |

## Discovery

Obtain the public [NOAA catalog XML][catalog] using an HTTPS client and save it
outside the repository. Retain the source URL, retrieval time and HTTP status
with the response. Pass the saved XML to `discover_crm_volumes`:

```python
from pathlib import Path

from worldenergydata.field_development.coastal_relief import discover_crm_volumes

volumes = discover_crm_volumes(Path("crm-catalog.xml").read_bytes())
volume = next(item for item in volumes if item.name == "crm_vol3")
```

Only numbered `crm_vol*.nc` products are returned. Other CRM products and nested
catalog references are excluded. Returned HTTP and OPeNDAP URLs use the endpoint
templates in `terrain_sources.yml`; XML cannot redirect a volume to another
host. Discovery rejects malformed catalog XML, unexpected volume paths,
duplicates and empty inventories. Catalog presence establishes availability in
that saved inventory, not current endpoint health or engineering suitability.

## Index subset requests

Inspect each selected volume's `.dds` for its variable names, dimension order and
lengths, and its `.das` for coordinate units, missing values and vertical datum.
The [volume 3 DDS][dds], accessed 2026-10-19, declares a grid `z[y][x]`.
The following example plans an ASCII request; the caller decides whether and how
to execute it:

```python
from worldenergydata.field_development.coastal_relief import (
    IndexRange,
    plan_crm_subset,
)

# Axis lengths: NOAA volume 3 DDS, accessed 2026-10-19 (linked below).
# First two indices per axis are an arbitrary small example, not a location.
rows = IndexRange(start=0, stop=1, stride=1, length=13201)
columns = IndexRange(start=0, stop=1, stride=1, length=10801)
# Four cells = two rows times two columns; caller-selected request budget.
url = plan_crm_subset(volume, rows, columns, grid_name="z", max_cells=4)
```

The [OPeNDAP User Guide, section 4.4.2][guide] defines zero-based hyperslabs as
`[start:stride:stop]` with an inclusive stop. The selected count is
`floor((stop - start) / stride) + 1`. The guide's published `[0:5:19]` example
selects indices `0, 5, 10, 15`. The planner multiplies the two axis counts and
refuses a request above the required caller-supplied `max_cells` budget. The
returned URL percent-encodes brackets for transport. An ASCII grid response
includes coordinate maps; it is not a netCDF file.

## Limits and later work

- Dimension lengths and grid order are required inputs from inspected metadata;
  the planner cannot authenticate those inputs or detect subsequent source changes.
- Cell budgets bound selected grid values, not response bytes or server resources.
- No geographic bounding-box conversion, remote fetch, retry or resumable cache
  is included. Source resolution is not treated as a navigation or design tolerance.
- Vertical datum, elevation sign, missing values and suitability remain
  `NOT_EVALUATED`. The planner does not convert elevations to positive depths.
- A later reader must qualify these conventions before integrating CRM with
  `bathymetry_grid.py`, whose current netCDF reader expects different variables.

[catalog]: https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.xml
[dds]: https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_vol3.nc.dds
[guide]: https://opendap.github.io/documentation/UserGuideComprehensive.html
