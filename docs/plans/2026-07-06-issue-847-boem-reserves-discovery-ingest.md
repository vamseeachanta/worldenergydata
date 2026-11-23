# Plan for #847: Ingest BOEM free reserves + discovery dates into the refresh pipeline (Table 4 validation)

> **Status:** plan-approved (owner approved in-session 2026-07-06; r1+r2 findings folded in — see issue comment)
> **Complexity:** T2
> **Date:** 2026-07-06
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/847
> **Client:** N/A
> **Project:** —
> **Lane:** lane:claude
> **Review artifacts:** scripts/review/results/2026-07-06-plan-847-claude.md (r1 MAJOR→fixed) | 2026-07-06-plan-847-codex.md (r2 MAJOR→fixed)

---

## Resource Intelligence Summary

### Existing repo code
- Found: `packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/url_registry.py` — frozen `DatasetSpec` registry (28 regular specs + OGOR-A yearly); **`deepqual` already registered** (`DeepQualRawData.zip` → `mv_deep_water_field_leases.bin`, materialized at `data/modules/bsee/bin/deepqual/`). All specs use the BSEE base URL; no `data.boem.gov` source exists yet. `zip_url` is a plain string consumed host-agnostically by `refresh_bsee_all.py`, so an absolute BOEM URL works unchanged in the **standalone** path.
- Found (r1 review): `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/bsee_refresh.py` — the **scheduler** path is host-pinned: `ALLOWED_URL_PREFIX = "https://www.data.bsee.gov/"`; `validate_dataset_entry` raises `ValueError` on any other host (documented injection-surface guard), and `load_dataset_catalog` propagates it (one bad entry crashes the weekly job at config load). A builtin `BSEE_DATASETS` dict (4 entries) is drift-guarded by `tests/unit/scheduler/test_bsee_adapter.py` (`test_foreign_host_url_rejected`; set-equality assert vs the catalog). Any scheduler-cadence deliverable MUST bring these into scope.
- Found (r1 review): deepqual bin is 698×12 and carries `FIELD_NAME_CODE`, `FLD_NICK_NAME`, `FLD_DISCVR_DATE`, `FLD_FIRST_PROD`, `FIRST_PROD_DATE` — discovery/first-production dates are available now. Note `FLD_FIRST_PROD` and `FIRST_PROD_DATE` disagree on some rows; the builder must pick one (default `FIRST_PROD_DATE`) and document the choice in the companion MD.
- Found: `scripts/refresh_bsee_all.py` — `BSEERefreshOrchestrator`: downloads each `zip_url`, extracts delimited members, pickles DataFrames to `expected_bins`; LFS-stub aware; `--dry-run/--force/--dir` flags. New specs are picked up automatically via `get_all_specs()`.
- Found: `config/scheduler/scheduler_config.yml` (`bsee_refresh` weekly) + `config/bsee.yml` `scheduler_datasets:` — the scheduler pulls only the parameterized subset; **`deepqual` is NOT in the subset** (refreshes only via the standalone script).
- Found: `packages/.../bsee/data/field_names.py` — `FieldNameResolver` already joins on **`FIELD_NAME_CODE`** from the deepqual bin (`FLD_NICK_NAME`). This is the natural join anchor for FieldReserves.
- Found: `config/input/world_oil_lower_tertiary.yaml` — LT field → area+blocks map (via `LTConfig.field_blocks`). **North Platte, Big Foot, Buckskin are missing from it.**
- Found: `data/modules/offshore_assets/curated/` — curated per-field CSV convention (UPPER_SNAKE_CASE headers, companion `.md` provenance doc, builder script under `scripts/field_development/`). `fields.csv` carries a non-BOEM `DISCOVERY_DATE`.
- Gap list at end of this section.

### Standards
Not applicable (public-domain US federal data; no engineering standard consumed). Routing: BOEM is US federal public-domain — per `.claude/rules/codes-standards-data-routing.md` §6 this data may live in public repos; no wiki-sibling routing needed (`Client: N/A`).

