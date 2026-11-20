# worldenergydata-texas_rrc

`texas_rrc` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.texas_rrc` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Production district reference

Source identity: `texas-rrc` (RRC); collection owner: `worldenergydata`.
The public [Production Data Query Dump manual](https://www.rrc.texas.gov/media/50ypu2cg/pdq-dump-user-manual.pdf),
data dictionary, printed page 26 (PDF page 28), is inspected on 2026-11-04.
No publication date or edition is stated in the document. The inspected PDF has
SHA-256 `a24a6b5e5daf9863b82b579924b485de573b94e0d2da439695b72e8b04fbf4d2`.

The qualified use is validation and normalization of **production district
names** in the local CSV route. The `DISTRICT_NAME` definition gives:
`01, 02, 03, 04, 05, 06, 6E, 7B, 7C, 08, 8A, 09, 10`.
The adjacent conversion table qualifies `6E` as oil-only and marks `8B` unused.
Thus `6E` is supported alongside the existing `7B`, `7C` and `8A`; `07`, `8B`,
`12` and `20` are not in the qualified production district-name list.
Blank and invalid names enter the existing unclassified bucket, separately from
assigned districts; their production volumes remain in the totals.

`TexasDataValidator.VALID_DISTRICTS` owns this list. The router, CLI and production
atlas derive their accepted names from it; endpoint lookup includes the same
names. Headquarters and county counts are not qualified by this reference, so
the `6E` lookup supplies its name only.

The manual distinguishes names from internal numeric `DISTRICT_NO` values:
internal `07` means `6E`, `08` means `7B`, and `10` means district `08`.
Numeric-ID conversion is not established by this change. CSV callers must
supply district **names**, including when a legacy column alias such as
`DISTRICT_NO` is used. Raw PDQ numeric-ID ingestion, historical district changes
and broader production-data accuracy remain outside this qualification. The
reference qualifies identifiers only, not volume units, commodity-specific
record validation or engineering inputs. Aggregate rows must not be mixed with
individual production records; detecting such mixtures is not established.
