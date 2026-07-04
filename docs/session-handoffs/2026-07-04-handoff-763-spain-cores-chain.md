# Session handoff — continue worldenergydata #763 (Spain CORES chain)

You are picking up an in-progress, **user-approved** implementation. Mission: finish the Spain CORES field-development chain (#763) and land it, following the pattern already merged for Norway (#716). Work in the existing worktree; do NOT re-plan (plan is approved) — implement.

## Preflight (run first, verify state)
```
cd /mnt/local-analysis/wt-wed-763-spain
git rev-parse --abbrev-ref HEAD          # expect: feat/spain-763-cores-chain
git log origin/main..HEAD --oneline      # expect: one WIP commit (handoff + spain parser skeleton)
git status --short                        # expect: clean (WIP committed)
gh issue view 763 --repo vamseeachanta/worldenergydata --json labels --jq '[.labels[].name]|join(",")'  # status:plan-approved
gh issue view 763 --repo vamseeachanta/worldenergydata --comments | tail -140   # plan v2 (canonical) + review evidence
```
Read plan v2 (the #763 comment dated 2026-07-04, grounded in the real CORES XLSX). Mirror the merged Norway chain: `packages/worldenergydata-sodir/src/worldenergydata/sodir/{field_concept.py,reference_chain.py}` and `.../production/unified/adapters/sodir_adapter.py` (the DI-loader real path).

## Already done (verified + committed on the branch — do not redo)
- **`packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py`** — the CORES XLSX parser. `parse_cores_frame(raw, product="oil"|"gas")` is a pure DataFrame transform: wide→long melt over per-field columns, drops annual `Total`/`total` rows + no-year tail rows (positive-int Year filter), converts **oil tonnes→bbl (×7.33, `TONNES_TO_BBL`)** and **gas GWh→Mcf (×3290, `GWH_TO_MCF`)**. `CoresProductionLoader(product=, path=|raw_frame=)` wraps `read_excel`. **Logic verified** (melt + row-drop + both unit conversions) against a synthetic frame; NOT yet importable as a member (needs packaging below).
- `spain/__init__.py`, `spain/production/__init__.py` placeholders exist.
- This handoff doc.

## Remaining work (do in order)

### 763a — ingest (make the member real)
1. `packages/worldenergydata-spain/pyproject.toml` — mirror `packages/worldenergydata-sodir/pyproject.toml`: name `worldenergydata-spain`, deps `worldenergydata-core` + `pandas` + `openpyxl`, `[tool.setuptools.packages.find] include=["worldenergydata.spain*"]`, `namespaces=true`, README.
2. Root `pyproject.toml` — add `"worldenergydata-spain"` to `[project.dependencies]` AND `worldenergydata-spain = { workspace = true }` to `[tool.uv.sources]` (see how `worldenergydata-sodir` is listed).
3. `mkdocs.yml` — add `- packages/worldenergydata-spain/src` (alphabetical).
4. Single `uv lock` (review diff: only worldenergydata-spain added, no version churn).
5. Committed **Ayoluengo oil fixture** (real, public — the oil field with the longest history, onshore Burgos). Either a tiny real XLSX slice OR (simpler) a CSV/parquet the loader reads; the loader test can also use `raw_frame=` DI. Record attribution provenance (`source_url` https://www.cores.es/en/estadisticas + `_metadata.json`; CORES is attribution-licence, not CC-BY).
6. Loader tests under `tests/unit/spain/` — assert melt, Total/no-year drop, tonnes→bbl + GWh→Mcf factors. Self-contained.

### 763b — chain (mirror #716)
7. `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py` — `SpainCoresAdapter(AbstractProductionAdapter)`, `region="spain"`, DI-loader like `SodirAdapter`; `_loader_to_standard_columns` sets `region="spain"`, `source="cores"`, **`water_bbl`/`condensate_bbl` = NaN** (CORES has neither). Bare `SpainCoresAdapter()` default should load the committed fixture (not synthetic).
8. Register in **3 places**: `production/unified/router.py` (REGION_ALIASES `"spain"`/`"cores"` + `_adapters` dict + import), `production/unified/adapters/__init__.py` (import + `__all__`), `tests/unit/production/unified/test_adapters.py` (`_ALL_ADAPTERS` list — drives the parametrized conformance suite; adapter must self-populate non-empty).
9. `spain/field_concept.py` — sparse `FieldMetaMapping` (name + constant `region` + `data_source="cores"`); **onshore→dev_system `"dry"`** default (CORES has no water depth → `dev_system_from_water_depth_m(None)="unknown"`; do NOT let it fall to `"subsea15"`, which pulls a phantom $300MM offshore host — Ayoluengo is onshore). Import F2 from `worldenergydata.fdas.adapters.field_concept_normalizer` (member→root runtime pattern, no declared dep).
10. `spain/reference_chain.py` — mirror `sodir/reference_chain.py`'s `run_*_reference_chain`; economics labeled `chain_plumbing_pre_tax` AND add **`onshore_model_mismatch: true`** to the returned metrics. NOTE: cashflow models OIL revenue only → use an OIL field (Ayoluengo/Casablanca); gas fields are degenerate.
11. Chain tests under `tests/unit/spain/`.

### Close out
12. Follow-ons to FILE (linked to epic #713): live CORES XLSX download lane; per-field crude density/API table (7.33 default is approximate — Ayoluengo crude heavier); gas-revenue modeling; scheduler `SpainCoresRefreshJob`; HTML report. (Plan v2 lists these.)
13. `scripts/legal/legal-sanity-scan.sh` clean; commit; push; open PR `Closes #763`; merge via the ruleset dance (below).

## Critical gotchas / recipes (this repo, this box)
- **Run tests via the synced venv, NOT `uv run`.** `uv run pytest` full-copy re-syncs 231 pkgs (~6 min) EVERY call; and `tests/conftest.py` HANGS on a fresh worktree (waits on absent BSEE `make data`). Use: `.venv/bin/python -m pytest <paths> --noconftest -o addopts="" -q` (2–40s). Keep new tests self-contained (no repo fixtures/data). CI runs the full conftest path fine.
- **Fresh worktree has no `.venv`** → one `uv sync` (~6 min, `UV_LINK_MODE=copy` fallback) after adding the member to root pyproject; then use `.venv/bin/python` directly.
- **black/isort/flake8 are NOT in the venv** — use `/home/vamsee/.local/bin/black` + `/home/vamsee/.local/bin/isort` (read the repo pyproject config). Remove unused imports (flake8 F401 fails Lint CI).
- **PR-title CI rule**: subject after `type(scope):` must be ≤80 chars.
- **Merge = ruleset dance**: `protect_repo` ruleset is `strict` (branch must be up-to-date) with EMPTY bypass_actors → `--admin` CANNOT bypass; main moves fast. Enable `gh pr merge <N> --squash --delete-branch --auto` then run a park-until-quiet babysit (poll main; when quiet ~10 min AND branch behind, `git merge origin/main --no-edit && git push`; auto-merge lands it). Agent cannot self-merge; the `--auto` enable is the mechanism.
- **Parallel sessions are active** on this repo (#717/#718 chains, insights work). Only shared collision surface has been `docs/plans/README.md` (append-conflict → union-resolve). Your files (spain member) are isolated. If a file shows unexpected edits, another session touched it — verify, don't clobber.
- **Marker**: the user applies `.planning/plan-approved/763.md` (never the agent); you may flip labels on the user's verbal approval (already `plan-approved`).

## Epic context (brief)
Epic #713 = international field-development: per-country data source → FDAS economics + FieldConcept screening. **On main:** #714 (F1: source-agnostic FDAS + fiscal decks), #715 (F2: `to_fdas_production` + `FieldMetaMapping`/`to_field_concept`), #716 (Norway chain — the template). Spain is greenfield/harder (new member + XLSX parser; onshore fields don't fit FDAS's offshore dev-system model — hence the onshore-`dry` default + mismatch flag). F2 API: `fdas.adapters.contract.to_fdas_production(unified_df)` (needs STANDARD_COLUMNS: region/field_name/year/month/oil_bbl/gas_mcf/water_bbl); `fdas.adapters.field_concept_normalizer.{FieldMetaMapping,FieldMapEntry,to_field_concept,dev_system_from_water_depth_m}`. Memory: `project_wed_international_field_dev_epic.md`.