### Documents consulted
- `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` — acceptance-contract shape for a new/refreshed source (readiness fields, validator, tests).
- `docs/plans/2026-05-04-issue-129-boem-bsee-cli-refresh.md` — prior BOEM/BSEE refresh CLI work.
- `docs/plans/2026-05-03-issue-374-...big-foot-north-platte.md`, `...issue-375-per-field-economics-10-lt-fields.md` — LT curation + citation follow-ups (#361).
- `docs/data/bsee-source-catalog.md` — dataset → URL → code-home catalog (new source must be added).
- `reports/lower_tertiary/wo-april-2026-validation.md` (PR #853) — the Table 4 validation this ingest firms up.
- Related issues: #847 (this), #844 (cost time-series), #842 (KC ingest), #361 (citation contract).

### Gaps identified
1. No FieldReserves/EOGR ingestion anywhere (no spec, no bin dir, no loader; `reservesData.html` is a data-less UI stub).
2. No `data.boem.gov` source in the registry (all specs are `www.data.bsee.gov`).
3. `deepqual` not on the weekly scheduler cadence.
4. No curated per-field recoverable-reserves + discovery-date table; no `FIELD_NAME_CODE`-keyed bridge to the LT development names.
5. #361 `Citation` schema (`src/worldenergydata/citations/schema.py`) not yet implemented in this repo; the implemented citation pattern is the LNG `SourceCitation` pydantic model + curated companion-MD convention.

### Evidence (embedded verification)
- Issue #847 OPEN, title `feat(data): ingest BOEM free reserves + discovery dates into the refresh pipeline (Table 4 validation)` (gh, 2026-07-06).
- **Correct reserves artifact (r2 Codex MAJOR-1, verified by live pull 2026-07-06):** `https://www.data.boem.gov/FieldReserves/Files/2023 Tables xlsx Public.zip` (from the `estimated2023` page) contains one workbook with sheets: `2023 - Table 4 Final` (1,336 fields ranked by **Original BOE reserves** — Field name, Field nickname, Disc year, Water depth, Field type, Original Reserves MMBOE), `2023-Table 5 Final` (same by **Remaining** reserves), `HIST-2023` (per-field reserve history by year), Tables 1–3/8/9 (aggregates). This — not the `FieldReserves/Files/mastdata*` zips — is the recoverable-reserves source.
- `mastdatadelimit.zip` (113,392 bytes, verified pull) is the **Field Name Master List** (rows like `"AC","   24","AC024","G10379",...` = area/block/FIELD_NAME_CODE/lease) — useful ONLY as the lease↔field-code bridge input; `appendadelimit.zip` verified same shape. Neither carries reserve volumes.
- `https://www.data.boem.gov/Main/FieldReserves.aspx` and `.../Other/DataTables/DeepQualFields.aspx` → HTTP 200 (curl -sI, 2026-07-06). DeepQualFields is an ASP.NET postback grid with **no direct file link** — but the equivalent raw data is already ingested via BSEE `DeepQualRawData.zip` (deepqual spec), so no scraping is needed.
- `data/modules/bsee/bin/deepqual/mv_deep_water_field_leases.bin` exists (65 KB) in the main checkout.
- Reproduction proofs: **N/A — feature ingest, no runtime failure alleged.**

## Deliverable

0. **Step-1 go/no-go gate (partially discharged at plan time):** the 2023 Tables workbook was pulled and inspected (see Evidence) — Table 4/5 carry field-level Original/Remaining BOE reserves keyed by **Field name / Field nickname** (no `FIELD_NAME_CODE` column visible). Remaining gate at implementation: confirm nickname values join cleanly to deepqual `FLD_NICK_NAME` for the LT set; where ambiguous, fall back to the `mastdatadelimit` lease↔`FIELD_NAME_CODE` master. Schema note recorded in the companion MD.
1. **Raw layer:** two new `DatasetSpec`s in `url_registry.py`, refreshed by `scripts/refresh_bsee_all.py` (host-agnostic path, verified):
   - `fieldreserves_tables` → `https://www.data.boem.gov/FieldReserves/Files/2023 Tables xlsx Public.zip` (vintage-pinned; annual bump is a one-line registry change, procedure documented in the companion MD). **Requires extending the orchestrator's member handling to `.xlsx`** (today it extracts CSV/`.txt` members → pickle; add `read_excel` → one bin per relevant sheet).
   - `fieldreserves_master` → `mastdatadelimit.zip` (lease↔`FIELD_NAME_CODE` bridge master, delimited — existing member handling works).
   LFS-stub dirs `data/modules/bsee/bin/fieldreserves_tables/`, `.../fieldreserves_master/`.
2. **Cadence:** add `fieldreserves` AND the existing `deepqual` to `config/bsee.yml scheduler_datasets:`, **which requires scheduler-code changes** (r1 MAJOR-1/-2):
   - `bsee_refresh.py`: `ALLOWED_URL_PREFIX` (str) → `ALLOWED_URL_PREFIXES` tuple `("https://www.data.bsee.gov/", "https://www.data.boem.gov/")` — a scoped widening to a second official federal portal, NOT a validator removal; non-federal hosts still rejected. `BSEE_DATASETS` builtin dict gains the two entries.
   - `tests/unit/scheduler/test_bsee_adapter.py`: extend `test_foreign_host_url_rejected` (BOEM host accepted; `https://evil.example/` still rejected) and the builtin↔catalog set-equality drift guard.
   - **Fallback (approver's call):** if widening the allowlist is unwanted, drop scheduler cadence and rely on the standalone `refresh_bsee_all.py` (documented cadence in source-registry.yml `update_frequency`). Default recommendation: widen with tests.
   **Scope note (r1 MINOR-3, owner to confirm at plan-review):** the issue names BOEM's `DeepQualFields.aspx` as source 2; that page is an ASP.NET postback grid with no direct file link, and its underlying data is **already ingested** via the registered `deepqual` spec (BSEE `DeepQualRawData.zip`, same substrate). This plan therefore satisfies source 2 by putting the existing `deepqual` feed on cadence rather than scraping the BOEM grid.
3. **Curated layer:** `data/modules/offshore_assets/curated/lt_reserves_discovery.csv` + companion `LT_RESERVES_DISCOVERY.md`, built by new `scripts/field_development/build_lt_reserves_discovery.py`: per-LT-development recoverable reserves (proved + indicated EOGR, cumulative production) from FieldReserves joined to discovery/first-production dates from deepqual, keyed on `FIELD_NAME_CODE`, with a `DEV_NAME` column bridging to the 11 LT development names (Anchor, Big Foot, Buckskin, Cascade Chinook, Jack St Malo, Julia, Kaskida, North Platte, Shenandoah, Stones, Tiber).
4. **Citation:** each curated row carries `SOURCE_NAME`, `SOURCE_URL`, `SOURCE_VINTAGE` (e.g. `31-Dec-2023`), `ACCESS_DATE` columns (LNG `SourceCitation` field shape flattened to CSV); companion MD documents provenance + the "2023 vintage — Anchor/Shenandoah may be unbooked; pre-FID fields absent" caveat verbatim. STOIIP explicitly NOT included (stays operator/announced, separately cited — owner decision).
5. **Catalog:** entries in `data/catalog/source-registry.yml` and `docs/data/bsee-source-catalog.md`.
6. **Validation hook:** the WO Table 4 cross-check table appended to `reports/lower_tertiary/wo-april-2026-validation.md` §5 follow-up (BOEM recoverable vs WO/operator figures for Anchor 440 / JSM 500 / Stones 250).

## Pseudocode (T2)

```
# build_lt_reserves_discovery.py
tables     = load fieldreserves_tables bins (Table 4: Original BOE; Table 5: Remaining BOE;
             key = Field name / Field nickname; vintage = 31-Dec-2023)
master     = load fieldreserves_master bin (area/block/FIELD_NAME_CODE/lease bridge)
deepqual   = load deepqual bin (FIELD_NAME_CODE, FLD_NICK_NAME, FLD_DISCVR_DATE,
             FIRST_PROD_DATE — default FIRST_PROD_DATE, choice documented)
bridge     = LT_DEV_TO_FIELD_CODE mapping (NEW, config/input/lt_field_name_codes.yaml)
             # built once at implementation by resolving each LT dev's area/blocks
             # (world_oil_lower_tertiary.yaml + buckskin_config.py + #374 configs)
             # against deepqual FLD_NICK_NAME; reviewed values, committed as config
out        = bridge ⨝ latest ⨝ deepqual  → one row per LT development
             columns: DEV_NAME, FIELD_NAME_CODE, RECOV_OIL_MMBBL, RECOV_GAS_BCF,
                      CUM_OIL_MMBBL, RESERVES_VINTAGE, DISCOVERY_DATE, FIRST_PROD_DATE,
                      SOURCE_NAME, SOURCE_URL, SOURCE_VINTAGE, ACCESS_DATE
write CSV + regenerate companion MD; absent fields → row present with NULLs + caveat flag
```

## Files to Change

| File | Change |
|---|---|
| `packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/url_registry.py` | + `fieldreserves_tables` + `fieldreserves_master` DatasetSpecs (absolute BOEM URLs) |
| `scripts/refresh_bsee_all.py` | extend member handling to `.xlsx` (read_excel → per-sheet bins) |
| `tests/unit/bsee/test_url_registry.py` | + both dirs in `EXPECTED_DIRS`, bump stub count |
| `data/modules/bsee/bin/fieldreserves_tables/.gitkeep`, `.../fieldreserves_master/.gitkeep` | new LFS-stub dirs |
| `config/bsee.yml` | + `fieldreserves`, + `deepqual` under `scheduler_datasets:` (with `url_key`/`registry_dir`/member patterns) |
| `packages/worldenergydata-scheduler/.../scheduler/jobs/bsee_refresh.py` | `ALLOWED_URL_PREFIX` → `ALLOWED_URL_PREFIXES` (+ BOEM host); `BSEE_DATASETS` builtin + 2 entries |
| `tests/unit/scheduler/test_bsee_adapter.py` | foreign-host test extended (BOEM accepted, non-federal rejected); builtin↔catalog drift guard updated |
| `BSEEWebScraper.URLS` (module per drift-guard test) | + matching URL keys |
| `config/input/lt_field_name_codes.yaml` | NEW — LT dev → FIELD_NAME_CODE bridge (reviewed, committed) |
| `scripts/field_development/build_lt_reserves_discovery.py` | NEW builder |
| `data/modules/offshore_assets/curated/lt_reserves_discovery.csv` + `LT_RESERVES_DISCOVERY.md` | NEW curated output + provenance doc |
| `data/catalog/source-registry.yml`, `docs/data/bsee-source-catalog.md` | + source entries |
| `docs/plans/README.md` | index row |

## TDD Test List

1. `test_url_registry.py`: `fieldreserves` spec present, dir expected, URL is absolute BOEM (**write first, red**).
2. Drift-guard: `config/bsee.yml` entries ↔ registry ↔ `BSEEWebScraper.URLS` consistent for `fieldreserves` + `deepqual` (existing cross-check test extended).
2b. Scheduler allowlist: `validate_dataset_entry` accepts `https://www.data.boem.gov/...`, still rejects `https://evil.example/...`; `BSEE_DATASETS` builtin set-equality guard updated to 6 entries (**write first, red** — these encode r1 MAJOR-1/-2).
3. `tests/unit/bsee/data/test_fieldreserves_loader.py`: loader reads a fixture bin (tiny synthetic mast-data frame), returns `FIELD_NAME_CODE`-indexed latest-vintage EOGR.
4. Bridge integrity: every `lt_field_name_codes.yaml` code resolves via `FieldNameResolver`; all 11 LT dev names enumerated; unknown code fails loudly.
5. Curated builder: given fixture fieldreserves+deepqual frames, output has 11 rows, citation columns non-null, absent-field rows carry NULL reserves + caveat flag (Kaskida/North Platte/Tiber pre-FID; possibly Anchor/Shenandoah unbooked).
6. Known-answer (falsifiable, r2 finding 2): at implementation, read Stones' actual `Original Reserves (MMBOE)` from Table 4 of the real 2023 pull and **pin that exact value in the test** (Anchor-fidelity pattern). Separately, the curated builder emits `lt_reserves_discrepancies.csv` whenever |BOEM − operator-announced| / operator > 20% (operator figures: Anchor 440 / JSM 500 / Stones 250 MMboe); a test feeds a fixture breaching the threshold and asserts the discrepancy row appears with units (MMBOE) and both values.
7. Orchestrator xlsx support: fixture zip containing a tiny .xlsx → member extracted via `read_excel`, one bin per configured sheet, delimited path unchanged (**write first, red**).
8. DeepQual equivalence (r2 finding 3): test asserts the deepqual bin carries `FIELD_NAME_CODE`, `FLD_NICK_NAME`, `FLD_DISCVR_DATE`, `FIRST_PROD_DATE` (verified 698×12 at plan time) — the fields the BOEM `DeepQualFields.aspx` export would provide.

## Acceptance Criteria

- [ ] `scripts/refresh_bsee_all.py --dir fieldreserves` performs a real pull creating the bin (evidence in PR).
- [ ] Weekly scheduler config covers `fieldreserves` + `deepqual`; drift-guard tests green.
- [ ] `lt_reserves_discovery.csv` exists with 11 LT development rows, per-row source citation columns, vintage caveats documented in companion MD.
- [ ] STOIIP absent from the curated table by design (documented).
- [ ] DeepQual substitution recorded: companion MD carries the equivalence note (BSEE `DeepQualRawData.zip` ⊇ required BOEM `DeepQualFields.aspx` fields: `FIELD_NAME_CODE`, discovery date, first production) backed by the column-presence test — OR the owner requests the direct BOEM export instead at plan review.
- [ ] WO Table 4 cross-check appended to the validation report (BOEM vs operator/WO figures).
- [ ] All new tests pass; CI lint (black/isort on `src/ tests/`) clean via `uv run` toolchain.

## Risks

1. **`mastdatadelimit.zip` schema unknown until first pull** (member names, column layout, whether yearly rows or latest-only). Mitigation: implementation step 1 is an exploratory pull + schema note in the companion MD; bin/loader names finalized then.
2. **2023 vintage misses Anchor (FO 2024) / Shenandoah (FO 2025)**; pre-FID fields absent. Mitigation: rows kept with NULLs + caveat flag; refresh picks up future vintages automatically.
3. **LT-name ↔ FIELD_NAME_CODE bridge errors** (e.g. Cascade vs Chinook are separate BOEM fields; Jack and St Malo separate). Mitigation: bridge is a reviewed committed YAML (not runtime fuzzy matching); integrity test 4; many-codes-to-one-dev supported.
4. **BOEM URL churn** (`data.boem.gov` reorganizes). Mitigation: payload classifier already handles HTTP-200-HTML-not-zip; drift-guard + `test_source_refresh_contract.py` patterns apply.
5. **Scope creep into #361 citation schema.** Mitigation: use flattened SourceCitation columns now; #361 adoption stays a separate issue.
