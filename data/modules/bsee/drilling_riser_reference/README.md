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
| `sources.csv` | The 22 sources of the two tables above, with DOI where one exists, terms and the date opened. |
| `vendor_riser_joint_data.csv` | Main tube OD, wall thickness, joint length, coupling rating, line sizes and buoyancy depth rating from 15 public vendor datasheets, product pages and vendor articles (26 rows). Each row carries its own citation and URL. |
| `drilling_riser_incidents.csv` | Drilling riser partings, separations and drops, unplanned LMRP disconnects and riser handling drops, as described in public regulator, safety board and industry alert documents (22 rows). Each row carries its own citation and URL. |
| `drilling_riser_failure_papers.csv` | Conference papers and regulator documents on drilling riser failure, recoil and disconnect (30 rows). |

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

## What the vendor data shows

- One datasheet (NOV) prints wall thickness for eight 21 in joint families:
  5/8 in to 15/16 in, with tension ratings of 1,125,000 lb to 4,000,000 lb.
  7/8 in is an option on four families rated 3,000,000 to 3,500,000 lb.
- One flysheet (Oil States, Merlin) prints 19.25 in ID with 1.0 in and
  1.125 in walls, grade X80. The OD (21.25 in and 21.5 in) is by
  arithmetic.
- No readable vendor document prints joint weight in air or in water,
  buoyancy module OD or uplift per joint. Buoyancy rows give depth ratings
  only.

## What the incident table holds

- 12 riser partings, separations or drops of the riser string, 5 unplanned
  LMRP disconnects or separations, and 5 riser handling drops.
- Each row gives what failed or fell and the riser configuration the
  document states. The table records no cause; the cited document is the
  place to read one.

## How the tables are kept

- `*_as_stated` columns hold the value and unit printed in the source.
  `od_in` and `wall_in` are the same values in inches for sorting.
- Values calculated here are marked: the 4.8 million lb tensioner total and the
  three derived wall thicknesses.
- The investigation reports are read for configuration facts and for what
  failed. No cause of any event is stated or implied.
- Where a report's file name carries a company name, the URL given is the
  BSEE index page that lists the report; the report title and number
  identify it there.
- The source files are not in this repository. `sources.csv` cites each one.

## Not opened

- Two riser posters from Offshore magazine (November 2010 and April 2015)
  were opened. Both cover production risers and give no drilling riser joint
  data.
- Twelve more papers and theses were found but their sites refused
  automated download or returned no file. They are not used here.
