# BSEE raw data fact check: new-well permits by rig type and incident investigations

`count_rawdata.py` recounts two sets of facts from the public raw data files of the
BSEE Data Center (US Bureau of Safety and Environmental Enforcement), US federal
government data, listed on the [raw data page](https://www.data.bsee.gov/Main/RawData.aspx)
as updated daily.

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
  incident dates, the count by kind (district or panel) and status, and the incident
  dates of the pending investigations.

With `--out <folder>` it also writes `new-well-permits-by-rig-type.csv` and
`counts.json`.

## Counting rules

- One permit per well (API well number): the lowest `SN_APD` among the well's
  `New Well` permits with `REGION_CODE` `G` (Gulf of Mexico), counted in the year of its
  requested spud date, with the rig type named in that permit. Wells whose first `New Well`
  permit gives no requested spud date are left out; their number is printed as
  `no_spud_date`.
- Rig types are named as in `RIG_TYPE_CODE`: jack-up, drillship, semisubmersible,
  DP (dynamically positioned) semisubmersible, platform rig and submersible. Barge,
  barge rig and well intervention vessel, each under 1 % of the permits counted, are
  grouped as "Other"; the grouped codes are printed in `other_grouped`.
- Investigations are counted by `PANEL_DISTRICT` and `STATUS` as the file gives them.

## Run

Python 3.10 or later, standard library only:

```bash
python examples/bsee/rawdata_fact_check/count_rawdata.py --self-test
python examples/bsee/rawdata_fact_check/count_rawdata.py --data-dir bsee-raw --out out
```

`--first-year` (default 2005) and `--last-year` (default the current year) set the
years counted. The self-test runs a hand-counted synthetic case and needs no files.

## Check values

The files of 2 November 2026 (APDRawData.zip SHA-256 `b4ab6606...99c0`,
IncInvRawData.zip SHA-256 `bb738acc...59b1`) give, for 2005 to 2026:

- 2,895 new-well permits (10 wells left out for no requested spud date): jack-up 1,333; drillship 758; semisubmersible 282;
  DP semisubmersible 260; platform rig 162; submersible 81; other 19;
- 2005: 322 permits, 234 naming a jack-up; 2025: 47 permits, 44 naming a drillship;
- 2,029 investigations of incidents from 4 January 1995 to 24 October 2026: 1,948 by a
  district office and 81 by a panel; 12 listed as pending, 3 of them panel investigations.

Later files can differ, because BSEE updates the files daily.
