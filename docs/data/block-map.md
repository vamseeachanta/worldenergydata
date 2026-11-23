# Local lease block polygon maps

The block map primitive selects an exact, complete set of local GeoJSON block
polygons and renders one standalone SVG. The tests use synthetic geometry;
no real lease boundary image is supplied. #37 remains open until the real
source-qualified boundary image has been reviewed.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-16 | Define normalized input and offline rendering to test polygon coverage. |
| 2 | 2026-11-17 | Reject nested legacy CRS members so selected geometry cannot override the normalized source contract. |

## Input contract

`worldenergydata.bsee.visualization.block_map` exposes `select_blocks(document,
requested)` and `render_svg(document, requested, title="Lease blocks")`.
Both functions accept a parsed GeoJSON `FeatureCollection` dictionary. Neither
performs retrieval, writes a cache, repairs geometry or substitutes centroids.
The caller reads local JSON and writes the returned SVG string to its destination.

Each feature has `type: "Feature"`, string properties `area` and `block`, and a
`Polygon` or `MultiPolygon` geometry. Coordinates are two-dimensional numeric
`[longitude, latitude]` positions in degrees, EPSG:4326, with longitude in
[-180, 180] and latitude in [-90, 90]. Booleans, numeric strings, nonfinite
values, unclosed rings, rings with fewer than four positions and zero signed
area are rejected. The first ring is the exterior; subsequent rings are holes.
All components and rings are retained with SVG's even-odd fill rule. Legacy
GeoJSON `crs` members on the collection, selected features and their geometries
are rejected, including redundant declarations: the source adapter must explicitly
normalize coordinates first.

The collection must carry a `source` object with nonempty string fields:

| Field | Required evidence |
| --- | --- |
| `source_id` | Public source URL or persistent identifier for the exact extract. |
| `release` | Source release/version and observation date. |
| `sha256` | Lowercase 64-character SHA-256 digest of the original source bytes. |
| `terms` | Source terms reference and evidence permitting the intended use. |
| `crs` | Exactly `EPSG:4326`, after any documented reprojection. |
| `units` | Exactly `degrees`, with longitude first. |

These fields are structurally checked and preserved in SVG metadata. Their
truth, licence eligibility, date and digest correspondence are the caller's
responsibility. Hash the original bytes before parsing; do not hash a rewritten
dictionary and present it as the original. Duplicate JSON object keys must be
rejected by the caller's loader before passing a dictionary. Synthetic fixtures
use explicit synthetic source labels and a placeholder digest, without claiming
source qualification.

`requested` maps exact `(area, block)` string tuples to nonempty display group
strings. There is no trimming, case folding, numeric conversion or default key
set. All feature identities are validated, including unrelated features;
duplicate identities anywhere and missing requested keys fail explicitly.
Only selected geometries are validated. Selection returns an independent copy
in request order with the requested `group` property assigned. Rendering always
rechecks completeness. Labels are XML escaped.

## Synthetic usage

This example selects a local normalized input; its label describes no real site:

```python
import json
from pathlib import Path

from worldenergydata.bsee.visualization.block_map import render_svg


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


document = json.loads(
    Path("qualified-blocks.geojson").read_text(encoding="utf-8"),
    object_pairs_hook=unique_keys,
)
requested = {("AA", "001"): "Group A"}
svg = render_svg(document, requested, title="Synthetic block display")
Path("blocks.svg").write_text(svg, encoding="utf-8")
```

The eight block identifiers required by #37 are tested together: WR 758, 759,
678, 540, 583, 584, 627 and 628. Their test coordinates and group labels are
synthetic, unrelated to actual boundaries, facilities or tiebacks.

## Display and source limits

The display uses a local equirectangular projection centered on the combined
extent, with longitude scaled by the cosine of the midpoint latitude. One
uniform scale fits a 640 by 400 pixel plotting region. Longitude and latitude
axes remain in degrees. Extents wider or taller than ten degrees, dateline
crossings and absolute latitudes of 85 degrees or more are rejected. At most
six display groups receive distinct colors and legend entries.

No distance or area is to be read from this display. There is no engineering
scale bar, basemap, reserve layer, platform position or tieback route. Labels
use bounding-box centers, which may lie outside concave polygons or in holes;
they may overlap. Ring closure, numeric validity and signed area checks do not
establish polygon topology: self-intersections, intersecting components and
hole containment require upstream qualification. Antimeridian wrapping is not
supported. Existing point-map hover and HTML exports remain separate.
Projected rings are serialized to nine decimal places in pixels. A ring that
collapses to zero signed area, or a polygon whose holes consume its exterior
area at that precision, raises an explicit error.

For source discovery, the repository references the public
[BOEM mapping catalog](https://www.boem.gov/oil-gas-energy/mapping-and-data)
and the BOEM GIS service context in
`tests/unit/data_procurement/api-sources.yml`. The catalog responded successfully
on 2026-11-16; this confirms reachability only. No particular current layer,
CRS or redistribution terms have been qualified. A future real-map delivery
must record the exact layer and query, retrieval time, source release/date,
original-byte digest, native CRS and units, reprojection details, and terms
permitting redistribution. Unknown CRS or rights blocks real-data ingestion.
Actual boundary acquisition, source adapters, actual platform position,
tieback geometry and reserve estimation remain subsequent work.
