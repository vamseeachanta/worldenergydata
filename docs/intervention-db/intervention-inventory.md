# Intervention inventory and observed supply bounds

The intervention inventory combines the packaged dedicated-intervention seed
and vendor roster into a queryable view of distinct hulls. Each original
observation retains its citation, confidence and YAML locator. Conflicting
capabilities remain unknown in the merged view. Counts describe these inputs;
they do not establish the worldwide population or current availability.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Add typed queries and observed bounds so conflicting source listings remain visible. |

## Taxonomy and fields

Issue #585 defines the supply taxonomy. Existing `fleet_catalog` classes cover
MODU drillships, drilling semis and jack-ups; heavy intervention semis; RLWI
monohulls; MPSV/OSV support; and liftboats. BSEE `RigType` now accepts
`rlwi_monohull` and `heavy_intervention_semi` explicitly. Existing name heuristics
are retained; they are not an authoritative classification of an unknown hull.

`InterventionVesselSchema.INTERVENTION_CLASS` uses the string enum
`InterventionClass.LIGHT` or `InterventionClass.HEAVY`. Strings normalize case
and whitespace and still serialize as `light` or `heavy`. Missing class,
riser/lubricator/IRS capability, coiled-tubing capability, depth or residency
remain unknown. Water depth must be finite and nonnegative by definition;
there is no assumed equipment rating or screening limit.

The inventory treats hull type and intervention scope as separate attributes.
An RLWI label does not prove the absence of every riser capability, and a
support asset's ROV depth does not establish well-control suitability.

## Inputs and method

`load_intervention_inventory()` reads these existing package data files:

- `intervention_vessels_seed.yml`: dedicated assets and per-row source descriptions.
- `intervention_osv_roster.yml`: intervention/support assets and per-row public source URLs.

Supply an iterable of paths to use other rosters with either `name` or
`vessel_name` and the same lowercase capability keys. An empty iterable means
an empty input. Missing files, malformed records and invalid schema values
raise errors. There is no silent fallback to a partial roster.

The existing identity resolver groups listings by IMO, normalized name and
operator compatibility, or declared aliases. It supplies the identity basis;
this view does not introduce another identity heuristic. The merged value for
a capability is the sole distinct known observation, if one exists. Multiple
distinct known values produce `None` and a field in `asset.conflicts`. All
original values remain in `asset.observations`, including the portable
`filename:vessels[index]` locator, source and confidence.

Classification uses explicit source types without named-asset overrides. If
classifications disagree, the merged class is `other` and `ASSET_CLASS` is
listed as a conflict. No maximum, average or preferred-source rating is chosen.
All source depths remain in metres, so no conversion coefficient is needed.

The observed dedicated-resident bounds are independently countable sets:

- Lower: hulls with an agreed dedicated class and residency explicitly true.
- Upper: hulls with any dedicated-class observation and residency not confirmed false.

Dedicated classes here are RLWI monohulls and heavy intervention semis. Unknown
or conflicting residency contributes only to the upper bound. Class conflicts
may also contribute to the upper bound. Support assets and MODUs are counted
by class but excluded from these dedicated bounds. These are bounds within the
observed inputs, not a statistical confidence interval or population forecast.

## Queries

```python
from worldenergydata.vessel_fleet.intervention_inventory import (
    load_intervention_inventory,
    query_intervention_inventory,
    summarize_intervention_inventory,
)

assets = load_intervention_inventory()
resident = query_intervention_inventory(assets, gom_resident=True)
summary = summarize_intervention_inventory(assets)
```

Filters combine with AND. `minimum_depth_m` is supplied by the caller and uses
an inclusive comparison. Specified filters exclude unknown/conflicting values;
`gom_resident=False` selects confirmed non-residents. Omitting a filter includes
unknowns. Residency is a historical source assertion, not evidence of current
commercial availability. Depth matching alone is not serviceability approval;
well-control package, tree interface, pressure and intervention scope require
separate evidence.

## Worked example

The runnable example is `examples/vessel_fleet/intervention_inventory.py`, with
inputs in the adjacent YAML. All values are artificial test inputs, not
published asset specifications or design criteria.

| Synthetic identity | Class | Depth observations (m) | Resident observation |
| --- | --- | --- | --- |
| alpha | RLWI | 100, 200 | true |
| beta | RLWI | 200 | unknown |
| gamma | heavy intervention semi | 300 | false |
| delta | MPSV | 300 | true |

Hand calculation: five listings resolve to four identities. Alpha's two depth
observations conflict, so its merged rating is unknown. Only alpha is a
confirmed dedicated resident. Beta may be resident, giving lower = one and
upper = one + one = two. Gamma is non-resident and delta is support. At an
input screening depth of 200 m, beta satisfies the RLWI depth filter; alpha's
unknown depth cannot satisfy it.

Run with the vessel package and its dependencies installed:

```bash
python examples/vessel_fleet/intervention_inventory.py
```

Expected output, also asserted by the example test:

```text
Distinct assets: 4
Observed dedicated resident bounds: 1 to 2
Conflicted assets: 1
RLWI depth matches: 1
```

## Evidence and limits

The packaged rosters and `intervention_fleet_catalog.yml` are existing research
snapshots. This change neither refreshes their sources nor certifies individual
ratings. Conflicting depth, hull class and residency assertions remain visible
for review rather than being resolved from memory.

`summary['research_estimates']` retains each existing reconciliation figure and
its historical confidence label, with a repository source locator and
`status: NOT_EVALUATED`. Those figures include dedicated GoM supply, worldwide
RLWI supply and pressure-rated rig counts. The committed reconciliation block
has no dated primary-source basis for validating these population assertions;
its historical `on_record` label does not override `NOT_EVALUATED`.

Further work requires dated public evidence to resolve source conflicts,
distinguish nameplate and deployed intervention-system ratings, validate
population estimates and establish current availability. The inventory
preserves unknown riser/lubricator/IRS values rather than inferring them from
a coarse asset class. No pressure-capability screening is implemented.
