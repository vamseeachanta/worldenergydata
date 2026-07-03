# Plan: Issue #740 - Oklahoma OCC completion-pressure observations

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/740
**Status:** plan-review
**Tier:** T2 (new direct-source state ingest, `/mnt/ace` raw snapshot, curated pressure observations, screen integration, docs)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will start from `origin/main` after this plan is reviewed,
pushed, marked `status:plan-review`, and explicitly approved by the user. The
approved implementation will use TDD: tests will be written before production
code for source manifest handling, OCC workbook parsing, pressure/depth
coercion, duplicate/earliest selection, screen normalization, and docs.

### Issue and dependency status

Planning-time issue probes on 2026-07-03 indicate:

| Issue | State | Current role |
|---|---|---|
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open, `status:needs-plan` | Parent pressure-screen epic |
| [#709](https://github.com/vamseeachanta/worldenergydata/issues/709) | closed, `status:done` | Texas RRC pressure observations |
| [#725](https://github.com/vamseeachanta/worldenergydata/issues/725) | closed, `status:done` | Kansas KGS pressure observations |
| [#732](https://github.com/vamseeachanta/worldenergydata/issues/732) | closed, `status:done` | Existing screen consumes Kansas + Texas |
| [#740](https://github.com/vamseeachanta/worldenergydata/issues/740) | open, `status:needs-plan` | This Oklahoma OCC direct-source slice |

#740 will extend the existing pressure-observation and screen contracts rather
than creating a parallel analysis path.

### Parallel work check

Planning-time worktree probes show other active worktrees for Texas RRC source
catalog, Texas RRC refresh, FDAS, corpus datasets, pages, field equipment, and
autorun lanes. #740 will avoid those scopes. It will stay inside:

- `src/worldenergydata/modules/state_regulators/oklahoma_occ/`
- `src/worldenergydata/analysis/underpressured_screen/observations.py`
- `config/underpressured_screen.yml`
- focused unit tests and onshore pressure-screen docs

### Direct-source evidence

Official OCC evidence checked on 2026-07-03:

| Source | Planning-time evidence | Implementation use |
|---|---|---|
| OCC Oil and Gas Data Files | https://oklahoma.gov/occ/divisions/oil-gas/oil-gas-data.html lists the "Monthly Well Completions Report" as daily `.xlsx` and links production records to Oklahoma Tax Commission | Source catalog and refresh metadata |
| Completion workbook | `https://oklahoma.gov/content/dam/ok/en/occ/documents/og/ogdatafiles/completions-wells-formations-base.xlsx`; HEAD 200, `content-length: 76131895`, `last-modified: Tue, 30 Jun 2026 00:34:55 GMT` | `/mnt/ace/.../oklahoma_occ/raw/` snapshot |
| Completion dictionary | `https://oklahoma.gov/content/dam/ok/en/occ/documents/og/ogdatafiles/completions-wells-formations-data-dictionary.xlsx`; HEAD 200, `content-length: 43286`, `last-modified: Tue, 26 Aug 2025 15:33:40 GMT` | Schema validation and provenance |

The implementation will use the official OCC direct URLs only. It will not use
PatchOps, LinkedIn, commercial data vendors, or third-party scraper output.

### Source bounds

The initial implementation will cover structured 2010-present OCC completion
records from Form 1002A. It will not attempt:

- pre-2010 legacy workbook interpretation unless the structured base workbook
  integration is already complete and tests show the same schema contract;
- imaged Form 1016 back-pressure/deliverability tests;
- Oklahoma Tax Commission production bulk acquisition.

Those lanes require separate acquisition, OCR, or access decisions and will be
tracked outside #740.

### Current code shape

Relevant existing patterns:

- `src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py`
  writes `/mnt/ace` raw manifests, normalized parquet, curated pressure
  observations, and coverage stats.
- `src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py`
  isolates source-format parsing from pipeline orchestration.
- `src/worldenergydata/analysis/underpressured_screen/observations.py`
  normalizes source-specific schemas to the screen contract and will receive an
  Oklahoma OCC adapter.
- `config/underpressured_screen.yml` already models per-source entries with
  `name`, `path`, `schema`, `state`, `era`, and optional quality metadata.
- `docs/data-sources/onshore/state-well-databases/source-catalog.md` already
  identifies Oklahoma as the second high-value pressure-screen source after
  Kansas.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex inline | `scripts/review/results/2026-07-03-plan-740-codex-inline.md` |
| New package | `src/worldenergydata/modules/state_regulators/oklahoma_occ/` |
| New package tests | `tests/unit/modules/state_regulators/test_oklahoma_occ_*.py` |
| Observation normalizer | `src/worldenergydata/analysis/underpressured_screen/observations.py` |
| Screen config | `config/underpressured_screen.yml` |
| Screen tests | `tests/unit/analysis/test_underpressured_observations.py`, `tests/unit/analysis/test_underpressured_screen.py` |
| Source docs | `docs/data-sources/onshore/state-well-databases/source-catalog.md` |
| Screen report docs | `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md` |

## Deliverable

The approved implementation will create or refresh:

```text
/mnt/ace/worldenergydata/data/modules/oklahoma_occ/
  raw/
    completions-wells-formations-base.xlsx
    completions-wells-formations-data-dictionary.xlsx
    manifest.json
  normalized/
    completions/
      completion_pressure_rows.parquet
  curated/
    pressure/
      well_pressure_observations.parquet
      oklahoma_occ_pressure_observation_quality.json
```

The approved screen run will refresh:

```text
/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/
  well_screen_earliest.parquet
  underpressured_field_ranking.parquet
  screen_summary.json
```

The refreshed screen summary will report Oklahoma counts through
`state_counts`, `source_counts`, `input_row_counts`, `loaded_row_counts`, and
`participation_gate`. It will not add a Hugoton/Panhandle analog validation gate
for Oklahoma until pre-2010/Form 1016 pressure evidence is available.

## Implementation Plan

### Task 1: Add OCC source configuration and manifesting

**Files:**

- Create: `config/oklahoma_occ.yml`
- Create: `src/worldenergydata/modules/state_regulators/oklahoma_occ/__init__.py`
- Create: `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py`
- Test: `tests/unit/modules/state_regulators/test_oklahoma_occ_pipeline.py`

**Interfaces:**

- `load_config(config_path: str | Path) -> dict`
- `download_source(url: str, destination: Path) -> dict`
- `write_manifest(config: dict, base_dir: Path, downloads: list[dict]) -> dict`

**TDD steps:**

1. Write a failing manifest test that stubs two local source files and expects
   `source_url`, `raw_path`, `sha256`, `size_bytes`, `refresh`, and
   `manifest_written_at`.
2. Run:

   ```bash
   pytest tests/unit/modules/state_regulators/test_oklahoma_occ_pipeline.py -q
   ```

   Expected: fail because the Oklahoma package does not exist.
3. Implement the minimal package and manifest writer. `download_source` will use
   `requests` or the standard library with streaming writes and will capture
   `Last-Modified` and `ETag` headers when available.
4. Re-run the focused test and commit only the package/config/test files.

### Task 2: Parse structured OCC completion pressure rows

**Files:**

- Create: `src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py`
- Modify: `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py`
- Test: `tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py`

**Interfaces:**

- `read_completion_workbook(path: str | Path) -> pd.DataFrame`
- `build_pressure_observations(completions: pd.DataFrame, settings: dict) -> pd.DataFrame`
- `build_quality_stats(completions: pd.DataFrame, observations: pd.DataFrame) -> dict`

**TDD steps:**

1. Create tiny in-test Excel fixtures with columns equivalent to the OCC
   dictionary fields needed by the issue: API, well name, operator, county,
   field, formation, completion number, test date, shut-in pressure, flowing
   tubing pressure, gas rate, oil rate, water rate, total depth/TVD/formation
   depth.
2. Write failing tests for:
   - pressure columns coercing to numeric psia/psig fields;
   - `test_year` deriving from `Test_Date`;
   - `reference_depth_ft` selecting TVD/depth in deterministic priority order;
   - rows without both usable pressure and reference depth being excluded from
     curated observations while counted in quality stats.
3. Implement parser constants for OCC column aliases and one explicit
   normalized schema. The parser will fail closed when required columns are
   missing rather than silently changing semantics.
4. Re-run focused parser tests and commit only parser/pipeline/test changes.

### Task 3: Produce curated observations and screen adapter

**Files:**

- Modify: `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py`
- Modify: `src/worldenergydata/analysis/underpressured_screen/observations.py`
- Modify: `config/underpressured_screen.yml`
- Test: `tests/unit/analysis/test_underpressured_observations.py`
- Test: `tests/unit/analysis/test_underpressured_screen.py`

**Interfaces:**

- New screen schema: `oklahoma_occ_completion_v1`
- Curated columns will include the existing screen-required fields:
  `well_key`, `state`, `field`, `test_year`, `pressure_kind`, `pressure_psia`,
  `reference_depth_ft`.

**TDD steps:**

1. Write failing normalizer tests showing `oklahoma_occ_completion_v1` maps OCC
   curated columns to the shared screen contract and preserves `source_name`,
   `era`, and `screen_observation_priority`.
2. Write a failing screen test that includes one Oklahoma fixture input plus
   Kansas/Texas fixture rows and expects `state_counts["OK"]` and
   `source_counts["oklahoma_occ_completions"]`.
3. Implement the OCC normalizer branch and config entry. The config will mark
   Oklahoma as `era: completion_test_2010_present` and add an Oklahoma
   participation gate with `min_wells: 1`.
4. Re-run the focused screen tests and commit only adapter/config/test changes.

### Task 4: Refresh live `/mnt/ace` outputs and documentation

**Files:**

- Modify: `docs/data-sources/onshore/state-well-databases/source-catalog.md`
- Modify: `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`

**TDD/verification steps:**

1. Run the OCC ingest against official direct-source URLs:

   ```bash
   PYTHONPATH=src python -m worldenergydata.modules.state_regulators.oklahoma_occ.pipeline \
     --config config/oklahoma_occ.yml
   ```

2. Verify the `/mnt/ace` outputs exist and quality stats are internally
   consistent:

   ```bash
   python - <<'PY'
   from pathlib import Path
   import json
   import pandas as pd

   base = Path('/mnt/ace/worldenergydata/data/modules/oklahoma_occ')
   obs = pd.read_parquet(base / 'curated/pressure/well_pressure_observations.parquet')
   quality = json.loads((base / 'curated/pressure/oklahoma_occ_pressure_observation_quality.json').read_text())
   assert len(obs) == quality['curated_count']
   assert obs['state'].eq('OK').all()
   assert obs['reference_depth_ft'].gt(0).all()
   assert obs['pressure_psia'].gt(0).all()
   print({'curated_count': len(obs), 'wells': obs['well_key'].nunique()})
   PY
   ```

3. Run the full screen:

   ```bash
   PYTHONPATH=src python -m worldenergydata.analysis.underpressured_screen.screen \
     --config config/underpressured_screen.yml
   ```

4. Update docs with live counts, refresh cadence, `/mnt/ace` paths, and source
   limitations. The docs will explicitly say that Oklahoma production remains
   at OTC and that Form 1016 is deferred to an OCR/imaging issue.
5. Run focused tests, formatting, legal scan, and commit docs plus any live-run
   code/config fixes.

## Verification Plan

Minimum verification before PR:

```bash
pytest tests/unit/modules/state_regulators/test_oklahoma_occ_pipeline.py \
  tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py \
  tests/unit/analysis/test_underpressured_observations.py \
  tests/unit/analysis/test_underpressured_screen.py -q
ruff check src/worldenergydata/modules/state_regulators/oklahoma_occ \
  src/worldenergydata/analysis/underpressured_screen tests/unit/modules/state_regulators \
  tests/unit/analysis
ruff format --check src/worldenergydata/modules/state_regulators/oklahoma_occ \
  src/worldenergydata/analysis/underpressured_screen tests/unit/modules/state_regulators \
  tests/unit/analysis
PYTHONPATH=src python -m worldenergydata.modules.state_regulators.oklahoma_occ.pipeline \
  --config config/oklahoma_occ.yml
PYTHONPATH=src python -m worldenergydata.analysis.underpressured_screen.screen \
  --config config/underpressured_screen.yml
bash scripts/legal/legal-sanity-scan.sh
```

PR closeout will also include GitHub Actions status and an issue comment with
live row counts, files refreshed under `/mnt/ace`, residual source limitations,
and follow-on recommendations.

## Risks and Controls

| Risk | Control |
|---|---|
| OCC workbook schema drifts silently | Dictionary file will be downloaded, hashed, and referenced in quality metadata; parser will fail closed on missing required columns |
| 76 MB XLSX parsing is slow or memory-heavy | Parser will read only required columns where supported and keep raw heavy data out of git |
| Completion pressure is not virgin pressure for all wells | Output will carry `era: completion_test_2010_present` and docs will frame it as structured completion-test evidence, not pre-2010 Panhandle analog validation |
| Same well has multiple formation completions/tests | Curated output will preserve observations and set deterministic earliest/priority fields for the screen |
| Oklahoma production is requested later | This issue will document that OTC is the official production recordkeeper and will defer production acquisition to a separate issue |

## Plan Review Notes

This plan will require explicit user approval before implementation. Do not add
`status:plan-approved` without user approval.
