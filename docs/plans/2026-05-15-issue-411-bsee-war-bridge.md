---
title: "Issue #411 plan — BSEE WAR bridge to restore 2,211-row vessel_fleet baseline"
issue: 411
status: draft
created: 2026-05-15
last_updated: 2026-05-15
---

# Issue #411 Plan — BSEE WAR Bridge

## Gate status

- GitHub issue: [vamseeachanta/worldenergydata#411](https://github.com/vamseeachanta/worldenergydata/issues/411) (created 2026-05-15)
- Local plan status: `draft`
- Implementation status: not started; awaiting adversarial review + user approval.
- Predecessor work: [PR #409](https://github.com/vamseeachanta/worldenergydata/pull/409) merged 2026-05-15T03:36:43Z (Path A vendor merge, 48 rows); [#408](https://github.com/vamseeachanta/worldenergydata/issues/408) closed (hull_estimator sparse-data guard).

## Resource intelligence

Sources consulted:

1. **Issue body** ([#411](https://github.com/vamseeachanta/worldenergydata/issues/411)) — goal, approach, acceptance, cross-references.
2. **Issue [#407](https://github.com/vamseeachanta/worldenergydata/issues/407)** — Path A dry-run + execution research; comments document the 48-row outcome and the BSEE bridge gap explicitly.
3. **`scripts/vessel_fleet/fuse_and_deduplicate.py`** (111 LOC, read 2026-05-15) — fuse pipeline iterates `data/modules/vessel_fleet/raw/*/` subdirs, loads parquet via `ParquetStore`, calls `deduplicate_fleet()`, then `validate_fleet()` + `populate_hull_forms()` + `populate_estimated_dimensions()`. **Architectural insight: the fuse script needs no modification — a new `raw/bsee_war/` source dir picks up automatically.**
4. **Curated CSV schema** (`data/modules/vessel_fleet/curated/drilling_rigs.csv` header, verified 2026-05-15): 14 columns — `VESSEL_NAME, VESSEL_CATEGORY, OWNER, DATA_SOURCE, RIG_DESIGN, WATER_DEPTH_RATING_FT, RIG_TYPE, DATA_SOURCE_URL, HULL_FORM_TYPE, HULL_LIBRARY_REF, LOA_M, BEAM_M, DRAFT_M, DIMENSION_CONFIDENCE`.
5. **WAR pickle existence** verified: `data/modules/bsee/.local/war/war_borehole_view.pkl` (6.0 MB, mtime 2026-02-09). Schema verification deferred to implementation Step 1.5 (slow `uv run` startup).
6. **Prior baseline reference** ([#407 body](https://github.com/vamseeachanta/worldenergydata/issues/407)): 2,211 rows pre-PR, dominantly `DATA_SOURCE=bsee_war`. **The prior baseline already came through this same fuse pipeline** — proves the projection-to-parquet approach worked historically. We are restoring an architectural pattern, not inventing one.
7. **Dedup module** `src/worldenergydata/vessel_fleet/dedup/deduplicator.py` (read scope: confirm precedence rules around `DATA_SOURCE`). Will read during implementation Step 2.
8. **Validator** `src/worldenergydata/vessel_fleet/quality/validator.py` (read scope: confirm BSEE-WAR rows pass schema validation; field-coverage tolerance for rows missing hull dimensions).

**Gaps identified:**

- No `raw/bsee_war/` directory in current fuse-pipeline tree (it would have been there pre-slim per `7493f543` commit).
- No `scripts/vessel_fleet/project_war_to_parquet.py` (or similar) script exists to do the pickle→parquet projection.
- Dedup precedence may need a rule: `DATA_SOURCE=contractor_fleet_page` (vendor-parsed) > `DATA_SOURCE=bsee_war` on rig-name collision. **Verify** the existing `deduplicate_fleet()` already encodes this or needs amendment.

## Evidence (embedded verification)

**Issue statuses** (verified 2026-05-15T~14:00 via `gh issue view`):
- `#411` — OPEN — title "feat(vessel_fleet): BSEE WAR bridge — restore 2,211-row baseline via non-destructive merge"
- `#407` — OPEN — title "research+plan(vessel_fleet): dry-run findings + Noble/Seadrill vendor→curated merge readiness assessment"
- `#408` — CLOSED 2026-05-15T03:36:44Z — title "bug(vessel_fleet): populate_estimated_dimensions crashes…"
- `#409` (PR) — MERGED 2026-05-15T03:36:43Z

**File existence** (`ls -la` 2026-05-15T~14:00):
- EXISTS: `data/modules/bsee/.local/war/war_borehole_view.pkl` (6,020,228 bytes, 2026-02-09)
- EXISTS: `data/modules/vessel_fleet/curated/drilling_rigs.csv` (48 rows post-PR #409)
- EXISTS: `data/modules/vessel_fleet/raw/spec_details/{noble,seadrill}.parquet`
- MISSING (new — this plan creates): `data/modules/vessel_fleet/raw/bsee_war/`
- MISSING (new — this plan creates): `scripts/vessel_fleet/project_war_to_parquet.py`

**Reproduction proofs:** N/A — feature-add scope, not a runtime-failure scope. Plan adds new behavior (BSEE WAR ingestion) rather than fixing broken behavior.

## Approach

**Architecture:** project the WAR pickle to parquet at `data/modules/vessel_fleet/raw/bsee_war/borehole_view.parquet`, then let the existing fuse pipeline pick it up automatically. No fuse-script modification needed unless dedup-precedence requires it.

**Pipeline stages:**

1. **New script: `scripts/vessel_fleet/project_war_to_parquet.py`**
   - Reads `data/modules/bsee/.local/war/war_borehole_view.pkl`
   - Projects per-well rows to per-rig rows (groupby distinct `RIG_NAME` × `OPERATOR`)
   - Maps WAR schema → vessel_fleet schema (14 cols). Unknown vendor-rich cols (`HULL_FORM_TYPE`, `HULL_LIBRARY_REF`, `LOA_M`, `BEAM_M`, `DRAFT_M`) set to None; `DIMENSION_CONFIDENCE = 'unknown'`; `DATA_SOURCE = 'bsee_war'`.
   - Writes to `data/modules/vessel_fleet/raw/bsee_war/borehole_view.parquet`.

2. **Fuse-script invocation (no modification needed)**: `uv run python scripts/vessel_fleet/fuse_and_deduplicate.py` will pick up the new `raw/bsee_war/` source via its existing `raw_dir.iterdir()` loop.

3. **Dedup-precedence verification (modify if needed)**: read `src/worldenergydata/vessel_fleet/dedup/deduplicator.py`; if the precedence rule isn't `contractor_fleet_page > bsee_war`, add it. The 48 vendor-parsed rows from PR #409 MUST persist exactly.

4. **Validator-tolerance verification (modify if needed)**: read `validator.py`; if it rejects rows missing hull dimensions, add a `DATA_SOURCE='bsee_war'` exemption (or relax the rule globally and document in changelog).

## Artifact map

| Artifact | Path |
|---|---|
| This plan | `worldenergydata/docs/plans/2026-05-15-issue-411-bsee-war-bridge.md` |
| New script | `worldenergydata/scripts/vessel_fleet/project_war_to_parquet.py` |
| Possibly modified | `worldenergydata/src/worldenergydata/vessel_fleet/dedup/deduplicator.py` (precedence) |
| Possibly modified | `worldenergydata/src/worldenergydata/vessel_fleet/quality/validator.py` (BSEE-WAR row tolerance) |
| New raw source dir | `worldenergydata/data/modules/vessel_fleet/raw/bsee_war/borehole_view.parquet` |
| Updated curated | `worldenergydata/data/modules/vessel_fleet/curated/drilling_rigs.{csv,parquet}` (regenerated) |
| TDD tests | `worldenergydata/tests/unit/vessel_fleet/test_bsee_war_bridge.py` (new) |
| Plan review — Claude | `scripts/review/results/2026-05-15-plan-411-claude.md` |
| Plan review — Codex | `scripts/review/results/2026-05-15-plan-411-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-05-15-plan-411-gemini.md` |

## Pseudocode

```
function project_war_to_parquet(war_pkl_path, out_parquet_path):
    df_well = pd.read_pickle(war_pkl_path)
    # WAR pickle is per-well-report — collapse to per-rig
    df_rig = (df_well
              .groupby(['RIG_NAME', 'OPERATOR'], dropna=True)
              .agg(spud_count=('SPUD_DATE', 'count'),
                   latest_spud=('SPUD_DATE', 'max'),
                   water_depth_max=('WATER_DEPTH_FT', 'max'))
              .reset_index())
    # Project to vessel_fleet schema
    df_out = pd.DataFrame({
        'VESSEL_NAME': df_rig['RIG_NAME'],
        'VESSEL_CATEGORY': 'drilling_rig',
        'OWNER': df_rig['OPERATOR'],  # NB: WAR OPERATOR = lease holder, not rig contractor; document this caveat
        'DATA_SOURCE': 'bsee_war',
        'RIG_DESIGN': None,
        'WATER_DEPTH_RATING_FT': df_rig['water_depth_max'],
        'RIG_TYPE': None,
        'DATA_SOURCE_URL': 'https://www.data.bsee.gov/Main/RawData.aspx',
        'HULL_FORM_TYPE': None,
        'HULL_LIBRARY_REF': None,
        'LOA_M': None,
        'BEAM_M': None,
        'DRAFT_M': None,
        'DIMENSION_CONFIDENCE': 'unknown',
    })
    df_out.to_parquet(out_parquet_path, index=False)
    return len(df_out)
```

## Files to change

| Action | Path | Reason |
|---|---|---|
| Create | `scripts/vessel_fleet/project_war_to_parquet.py` | WAR pickle → parquet projection |
| Create | `data/modules/vessel_fleet/raw/bsee_war/borehole_view.parquet` | Pipeline-stage output (script generates) |
| Modify (maybe) | `src/worldenergydata/vessel_fleet/dedup/deduplicator.py` | Precedence: contractor_fleet_page > bsee_war |
| Modify (maybe) | `src/worldenergydata/vessel_fleet/quality/validator.py` | Tolerate WAR-row missing-dimension fields |
| Create | `tests/unit/vessel_fleet/test_bsee_war_bridge.py` | TDD coverage |
| Regenerate | `data/modules/vessel_fleet/curated/drilling_rigs.{csv,parquet}` | Fuse output after WAR is added |
| Update | `docs/plans/README.md` | Plan index entry |

## TDD test list

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_project_war_schema` | Output parquet has exactly the 14 vessel_fleet columns | WAR pickle | 14-col DataFrame |
| `test_project_war_row_count` | Output row count is within tolerance of historical baseline | WAR pickle | rows ≥ 2,100 (baseline 2,211 minus drift) |
| `test_project_war_data_source_tag` | All output rows carry `DATA_SOURCE='bsee_war'` | WAR pickle | 100% match |
| `test_fuse_preserves_48_vendor_rows` | After fuse-with-WAR, all 48 Noble+Seadrill rows from PR #409 persist exactly | Raw spec_details + raw bsee_war | 48 rows present with identical field values |
| `test_fuse_row_count_target` | Final curated row count ≥2,159 (= baseline – dedup overlap) | Full raw tree | ≥2,159 rows |
| `test_dedup_precedence_vendor_wins` | When vendor row and BSEE-WAR row collide on RIG_NAME, vendor row wins (DIMENSION_CONFIDENCE not regressed) | Synthetic collision fixture | Vendor row retained |

**Reproduction proofs:** Not applicable — this is feature-add scope. Marked `N/A — feature-add, not runtime-failure scope` per template Step 1.5 skip-allowed rules.

## Acceptance criteria

- [ ] `scripts/vessel_fleet/project_war_to_parquet.py` exists, with module docstring referencing WAR pickle path + projection rules
- [ ] Running the script produces `data/modules/vessel_fleet/raw/bsee_war/borehole_view.parquet` (≥2,100 rows)
- [ ] Running `scripts/vessel_fleet/fuse_and_deduplicate.py` then produces `curated/drilling_rigs.csv` with ≥2,159 rows
- [ ] All 48 vendor-parsed rows from PR #409 persist with identical field values (regression-locked by TDD test)
- [ ] Dedup precedence rule (vendor > BSEE-WAR) verified by TDD test
- [ ] `uv run pytest tests/unit/vessel_fleet/` passes (824-pass baseline preserved + 6 new tests)
- [ ] Plan + adversarial review artifacts posted to `scripts/review/results/2026-05-15-plan-411-*.md`
- [ ] PR opened with both the script + regenerated curated CSV; reviewer can confirm 48 vendor rows persist

## Risks and open questions

- **Risk:** WAR pickle schema may differ from assumption (per-well-report vs per-rig-aggregation). Mitigation: Step 1.5 of implementation does the schema check via `uv run python -c "import pickle; …"` before writing the projection script. If schema differs, projection logic must be revised — flag as MAJOR rework if more than column-rename adjustments needed.
- **Risk:** `OPERATOR` field semantic mismatch — WAR's `OPERATOR` is the lease holder, not the rig contractor. The vendor rows' `OWNER` field is the rig contractor. Setting `OWNER = WAR.OPERATOR` is **semantically incorrect** but consistent with the prior baseline (which used the same projection per the slim-repo snapshot). Surface this in adversarial review; if reviewer flags as MAJOR, add an `OWNER='unknown'` for WAR rows instead.
- **Risk:** Validator rejection of WAR rows missing hull dimensions could break fuse. Mitigation: read validator first; if rejection is strict, add `DATA_SOURCE` exemption or relax globally with changelog note.
- **Risk:** Dedup may drop vendor rows if BSEE-WAR row has same RIG_NAME but slightly different OWNER spelling (e.g., "Noble" vs "Noble Corporation plc"). Mitigation: TDD test on synthetic collision fixture.
- **Risk:** WAR data is 2026-02-08 snapshot; refresh is out of scope here but may diverge from live BSEE data when the next refresh lands. Mitigation: document in script docstring.
- **Open:** Should the projection script be one-shot or part of the regular fuse cron? Recommend one-shot for now; promote to cron in a follow-up after the schema is validated in production.

## Complexity: T2

**T2** — one new script (~80 LOC), possibly two small modifications to existing modules (dedup + validator), six new TDD tests, no major architectural change. The fuse-script-unmodified property of this design keeps blast radius small.

## Adversarial review summary

**Round 1 — 2026-05-15** (single-author Claude fallback per [[feedback_permission_gate_blocks_cross_review]])

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | **MAJOR** | (1) **Wrong source-data file:** plan assumes `war_borehole_view.pkl` contains rig metadata. Live inspection shows it's per-borehole data (54,701 × 7 cols: `API_WELL_NUMBER, BOTM_LEASE_NUM, WELL_SPUD_DATE, TOTAL_DEPTH_DATE, BOREHOLE_STAT_DT, BH_TOTAL_MD, WELL_BORE_TVD`) — NO rig name, NO operator, NO water depth. Correct source: `data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin`. (2) **Scripts already exist:** `scripts/vessel_fleet/export_war_to_vessel_fleet.py` + `scripts/build_rig_fleet_from_war.py` + `src/worldenergydata/vessel_fleet/exporters/war_export.py` — plan proposed creating `project_war_to_parquet.py` from scratch. (3) **Dedup precedence already encoded:** `deduplicator.py:14` has `"bsee_war": 1` rank — vendor sources win on collision by existing design. (4) **Prior-bug surface not flagged:** WRK-104 review documents RIG_NAME bug and `pickle.load` no-try/except in the existing scripts; plan's risk section doesn't mention. |
| Codex | — | not run (plan needs revision before second-provider review is worth running) |

**Overall result:** NOT APPROVAL-READY. Plan must be substantially revised. Local plan-file status STAYS at `draft` per `issue-planning-mode` skill §"For new or recovered plan drafts, keep the local plan file status conservative as `draft` until actual provider artifacts exist."

**Revision direction:** Scope shrinks from T2 ("build new bridge") to T1 ("wire/execute existing bridge"). Five-step concrete revision: (a) run `scripts/build_rig_fleet_from_war.py` if `rig_fleet_full.bin` stale; (b) run `scripts/vessel_fleet/export_war_to_vessel_fleet.py` to populate `raw/bsee_war/war_fleet.parquet`; (c) run `scripts/vessel_fleet/fuse_and_deduplicate.py` to regenerate curated CSV; (d) verify 48 vendor rows persist + observe BSEE row count (don't pre-commit a target); (e) address WRK-104 RIG_NAME int-input bug if it fires, otherwise defer to follow-up.

Review artifact: [scripts/review/results/2026-05-15-plan-411-claude.md](https://github.com/vamseeachanta/workspace-hub/blob/main/scripts/review/results/2026-05-15-plan-411-claude.md) (in workspace-hub repo).
