# Equipment failure table and the HSE report appendix

## Summary

The equipment failure table maps public incident records to seven equipment
classes, a failure mode and, only where the source states it, a failure
mechanism. A report generator reads the table for the equipment class of the
report in hand and fills the standard "HSE and safety" appendix: data used,
incident history, counts by failure mode, two or three cited public cases and
the lessons for the design.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| Initial | 2026-11-12 | Table, case register and appendix generator added so each engineering report can carry a cited HSE and safety appendix. |

## Scope and limits

- Inputs are public data only. Operators, contractors and facilities are not
  named; records are identified by date and area block.
- A mechanism is recorded on two bases only: `source_coded` (an agency-coded
  cause field) and `investigation_stated` (the cited investigation report).
  Nothing is inferred from an event type. A riser disconnect is not fatigue and
  a mooring failure in a storm is not overload unless the source says so.
- The BSEE incident-investigation file gives an event type and no cause, so all
  of its rows carry `not_stated`. Its counts are a lower bound for an equipment
  class: an event typed only as a cost or injury category does not name the
  equipment.
- The case register stores links and page-referenced paraphrase. It stores no
  report text, in line with the [HSE source registry](source-registry.md).

## Vocabulary

Defined in `worldenergydata.safety_analysis.equipment.taxonomy`.

| Equipment class | Key |
|---|---|
| Risers (SCR, SLWR, flexible, drilling and production) | `riser` |
| Mooring lines and station keeping | `mooring_line` |
| Pipelines | `pipeline` |
| Jack-ups and liftboats | `jack_up` |
| Lifting and rigging | `lifting_rigging` |
| Wellheads and conductors | `wellhead_conductor` |
| Topsides process (FPSO and other facilities) | `fpso_topsides` |

A riser subclass (`scr`, `slwr`, `flexible`, `drilling_riser`,
`production_riser`, `flowline_jumper`) is set only when the source names the
riser type. Failure modes and mechanisms are listed in the module; the
mechanism list includes fatigue, vortex-induced vibration, corrosion, overload,
installation or fabrication error and incorrect operation (human factors).

## Table columns

`equipment_class`, `equipment_subclass`, `source_id`, `source_record_id`,
`date`, `location`, `event_text`, `failure_modes` (joined with `;`),
`mechanism`, `mechanism_basis`, `mechanism_source_text`, `fatality`, `injury`,
`pollution`, `classification_rule`, `source_url`, `retrieved`.

One row is one incident in one equipment class. An incident that names two
classes gives two rows. `classification_rule` holds the rule that produced the
row, and `source_url` with `retrieved` gives the citation for any count.

## Supported sources

| `source_id` | Source | Gives | Cause |
|---|---|---|---|
| `bsee_incident_investigations` | BSEE Incident Investigations raw data, `mv_acc_investigations.txt` | Class and failure mode from `ACCIDENT_TYPE` | Not stated |
| `phmsa_hazardous_liquid` | PHMSA hazardous liquid accident reports (agency flagged file or the curated export in `data/modules/pipeline_safety/raw/kaggle_usdot_pipeline/`) | Pipeline class; release, fire, explosion | Coded cause category and subcategory |

A new source needs a classifier function in `classify.py`, an entry in
`CLASSIFIERS` and tests.

Input files are delimited text. The delimiter (tab, comma or pipe) is read from
the header line, so the tab-separated agency exports and the comma-separated
curated export both load. A file without the columns its classifier needs is
refused. One file per source is supported; join the files of one source first.

## Build and query

List the inputs in a JSON file; each keeps its URL and retrieval date.

```json
[
  {"source_id": "bsee_incident_investigations",
   "path": "IncInvRawData/mv_acc_investigations.txt",
   "url": "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip",
   "retrieved": "2026-11-12",
   "title": "BSEE Incident Investigations raw data"}
]
```

```sh
python -m worldenergydata.safety_analysis.equipment build \
  --sources sources.json --out-dir out/
```

This writes `equipment-failure-table.csv` and `equipment-failure-summary.json`
(coverage and counts by class). In Python:

```python
from worldenergydata.safety_analysis.equipment import build_table, query, summarise
rows, stats = build_table(sources)
summarise(query(rows, "mooring_line"))
```

## Coverage on 12 November 2026

Built from the BSEE file read on 2026-11-12 (2,032 records, 1995-01-04 to
2026-10-24) and the curated PHMSA export downloaded on 2026-05-05 (2,795
records, 2010-01-01 to 2017-01-09).

| Equipment class | Records | Period | Records with a stated cause |
|---|---|---|---|
| Risers | 13 | 1999-10-22 to 2017-10-16 | 0 |
| Mooring lines and station keeping | 7 | 2004-08-26 to 2025-03-28 | 0 |
| Pipelines | 2,805 | 1997-02-02 to 2022-06-08 | 2,753 |
| Jack-ups and liftboats | 6 | 1998-12-31 to 2013-06-05 | 0 |
| Lifting and rigging | 340 | 1996-07-19 to 2026-09-12 | 0 |
| Wellheads and conductors | 79 | 1996-01-24 to 2024-01-18 | 0 |
| Topsides process | 594 | 1995-01-04 to 2026-10-24 | 0 |

Stated causes exist for pipelines only; 42 pipeline records are coded as unknown
by the agency and are not counted as stated. For the other classes the causes on
record are in investigation reports, of which the case register holds four,
all for mooring.

## The HSE and safety appendix

```sh
python -m worldenergydata.safety_analysis.equipment section \
  --sources sources.json --equipment-class mooring_line \
  --design-links links.json --out mooring-hse-appendix.md
```

The appendix has six fixed subsections: Data used; Incident history; Failure
modes and stated causes; Illustrative public cases; Lessons for this design;
References for this appendix. Every number carries a reference with the
retrieval date. `links.json` maps each lesson (`"<case id>#<n>"`) to the report
section that answers it. The command exits 1 and lists the open items while a
lesson has no design response, the class has no records, or fewer than two
cases are on file; `--allow-open` is for drafts.

Where the table holds no record, or fewer than two cases, for the class, the
appendix is generated with `--allow-open`. It then lists every data set read
with zero records, states "Not established" under the failure modes, the cases
and the lessons, and prints the text given with `--missing-data`, which names
the missing data and the issue raised for it.

## Worked example

[Mooring appendix](examples/mooring-hse-appendix.md), generated from the data
above for a codenamed spread-moored floating production unit.

- Inputs: 2,032 BSEE records read on 2026-11-12; three cases from the register.
- Method: the rules in `classify.py` select 7 records whose event type names
  mooring or station keeping; the generator counts them by decade and failure
  mode and prints the three cases with their page references.
- Result: 7 records, 2004-08-26 to 2025-03-28; 6 loss-of-station events; no
  record states a cause. The three cited investigations state overload of a
  tendon bottom connector, hydrogen embrittlement of a chain link and fatigue
  of a chain link. Two of the three cases are in the data file with an event
  type that does not name mooring, so the count of 7 is a lower bound.

## Adding a case

Add an entry to
`packages/worldenergydata-safety_analysis/src/worldenergydata/safety_analysis/equipment/data/public_cases.yml`.
Each statement is an original paraphrase of at most 60 words with the page that
supports it. A mechanism other than `not_stated` needs a cause statement. Give
`area_block` as the incident data set writes it, so the appendix can check
whether the case is among the counted records. The
loader rejects quoted report text, unknown terms and non-https links.

A factor the report rules out goes under `ruled_out`, never under
`cause_statements`. Where the direct file address of a report carries a company
name, `url` is the regulator's listing page; the title (block and date) and the
`sha256` of the file read identify the report.
