# OSHA fragment inventory

Run `python scripts/ingest/hse_bulk_ingest.py --help` for the inventory command
and its input and output options. The command profiles local CSV fragments;
it does not ingest or delete records.

## Tables, keys and dates

Each run profiles one table, chosen with `--table`, so totals never combine
tables. A fragment is selected only when its whole file name matches the table
pattern; names such as `osha_violation_old.csv` are not selected. Fragments are
processed in numeric suffix order, so `osha_violation2.csv` precedes
`osha_violation10.csv`, and `overlap_*` counts are attributed to the later
fragment in that order. Name matching is case-sensitive.

| `--table` | Fragment name | Candidate key | Date column | Key repeats |
| :-- | :-- | :-- | :-- | :-- |
| `violation` (default) | `osha_violation<N>.csv` | `activity_nr`, `citation_id` | `issuance_date` | not expected |
| `violation_event` | `osha_violation_event<N>.csv` | `activity_nr`, `citation_id` | `hist_date` | expected, one row per history event |
| `violation_gen_duty_std` | `osha_violation_gen_duty_std<N>.csv` | `activity_nr`, `citation_id` | none | expected, one row per text line |

The key and date columns are taken from the catalogued fragment schemas in
`data/catalog/data-catalog.yml` (entries `osha_violation0` to `osha_violation13`,
`osha_violation_event0` to `osha_violation_event11` and
`osha_violation_gen_duty_std0` to `osha_violation_gen_duty_std2`). `activity_nr`
is the inspection number and `citation_id` the citation within the inspection.
`load_dt` is a load stamp, not an event date, and is not used as a date column.

Dates are counted as valid only in ISO `YYYY-MM-DD` form with ASCII digits.
Other forms are counted in `invalid_dates`; they are not converted.

When a fragment lacks a key or date column, its key or date metrics are `null`,
and the fragment is listed in `files_missing_key_columns` or
`files_missing_date_column`. The top-level key totals (`keyed_rows`,
`unkeyed_rows`, `duplicate_candidate_keys`, `unique_candidate_keys`) are `null`
when any fragment lacks the key. A zero means zero observed repeats; `null`
means the key could not be measured.

## Encoding

Fragments are decoded as latin-1 by default, matching how the repository's OSHA
acquirer and importer read the DOL files; every byte sequence decodes. A
fragment that starts with a UTF-8 byte-order mark fails under latin-1 and must
be rerun with `--encoding utf-8-sig`. `--encoding utf-8` fails the run on any
byte sequence that is not valid UTF-8. The inventory records the encoding used.

## Failures and the index

A zero-byte fragment fails the entire run, even after earlier fragments have
been processed. A fragment containing only a valid header contributes zero rows.
Malformed CSV and a decode failure also fail the run without a JSON inventory.

The SQLite index is retained after success or failure and cannot be overwritten
by a rerun. Before using it, readers must execute `SELECT complete FROM meta`
and require exactly one row containing `1`. A missing table, an unreadable index,
or any other result means the index is incomplete. Failed runs can retain
committed signatures from earlier fragments; those signatures alone do not
establish that the inventory finished.

A successful JSON inventory includes `index_complete: true` and `index_db`,
the index basename without directory components. The inventory is returned only
after the complete marker is committed. The basename identifies the requested
index within its output directory; it does not establish content identity.

## Limits

No production fragments have been profiled with this command. Whether every
production fragment carries the catalogued header, and whether `issuance_date`
values are in ISO form, is therefore not established; both are reported, not
assumed, when the command runs.


## BSEE binary ingestion

The local BSEE command converts existing borehole, WAR, rig-fleet and directional
survey sources to timestamped CSV or Parquet and registers measured counts and
source digests in the existing catalog. Use `make unpack-bsee` with the source
and current-tier roots configured; pickle sources require `--trust-pickles`.
The command does not download data or run a solver. See the
[format, execution and validation contract](../../docs/data/bsee-binary-formats.html)
for interpreter compatibility, source layout, exact-row comparison and limits.
