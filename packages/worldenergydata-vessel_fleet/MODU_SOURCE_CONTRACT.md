# Public MODU source evidence contract

The selected public candidate is deliberately **NOT_EVALUATED** and cannot be
promoted. Its source row establishes public availability of a drilling-floater
listing, without a verified physical identity, loading condition or mass basis.
This source-only interface addresses #1050; consumer #1618 owns the physical-host
crosswalk and identity envelope. No hydrodynamic response or solver result is
created. The roster-wide riser-handling columns remain under #698.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-20 | Add the evidence contract and blocked candidate to expose source gaps. |
| 2 | 2026-10-20 | Reject unresolved metadata dispositions and add a fixed canonical-record oracle. |

## Three slices

1. `modu_source.py` defines typed sources, citations, identity claims, an explicit
   loading condition, geometry references, quantities and coordinate evidence.
2. `assess` rejects contradictory identity, aliases, physical units, loading
   bindings and units. Missing evidence or unknown rights blocks qualification.
3. `data/public_modu_source.json` selects exactly the first body row of the public
   rig table in its captured source bytes. The runnable example shows why it
   remains blocked. This is a source selection, not a physical-vessel assignment.

The existing roster and name resolver are unchanged. A record references its
source row through `rig_source_id`; it does not create another rig registry.
A row ordinal is meaningful only together with its source-byte digest. A later
capture must be reviewed as a different observation rather than silently joined
by row position or display name.

## Source selection and rights

