# BSEE Field Crosswalk

Name/block-based cross-reference between the global offshore O&G fields dataset
(`fields.csv`) and the BSEE data under `data/modules/bsee/`.

Companion artifact: `bsee_field_crosswalk.csv`. Refs worldenergydata #543 (corpus epic #767).

## Scope

- Source: 2,149 fields in `fields.csv`; filtered to the **333** rows with `US_GOM_FLAG = Y`.
- Target: BSEE field identifiers. In this module the only field-level identifier is
  `BOTM_FLD_NAME_CD` (bottom-hole field/area code) in
  `current/wells/well_data.csv` and `current/infrastructure/all_bsee_blocks.csv`.
  These are BSEE/BOEM **area-abbreviation + block-number** codes (e.g. `ST295` =
  South Timbalier block 295), **not** marketing/project names.

## Match-rate summary

| match_type | count | share of 333 |
|------------|-------|--------------|
| exact      | 0     | 0.0%         |
| fuzzy      | 11    | 3.3%         |
| none       | 322   | 96.7%        |

- **exact** — a block code derived from the field's `BLOCK` (area code + block number)
  is present verbatim in the BSEE `BOTM_FLD_NAME_CD` set.
- **fuzzy** — the field's BOEM protraction **area** is present in the BSEE data, but no
  specific block number matched (area-level association only; confidence 0.40).
- **none** — neither the block code nor the area is present in the BSEE data.

The 11 fuzzy matches are the South Timbalier (ST) and Ewing Bank (EW) fields —
the only two areas the current BSEE slice covers:
Arnold, Blackbeard East, EW 998, Hummingbird, Maserati, McLaren, Morpeth, Prince,
Saleen, Screwdriver, Toddy.

## Method / normalization

- **Field name** (`normalized_name`): uppercased; parenthetical aliases dropped
  (e.g. `Aasta Hansteen (Luva)` -> `AASTA HANSTEEN`); trailing descriptor words
  removed (FIELD/UNIT/PROSPECT/COMPLEX/AREA/PROJECT/BLOCK/...); punctuation stripped;
  whitespace collapsed.
- **Block code**: the leading area text of `BLOCK` is mapped to its BSEE area
  abbreviation (Mississippi Canyon -> MC, Green Canyon -> GC, South Timbalier -> ST,
  etc.); each trailing block number yields a candidate code (`<AREA><BLOCK>`),
  e.g. `Mississippi Canyon 305` -> `MC305`. Multi-block strings produce multiple
  candidate codes.
- Matching is done on the derived block codes / area against the union of
  `BOTM_FLD_NAME_CD` values from `well_data.csv` and `all_bsee_blocks.csv`.

A pure normalized **name** join is not possible against this BSEE slice because the
BSEE side carries no marketing field names — only area+block codes. The crosswalk
therefore joins on block geography, which is the only shared key.

## Caveats

- **BSEE slice is small.** The hydrated BSEE data here is a sample of ~100 wells
  covering only **21 distinct block codes in 2 areas** (South Timbalier, Ewing Bank;
  plus one `EW873`). This is why exact = 0 and most rows fall to `none`: the full BSEE
  GoM well universe (thousands of leases across ~30 protraction areas) is not present
  in this module. Re-running against a fully hydrated BSEE `well_data` would raise the
  match rate substantially.
- **`US_GOM_FLAG` is broader than the Gulf of Mexico.** Several flagged rows are not
  GoM at all: Alaska North Slope (Northstar, Liberty, Oooguruk, Sivulliq, Torpedo via
  Beechey Point / Flaxman Island), Pacific OCS / California (Beta via POCS), and
  offshore Brazil (Huna via BM-C-42). These can never match BSEE GoM data.
- **11 rows have no parseable GoM area** (empty `BLOCK`, bare block numbers like
  `6864`/`7007`, OCS-Y lease IDs, or non-GoM areas) and are reported as `none`.
- **`BLOCK` is free text**, not a normalized lease ID; many rows list several blocks.
  The first/all numeric tokens are used as candidate block numbers.
- **`well_data.csv` has a CSV-quoting artifact** — some company names containing commas
  spill into the `BOTM_FLD_NAME_CD` column; non-code tokens are filtered out before
  matching.

## Columns (`bsee_field_crosswalk.csv`)

| column | meaning |
|--------|---------|
| `og_field_name`   | field name from `fields.csv` |
| `normalized_name` | normalized field name (see method) |
| `bsee_match_name` | matched BSEE code, or area label for fuzzy, else empty |
| `bsee_id_if_any`  | matched BSEE `BOTM_FLD_NAME_CD` code (exact only) |
| `match_type`      | exact / fuzzy / none |
| `confidence`      | 0.95 exact, 0.40 fuzzy, 0.00 none |
