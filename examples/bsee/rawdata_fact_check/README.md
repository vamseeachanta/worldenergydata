# BSEE raw data fact check: new-well permits by rig type and incident investigations

`count_rawdata.py` recounts two sets of facts from the public raw data files of the
BSEE Data Center (US Bureau of Safety and Environmental Enforcement), US federal
government data, listed on the [raw data page](https://www.data.bsee.gov/Main/RawData.aspx)
as updated daily. No account, key or local file is needed: the script downloads both
files itself.

## Run it

From the root of a clone of this repository, with Python 3.10 or later (standard
library only):

```bash
python examples/bsee/rawdata_fact_check/count_rawdata.py --out bsee-out
```

This downloads the two files into `bsee-raw/` (a folder in the current directory), prints
the counts as JSON and writes them to `bsee-out/`. A run takes a few seconds once the
files are downloaded (about 4 MB in all).

## What it downloads

| File | Source | Member read |
|---|---|---|
| Application for Permit to Drill | <https://www.data.bsee.gov/Well/Files/APDRawData.zip> | `mv_apd_main_all.txt` |
| Incident Investigations | <https://www.data.bsee.gov/Other/Files/IncInvRawData.zip> | `mv_acc_investigations.txt` |

A file already in `--data-dir` is used as it is, and not downloaded again. The SHA-256
of each file is printed, so two runs can be compared.

## What it prints

A JSON document with:

- `files`: the path, SHA-256 and retrieval time of each zip file;
- `permits`: new-well permits in the Gulf of Mexico region by year of requested spud
  date and rig type, the totals by rig type, and the water depth (ft) of the permits of
  each rig type (count, median, minimum, maximum);
- `investigations`: the number of records, the fields of the file, the first and last
  incident dates, the count by kind (district or panel) and status, the incident date
  of each pending panel investigation (`pending_panel_incidents`), and the number of
  pending district investigations by incident year (`pending_district_by_year`).

With `--out <folder>` it also writes `new-well-permits-by-rig-type.csv` and
`counts.json`.

## Counting rules

- One permit per well (API well number): the lowest `SN_APD` among the well's
  `New Well` permits with `REGION_CODE` `G` (Gulf of Mexico), counted in the year of its
  requested spud date, with the rig type named in that permit. Wells whose first `New Well`
  permit gives no requested spud date are left out; their number is printed as
  `no_spud_date`.
- Rig types: a fixed list of six `RIG_TYPE_CODE` values is named: jack-up, drillship,
  semisubmersible, DP (dynamically positioned) semisubmersible, platform rig and
  submersible. Every other code, including a blank or unknown one, is grouped as
  "Other", and the grouped codes are printed in `other_grouped`. No share threshold is
  computed. In the files of 3 November 2026, for 2005 to 2026, "Other" held
  barge (16), barge rig (1) and well intervention vessel (2): 19 of 2,895 permits.
- Investigations are counted by `PANEL_DISTRICT` and `STATUS` as the file gives them.

## Options

```bash
python examples/bsee/rawdata_fact_check/count_rawdata.py --self-test
python examples/bsee/rawdata_fact_check/count_rawdata.py --data-dir bsee-raw --out bsee-out
```

- `--data-dir` (default `bsee-raw`): the folder for the two zip files. A file already
  there is used as it is; delete it to download a newer copy.
- `--out`: the folder for `new-well-permits-by-rig-type.csv` and `counts.json`.
- `--first-year` (default 2005) and `--last-year` (default the current year): the years
  counted.
- `--self-test`: runs a hand-counted synthetic case; needs no files or network.

## Check values

The files of 2 November 2026 (APDRawData.zip SHA-256 `b4ab6606...99c0`,
IncInvRawData.zip SHA-256 `bb738acc...59b1`) give, for 2005 to 2026:

- 2,895 new-well permits (10 wells left out for no requested spud date): jack-up 1,333; drillship 758; semisubmersible 282;
  DP semisubmersible 260; platform rig 162; submersible 81; other 19;
- 2005: 322 permits, 234 naming a jack-up; 2025: 47 permits, 44 naming a drillship;
- 2,029 investigations of incidents from 4 January 1995 to 24 October 2026: 1,948 by a
  district office and 81 by a panel; 12 listed as pending, 3 of them panel investigations.

The files of 3 November 2026 (APDRawData.zip SHA-256 `12d7e9d9...c272`,
IncInvRawData.zip SHA-256 `129573be...9891`) give:

- the same permit totals as above, with 10 wells left out for no requested spud date;
- 2005 by rig type: jack-up 234, semisubmersible 29, submersible 22, drillship 15,
  platform rig 10, DP semisubmersible 9, other 3 (322 in all);
- 2025 by rig type: drillship 44, jack-up 1, DP semisubmersible 1, platform rig 1
  (47 in all);
- 2,031 investigations: 1,950 by a district office and 81 by a panel; 13 listed as
  pending, 3 of them panel investigations.

Later files can differ, because BSEE updates the files daily.
