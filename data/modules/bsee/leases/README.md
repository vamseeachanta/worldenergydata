# Public BSEE lease snapshot

Scope: issue 959.
The extract contains the 20 Lower Tertiary leases assigned to the 10 lifecycle
poster fields in the canonical registry. All 20 resolve through `by_lease`.
Raw packages remain in caller-configured external storage; no full raw ZIP is
committed. The source manifest records URLs, UTC retrieval times, SHA-256,
byte sizes and the source disclaimer. No source update date is inferred.

## Revision history

| Revision | Date | What changed and why |
|---|---|---|
| 1 | 2026-10-20 | Connected the recorded snapshot to lease panels and freshness reporting to replace unsupported placeholders. |

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
offline; combining it with `--update-manifest` rebuilds the source manifest from
verified saved files and their original provenance without a retrieval. Observation timestamps describe this retrieval, not
database freshness.

A normal run exits 0 when sources agree and 2 when the file set, address, size,
or digest differs (including a missing curated manifest). Only the discovery
page is compared by its extracted archive links: byte changes are printed as
informational while link changes fail; terms, layouts and archives remain
byte-compared.
The explicit `--update-manifest` flag retains its replacement behavior.

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
- `panel_values.html`: generated escaped display with plain headers and one line
  per current owner, retaining serial, reported group, company and percentage;
  unresolved names show their source reason. Its digest and size are included
  in the extract manifest.
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

## Panel integration and freshness

The lifecycle-poster builder reads `leases.json`, `panel_values.json` and
`operators.json` through `load_lease_snapshot`. It checks their byte sizes and
SHA-256 digests against `extract_manifest.json`, plus the source-manifest digest,
before joining normalized lease identifiers. The poster and Explorer consume
the same escaped HTML table and structured JSON. Registry blocks remain an
unpaired field-level list; only the Lease Data snapshot supplies a per-lease
area/block. Field-level interests remain separate from owner assignment records.

Status and royalty bid-system values are displayed as source codes, without
assuming a legal interpretation. Current owner rows retain serial, group,
aliquot, percentage and assignment approval date. Operator history retains all
source assignment rows. Company names describe retrieval-time resolution, not
the company name at each historical date. Unknown values have explicit reasons;
lease type is not mapped. No expiration date is derived from an expected date.

`data/freshness-scorecard.json` has a separate `datasets.bsee_leases` entry;
the original module-level observation is retained. The scorecard generator also
emits that entry and a dataset note in its Markdown output. Freshness remains
`unknown`: retrieval receipts establish access, not the database update date.
No freshness interval or acceptance limit is assumed. This is a curated subset,
not coverage of every BSEE lease. Raw packages remain external, as described above.

Generate review outputs in a separate directory with:

```bash
uv run python scripts/lower_tertiary/build_lifecycle_posters.py --lease-panels-only --output-dir "$OUTPUT_DIR"
```

## Worked example: one recorded lease

Inputs are the G16942 source row in `tests/fixtures/bsee/leases/provenance.json`,
the owner fixture `lseowndelimit.txt`, and the corresponding curated JSON rows.
The published [BSEE Lease Data layout](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=leaseData)
defines effective and actual/expected expiration dates. The
[Lease Owner layout](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=leaseOwner)
defines assignment interest, group and aliquot. Both layouts were opened on
2026-10-20. The committed schema preserves these definitions.

Method: normalize `OCS-G 16942` to `G16942`; look up the lease row and its panel
values; preserve the current owner rows without adding their interests across
groups. No equations or fitted coefficients are involved.

Answer: area/block `WR029`, status code `PROD`, effective date `1996-09-01`,
actual expiration absent, expected expiration `2006-08-31`. The three recorded
owner rows carry `27.5`, `12.5` and `60.0` percent with assignment approval date
`2026-07-28`. Expected expiration is displayed separately and does not imply
that a producing lease expired. These literal expected values are transcribed
from the recorded source fixture, not generated by the panel code.

```python
from pathlib import Path
from worldenergydata.field_development.landman import build_landman, load_lease_snapshot

snapshot = load_lease_snapshot(Path("data/modules/bsee/leases"))
panel = build_landman({}, ["OCS-G 16942"], [], {}, 959, lease_snapshot=snapshot)
lease = panel["leases"][0]
assert lease["per_lease_block"] == "WR029"
assert lease["status"] == "PROD"
assert lease["effective_date"] == "1996-09-01"
assert lease["expiration_date"] is None
assert lease["expected_expiration_date"] == "2006-08-31"
assert [r["ASSIGNMENT_PCT"] for r in lease["per_lease_working_interest"]] == [27.5, 12.5, 60.0]
```

Offline fixtures are short recorded slices of the downloaded packages. The
fixed-width lease row is stored in a small fixture ZIP to retain source padding.
Fixture digests and source selection are recorded in `tests/fixtures/bsee/leases/provenance.json`.
