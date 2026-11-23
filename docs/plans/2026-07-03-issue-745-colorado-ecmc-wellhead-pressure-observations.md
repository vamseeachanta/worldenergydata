# Plan: Issue #745 - Colorado ECMC wellhead-pressure observations

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/745
**Status:** implemented
**Tier:** T2 (new direct-source state ingest, `/mnt/ace` raw snapshot, curated pressure observations, screen integration, docs)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will start from `origin/main` after this plan is reviewed,
pushed, marked `status:plan-review`, and explicitly approved by the user. The
approved implementation will use TDD: tests will be written before production
code for ECMC source manifesting, production CSV parsing, API/depth/field joins,
pressure-kind semantics, curated observation quality stats, screen
normalization, live `/mnt/ace` refresh, and docs.

### Issue and dependency status

Planning-time issue probes on 2026-07-03 indicate:

| Issue | State | Current role |
|---|---|---|
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open, `status:needs-plan` | Parent pressure-screen epic |
| [#709](https://github.com/vamseeachanta/worldenergydata/issues/709) | closed, `status:done` | Texas RRC pressure observations |
| [#725](https://github.com/vamseeachanta/worldenergydata/issues/725) | closed, `status:done` | Kansas KGS pressure observations |
| [#732](https://github.com/vamseeachanta/worldenergydata/issues/732) | closed, `status:done` | Multi-state screen foundation |
| [#740](https://github.com/vamseeachanta/worldenergydata/issues/740) | closed, `status:done` | Oklahoma OCC completion pressures |
| [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) | open, `status:needs-plan` | This Colorado ECMC direct-source slice |

[#745](https://github.com/vamseeachanta/worldenergydata/issues/745) will extend
the existing pressure-observation and screen contracts rather than creating a
parallel analysis path.

### Parallel work check

Planning-time worktree probes show other active worktrees for Texas RRC source
catalog, Texas RRC refresh, FDAS, corpus datasets, pages, field equipment, and
autorun lanes. This issue will avoid those scopes. It will stay inside:

- `src/worldenergydata/modules/state_regulators/colorado_ecmc/`
- `src/worldenergydata/analysis/underpressured_screen/observations.py`
- `config/colorado_ecmc.yml`
- `config/underpressured_screen.yml`
- focused unit tests and onshore pressure-screen docs

### Direct-source evidence

Official ECMC evidence checked on 2026-07-03:

| Source | Planning-time evidence | Implementation use |
|---|---|---|
| 2025 production CSV | `https://ecmc.state.co.us/documents/data/downloads/production/2025_prod_reports.csv`; HEAD 200, `content-length: 157411313`, `last-modified: Tue, 17 Feb 2026 17:42:14 GMT` | Initial annual production-pressure snapshot |
| Rolling monthly production CSV | `https://ecmc.state.co.us/documents/data/downloads/production/monthly_prod.csv`; HEAD 200, `content-length: 62020211`, `last-modified: Fri, 12 Jun 2026 17:04:34 GMT` | Current-year rolling refresh source |
| Wells shapefile | `https://ecmc.state.co.us/documents/data/downloads/gis/WELLS_SHP.ZIP`; HEAD 200, `content-length: 15747535`, `last-modified: Thu, 02 Jul 2026 12:48:36 GMT` | API, field, max TVD/MD, location reference |
| Production header sample | Range sample of `2025_prod_reports.csv` and `monthly_prod.csv` shows `GasPressureTubing`, `GasPressureCasing`, `WaterPressureTubing`, `WaterPressureCasing` | Parser contract and pressure-kind policy |
| Wells schema sample | Temporary inspection of `WELLS_SHP.ZIP` shows `API`, `API_County`, `API_Seq`, `API_Label`, `Field_Code`, `Field_Name`, `Facil_Id`, `Max_MD`, `Max_TVD`, `Latitude`, `Longitude` | Join and denominator contract |

The implementation will use official ECMC static download URLs only. It will
not use PatchOps, LinkedIn, commercial data vendors, or third-party scraper
output.

### Source bounds

The initial implementation will cover structured ECMC Form 7 production-report
wellhead pressure columns. It will support configurable annual production
years, and the first live run will use 2025 plus `monthly_prod.csv` to keep the
initial direct-source slice bounded while proving the parser and screen path.

It will not attempt:

- full 1999-present backfill by default;
- per-well COGIS Form 5A initial-test scraping;
- Bradenhead/Form 17 imaged forms;
- measured BHP claims from tubing/casing/wellhead pressure columns;
- field-development architecture modeling beyond the existing screen outputs.

Those lanes require separate source-volume, scraping, OCR, or interpretation
decisions and will be tracked outside [#745](https://github.com/vamseeachanta/worldenergydata/issues/745).

### Schema and interpretation contract

The curated output will follow the screen-required observation contract:

```text
well_key, state, field, test_year, pressure_kind, pressure_psia,
reference_depth_ft
```

Colorado-specific policy:

- `well_key` will use ECMC API12 when `ApiCountyCode`, `ApiSequenceNumber`, and
  `ApiSidetrack` are present in the production source. If a production row
  lacks a defensible API12, the parser will fall back to `FacilityId` for
  normalized rows but will not compute a curated gradient until a unique well
  reference join is available.
- `api12` will be normalized as `05` + three-digit county + five-digit sequence
  + two-digit sidetrack. `api10` will omit sidetrack. The parser will preserve
  raw API parts for audit.
- `field` will prefer the wells shapefile `Field_Name`, falling back to
  production `FormationCode` only as a named formation/proxy field and with a
  quality flag.
- `reference_depth_ft` will prefer `Max_TVD`, then `Max_MD` from the ECMC wells
  shapefile. No gradient will be computed without a positive reference depth.
- `GasPressureTubing` will map to `pressure_kind=WHP_flowing_tubing`.
- `GasPressureCasing` will map to `pressure_kind=WHP_casing`.
- `WaterPressureTubing` and `WaterPressureCasing` will be normalized as pressure
  candidates and counted in quality stats, but they will not become curated
  under-pressured gas-screen observations in v1.
- Surface pressure values will be treated as gauge pressure for screening, with
  `pressure_psia = pressure_raw_psi + 14.7`. Outputs will retain
  `pressure_psig_reported`, `pressure_kind`, and `gradient_method` caveats.
- `test_date` will be derived from `ReportYear`/`ReportMonth`, with month-end
  dates used only as ordering metadata. `test_year` will drive screen grouping.
- Earliest-observation flags will prefer earliest positive gas-pressure
  observation by `well_key`, then pressure-priority order
  `GasPressureTubing`, `GasPressureCasing`, then source row order.

### Current code shape

Relevant existing patterns:

- `src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py`
  writes official direct-source raw files, manifest JSON, normalized parquet,
  curated parquet, and quality JSON under `/mnt/ace`.
- `src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py`
  isolates source parsing from pipeline orchestration and fail-closes on
  missing required columns.
- `src/worldenergydata/analysis/underpressured_screen/observations.py`
  normalizes source-specific schemas to the screen contract and will receive a
  Colorado ECMC adapter.
- `config/underpressured_screen.yml` already models per-source entries with
  `name`, `path`, `schema`, `state`, `era`, and optional quality metadata.
- `docs/data-sources/onshore/state-well-databases/source-catalog.md` already
  identifies Colorado as the next high-value pressure-screen source after
  Kansas and Oklahoma.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex inline | `scripts/review/results/2026-07-03-plan-745-codex-inline.md` |
| Code review - Codex inline | `scripts/review/results/2026-07-03-code-745-codex-inline.md` |
| New config | `config/colorado_ecmc.yml` |
| New package | `src/worldenergydata/modules/state_regulators/colorado_ecmc/` |
| New package tests | `tests/unit/modules/state_regulators/test_colorado_ecmc_*.py` |
| Observation normalizer | `src/worldenergydata/analysis/underpressured_screen/observations.py` |
| Screen config | `config/underpressured_screen.yml` |
| Screen tests | `tests/unit/analysis/test_underpressured_observations.py`, `tests/unit/analysis/test_underpressured_screen.py` |
| Source docs | `docs/data-sources/onshore/state-well-databases/source-catalog.md` |
| Screen report docs | `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md` |

## Deliverable

The approved implementation will create or refresh:

```text
/mnt/ace/worldenergydata/data/modules/colorado_ecmc/
  raw/
    production/
      2025_prod_reports.csv
      monthly_prod.csv
    wells/
      WELLS_SHP.ZIP
    manifest.json
  normalized/
    production/
      production_pressure_rows.parquet
    wells/
      wells.parquet
  curated/
    pressure/
      well_pressure_observations.parquet
      colorado_ecmc_pressure_observation_quality.json
```

The approved screen run will refresh:

```text
/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/
  well_screen_earliest.parquet
  underpressured_field_ranking.parquet
  screen_summary.json
```

The refreshed screen summary will report Colorado counts through
`state_counts`, `source_counts`, `input_row_counts`, `loaded_row_counts`, and
`participation_gate`. It will not add a Colorado analog validation gate until
the late-life production-pressure behavior is calibrated against known
Colorado basin-centered-gas examples.

## Implementation Plan

### Task 1: Add ECMC source configuration and manifesting

**Files:**

- Create: `config/colorado_ecmc.yml`
- Create: `src/worldenergydata/modules/state_regulators/colorado_ecmc/__init__.py`
- Create: `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_pipeline.py`

**Interfaces:**

- `load_config(config_path: str | Path) -> dict`
- `configured_sources(config: dict) -> list[dict]`
- `download_source(url: str, destination: str | Path, timeout: int = 120) -> dict`
- `write_manifest(config: dict, base_dir: str | Path, downloads: list[dict]) -> dict`

**TDD steps:**

1. Write a failing config/source expansion test that expects `production_2025`,
   `production_monthly`, and `wells_shapefile` entries with direct ECMC URLs,
   raw paths, source type, refresh cadence, and `required_columns`.
2. Write a failing manifest test that stubs three local downloads and expects
   `source_url`, `raw_path`, `sha256`, `size_bytes`, `refresh`,
   `last_modified`, `etag`, `downloaded_at`, and `manifest_written_at`.
3. Run:

   ```bash
   PYTHONPATH=src:packages/worldenergydata-core/src pytest \
     tests/unit/modules/state_regulators/test_colorado_ecmc_pipeline.py -q
   ```

   Expected: fail because the Colorado package does not exist.
4. Implement the minimal package, config loader, source expansion, streaming
   downloader, and manifest writer.
5. Re-run the focused pipeline test and commit only the config/package/test
   files.

### Task 2: Parse ECMC production and wells sources

**Files:**

- Create: `src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py`
- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_parsers.py`

**Interfaces:**

- `read_production_csv(path: str | Path, settings: dict) -> pd.DataFrame`
- `read_wells_shapefile(path: str | Path) -> pd.DataFrame`
- `normalize_api_parts(frame: pd.DataFrame) -> pd.DataFrame`

**TDD steps:**

1. Create tiny CSV fixtures with ECMC production columns:
   `DocNum`, `ReportMonth`, `ReportYear`, `FacilityId`, `ApiCountyCode`,
   `ApiSequenceNumber`, `ApiSidetrack`, `Well`, `FormationCode`,
   `GasPressureTubing`, `GasPressureCasing`, `WaterPressureTubing`,
   `WaterPressureCasing`, `GasProduced`, `DaysProduced`.
2. Create a tiny shapefile ZIP fixture using `pyshp` with wells fields:
   `API`, `API_County`, `API_Seq`, `API_Label`, `Field_Code`, `Field_Name`,
   `Facil_Id`, `Max_MD`, `Max_TVD`, `Latitude`, `Longitude`.
3. Write failing tests for:
   - API12/API10 normalization from production API parts;
   - numeric coercion of gas/water pressure columns;
   - `test_date` derivation from report month/year;
   - wells shapefile parsing of `Field_Name`, `Max_TVD`, `Max_MD`, and
     `Facil_Id`;
   - fail-closed behavior when required production or wells columns are absent.
4. Implement the parser constants and typed DataFrames.
5. Re-run focused parser tests and commit only parser/pipeline/test changes.

### Task 3: Build curated Colorado pressure observations

**Files:**

- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py`
- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py`

**Interfaces:**

- `build_pressure_observations(production: pd.DataFrame, wells: pd.DataFrame, settings: dict) -> pd.DataFrame`
- `build_quality_stats(production: pd.DataFrame, wells: pd.DataFrame, observations: pd.DataFrame, settings: dict) -> dict`

**TDD steps:**

1. Write failing tests showing `GasPressureTubing` becomes
   `WHP_flowing_tubing` and `GasPressureCasing` becomes `WHP_casing`, with
   `pressure_psia = pressure_psig_reported + atmospheric_psi`.
2. Write a failing test showing water-pressure columns are counted in quality
   stats but excluded from curated gas-screen observations.
3. Write a failing test showing reference depth chooses `Max_TVD` first, then
   `Max_MD`, and excludes rows without a positive depth.
4. Write a failing test showing earliest observation per well is selected by
   earliest month/year and deterministic pressure priority.
5. Implement observation construction, join-quality flags, output schema, and
   quality JSON stats.
6. Re-run focused observation tests and commit only observation/pipeline/test
   changes.

### Task 4: Add Colorado to the under-pressured screen

**Files:**

- Modify: `src/worldenergydata/analysis/underpressured_screen/observations.py`
- Modify: `config/underpressured_screen.yml`
- Test: `tests/unit/analysis/test_underpressured_observations.py`
- Test: `tests/unit/analysis/test_underpressured_screen.py`

**Interfaces:**

- New screen schema: `colorado_ecmc_production_v1`

**TDD steps:**

1. Write a failing normalizer test showing `colorado_ecmc_production_v1` maps
   Colorado curated columns to the shared screen contract and preserves
   `source_name`, `era`, `screen_observation_priority`, and `state=CO`.
2. Write a failing screen summary test that includes Colorado fixture rows plus
   Kansas/Texas/Oklahoma rows and expects `state_counts["CO"]`,
   `source_counts["colorado_ecmc_production"]`, and a Colorado participation
   gate entry.
3. Implement the Colorado normalizer branch and config entry:

   ```yaml
   - name: colorado_ecmc_production
     path: /mnt/ace/worldenergydata/data/modules/colorado_ecmc/curated/pressure/well_pressure_observations.parquet
     quality_path: /mnt/ace/worldenergydata/data/modules/colorado_ecmc/curated/pressure/colorado_ecmc_pressure_observation_quality.json
     schema: colorado_ecmc_production_v1
     state: CO
     era: production_report_late_life
   ```

4. Add `CO: {min_wells: 1}` to the participation gate.
5. Re-run focused screen tests and commit only adapter/config/test changes.

### Task 5: Refresh live `/mnt/ace` outputs and documentation

**Files:**

- Modify: `docs/data-sources/onshore/state-well-databases/source-catalog.md`
- Modify: `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`

**TDD/verification steps:**

1. Run the ECMC ingest against official direct-source URLs:

   ```bash
   PYTHONPATH=src:packages/worldenergydata-core/src python3.12 \
     -m worldenergydata.modules.state_regulators.colorado_ecmc.pipeline \
     --config config/colorado_ecmc.yml
   ```

2. Verify `/mnt/ace` outputs exist and quality stats are internally
   consistent:

   ```bash
   PYTHONPATH=src:packages/worldenergydata-core/src python3.12 - <<'PY'
   from pathlib import Path
   import json
   import pandas as pd

   base = Path('/mnt/ace/worldenergydata/data/modules/colorado_ecmc')
   obs = pd.read_parquet(base / 'curated/pressure/well_pressure_observations.parquet')
   quality = json.loads((base / 'curated/pressure/colorado_ecmc_pressure_observation_quality.json').read_text())
   assert len(obs) == quality['curated_count']
   assert obs['state'].eq('CO').all()
   assert obs['reference_depth_ft'].gt(0).all()
   assert obs['pressure_psia'].gt(0).all()
   print({'curated_count': len(obs), 'wells': obs['well_key'].nunique()})
   PY
   ```

3. Run the full screen:

   ```bash
   PYTHONPATH=src:packages/worldenergydata-core/src python3.12 \
     -m worldenergydata.analysis.underpressured_screen.screen \
     --config config/underpressured_screen.yml
   ```

4. Update docs with live Colorado counts, refresh cadence, `/mnt/ace` paths,
   pressure-kind caveats, and source limitations.
5. Run focused tests, black/isort, ruff, legal scan, and commit docs plus any
   live-run code/config fixes.

## Verification Plan

Minimum verification before PR:

```bash
PYTHONPATH=src:packages/worldenergydata-core/src pytest \
  tests/unit/modules/state_regulators/test_colorado_ecmc_pipeline.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_parsers.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py \
  tests/unit/analysis/test_underpressured_observations.py \
  tests/unit/analysis/test_underpressured_screen.py -q --no-cov
.venv/bin/black --check --diff src/ tests/
.venv/bin/isort --check-only --diff src/ tests/
ruff check src/worldenergydata/modules/state_regulators/colorado_ecmc \
  src/worldenergydata/analysis/underpressured_screen tests/unit/modules/state_regulators \
  tests/unit/analysis
ruff format --check src/worldenergydata/modules/state_regulators/colorado_ecmc \
  src/worldenergydata/analysis/underpressured_screen tests/unit/modules/state_regulators \
  tests/unit/analysis
PYTHONPATH=src:packages/worldenergydata-core/src python3.12 \
  -m worldenergydata.modules.state_regulators.colorado_ecmc.pipeline \
  --config config/colorado_ecmc.yml
PYTHONPATH=src:packages/worldenergydata-core/src python3.12 \
  -m worldenergydata.analysis.underpressured_screen.screen \
  --config config/underpressured_screen.yml
bash scripts/legal/legal-sanity-scan.sh
```

PR closeout will also include GitHub Actions status and an issue comment with
live row counts, files refreshed under `/mnt/ace`, residual source limitations,
and follow-on recommendations.

## Risks and Controls

| Risk | Control |
|---|---|
| ECMC CSV schema drifts silently | Parser will fail closed on missing required pressure/API/date columns and quality JSON will record source headers |
| The 2025 annual CSV is 157 MB and historical backfill is multi-GB | Config will support selected years; v1 live run will use 2025 plus rolling monthly only |
| Pressure columns are wellhead/casing/tubing, not BHP | Curated rows will use `WHP_*` pressure kinds, `era: production_report_late_life`, and screening-only gradient methods |
| Water pressure columns could contaminate gas under-pressure screen | Water pressure fields will be normalized/counted but excluded from curated gas-screen observations in v1 |
| Wells shapefile joins can be ambiguous by API or FacilityId | Curated gradients will require a unique reference join and positive TVD/MD; ambiguous joins will be counted but excluded from screen-ready rows |
| `monthly_prod.csv` overlaps annual files | De-duplication will use source priority and row identity (`DocNum`, report month/year, API/FacilityId, pressure kind); quality stats will count dropped duplicates |

## Plan Review Notes

This plan requires explicit user approval before implementation. Do not add
`status:plan-approved` without user approval.
