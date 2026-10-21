# Metocean reference data and external licensed tables

The module documents structures for external licensed tables.
The repository attributes these tables to API RP 2MET-derived workbooks.
Their tabulated values are not distributed with the repository.

## Source audit

[table_sources.json](table_sources.json) records a source audit for every table
listed below. Each schema and metadata entry links to its record using a JSON
Pointer in `source_record`. The sidecar preserves the repository's attribution
to API RP 2MET-derived workbooks and pins its evidence to the original README
revision. This attribution does not establish the source edition or the exact
publication table or clause for any individual extraction.

All eight records are `NOT_EVALUATED`, with `edition` and `table_or_clause` set
to `null`. All eight names below therefore require a maintainer decision under
issue #1262. The required evidence is the source edition, the publication table
or clause, and confirmation that it corresponds to the attributed extraction.
Repository section titles are descriptive labels, not verified publication
locators. The shared citation below remains incomplete. A newer publication's
edition must not be substituted for the unknown edition used by the workbooks.

### Reproduce the audit (worked example)

From the repository root, with Python and PyYAML available:

```bash
python scripts/maintenance/audit_metocean_table_sources.py
```

Inputs are `table_sources.json`, `schema.yaml` and `_metadata.json` in this
directory. No CSV or publication is opened. The method checks that both
catalogues list the same external tables, contain no duplicate names, and point
to the corresponding sidecar records. It then checks each record's document,
edition, table or clause, recorded verification status and evidence reference.
An evidence reference must have a repository-relative path, a full revision and
a description of what it supports. The audit checks the reference's structure;
it does not open historical evidence or confirm its contents.

For the current inputs, the summary fields in the JSON answer are:

```json
{
  "status": "NOT_EVALUATED",
  "table_count": 8,
  "verified_citation_count": 0
}
```

The independent count comes from the eight filenames listed in issue #1262.
Every record in [table_sources.json](table_sources.json) has a null edition and
publication locator. Thus all eight appear in `maintainer_decisions`, sorted by
filename, with `missing_fields` equal to `["edition", "table_or_clause"]`, plus
the existing attribution, reason, required evidence and pinned evidence reference.
This list is the unresolved-source list for maintainer decisions; it does not
infer an edition from the API document title.

The default exit status is zero for structurally consistent metadata, including
unresolved records. For a consumer requiring recorded citations, use:

```bash
python scripts/maintenance/audit_metocean_table_sources.py --require-citations
```

This exits with status one on the current inputs, while emitting the same
decision list. Unreadable or inconsistent metadata exits with status two and
an `INVALID` JSON result. Both commands are read-only.

### Complete an unresolved record

Obtain the document edition and exact publication table or clause used for the
extraction. Record a repository-relative evidence reference with its full
revision and scope, and confirm the correspondence to the extraction. Filling
the fields alone leaves the record `NOT_EVALUATED` and in the decision list.
After that confirmation is reviewed, record `attribution_status` as
`publication_citation`, `verification_status` as `VERIFIED`, and
`decision_status` as `resolved`. All citation fields must then be nonempty.
Only the recorded assessment changes the count; the script does not make it.

When all records have that assessment, the summary becomes
`CITATIONS_RECORDED`. This means citation metadata is complete; it establishes
neither engineering validity nor redistribution rights. Unidentified sources
remain for a maintainer decision. This audit adds no tabulated values and
deletes no data. Publication matching and any change to table distribution are
later work requiring the missing source evidence.

## External licensed tables

These tables are **not distributed**. Their schema entries retain column names,
types and units, with no bundled path or values. Supply an authorized CSV copy
outside the repository using
`worldenergydata.metocean.licensed_tables.load_licensed_table(name, copy_path=...)`.
Alternatively, set `METOCEAN_LICENSED_DATA_DIR` to an external directory holding
the expected filename. An explicit `copy_path` takes precedence. The loader
requires the metocean source checkout to establish the repository boundary;
installed copies without that boundary fail plainly. Paths inside the
repository, including symlinks into it, are refused. Columns must match the
schema exactly, including order; returned cells remain strings.

Citation for each external table: API RP 2MET, Derivation of Metocean Design and Operating Conditions; edition and table titles: to be completed from the licensed copy

The following descriptions are repository section titles, not verified titles
of tables in the publication.

- `api_rp2met_hurricane_gom_extremes.csv` — not distributed; Hurricane extremes by return period.
- `api_rp2met_us_zone_100yr_waves.csv` — not distributed; Extreme waves, currents and storm tide by offshore zone.
- `api_rp2met_gom_extremes_by_region.csv` — not distributed; GoM hurricane extremes by sub-region and return period (long-form).
- `api_rp2met_us_zone_100yr_winds.csv` — not distributed; 100-year extreme 10m/60-min wind speeds by US offshore zone (wind companion to the US-zone waves table).

- `marine_growth_terminal_thickness.csv` — not distributed; Terminal marine-growth thickness by depth band.
- `metocean_regional_extremes.csv` — not distributed; Regional metocean extremes by parameter and return period.
- `metocean_hs_tp_occurrence.csv` — not distributed; Joint wave-height and peak-period occurrence.
- `metocean_temperature_ranges.csv` — not distributed; Air and sea temperature ranges by area.
