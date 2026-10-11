# Public table ingest evidence

- Hash verification shall require one unique record for every consumed table;
  validating only records supplied by a manifest does not establish completeness.
- Manifest file names shall be basenames; reject duplicate records and path traversal.
- Date exports shall retain four-digit years. Test historical dates before 1969;
  two-digit parser pivots silently change the century of source observations.
- Geographic associations shall retain candidate qualifiers until the entity
  identity crosswalk is established. A shared block does not establish field identity.
