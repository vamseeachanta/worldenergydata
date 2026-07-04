# Plan: Issue #732 - Texas RRC pressure-screen integration

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/732
**Status:** implemented
**Tier:** T2 (multi-source analysis adapter, config update, live `/mnt/ace` run, tests, docs)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after this
plan is reviewed, pushed, marked `status:plan-review`, and explicitly approved
by the user. The approved implementation will use TDD: tests will be written
before production code for mixed-source normalization, Texas WHP filtering,
earliest-observation selection, summary counts, validation gates, and docs.

### Issue and dependency status

Planning-time issue probes on 2026-07-03 show:

| Issue | State | Current role |
|---|---|---|
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open, `status:needs-plan` | Parent pressure-screen epic |
| [#709](https://github.com/vamseeachanta/worldenergydata/issues/709) | closed, `status:done` | Texas RRC pressure observations now available |
| [#710](https://github.com/vamseeachanta/worldenergydata/issues/710) | closed, stale `status:needs-plan` label | Kansas-first pressure screen implementation |
| [#725](https://github.com/vamseeachanta/worldenergydata/issues/725) | closed, `status:done` | Kansas KGS pressure-observation table |
| [#732](https://github.com/vamseeachanta/worldenergydata/issues/732) | open, `status:needs-plan` | This Texas pressure-screen integration slice |

The next executable slice will be #732, not #707 or #710. #707 is closed and
already has architecture-portfolio code in the repository. #710 has a
Kansas-first implementation but no tracked plan file in this checkout. #732
will extend that existing screen rather than creating a parallel analysis path.

### Parallel work check

Planning-time worktree probes show these related lanes:

| Worktree | Branch | Scope impact |
|---|---|---|
| `/mnt/local-analysis/wt-wed-714-fdas` | `feat/fdas-714-source-agnostic-package` locked | Avoid FDAS/package-generalization changes |
| `/mnt/local-analysis/wt-wed-660` | `feat/onshore-rrc-source-catalog-660` | Avoid source-catalog rewrites |
| `/mnt/local-analysis/wt-wed-661` | `feat/onshore-rrc-refresh-661` | Avoid Texas raw-refresh changes |
| `/mnt/local-analysis/wt-wed-779` | `feat/corpus-datasets-779` | No pressure-screen overlap observed |

Implementation will stay inside the existing `underpressured_screen` analysis
module, its tests, config, and docs.

### Direct-source and `/mnt/ace` inventory

The implementation will consume direct-source outputs already written under the
storage contract. It will not scrape PatchOps, Collide, LinkedIn, commercial
services, or historical third-party scraper code.

| Source | Current direct-source artifact | Planned role |
|---|---|---|
| Kansas KGS #725 | `/mnt/ace/worldenergydata/data/modules/kansas_kgs/curated/pressure/well_pressure_observations.parquet` | Existing Hugoton/Panoma validation source |
| Texas RRC #709 | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/pressure/well_pressure_observations/texas_rrc_well_pressure_observations.parquet` | New Texas screen input |
| Texas RRC #709 quality | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/pressure/well_pressure_observations/texas_rrc_pressure_observation_quality.json` | Source warnings and caveat propagation |
| Existing screen output | `/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/` | Output location to refresh after approval |

Current live evidence:

| Artifact | Rows / coverage | Notes |
|---|---:|---|
| Kansas pressure observations | 39,134 rows | Current screen reduces this to 10,103 earliest wells and 8 ranked fields |
| Texas pressure observations | 48 rows | 25 API14 wells, 8 fields, all `WHP_shut_in` |
| Texas source records | 25 `G-1 Field Data`, 23 `G-10` | Duplicate source observations exist per well and must be resolved by earliest-per-well logic |
| Texas usable proxy rows | 43 rows | `usable_for_virgin_pressure_proxy=True` rows will be eligible for screening |
| Texas earliest flags | 25 rows | One earliest pressure observation per API14 in #709 output |
| Texas top field | 32 rows for `BRISCOE RANCH (EAGLEFORD)` | The Texas daily packet is too narrow to require West Panhandle analog recovery |
| Current screen summary | 10,103 wells, all severe, 264 near-vacuum wells | Kansas-only validation gate currently passes |

Texas #709 quality currently includes:

```json
{
  "candidate_count": 360,
  "curated_count": 48,
  "pressure_kind_counts": {"WHP_shut_in": 48},
  "pressure_unit_basis_counts": {"psig_assumed": 48},
  "source_warnings": [
    "raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z"
  ],
  "w2_pressure_candidates_not_curated": 144
}
```

### Current code shape

The current implementation is intentionally small but assumes a single logical
schema:

- `src/worldenergydata/analysis/underpressured_screen/screen.py`
  - `load_observations()` blindly concatenates parquet inputs and only adds
    `source_name` and `era`.
  - `earliest_per_well()` sorts by `well_key` and `test_year`.
  - `rank_fields()` groups by `field` and aggregates `state`, `era`, and
    pressure-gradient statistics.
  - `run_screen()` writes `well_screen_earliest.parquet`,
    `underpressured_field_ranking.parquet`, and `screen_summary.json`.
- `config/underpressured_screen.yml`
  - currently contains only the Kansas KGS input.
  - comments say Texas joins after #709.
- `tests/unit/analysis/test_underpressured_screen.py`
  - covers BHP estimate, tier boundaries, earliest selection, field ranking,
    and the Kansas analog validation gate.
- `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`
  - is still titled as a Kansas first cut.

The #732 implementation will not change state package outputs. It will adapt
different state-source schemas at the analysis boundary.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex inline | `scripts/review/results/2026-07-03-plan-732-codex-inline.md` |
| New normalizer module | `src/worldenergydata/analysis/underpressured_screen/observations.py` |
| Screen orchestration | `src/worldenergydata/analysis/underpressured_screen/screen.py` |
| Screen config | `config/underpressured_screen.yml` |
| Existing screen tests | `tests/unit/analysis/test_underpressured_screen.py` |
| New normalizer tests | `tests/unit/analysis/test_underpressured_observations.py` |
| Report docs | `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md` |

## Deliverable

The approved implementation will refresh:

```text
/mnt/ace/worldenergydata/data/modules/pressure_screen/curated/
  well_screen_earliest.parquet
  underpressured_field_ranking.parquet
  screen_summary.json
```

The refreshed `screen_summary.json` will include at least:

```json
{
  "wells_screened": 10128,
  "state_counts": {"KS": 10103, "TX": 25},
  "source_counts": {
    "kansas_kgs_proration": 10103,
    "texas_rrc_completion_packets": 25
  },
  "source_warnings": {
    "texas_rrc_completion_packets": [
      "raw_manifest_warning:completion_data:error:2026-07-01T00:36:55Z"
    ]
  },
  "validation_gate": {"passed": true},
  "participation_gate": {"passed": true}
}
```

Exact counts may change if the approved run refreshes direct-source inputs
before execution. The implementation will report the live counts it actually
loads rather than hardcoding the plan-time counts.

## Implementation Plan

### Task 1: Add mixed-source observation normalization

**Files:**

- Create: `src/worldenergydata/analysis/underpressured_screen/observations.py`
- Create: `tests/unit/analysis/test_underpressured_observations.py`
- Modify: `src/worldenergydata/analysis/underpressured_screen/screen.py`

**Interfaces:**

- Produces:
  - `REQUIRED_SCREEN_COLUMNS: tuple[str, ...]`
  - `normalize_observations(frame: pd.DataFrame, input_config: dict) -> pd.DataFrame`
  - `load_observations(inputs: list[dict]) -> tuple[pd.DataFrame, dict]`
- Consumes:
  - input config keys: `name`, `path`, `schema`, `era`, `state`,
    optional `quality_path`, optional `require_usable_proxy`

**TDD steps:**

1. Write failing normalizer tests:

```python
def test_normalizes_texas_pressure_schema_to_screen_contract(tmp_path):
    frame = pd.DataFrame(
        [
            {
                "api14": "42127373050000",
                "field_name": "BRISCOE RANCH (EAGLEFORD)",
                "test_year": 2017,
                "pressure_kind": "WHP_shut_in",
                "pressure_psia": 1046.7,
                "reference_depth_ft": 7394.0,
                "usable_for_virgin_pressure_proxy": True,
                "is_earliest_observation_for_well": True,
                "gradient_method": "surface_pressure_over_reference_depth_screening_only",
            }
        ]
    )
    result = normalize_observations(
        frame,
        {
            "name": "texas_rrc_completion_packets",
            "schema": "texas_rrc_pressure_v1",
            "state": "TX",
            "era": "completion_packet_screening",
            "require_usable_proxy": True,
        },
    )
    assert result.loc[0, "well_key"] == "42127373050000"
    assert result.loc[0, "field"] == "BRISCOE RANCH (EAGLEFORD)"
    assert result.loc[0, "state"] == "TX"
    assert result.loc[0, "source_name"] == "texas_rrc_completion_packets"
    assert result.loc[0, "era"] == "completion_packet_screening"
```

2. Write a failing filter test proving Texas rows with
   `usable_for_virgin_pressure_proxy=False` are excluded when
   `require_usable_proxy=True`.
3. Implement the normalizer with explicit schema branches:
   - `screen_v1`: validate required screen columns and pass through existing
     Kansas-style columns.
   - `texas_rrc_pressure_v1`: map `api14 -> well_key`, `field_name -> field`,
     inject `state`, preserve `api14`, `pressure_kind`, `pressure_psia`,
     `reference_depth_ft`, `gradient_method`, and `test_year`.
4. Replace `screen.load_observations()` with the new loader and return metadata
   for source row counts and optional quality warnings.
5. Run:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest \
  tests/unit/analysis/test_underpressured_observations.py -q
```

Expected result after implementation: all new normalizer tests pass.

### Task 2: Preserve screen behavior while adding source/state summaries

**Files:**

- Modify: `src/worldenergydata/analysis/underpressured_screen/screen.py`
- Modify: `tests/unit/analysis/test_underpressured_screen.py`

**Interfaces:**

- Consumes: `load_observations()` returning `(observations, load_summary)`
- Produces:
  - `run_participation_gate(wells: pd.DataFrame, gate: dict) -> dict`
  - `build_screen_summary(wells, ranking, validation_gate, participation_gate, load_summary) -> dict`

**TDD steps:**

1. Add a failing test that mixed Kansas/Texas earliest rows produce:
   - `state_counts == {"KS": 1, "TX": 1}`
   - `source_counts` separated by source name
   - `era_note` including both `depleted` and `completion_packet_screening`
2. Add a failing test for duplicate Texas observations:

```python
def test_earliest_per_well_uses_texas_api14_well_key():
    screened = make_observations(
        [
            {"well_key": "42127373050000", "state": "TX", "test_year": 2018, "pressure_psia": 1000.0, "reference_depth_ft": 7000.0},
            {"well_key": "42127373050000", "state": "TX", "test_year": 2017, "pressure_psia": 900.0, "reference_depth_ft": 7000.0},
        ]
    )
    wells = earliest_per_well(classify_tiers(estimate_bhp(screened, BHP_SETTINGS), TIERS))
    assert len(wells) == 1
    assert int(wells.loc[0, "test_year"]) == 2017
```

3. Add a failing participation-gate test that requires at least one TX well
   without requiring a Texas severe-underpressure field.
4. Implement summary builders and the participation gate.
5. Keep the existing `run_validation_gate()` behavior unchanged for the Kansas
   analog gate.
6. Run:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest \
  tests/unit/analysis/test_underpressured_screen.py \
  tests/unit/analysis/test_underpressured_observations.py -q
```

Expected result after implementation: existing #710 tests and new #732 tests
pass.

### Task 3: Wire Texas input into config and docs

**Files:**

- Modify: `config/underpressured_screen.yml`
- Modify: `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`

**Config change:**

```yaml
inputs:
  - name: kansas_kgs_proration
    path: /mnt/ace/worldenergydata/data/modules/kansas_kgs/curated/pressure/well_pressure_observations.parquet
    schema: screen_v1
    state: KS
    era: depleted
  - name: texas_rrc_completion_packets
    path: /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/pressure/well_pressure_observations/texas_rrc_well_pressure_observations.parquet
    quality_path: /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/pressure/well_pressure_observations/texas_rrc_pressure_observation_quality.json
    schema: texas_rrc_pressure_v1
    state: TX
    era: completion_packet_screening
    require_usable_proxy: true
```

**Docs update:**

The report will change from "Kansas First Cut" to a multi-state screen report.
It will include:

- Kansas validation results retained as the analog gate.
- Texas participation counts by wells, fields, source record type, and caveats.
- A clear warning that Texas #709 WHP gradients are screening-only and are not
  claimed as measured virgin BHP.
- The #709 raw manifest warning if present in the live run summary.

### Task 4: Run the live `/mnt/ace` screen and verification

**Files:**

- No generated `/mnt/ace` files will be committed to git.
- Commit only source, config, tests, and docs.

**Commands:**

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest \
  tests/unit/analysis/test_underpressured_screen.py \
  tests/unit/analysis/test_underpressured_observations.py -q

PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m \
  worldenergydata.analysis.underpressured_screen.screen \
  --config config/underpressured_screen.yml

scripts/legal/legal-sanity-scan.sh
```

Expected live-run checks:

- `validation_gate.passed == true`
- `participation_gate.passed == true`
- `state_counts` includes both `KS` and `TX`
- `source_counts` includes both configured inputs
- `source_warnings.texas_rrc_completion_packets` carries the #709 raw manifest
  warning if the quality file still reports it

## Out of Scope

The implementation will not:

- alter Texas RRC or Kansas KGS raw/curated package output schemas
- scrape PatchOps, LinkedIn, Collide, commercial vendors, or third-party code
- require Texas West Panhandle recovery from the current 48-row daily packet
- claim WHP-derived Texas gradients are measured virgin BHP
- perform economic, reserves, or field architecture ranking
- commit generated parquet, CSV, JSON, ZIP, or raw datasets under `/mnt/ace`

## Adversarial Review Checklist

- Mixed physical schemas must be normalized before `estimate_bhp()` sees rows.
- Texas rows must not bypass `usable_for_virgin_pressure_proxy`.
- The Kansas Hugoton/Panoma validation gate must remain load-bearing.
- Texas participation must be validated without forcing a false analog result.
- Source warnings from #709 quality JSON must not be dropped in the summary.
- Generated `/mnt/ace` data must remain untracked.
