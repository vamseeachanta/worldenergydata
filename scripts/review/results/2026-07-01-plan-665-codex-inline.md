# Codex inline adversarial plan review - Issue #665

**Plan:** `docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md`
**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/665
**Reviewer:** Codex inline
**Date:** 2026-07-01
**Default stance:** non-approve unless defects are explicitly resolved

## Verdict

APPROVE FOR USER APPROVAL REQUEST after the mitigations embedded in this plan.

## Findings

### Finding 1 - MAJOR - Pipeline proximity can become computationally explosive

The naive approach would compare every field/well point to every pipeline
polyline. Statewide county GIS fanout can make that too slow for local
repeatable builds.

Resolution in plan: Task 3 requires county and grid/bounding-box prefilters
before exact point-to-segment checks. Task 4 requires repeatable sorting and
small fixture coverage. Implementation should add a modest performance fixture
before full `/mnt/ace` execution if real fanout proves large.

### Finding 2 - MAJOR - Field geometry cannot be derived from production alone

The #664 production/lifecycle output is field-keyed but does not carry a true
field polygon or surface extent. Computing nearest pipeline distance from only a
field name or production row would produce false precision.

Resolution in plan: Task 4 derives field geometries from official RRC well GIS
points joined back through lifecycle API keys and field keys. Missing GIS joins
produce source caveats instead of fabricated geometry.

### Finding 3 - MAJOR - RRC GIS data is not legal or survey-grade

The official RRC pages warn that the GIS data is informational and suitability
must be assessed by the user. A field-development architecture workflow could
overstate these metrics as engineered tie-in feasibility.

Resolution in plan: Deliverable and quality report scope the output as
planning-screening metrics only. Out-of-scope explicitly excludes engineered
routing, capacity, tariffs, and right-of-way feasibility.

### Finding 4 - MODERATE - Heavy GIS dependencies would expand the Texas RRC package surface

Adding GeoPandas/Fiona/Shapely would materially enlarge the leaf package and
could destabilize CI packaging. The repo currently has no geospatial runtime in
the Texas RRC package.

Resolution in plan: Dependency policy limits the implementation to a small
pure-Python shapefile reader unless discovery finds an approved local reader.
Spatial math remains deterministic local code with tests.

### Finding 5 - MODERATE - PatchOps validation could accidentally become a source dependency

The issue mentions PatchOps, but the user also directed direct-source data for
reliability. If PatchOps becomes required, builds will depend on a third-party
service and violate the direct-source contract.

Resolution in plan: PatchOps is validation-only. The output manifest and docs
will cite official RRC source manifests as durable inputs, not PatchOps.

### Finding 6 - MODERATE - Pipeline status/product may be unavailable or inconsistent

RRC pipeline shapefiles may contain active, inactive, abandoned, and
product-specific lines. A nearest mapped line is not necessarily a viable
connection.

Resolution in plan: Output caveats and out-of-scope language prevent the metric
from claiming capacity, product compatibility, or tie-in feasibility.

## Required implementation watchpoints

- Fail closed when `/mnt/ace` lacks GIS raw source manifests and
  `--refresh-gis` is not passed.
- Keep all output under `/mnt/ace/worldenergydata/data/modules/texas_rrc`.
- Preserve source filenames and checksums in manifests so field metrics can be
  traced to official county shapefile ZIPs.
- Add a code review checkpoint before merging because this implementation will
  introduce new spatial math.
