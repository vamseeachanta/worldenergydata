# Public BSEE lease snapshot

Scope: issue 959.
The extract contains the 20 Lower Tertiary leases assigned to the 10 lifecycle
poster fields in the canonical registry. All 20 resolve through `by_lease`.
Raw packages remain in caller-configured external storage; no full raw ZIP is
committed. The source manifest records URLs, UTC retrieval times, SHA-256,
byte sizes and the source disclaimer. No source update date is inferred.

## Reproduction

Set `BSEE_LEASE_RAW_DIR` to a new directory on the data disk. With the repository
Python environment and BSEE/core packages available, run:

```bash
uv run python scripts/bsee/fetch_leases.py
uv run python scripts/bsee/fetch_leases.py --update-manifest
uv run python scripts/bsee/fetch_leases.py --from-saved
```

The committed manifest was emitted by the script during one paced retrieval on
2026-10-11: the discovery page, disclaimer, one schema-listed layout per table,
and four archives (ten files). The first command writes its run manifest beside
the external raw files and reports differences in names, URLs, sizes and SHA-256
against the committed manifest; it changes no curated files. Use a separate new
raw directory for the explicit `--update-manifest` command, which replaces the
committed manifest and regenerates the extract. `--from-saved` verifies those
saved archives and regenerates all derived outputs, including the HTML table,
offline. Observation timestamps describe this retrieval, not database freshness.

Downloads are sequential, with at least two seconds before every request attempt,
including a retry. The User-Agent supplies the repository contact URL.
Existing raw files are never overwritten. HTTP 401, 403 or 429 stops downloads;
an access challenge also stops downloads. Timeouts and server errors have at most
one retry. Completed downloads retain
individual provenance sidecars even if a later request fails; interruptions are
recorded. Each run reads back its outputs.
The environment's prescribed cache and temporary-directory configuration applies.

## Tables and meaning

- `leases.json`: exactly the issue's eight columns. `approval_date` and `gwi_pct`
  are arrays aligned to `panel_values.json` current owner rows, in source order.
  Approval is assignment approval; effective date is lease commencement.
- `owners.json`: every recorded owner row for these leases, including terminated
  assignments. `SN_LSE_OWNER`, owner group, aliquot, assignment dates and source
  `ASSIGNMENT_PCT` remain present. Percentage units are 0–100, never fractions.
- `operators.json`: designated-operator rows, preserved separately to avoid
  multiplying owners through a many-to-many join. Designation dates remain present.
- `panel_values.json`: structured current owner/operator records and separately
  labeled actual expiration and expected expiration dates. No actual expiration
  is inferred from expected expiration or a primary term. Surface area and its
  source unit code remain present.
- `panel_values.html`: escaped display of the same curated rows; its digest and
  size are included in the extract manifest.
- `registry.json` / `missing.json`: explicit registry and source-presence outcomes.
- `source_schema.json`: verified source aliases, positions, lengths and parsed
  scalar types. Published layouts govern parsing; the existing conceptual
  [lease dictionary](../../../../docs/knowledge-base/bsee/data-dictionaries/leasing/lease-fields.md)
  provides context, rather than a literal ASCII contract.
- `extract_manifest.json`: source row counts and readback hashes for derived files.

Only assignment status `C` enters current ownership. `H`, `P`, `T` and blank
remain in history. Percentages are never added across owner groups or aliquots.
Company names represent the unique unterminated Company (All) name at retrieval,
including on historical rows; they are not names reconstructed as of assignment.
Unresolved or ambiguous names remain null with an explicit reason. Empty current
owner or operator collections also carry a reason in panel values.

The BSEE disclaimer states that the working database may contain errors and is
not a legal document or for navigational use. No explicit license grant is stated
on the download page. This snapshot is public research evidence; legal title and
current commercial interests are not established solely by these downloads.

## Deferred integration

Panel wiring remains outside this PR: status, lease effective date, actual versus
expected expiration, individual lease block, and owner/group-specific working
interest. Exact available values are in `leases.json` and `panel_values.json`.

The download/provenance helper overlaps conceptually with
[PR 1155](https://github.com/vamseeachanta/worldenergydata/pull/1155); consolidation
will follow both additions. Shared `data/modules/bsee/README.md`, `DATA_DICTIONARY.md`, `schema.yaml`,
`_metadata.json`, and freshness-scorecard integration remain deferred until the
parallel BSEE work merges. No panel or registry configuration is changed here.

Offline fixtures are short recorded slices of the downloaded packages. The
fixed-width lease row is stored in a small fixture ZIP to retain source padding.
Fixture digests and source selection are recorded in `tests/fixtures/bsee/leases/provenance.json`.
