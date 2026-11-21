# Drilling riser reference data from public sources

Drilling riser facts collected from public reports and open papers: main tube
size, wall thickness, joint length, buoyancy and layout. The tables give a
starting point for a drilling riser model when the rig's own riser data is not
available.

## What is here

| File | What it is |
|---|---|
| `drilling_riser_configurations.csv` | Riser, tensioner and BOP facts for named rigs, as stated in 14 public investigation reports and safety alerts (8 rows). |
| `drilling_riser_joint_data.csv` | Main tube outside diameter, wall thickness, joint length, buoyancy and layout from 8 open papers and theses (8 rows). |
| `sources.csv` | The 22 sources, with DOI where one exists, terms and the date opened. |

## What the joint data shows

- Seven of the eight sources give a wall thickness. Six are for a 21 in main
  tube: 0.625 in, 0.807 in, 0.874 in, 0.875 in (two sources) and 1.0 in. One
  is for a 22 in main tube: 1.0 in.
- Three wall thicknesses are derived from the outside and inside diameters printed in the
  source. The `wall_basis` column marks them.
- Joint length is 75 ft in four sources and 15.24 m (50 ft) in one.
- Three sources give the buoyancy outside diameter: 54 in, 1.22 m and 1.235 m.
- One source gives a layout: 133 joints in 3048 m of water, with 7 slick
  joints at the bottom, then 4 buoyancy joints and 2 slick joints alternately.

These are design studies and analysis examples. They are not records of a
particular rig's riser. A model built on them marks the values as assumed
until the rig's riser data confirms them.

## How the tables are kept

- `*_as_stated` columns hold the value and unit printed in the source.
  `od_in` and `wall_in` are the same values in inches for sorting.
- Values calculated here are marked: the 4.8 million lb tensioner total and the
  three derived wall thicknesses.
- The investigation reports are read for configuration facts only. No cause
  of any event is stated or implied.
- The source files are not in this repository. `sources.csv` cites each one.

## Not opened

- Two riser posters from Offshore magazine (November 2010 and April 2015)
  were opened. Both cover production risers and give no drilling riser joint
  data.
- Twelve more papers and theses were found but their sites refused
  automated download or returned no file. They are not used here.
