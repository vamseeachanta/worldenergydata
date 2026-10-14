# Sourced construction-vessel evidence

`_data/curated/construction_evidence.json` is a linked evidence table keyed by
the exact `VESSEL_NAME` in `construction_vessels.csv`. Every roster row has a
disposition. It does not replace the historical CSV or its paired Parquet file.
Those legacy engineering values are not used by the evidence lookup.

Identity fields (`imo`, `current_name`, `owner`, `operator`, `status`) contain
either `null` or a fact with a source ID, locator and quotation key. `aka` records
only documented former names; it is not a complete rename history. A source
records its URL, publisher, retrieval and re-fetch timestamps, byte digests and
short verbatim identity quotations. Fleet associations are qualified separately
from verified legal operating entities. A fleet listing does not imply active
status. `partial` means some identity fields are supported; `unresolved` means
none is accepted. Candidate names never become accepted identities by proximity
or spelling alone. Records with no matching named hull model use `hull_model:
"none"`; the inventory review is recorded in the bundle. Generic meshes are not
assigned to named vessels.

The third identity field, `owner`, means the registered title holder from a
vessel register; a designer's ownership label does not establish that fact.

Coverage at 2026-10-14: 161 roster rows, 0 resolved, 30 partial and 131 unresolved.
The unresolved rows comprise 28 researched-unresolved and 103 not researched.
Four rows have sourced IMO numbers, two vessels have sourced lay tension, and
five vessels have crane ratings (20 ratings). Six previously unresolved rows
now have exact published fleet names. This is partial coverage of the roster.

Every unresolved row has `searched` and `candidates` lists. Each search attempt
records its URL, date, locator and outcome. An empty search list means
`limitation: "not researched"`; a nonempty list means
`limitation: "researched, unresolved"`. Where no candidate is supported,
`candidate_summary` states `no candidate found in` followed by the attempted
sources, or `sources: none (not researched)`. Failed retrievals do not establish
that a vessel is absent from a fleet. Historical names and similar spellings
remain candidates unless the identity bridge is established.

`construction_crane_ratings.csv` exports printed capacity/radius points and
intervals, with metric-tonne and metre units in the headers. Each row retains
the vessel, hoist, configuration, source URL, retrieval timestamp and locator.
`value_quote` preserves the printed value string. The vessel's `crane_evidence`
names omitted hoists or modes where the export is only part of a printed table.
`point` has equal minimum/maximum radii; `interval` retains both printed bounds;
`up_to` has an unknown lower bound, not zero. Ratings are per identified crane,
not automatically tandem capacities. No plot is digitised or interpolated.
The table is not a complete operational load chart: source age, current crane
configuration, stability and operating limits require confirmation before use.
Missing ratings and identities remain explicit data gaps.

The companion `construction_evidence_manifest.json` carries record counts,
units and SHA-256 digests. `load_evidence()` validates the bundle, reads both
outputs back and verifies their agreement. Raw publisher files are not
redistributed because redistribution permission was not established; source
sizes and original/re-fetch digests remain in the evidence bundle. Public
availability alone is not permission to republish a brochure.

```python
from worldenergydata.vessel_fleet.construction_evidence import (
    find_pipelay, load_evidence,
)

evidence = load_evidence()
shortlist = find_pipelay("s-lay", 1050, bundle=evidence)
names = [row["vessel_name"] for row in shortlist]
# PIONEERING SPIRIT and SOLITAIRE, using only sourced method/tension pairs.
```

The query returns screening candidates, including their identity limitations
and matched-capability provenance. It does not establish present availability
or engineering suitability. Distinct methods retain distinct tension ratings.
Missing capacities never qualify and nonfinite/negative thresholds are rejected.
Each lay rating retains `value_quote` and `rating_basis`. Holding capacity,
S-lay tension capacity and dynamic maximum tension are distinct publisher bases;
the numeric screening threshold does not make them interchangeable. The current
bundle has no reverified dynamic maximum tension values: inaccessible evidence
was removed rather than retained as a current sourced result.

The hull inventory reference resolves within the `worldenergydata` repository at
`data/modules/vessel_hull_models/INVENTORY.md`; its LF-normalized digest is
recorded and tested. The inventory is not included in the installable package.

Reviewed evidence can be ingested offline with
`python -m worldenergydata.vessel_fleet.construction_evidence <bundle.json> <output-directory>`.
Ingest validates roster coverage and provenance before writing the JSON, crane
CSV and manifest, then reads the outputs back. It makes no network or solver call.
Tests are in `tests/unit/vessel_fleet/test_construction_evidence.py`.
