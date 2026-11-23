# Plan Review: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Source/Provenance - r1

**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Reviewer:** parallel Codex explorer
**Verdict:** MAJOR

## Findings

1. **MAJOR - Partial/defaulted conversion could satisfy the draft despite [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) asking for each field's real cited factor.**

   The draft permitted field-specific factors only where cited values existed and
   allowed default conversion when strict mode was off. That was source-safe only
   if treated as incomplete. Required change: closeout must be all-or-blocked.
   Every current CORES oil field must have a validated cited factor, or
   [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) must
   remain open with named source gaps.

2. **MAJOR - Ayoluengo example used non-representative/conflicted evidence.**

   The draft example used 36 API from an AAPG discovery well while the same
   source reports Ayoluengo oils vary from 20 to 39 API by well/sand. Required
   change: Ayoluengo must remain missing/defaulted unless a source identifies a
   representative produced stream, sales crude, blend, field-average density, or
   explicit current conversion basis. Ranged/non-representative evidence must not
   populate `bbl_per_tonne`.

3. **MAJOR - Secondary-source policy was too permissive for values that change production volumes.**

   The draft allowed non-official/operator/regulator sources if labeled with
   `source_class` and `confidence`. Required change: numeric factors affecting
   `oil_bbl` must come from regulator/operator/filing/crude assay/technical
   literature with explicit measurement basis. Secondary articles may support
   notes only unless they provide representative field-applicable values.

4. **MAJOR - Provenance was stripped before parsing.**

   The draft exposed `crude_density_mapping() -> dict[str, float]` and
   `parse_cores_frame(..., density_by_field=...)`, allowing uncited floats and
   silent fallback. Required change: live/default path must consume validated
   factor objects or emit conversion metadata from the parser boundary. Fallback
   must require explicit opt-in and report exact defaulted fields.

5. **MINOR - Report caveat removal was keyed to sidecar existence, not full cited coverage.**

   Required change: remove the issue-807 caveat only when sidecar coverage is
   complete and no fields are defaulted; otherwise retain a limitation naming
   defaulted/missing fields.

## Sources Checked

- CORES statistics page and crude workbook confirm production unit is tonnes and
  do not provide density/API:
  `https://www.cores.es/en/estadisticas`,
  `https://www.cores.es/sites/default/files/archivos/estadisticas/crude-oil-production.xlsx`
- EIA supports the API gravity formula:
  `https://www.eia.gov/dnav/pet/TblDefs/pet_crd_api_tbldef2.asp`
- AAPG supports Ayoluengo conflict/range:
  `https://www.aapg.org/news-and-media/explorer/spains-oldest-and-only-onshore-oilfield/`

## Patch Response

The plan was patched to require all-or-blocked closeout, reject
non-representative/ranged evidence as conversion factors, add
`accepted_for_conversion`, require explicit `allow_default_density=True`, and
gate report caveat removal on complete sidecar coverage.