The [public rig table](https://www.deepwater.com/our-fleet/our-rigs), captured
2026-10-20, contains the selected row at
`table.our-rigs > tbody > tr:first-child`. Its byte count, capture instant,
HTTP response and SHA-256 are recorded in the candidate. A publicly accessible
listing is evidence of access, not permission to redistribute the original.
Redistribution therefore remains `unknown`; no source document, display name or
engineering value from that page is reproduced. Only its URL, locator, capture
metadata and commitment are retained in the package. No private material seeds
this candidate. The source may change; a live download is not assumed to match
the captured commitment.

The candidate deliberately withholds aliases: the captured first cell locates
the display-name evidence, which cannot prove physical identity. Missing aliases
are a qualification blocker. The row gives an operational capability category;
no hull class, geometry or loading condition is inferred from it. In particular,
operational capacity and gross tonnage must never replace displacement.

## Inputs and method

Each `SourceRecord` requires the schema version, source record and rig source
identifiers, rig class, citations and source commitments. Optional engineering
fields must be explicitly null or absent from `quantities`, with dispositions in
`missing_evidence`. Unknown is never represented by zero.

Supported disposition keys are the required quantity names and
`physical_identity`, `loading_condition`, `geometry`, `coordinate_frame`,
`aliases`, `rig_class` and `public_eligibility`. Unknown keys are rejected with
`UNKNOWN_DISPOSITION:<key>`. Every metadata disposition adds
`UNRESOLVED_DISPOSITION:<key>` and blocks promotion. A disposition conflicting
with a populated fact also adds `CONTRADICTORY_DISPOSITION:<key>` and yields
`REJECTED`. Physical identity conflicts if any physical identifier, IMO, fallback
or identity citation is populated; loading, geometry and coordinate dispositions
conflict with their respective condition, geometry citation and frame. Aliases
conflict with a nonempty alias list; rig class conflicts with a class other than
`floater_unspecified`. Public eligibility conflicts when every source asserts
public origin, cleared fact redistribution and HTTP 200. These assertions still
require matching bytes and independent authentication before use.

A complete record carries:

- A non-name physical identifier with a cited IMO claim or cited fallback plus a
  review reference. Aliases each bind to that same physical unit and cannot
  introduce another IMO. Names alone do not qualify.
- A geometry citation and principal length, beam, depth and draft in metres.
- One described loading-condition identifier bound to the physical unit.
- Displacement in metric tonnes, CoG coordinates in metres, and all six
  independent inertia tensor components in metric tonne square metres. Values
  retain their input units; no conversions or defaults are performed.
- Coordinate origin and directed axes, plus inertia about the CoG using tensor
  components. Products of inertia need an explicit sign convention. Every
  engineering quantity and frame citation binds to the same physical unit and
  condition, so different loading conditions cannot be combined.
- Source URLs, aware capture times, response status, exact source-byte size and
  SHA-256, source class, redistribution disposition and rights evidence.

The interface applies evidence consistency checks, not engineering equations,
hydrostatic calculations or numerical tolerances. Strictly positive dimensions,
displacement and diagonal inertias are basic input-domain checks. No tensor
realizability, stability or engineering suitability is claimed. All engineering
values in the tests are explicitly stipulated synthetic inputs; their expected
dispositions are enumerated independently in the test docstring.

Source dates cannot be in the future. Missing, conflicting and unknown evidence
is preserved, with explicit machine-readable reasons. `COMPLETE` describes the
input evidence shape; it is not an authenticated approval. Synthetic, private
and licensed sources can never become publicly promotable. Unknown or prohibited
redistribution cannot qualify even when all engineering fields are present.

## Commitments and consumer interface

`canonical_bytes` serializes the validated model as UTF-8 JSON with sorted object
keys, compact separators, unescaped Unicode and no non-finite numbers. Array
order is retained and is part of the observation. Parsed numeric types and
normalized timezone representations are part of this version's encoding; this
is not a claim of RFC 8785 compatibility. Duplicate JSON keys and undeclared
fields are rejected. The schema can be obtained from
`SourceRecord.model_json_schema()`.

`commitment` hashes those bytes using
[SHA-256, FIPS 180-4 (2015), section 6.2](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf).
This digest commits the complete source observation, including rights and missing
evidence. It is distinct from each original source-byte digest and from the
consumer's future physical-host identity. No consumer identity algorithm is
defined here. The independent hash fixture comes from the
[NIST SHA-256 One Block Message Sample](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA256.pdf),
whose input is `abc`.

A separate handwritten canonical-record byte fixture in
`tests/unit/vessel_fleet/test_modu_source.py` has a fixed SHA-256 established with
`sha256sum` and OpenSSL, independently of the encoder. It checks unescaped
Unicode, nested object-key ordering, integer and floating-point representation
(including negative zero), and meaningful alias-array order. Both
`canonical_bytes` and `commitment` are compared with those fixed expectations.

The IMO format check uses the
[IMO Ship Identification Number Scheme explanatory page](https://www.imo.org/en/OurWork/MSAS/Pages/IMO-identification-number-scheme.aspx),
which specifies seven digits. Format validation cannot authenticate the number,
and a checksum or name match is never treated as identity evidence. Successful
source-response evidence uses
[HTTP 200, RFC 9110 (2022), section 15.3.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.1).

Consumers load a record with `load_record`, retain its `record_sha256`, and call
`assess(record, source_bytes={source_id: raw_bytes})`. Bytes must match both
length and digest; unavailable or changed originals cannot qualify. Without
supplied bytes `promotable` is false. A complete public record with cleared
rights and matching source bytes can qualify at this evidence boundary only.
Consumers must separately authenticate cited identity, fallback reviews and
rights evidence, join their existing catalogs, and authorize intended use.
Caller-authored assertions, URLs and hashes alone do not establish those facts.
No implicit fetch, guessed fallback or solver import occurs.

## Worked example

Run from a source checkout with the domain package available on the Python path:

```sh
PYTHONPATH=src:packages/worldenergydata-vessel_fleet/src:packages/worldenergydata-core/src \
  python examples/vessel_fleet/modu_source_example.py
```

Inputs are the committed candidate's captured row reference and explicit missing
evidence. The method validates the JSON, checks the required bindings and units,
then computes the canonical commitment. The answer is `NOT_EVALUATED`,
`promotable: false`, with reasons including `IDENTITY_MISSING`,
`LOADING_MISSING`, `MISSING:displacement`, `FRAME_MISSING` and
`RIGHTS_NOT_CLEARED:public-rig-page`. The example emits the record commitment
and all reasons as JSON. Optional `--source-file` verifies retained source bytes;
matching bytes alone cannot fill the missing engineering or rights evidence.

A complete synthetic worked input is `complete_record()` in
`tests/unit/vessel_fleet/test_modu_source.py`. Its docstring gives every quantity
and the independent expected answer: `COMPLETE` and non-promotable because the
source is synthetic. Changing one condition binding produces `LOADING_MISMATCH`;
removing any required quantity produces `NOT_EVALUATED`.

## Remaining evidence

A promotable public record still requires authentic physical identity and aliases,
hull geometry, a loading condition, displacement, CoG, the inertia tensor and
coordinate basis, plus source-specific publication rights. No unverified value
is backfilled from a generic hull, sister unit or earlier private work. External
artifact review remains required before the evidence is accepted for analysis.
