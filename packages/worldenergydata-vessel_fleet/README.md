# worldenergydata-vessel_fleet

`vessel_fleet` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 4, #529).

Importable transparently as `worldenergydata.vessel_fleet` once the workspace
is installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for
the shared `worldenergydata.common` layer.

See [drilling riser CSV validation](docs/drilling-riser-csv.md) for the input
contract, rejection behavior and a worked example of correcting malformed data.

## Data relocation (option (i) — data travels with the package)

The curated dataset (construction vessels, drilling rigs, riser components;
~0.7 MB) ships INSIDE this member at `worldenergydata/vessel_fleet/_data/` and
is resolved package-relative by the loaders and `FleetRouter`. This makes the
domain self-contained — no repo-root or external data mount is required — and
the data ships in the built wheel.

## Riser classes, bundles and buoyancy OD ratio

The additive riser fields address [the riser catalog issue](https://github.com/vamseeachanta/worldenergydata/issues/1138).
`RiserJointSchema.RISER_CLASS` and `RiserJointEntry.riser_class` accept
`drilling`, `lift` (including mining/hydraulic lift), or `production`. Missing
class values default to `drilling`. Existing CSV rows and component identifiers
are unchanged. `COMPONENT_TYPE=riser_joint` describes the joint independently
of its class; a lift record does not require a BOP or kill/choke lines.

`OD_IN`, `ID_IN` and `WALL_THICKNESS_IN` remain main-tube dimensions.
Optional `AUXILIARY_LINES` is a JSON array in CSV, or a list in the schema,
with one object per strapped line. Each object requires `function`, `od_in`
and `wall_thickness_in`; the latter dimensions are inches, finite and positive.
A hollow circular line requires `2 * wall_thickness_in < od_in`, from
`ID = OD - 2 * wall`. This is a geometric identity, not a code limit.
Empty cells mean no auxiliary lines are recorded, rather than proof that none
are installed. Geometry, functions, operating depth, internal medium and erosion
duty require source records; no mining equipment data is inferred from drilling
equipment. No new qualified lift or production records are supplied here.

`DrillingRiserLoader.get_riser_joint_entries(riser_class=None)` validates and
returns typed joint entries, optionally filtered by class. Existing tabular
methods retain their original columns and behavior. Signed submerged weight
is retained: negative values represent net uplift.

### Worked example: catalog OD ratio

Inputs below come from the packaged `drilling_riser_components.csv`, component
`RJ-21-75-BUOY`: main OD = 21 inches, buoyancy OD = 49 inches, and coverage
= 100 percent. The definition in the linked issue is
`buoyancy_od_ratio = buoyancy_od_in / od_in`; both diameters use the same unit.
Independent hand calculation: `49 / 21 = 7 / 3`. Displayed to one decimal,
the answer is **2.3**. The model retains full calculation precision.

```python
from worldenergydata.vessel_fleet import DrillingRiserLoader

joints = DrillingRiserLoader().get_riser_joint_entries("drilling")
joint = next(row for row in joints if row.component_id == "RJ-21-75-BUOY")
print(f"{joint.buoyancy_od_ratio:.1f}")  # 2.3
```

The loader regression checks every buoyed joint against hand calculations from
the committed rows: `49/21`, `44/18.75 = 176/75`, and `55/24`.
The observed minimum is `55/24` and maximum is `176/75`, across the five buoyed
rows in this revision. That range describes this catalog, not an industry band
or an acceptance limit. Missing, nonfinite or nonpositive diameters/coverage,
and bare joints, return `None` rather than a numerical assessment.

The ratio uses the main-tube OD even for a bundle. It does not establish a bare
bundle envelope, connection envelope, minimum handling clearance, depth rating,
foam qualification, tension capacity or erosion allowance. Those assessments
are **NOT_EVALUATED**; they require layout, equipment geometry, operating loads,
material data and governing criteria supplied by the consumer.

### Grade vocabulary and source limits

`GRADE` preserves source text. The catalog mixes X-80 line-pipe designations
with G105/S135 drill-pipe designations. They are not interchangeable material
specifications. The [API 2025 Publications Catalog](https://www.api.org/-/media/files/publications/2025-catalog/2025_pubs%20catalog.pdf),
Tubular Goods entries, identifies API Spec 5L, *Line Pipe*, 46th edition (2018),
and API Spec 5DP, *Drill Pipe*, 2nd edition (2020). The public catalog supports
the specification distinction; it supplies no material qualification for these
records. No yield strength, allowable stress or grade conversion is assigned.
Consumers require the applicable specification edition and material certificate
before engineering use. The packaged data is the basis of the ratio example,
not independent certification of the original catalog dimensions.
