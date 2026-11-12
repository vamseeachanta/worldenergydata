# OSHA fragment inventory

Run `python scripts/ingest/hse_bulk_ingest.py --help` for the inventory command
and its input and output options. The command profiles local CSV fragments;
it does not ingest or delete records.

A zero-byte fragment fails the entire run, even after earlier fragments have
been processed. A fragment containing only a valid header contributes zero rows.
Malformed CSV and invalid UTF-8 also fail the run without a JSON inventory.

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
