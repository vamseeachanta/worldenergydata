# Area and operator-class activity characterisation

The analysis now partitions completion, EOR and WAR records by year, bottom
area code, supplied operator class and raw activity or status code. The
[charted example](area_operator_example.html#activity-strata) uses only the
existing public-source fixture projections. It demonstrates counting and
coverage reporting; it does not describe the complete offshore population.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-19 | Added area distributions and explicit operator-class coverage to expose missing classifications. |
| 2 | 2026-10-21 | Corrected classification requirements and digest labels, added reproducible fixture generation and independent CSV counts, and omitted unevaluated operator charts. |

## Method and sources

For a cell defined by year, area, class and code, its record count is
`N(cell) = sum over source rows of indicator(row belongs to cell)`.
Every row belongs to exactly one cell, including rows with unknown values.
This follows the frequency-count definition in the
[NIST/SEMATECH e-Handbook of Statistical Methods, section 1.3.3.14, Histogram](https://www.itl.nist.gov/div898/handbook/eda/section3/histogra.htm)
(online edition accessed 2026-10-19; the page does not specify an edition year).
Distinct wells are the set of valid API12 identifiers in each cell. Their
counts are not additive across cells because a well can appear in several
years or activities. No coefficient, engineering acceptance limit, duration
or exposure denominator is introduced.

The source field names and row counts are documented by the repository's
[fixture manifest](../../../../../tests/fixtures/bsee/completion_intervention/manifest.json)
and its CSV projections, from the pinned public BSEE archives:

- [WAR](https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip):
  `WAR_START_DT`, `BOTM_AREA_CODE`, `WELL_ACTIVITY_CD`; properties join by
  `SN_WAR`, with a unique report key.
- [EOR](https://www.data.bsee.gov/Well/Files/eWellEORRawData.zip):
  `BOREHOLE_STAT_DT`, `BOTM_AREA_CODE`, `EOR_OPERATION_CD`.
- [API Lookup](https://www.data.bsee.gov/Well/Files/APIRawData.zip):
  `COMPLETION_DATE`, `COMP_STATUS_CD`; area is the unique nonblank
  `BOTM_AREA_CODE` per API12 from the
  [borehole snapshot](https://www.data.bsee.gov/Well/Files/BoreholeRawData.zip).
  Conflicting areas are unknown. Repeated metadata cannot multiply counts.

| Source projection | Records | Unknown area | Unknown operator class |
| --- | ---: | ---: | ---: |
| WAR | 26 | 0 | 26 |
| EOR | 25 | 0 | 25 |
| Completion | 91 | 0 | 91 |

These totals enumerate the rows of the manifest-pinned fixture projections.
They are example data counts, not acceptance thresholds. All area fields
are populated in this subset; that observation establishes no completeness
claim for the full archives.

The fixture example is reproduced from the repository root with:

```bash
uv run python scripts/reporting/build_completion_activity_example.py
```

The command checks each CSV projection against its manifest digest and row
count before writing the example. Catalogue rows are derived from that
manifest: File SHA-256 identifies the CSV projection and Archive SHA-256
identifies the source ZIP. Raw member digests and projection retrieval dates
are not established. No archive is downloaded or changed by this command.

## Operator classes and use

Call `analyse(tables, operator_classes=classes)` with a DataFrame containing
`API_WELL_NUMBER`, `OPERATOR_CLASS` and `SOURCE`. Every supplied row requires
a nonblank class, a nonblank source reference and a valid API12. Conflicting classes for the same API12
are rejected. Exact duplicates and repeated evidence for the same class do
not multiply records. Inputs are not modified.

No supported size-class mapping is supplied by these projections. Without
one, classification is `NOT_EVALUATED`, sources are empty, and all operator
classes are unknown. Operator-class charts are omitted in that state; area
charts and all record-count tables remain available. Caller-supplied classes describe an API12 snapshot;
historical operators and corporate succession are not established. Sources
are retained in results and shown in the report. A classification source
should state its own definition and snapshot date. Those descriptive
metadata are not validated by the analysis, which does not invent size
thresholds or classify names.

## Verification and limits

The tests enumerate synthetic records by hand and independently tally fixture
CSV records and completion-area API sets. Those counts check each source's
analysis, delivered area chart and table, and the note's fixture totals.
Tests also exercise missing and conflicting metadata, persisted results,
digest labels and reproducible example generation. The existing characterisation tests cover
report grains, revision history, digests and deterministic products.

WAR rows remain reporting records; EOR years remain borehole-status years.
Completion codes describe status, not completion design. Snapshot area
attribution does not reconstruct historical geography. The existing full
snapshot report is retained at its recorded revision; this example is a
separate fixture demonstration, with no new archive retrieval or population
analysis. Rates, durations and production correlations remain deferred to
issue #1063. Later work requires a sourced operator-class snapshot and a
rebuild from complete, digest-verified public archives.
