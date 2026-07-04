# Plan Review: Issue #806 Spain CORES live XLSX download lane

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/806
**Plan:** `docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md`
**Reviewer:** Codex inline
**Date:** 2026-07-04
**Verdict:** APPROVE after r1 patch

## Adversarial Findings

### R1 - Real CORES workbooks require explicit `Production` sheet selection

**Severity:** Major before patch

The plan originally said the live lane would reuse `CoresProductionLoader`, but
the current loader calls `pd.read_excel(self._path, header=...)` without a sheet
name. Real CORES workbooks contain a non-data `Start` sheet before the data
sheet, so live reads would parse the wrong sheet and fail at runtime.

**Required fix:** The plan must require explicit `sheet_name="Production"` for
live workbook reads and a regression workbook fixture with `Start` plus
`Production` sheets.

**Resolution:** Folded into the plan before `status:plan-review`.

## Checked Risk Areas

- Direct-source contract: acceptable. The plan uses official CORES URLs and the
  statistics page as a drift check, not third-party mirrors.
- Parser duplication: acceptable. The plan requires the live lane to reuse
  `CoresProductionLoader`/`parse_cores_frame`.
- `/mnt/ace` writes: acceptable. The plan requires caller-supplied cache roots
  and avoids hardcoded absolute paths in library code.
- Fixture scope: acceptable. Full live outputs stay under `/mnt/ace`; only the
  small conformance fixture and metadata are repo-tracked.
- Scheduler scope: acceptable. Scheduling remains deferred to #809.

## Remaining Non-Blocking Notes

- Implementation should preserve UTF-8 field names such as `Boquerón`,
  `Poseidón`, and `Biogás` when writing normalized CSVs.
- The live downloader should fail closed on missing source links rather than
  falling back silently to stale cached URLs when `force_refresh=True`.
