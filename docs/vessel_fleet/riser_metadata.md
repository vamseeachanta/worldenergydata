# Riser classes, bundles and buoyancy diameter

Riser joint records can describe drilling, lift/mining and production duties.
The buoyancy OD ratio is a dimensionless observation of a joint's main tube
and buoyancy module. It does not determine the full bundle or connection
envelope and cannot establish handling clearance by itself.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Add optional riser metadata and catalog arithmetic for reuse outside drilling. |

## Record contract

Existing curated CSV records and tabular query results are unchanged.
`DrillingRiserLoader.get_riser_joint_entries(riser_class=None)` validates joint
rows and returns `RiserJointEntry` objects; a class argument selects one duty.
Malformed new metadata raises `ValueError` identifying the component.

| Optional CSV/schema field | Model field | Meaning |
| --- | --- | --- |
| `RISER_CLASS` | `riser_class` | `drilling` (legacy default), `lift` (including mining), or `production` |
| `AUXILIARY_LINES` | `auxiliary_lines` | JSON array of strapped lines; missing/blank means no lines recorded |
| `DESIGN_WATER_DEPTH_M` | `design_water_depth_m` | Caller-supplied positive finite intended water depth in metres; no depth rating |
| `INTERNAL_MEDIUM` | `internal_medium` | Caller-supplied medium description, including solids duty when applicable |

Each auxiliary line requires `function`, `od_in` and `wall_thickness_in`.
The last two are positive finite dimensions in inches. The purely geometric
condition `OD - wall - wall > 0` leaves an open bore. No thickness allowance,
foam grade, strength coefficient or erosion limit is supplied by this schema.
Main-tube dimensions retain their existing meanings. A lift joint uses
`COMPONENT_TYPE=riser_joint`; it requires no BOP or kill/choke designation.

For example, this is a **synthetic representation**, not a sourced equipment
record. Its dimensions are chosen only to show an open bore:

```python
from worldenergydata.vessel_fleet.schemas.drilling_riser import RiserJointSchema

joint = RiserJointSchema(
    COMPONENT_ID="synthetic",
    RISER_CLASS="lift",
    INTERNAL_MEDIUM="solids-laden water",
    AUXILIARY_LINES=[
        {"function": "return", "od_in": 4.0, "wall_thickness_in": 0.5},
    ],
)
# Synthetic line bore: 4.0 - 0.5 - 0.5 = 3.0 inches, by geometry alone.
```

## Ratio definition and worked example

The definition in issue #1138 (2026) is
`buoyancy_od_ratio = buoyancy_od_in / od_in`, where `od_in` is main-tube OD.
The property returns `None` when either diameter or buoyancy coverage is
missing, nonfinite or nonpositive. It uses the same diameter definition for
all classes, retains full floating-point precision and applies no acceptance
criterion. A bare joint has no buoyancy OD ratio.

Input source: the packaged
`vessel_fleet/_data/curated/drilling_riser_components.csv`, observed 2026-10-20.
For `RJ-21-75-BUOY`, main-tube OD is 21.0 inches, buoyancy OD is 49.0 inches
and coverage is 100.0 percent. Divide the buoyancy diameter by the main-tube
diameter: `49/21 = 7/3`. The displayed ratio is **2.3**, rounded to one decimal;
the stored property is unrounded. No conversion factor is needed because both
diameters use inches.

The independent cross-check `RJ-18.75-75-BUOY` has main-tube OD 18.75 inches
and buoyancy OD 44.0 inches: `44/(75/4) = 176/75`, also displayed as 2.3.
The catalog contains a further buoyed size, `RJ-24-75-BUOY`, at `55/24`.
All buoyed drilling joints currently fall between the exact fractions `55/24`
and `176/75`. Tests record these observed extrema without adding a margin.
A departure requests row review; it does not prove an engineering defect.
The issue's four-row illustration is therefore not the whole catalog range.

Run the [worked example](../../examples/vessel_fleet/riser_metadata.py) from the
repository root in an environment containing the package dependencies:

```bash
PYTHONPATH=src:packages/worldenergydata-vessel_fleet/src:packages/worldenergydata-core/src \
  python examples/vessel_fleet/riser_metadata.py
```

```text
bare_od_in: 21.0
buoyancy_od_in: 49.0
buoyancy_od_ratio: 2.3
```

## Grade vocabulary and sources

`GRADE` remains source text. Issue #1138 identifies the catalog's mixture of
line-pipe and drill-pipe designations; no equivalence is inferred between them.
The public [API 2025 Publications Catalog](https://www.api.org/-/media/files/publications/2025-catalog/2025_pubs%20catalog.pdf),
Tubular Goods section, lists API Spec 5L, *Line Pipe*, 46th edition (2018),
separately from API Spec 5DP, *Drill Pipe*, 2nd edition (2020).
This citation establishes the specification distinction only. The specifications
themselves were not used for material values or acceptance criteria.

The packaged CSV is the sole dimensional source for the worked ratio example.
Those existing observations have not been independently certified here.
Submerged weight is signed: the buoyed example's negative weight represents
net uplift and must survive typed loading.

## Assessment limits and later slices

No qualified lift/mining or production equipment record is added. Auxiliary
placement, connection geometry and a complete bundle envelope are unrecorded.
The following remain **NOT_EVALUATED** until source records and governing
criteria are supplied:

- Moonpool, spider and tensioner clearance, including full bundle geometry.
- Depth and foam qualification, including water conditions and pressure basis.
- Strength, top tension and fatigue, including material properties and loads.
- Erosion duty, including solids, flow conditions and wear allowance.

Class and intended depth metadata describe a use case; they provide no rating
or assurance that these checks pass.
