# Plan: worldenergydata #927 — Public BSEE algorithm-run pilot to Hugging Face

> **Status:** draft (adversarial review PENDING — placeholder below; not yet user-approved)
> **Complexity:** T3
> **Date:** 2026-07-11
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/927
> **Parent:** https://github.com/vamseeachanta/workspace-hub/issues/3427 (repository-linked algorithm-run datasets)
> **Blocked-by:** https://github.com/vamseeachanta/workspace-hub/issues/3433 (run-ledger contract surface)
> **Input-contract:** https://github.com/vamseeachanta/workspace-hub/issues/3430 (pinned-snapshot input admission)
> **Client:** N/A
> **Project:** Repository-linked algorithm-run datasets
> **Lane:** lane:claude
> **Execution mode:** single-lane; PR branch is the documented exception to main-only execution
> **HF target:** `aceengineer/worldenergydata-runs` (dedicated worldenergydata run-ledger surface — the wh#3433 contract-managed ledger, NOT a queryable projection, NEVER a combined domain-run store)
> **Sibling pilot (pattern mirrored):** digitalmodel #1505 synthetic VIV pilot — plan `docs/plans/2026-07-11-issue-1505-synthetic-viv-parametric-hf-pilot.md`, built + dry-run-green in PR #1547
> **Review artifacts:** `scripts/review/results/issue-927-round-1/2026-07-11-plan-927-{claude,codex,gemini,disagreement}.md` (current round; outputs never inputs — promote only after fanout exits)
> **Artifact timing:** current-round provider files are outputs; zero/missing files observed by a provider during its own run are not evidence

---

## Resource Intelligence Summary

Issue #927 is OPEN at `status:needs-plan`, the SECOND pilot of the run-dataset epic
(workspace-hub#3427) and AFK-capable-only after its own adversarially reviewed plan
**and** explicit user approval. Unlike the synthetic VIV sibling (dm#1505), this
pilot's inputs are **genuinely US federal public-domain BSEE data** — which is the
central design advantage (the published dataset can be genuinely PUBLIC) AND the
central design risk (dataset-backed inputs demand a pinned source snapshot, not a
run timestamp). The owner comment on #927 states the risk almost verbatim.

### Sources consulted (concrete)

1. **Issue #927 body + two owner comments** (`gh issue view 927 --repo
   vamseeachanta/worldenergydata`, captured 2026-07-11) — supplies the ten
   acceptance criteria copied verbatim below, blocked-by workspace-hub#3433, and the
   parent-contract dependency on the reviewed wh#3427 plan + decision manual. The
   **first owner comment is the primary evidence for the central risk**, quoted
   verbatim: *"The BSEE replay snapshot must carry authoritative source vintage,
   rights, schema, query/transformation, content hashes, and a stable retrieval path;
   the current runner's runtime `data_as_of` timestamp cannot substitute for
   source-data vintage."* The second owner comment records the Explorer-side bridge
   (#965 results-bundle exporter, #966 HF-render Space) that CONSUMES this pilot's
   dataset contract as one projection under the single dedicated
   `worldenergydata` surface — so the dataset layout/manifest defined here is
   authoritative and #965 tracks it.

2. **The chosen BSEE workflow — `bsee-production-summary`** (`docs/registry/workflows.yaml`
   lines 12–38; example `examples/workflows/bsee-production-summary/input.yml`;
   `README.md`). Selected because it is the strongest deterministic, redistribution-free
   federal-BSEE candidate already wired end-to-end:
   - `id: bsee-production-summary`, `basename: bsee`, `runtime: offline`,
     `result.kind: files`. Dispatches through the existing
     `worldenergydata.bsee.bsee.bsee().router(...)` arm (engine.py line 115–117) — **no
     new router needs to be authored** (a key simplification vs dm#1505, which had to
     wire one).
   - Produces six curated domain-native outputs: `prod_summ_*.csv` + `prod_summ_*.json`
     (per-well production summary), `prod_rate_bopd_*.csv`, `prod_cumulative_mmbbl_*.csv`,
     `prod_all_block_WR_718.csv`, and a `prod_raw_*.xlsx`. These are the algorithm's
     deterministic curated native outputs — exactly the "curated native outputs +
     algorithm-scoped metrics" the contract requires.
   - `data_source: type: bundled-fixture, network_required: false` — verified offline
     2026-06-13 (workspace-hub#3064) with HTTP fully blocked. Input `data.refresh:
     false, source: csv` reads a committed fixture, so CI is network-free and
     deterministic. The BSEE production domain (OGOR-A well production: oil/gas/water by
     API12 well, block, month) is US federal public-domain — the input is genuinely
     public, not merely synthetic.
   - A sibling BSEE row `bsee-well-comparison` (registry lines 39–58, block MC-778)
     shares `basename: bsee` and the same output family — available as an additional
     meaningful variation source.

3. **`src/worldenergydata/workflow_api/runner.py`** (this checkout) — the deterministic
   in-process runner the pilot crosswalks. Two load-bearing findings:
   - **Line 238 (the central risk, source-confirmed):**
     `provenance=make_provenance(ihash, package_name=PACKAGE_NAME,
     data_as_of=utc_now_iso())`. The runner stamps `data_as_of` as **wall-clock at run
     time**. For a dataset-backed BSEE input this FAILS the #3430 pinned-snapshot
     admission (Gate A) — a run timestamp cannot serve as source-data vintage (owner
     comment, source 1). This is the pilot's central design fix.
   - **Lines 46–84 (`_canonical_content_digest` / `_normalize_container_hashes`):** the
     runner already rewrites ZIP-container (`.xlsx`) output hashes to a
     timestamp-independent digest over sorted decompressed members, excluding
     `docProps/core.xml`. So the `prod_raw_*.xlsx` output is already determinism-stable
     — no new byte-stability work is needed there (contrast dm#1505's `timestamp=None`
     recipe). Plain CSV/JSON outputs hash by raw bytes; the router writes stable
     (timestamp-free) basenames via `overwrite.output: True` (`_ensure_default_block`,
     lines 117–134).

4. **assetutilities `workflow_api` modules the pilot CONSUMES** (now MERGED to
   assetutilities `main` per task brief — cited by contract, content-verify the public
   signatures on `main` before RED capture, see Risks/Sequencing; assetutilities is
   not in this checkout):
   - **`identity`** — `algorithm_version_id` (clean SHA-bound Algorithm Version) +
     deterministic `run_id` from pinned canonical inputs.
   - **`artifact`** — content-addressed artifact store.
   - **`inputs`** — public-admission Gate A (complete / canonical / hashed /
     schema-valid / publicly-replayable); for dataset-backed sources this is where the
     **pinned snapshot_identity + versioned public_locator** must be supplied instead of
     a run timestamp.
   - **`output_contract` + `report`** — curated native outputs, one rolling HTML report,
     `output_equality_digest`.
   - **`metrics`** — algorithm-scoped metric definitions/units/derivations/quality.
   - **`publication`** — `build_projection` (RunProjection per run), `PromotionMachine`
     (emitted→staged→…→accepted), real `HfPort` + `InMemoryHfPort`, source-repo
     `publications.jsonl` ledger.

5. **digitalmodel #1505 plan** (`docs/plans/2026-07-11-issue-1505-synthetic-viv-parametric-hf-pilot.md`,
   built + dry-run-green PR #1547) — the pattern this plan mirrors section-for-section:
   ≥3 external `run_workflow(..., params=variant)` variations + exactly 1 exact replay
   (same `run_id` + output equality), committed determinism golden, `RunProjection` →
   `PromotionMachine`, real `HfPort` execution-only (CI mocks), rolling HTML report with
   mandatory Inputs+Outputs + pinned-revision links, clean-room replay, legal/secret
   scans, no absolute paths. The DIVERGENCES from dm#1505 are the design core here:
   (a) inputs are federal public-domain → published dataset is PUBLIC; (b) inputs are
   dataset-backed → pinned-snapshot identity, not `data_as_of=utc_now`; (c) the router
   already exists — no engine wiring.

6. **The synthetic-fixture nuance** (`examples/workflows/bsee-production-summary/README.md`:
   *"Offline BSEE production workflow using bundled synthetic Gulf of Mexico CSV
   data"*). The currently committed fixture (`sample_production.csv`, WR-718 "ANCHOR"
   block) is a **synthetic stand-in**, not yet a pinned real BSEE extract. Because BSEE
   is public-domain, the pilot's advantage is it CAN pin and redistribute a REAL public
   extract — so the plan must establish the canonical source snapshot as an authoritative
   BSEE public-locator + content hash (see Design D2 and the lead Risk), rather than
   inheriting the synthetic fixture's provenance.

Data rights: BSEE (Bureau of Safety and Environmental Enforcement) production data is a
US-federal-government work in the public domain (no copyright; redistribution-free).
Per `.claude/rules/codes-standards-data-routing.md` §6, a genuinely public-domain
federal source routes to a PUBLIC dataset published `--public --license cc-by-4.0`.
This is the explicit differentiator from dm#1505.

---

## Deliverable

One published, immutable Hugging Face dataset revision under
`aceengineer/worldenergydata-runs` (the wh#3433 contract-managed run-ledger surface,
published **public** with `--public --license cc-by-4.0` because the BSEE inputs are
federal public-domain) projecting **≥3 meaningful BSEE production-summary parameter
variations + 1 exact replay** of the `bsee-production-summary` workflow. Each run is
pinned to an **authoritative BSEE source snapshot** (versioned public_locator +
content-hash snapshot_identity + rights + schema + query/selection rules), NOT a run
timestamp. The source repo retains a single rolling HTML report (mandatory Inputs +
Outputs sections, links to the exact dataset revision), a committed determinism golden,
complete/canonical/hashed replayable inputs, curated native outputs, algorithm-scoped
metrics, and a passing clean-room replay — all with legal + secret scans clean (no
private data, no local absolute paths).

---

## Design

### D1 — Reuse the existing `bsee-production-summary` workflow; add only the run-ledger layers

Unlike dm#1505, no engine router is authored. `bsee-production-summary` already
dispatches through `worldenergydata.bsee.bsee.bsee().router(...)` (engine.py:115), runs
offline+deterministic under `run_workflow`'s throwaway embed root, and emits the six
curated native outputs. The pilot ADDS, around the unchanged workflow:
- an **Algorithm Version + run identity** layer (assetutilities `identity`),
- a **pinned-snapshot input contract** (assetutilities `inputs`, the D2 fix),
- **algorithm-scoped metrics** (assetutilities `metrics`),
- a **projection + promotion + HF publication** path (assetutilities `publication`),
- a **rolling HTML report** and **clean-room replay** test.

The native production schema (per-well/per-block oil/gas/water, days-on-prod, BOPD
rate, cumulative MMBBL) is retained in full in the native outputs; only curated
artifacts publish (D4).

### D2 — Pinned BSEE source snapshot (THE central design fix; resolves the `data_as_of` risk)

**Problem.** `runner.run_workflow` stamps `provenance.data_as_of = utc_now_iso()`
(runner.py:238) — a wall-clock value that changes every run. The #3430 input contract
requires a dataset-backed source to carry an authoritative source vintage; the owner
comment states the runtime timestamp "cannot substitute for source-data vintage." As
written, Gate A public admission FAILS for this pilot.

**Fix.** Introduce a canonical **BSEE source-snapshot descriptor** consumed by the
`inputs` admission layer and threaded into provenance in place of `utc_now`:
- `public_locator`: the versioned BSEE Data Center OGOR-A production dataset URL (the
  stable retrieval path for the WR-718 / Gulf-of-Mexico production extract) + the
  dataset publication vintage (BSEE publishes monthly; pin the exact month/version).
- `snapshot_identity`: the sha256 content hash of the pinned, committed extract
  (`sample_production.csv` replaced/supplemented by a genuinely-public BSEE slice — see
  the lead Risk), so the snapshot is byte-reproducible and clean-room replayable.
- `retrieved_at`: the retrieval timestamp (recorded once, at pin time — NOT run time).
- `rights`: `public-domain (US federal work; BSEE)`, license routing `cc-by-4.0`.
- `schema` + `query/selection rules` + `transformations`: the column schema of the
  extract and the group/block/API12 selection applied.

Two threading options (decide in the assetutilities-signature pre-req step, Sequencing 3):
- **(Preferred)** pass the snapshot vintage through to `make_provenance(...,
  data_as_of=<snapshot_vintage>)` via a `run_workflow` parameter or cfg field, so
  `data_as_of` carries the SOURCE vintage, not `utc_now`; the run's own wall-clock lives
  in a distinct `run_at`/`generated_at` field that is EXCLUDED from the equality digest.
- **(Fallback)** leave `runner` untouched and let the `publication`/`inputs` layer
  supply `source_snapshot` as the admission identity, with `provenance.data_as_of`
  pruned from the equality/admission set by name (mirroring the golden's volatile-key
  pruning). Either way, the equality digest and Gate A admission depend on the pinned
  snapshot identity, never on `utc_now`.

The `output_equality` / curated digest is explicitly limited to the timestamp-free
curated outputs (the CSV/JSON summaries + the canonicalized xlsx member digest);
volatile provenance (`data_as_of` / any `run_at`) is NOT part of the equality digest.

### D3 — Identity, ≥3 variations + exactly 1 exact replay

- Build `algorithm_version_id` from the SHA-bound Algorithm Version (assetutilities
  `identity`) over the bsee production-summary router code + descriptor.
- Emit **≥3 distinct-parameter runs** as EXTERNAL calls (the single, unambiguous sweep
  mechanism — mirroring dm#1505), each varying the input's `data.groups` selection so
  the canonical input (and thus `run_id`) differs and the outputs are meaningfully
  different, not accidentally equal:
  - **V1 — WR-718 Anchor, both API12 wells** (`177154051100` + `177154051200`): the base
    case; expected oil total 90,000 bbl across 2 wells (README-anchored).
  - **V2 — WR-718 Anchor, single API12 well** (`177154051100` only): a strict subset →
    smaller oil total, distinct per-well summary → distinct `run_id`.
  - **V3 — MC-778 block** (the `bsee-well-comparison` group / a distinct block+API12
    set): a different Gulf block → distinct curated outputs and cumulative curve.
  (Each variation is a real, comparable production-summary result; V1≠V2≠V3 by
  construction so the exact-replay equality below cannot pass degenerately.)
- Emit **exactly one exact replay**: re-run **V1** from its published canonical inputs;
  assert it **resolves to the SAME `run_id`** (via `identity`) and passes
  `output_equality` over the timestamp-free curated set. **Any mismatch BLOCKS
  publication** — the `PromotionMachine` must never reach `accepted`.
- **`run_id` dependency (hard):** today's `run_workflow` has NO `run_id` concept — it
  stamps `workflow_id` / provenance / `determinism.result_hash` only. Same-`run_id`
  (AC3) is provided entirely by wiring in assetutilities `identity`; that signature
  must be confirmed on `main` before the AC3 test is authored (Sequencing 3, TDD RED
  gate).

### D4 — Inputs / outputs / metrics / publication

- **Inputs** (assetutilities `inputs`): each variation's inputs are complete, canonical,
  hashed, schema-valid, publicly replayable, and pinned to the D2 source snapshot. Gate
  A public admission runs here — a genuinely-public BSEE extract + snapshot identity
  passes; a `data_as_of=utc_now`-only, dirty, licensed, pointer-only, or absolute-path
  field FAILS admission and BLOCKS.
- **Outputs** (`output_contract`): the six native production outputs retain full
  engineering schema; only the curated allowlist (curated CSV/JSON summaries + metrics +
  canonicalized xlsx digest) projects to the dataset. `output_equality_digest` is the
  exact-replay verdict.
- **Metrics** (`metrics`): algorithm-scoped — e.g. total oil produced (bbl; sum of
  `OIL_PRODUCTION` over the selection), peak/average oil rate (BOPD; from
  `prod_rate_bopd`), cumulative oil (MMBBL; from `prod_cumulative_mmbbl`), producing-well
  count. Each carries definition + units + derivation (the BSEE column + aggregation) +
  a quality note.
- **Publication** (`publication`): `build_projection` per run → `PromotionMachine`
  emitted→staged→…→accepted; the real `HfPort` publishes to
  `aceengineer/worldenergydata-runs` at a verified immutable revision (commit SHA
  pinned) **public, `cc-by-4.0`** (D-routing §6, federal public-domain); a
  `publications.jsonl` ledger row is appended in the source repo. CI uses
  `InMemoryHfPort`; the real port runs execution-only under owner go-ahead + a
  WRITE-scope token.

### D5 — Rolling report + clean-room replay

- ONE rolling HTML report in `worldenergydata` (e.g.
  `docs/reports/bsee-production-summary/index.html` via `report`) with MANDATORY
  **Inputs** and **Outputs** sections, the source-snapshot provenance (public_locator,
  vintage, sha256, rights), the applicable metrics/comparisons across V1–V3, and links
  to the **exact** dataset revision (pinned HF SHA).
- **Clean-room replay**: a fresh checkout, from the PUBLISHED inputs + pinned snapshot
  only, reproduces the accepted outputs (`result_hash` + per-artifact canonical digest
  match). CI-runnable test, not a manual step.

---

## Pseudocode

```text
# D2 — pinned BSEE source snapshot (resolves the data_as_of admission failure)
SNAPSHOT = {
    "public_locator": "https://www.data.bsee.gov/.../OGOR-A/<version>",   # versioned, stable
    "vintage": "2024-01 BSEE OGOR-A production release",                  # SOURCE vintage, not run time
    "retrieved_at": "2026-07-11T..Z",                                     # pinned once, not per run
    "sha256": "<content hash of committed public extract>",               # snapshot_identity
    "rights": "public-domain (US federal work; BSEE)", "license": "cc-by-4.0",
    "schema": [...OGOR-A columns...], "query": {"area":"WR","block":718, "api12":[...]},
}

# D3 — >=3 variations (EXTERNAL single runs; the ONLY sweep mechanism) + exact replay
VARIANTS = [ WR718_both, WR718_single_well, MC778_block ]                 # >= 3 distinct selections
runs = [ run_workflow("bsee-production-summary", params=v, snapshot=SNAPSHOT) for v in VARIANTS ]
replay = run_workflow("bsee-production-summary", cfg=canonical_inputs_of(runs[0]), snapshot=SNAPSHOT)
assert identity.run_id(replay) == identity.run_id(runs[0])               # same run_id (needs identity)
# equality over timestamp-free curated outputs ONLY (data_as_of / run_at excluded):
assert output_contract.output_equality(replay, runs[0])                  # else BLOCK publication

# D4 — inputs admission (Gate A, PUBLIC) + metrics + projection
for r in runs:
    assert inputs.admit(r, snapshot=SNAPSHOT, public=True)               # pinned identity, not utc_now
proj = publication.build_projection(runs, algorithm_version_id, snapshot=SNAPSHOT)
state = publication.PromotionMachine(proj).run()                         # emitted -> ... -> accepted
assert state == "accepted"                                              # blocks on any equality/admission fail

# D4 publish (execution-time; owner-gated; WRITE-scope token; PUBLIC per D-routing §6)
rev = publication.HfPort.publish("aceengineer/worldenergydata-runs", proj,
                                 public=True, license="cc-by-4.0")        # immutable revision
append publications.jsonl {algorithm_version_id, run_ids, hf_repo, hf_revision,
                           snapshot_sha256, accepted_at}

# D5 clean-room replay (CI, InMemoryHfPort)
inputs_only = hf_download(rev)/inputs
assert run_workflow(cfg=inputs_only, snapshot=SNAPSHOT).determinism["result_hash"] == accepted_result_hash
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `examples/workflows/bsee-production-summary/bsee_public_extract.csv` (+ replace/keep `sample_production.csv`) | genuinely-public BSEE OGOR-A extract as the pinned snapshot fixture (public-domain → redistributable); or documented decision to keep the synthetic fixture with the real public_locator pinned as source identity (lead Risk) |
| Create | `config/publication/bsee-production-summary.yml` | externalized publication config: HF target `aceengineer/worldenergydata-runs`, `public: true`, `license: cc-by-4.0`, curated-artifact allowlist, metric defs, report path, the BSEE source-snapshot descriptor (public_locator/vintage/sha256/rights/schema/query) |
| Modify | `src/worldenergydata/workflow_api/runner.py` | thread a pinned `data_as_of`/`source_snapshot` through provenance in place of `utc_now_iso()` (D2 preferred option), OR document the fallback where `inputs`/`publication` supplies the snapshot identity and prunes `data_as_of` — decided at the assetutilities-signature step |
| Create | `src/worldenergydata/workflow_api/bsee_pilot.py` (or a scripts/ entry) | the pilot driver: builds identity, runs V1–V3 + replay, admits inputs, builds metrics, projection, promotion, publication, ledger append |
| Create | `tests/workflow_api/goldens/bsee_production_summary.json` | committed determinism golden (result_hash + per-file canonical digest) |
| Create | `tests/workflow_api/test_bsee_pilot_runner.py` | envelope + reference-golden + snapshot-pinned-admission + exact-replay-equality tests |
| Create | `tests/workflow_api/test_bsee_pilot_publication.py` | admission-fail (utc_now/dirty), metrics-definition, promotion-block, public-license-routing, clean-room-replay tests |
| Create | `docs/reports/bsee-production-summary/index.html` | ONE rolling HTML report (mandatory Inputs+Outputs, source-snapshot provenance, V1–V3 comparison, links to pinned HF revision) |
| Create | `scripts/review/results/issue-927-round-1/2026-07-11-plan-927-{claude,codex,gemini,disagreement}.md` | revision-isolated plan reviews |
| Update | `../workspace-hub/docs/plans/README.md` | mandatory central plan index row (separate commit; do NOT mix into the wed PR) |

No private/PII data, no non-public BSEE field, no local absolute path enters any committed file.

---

## TDD Test List

Every acceptance criterion maps to a failing-first (RED) test captured against the
current checkout before the pilot code lands.

| Test | Current RED | Final GREEN | AC |
|---|---|---|---|
| `test_resource_intel_records_snapshot_provenance` | no descriptor | the source-snapshot descriptor carries URL, retrieval ts, sha256 snapshot_identity, public-domain rights, query/selection rules, transformations | AC1 |
| `test_snapshot_pinned_admission_passes` | admission uses `data_as_of=utc_now` → FAILS Gate A | inputs admitted only when pinned `source_snapshot` (vintage+sha256) is present; run-timestamp alone is REJECTED | AC1, AC4 |
| `test_runtime_data_as_of_is_not_source_vintage` | none | a run whose only vintage is `utc_now_iso()` is REJECTED by admission (BLOCKS); the pinned snapshot vintage is required | AC1, AC4 |
| `test_at_least_three_variations_plus_one_replay` | pilot absent | ≥3 distinct-input runs (V1 WR-718 both wells / V2 single well / V3 MC-778) + exactly 1 exact replay of V1 emitted; assert V1 oil total 90,000 bbl, V2 strict subset < V1, V3 distinct block so runs are meaningfully comparable, not accidentally equal | AC2 |
| `test_exact_replay_same_run_id_and_equality` | none | replay of V1 resolves to the SAME `run_id` (via `identity`) and passes `output_equality` over the timestamp-free curated set | AC3 |
| `test_data_as_of_excluded_from_equality_digest` | none | volatile provenance (`data_as_of`/`run_at`) is NOT in the equality/curated digest; two runs of identical inputs at different wall-clock times still pass exact-replay equality | AC3, AC5 |
| `test_equality_mismatch_blocks_publication` | none | a perturbed replay fails equality → `PromotionMachine` never reaches `accepted` | AC3, AC9(failed-run) |
| `test_inputs_complete_canonical_hashed_schema_valid_replayable` | none | inputs module validates all five properties against the pinned snapshot | AC4 |
| `test_outputs_retain_native_schema_only_curated_publish` | none | native six-output schema retained; only curated allowlist projects | AC5 |
| `test_metrics_have_definitions_units_derivations_quality` | none | oil-total / BOPD-rate / cumulative-MMBBL / well-count each carry the four metric fields with provenance to the exact snapshot + code revision | AC5(provenance), AC6-equivalent |
| `test_bsee_production_summary_reference_golden` | golden absent | `run_workflow(..., verify_reproducible=True)` result_hash == committed golden + per-file canonical digest (xlsx via `_canonical_content_digest`) | AC2, AC5 |
| `test_dataset_projection_publishes_immutable_revision` (InMemoryHfPort in CI; real port execution-only) | none | `build_projection` publishes at a verified immutable revision to `aceengineer/worldenergydata-runs` | AC6(dataset), AC7(HF) |
| `test_published_dataset_is_public_cc_by_4_0` | none | publication routes PUBLIC with `--public --license cc-by-4.0` (D-routing §6, federal public-domain); a private/wrong-license route FAILS the routing assertion | AC1(rights), routing rule |
| `test_rolling_report_has_inputs_outputs_and_revision_links` | report absent | HTML has Inputs+Outputs sections, source-snapshot provenance, metrics/comparisons, links to the exact dataset revision | AC7(report) |
| `test_clean_room_replay_reproduces_accepted_outputs` | none | replay from published inputs + pinned snapshot only == accepted result_hash + digests | AC8 |
| `test_failed_run_excluded_from_metrics_and_decisions` | none | a `status="error"` envelope (fail-closed, runner.py:244) is excluded from metric/report/decision populations | AC9 |
| `test_no_private_data_or_absolute_paths` | none | legal + secret scan over all new files finds no private data, no local absolute path | AC10 |

**HARD RED-phase pre-requisite (blocking).** Before ANY test referencing the
assetutilities surface is written, confirm these public signatures on assetutilities
`main` (not merely "cited by contract"): `identity` `run_id`/`derive_run_identity`;
`inputs` admission entry point (incl. `source_snapshot` argument for dataset-backed
sources); `output_contract` `output_equality_digest`; `publication` `build_projection`,
`PromotionMachine`, `HfPort`/`InMemoryHfPort` (incl. `public`/`license` publish args).
`run_workflow` has NO `run_id` today, so `test_exact_replay_same_run_id_and_equality`
cannot be authored until `identity` is verified. If any signature differs (especially
whether the snapshot is threaded via `run_workflow` or via `inputs`/`publication`),
adjust D2/D3/D4 and the tests before RED capture. Partial-coverage notes: AC1's
rights-acceptance is doc-satisfied at the resource-intelligence layer plus the
admission/routing tests; AC7's real immutable-revision check runs at owner-gated
**execution** with a live `HfPort` (CI uses `InMemoryHfPort`).

---

## Acceptance Criteria

Verbatim from issue #927:

- [ ] Resource intel selects one BSEE-based algorithm and records the source URL, retrieval timestamp, immutable snapshot/hash, license or public-domain basis, query/selection rules, and transformations.
- [ ] At least three meaningful runs and one exact replay are emitted.
- [ ] The exact replay resolves to the same run identifier and passes output equality; any mismatch blocks publication.
- [ ] Inputs are complete, canonical, hashed, schema-valid, and publicly replayable.
- [ ] Curated domain-native outputs and algorithm-specific metrics retain provenance to the exact source snapshot and code revision.
- [ ] The dedicated `worldenergydata` dataset projection is published at a verified immutable Hugging Face revision.
- [ ] One rolling HTML report in `worldenergydata` contains mandatory Inputs and Outputs sections, applicable metrics/comparisons, and links to exact dataset revisions.
- [ ] A clean-room replay from the published inputs reproduces the accepted outputs.
- [ ] Failed-run handling is exercised without allowing failure evidence into metric or decision populations.
- [ ] Legal and secret scans pass with no private data or local absolute paths.

Plan-specific gates:

- [ ] Every acceptance criterion above has a failing-first (RED) test captured before implementation.
- [ ] The BSEE input is pinned to an authoritative source snapshot (public_locator + vintage + sha256), NOT the runner's `data_as_of=utc_now`; admission rejects a run-timestamp-only vintage.
- [ ] Because the BSEE source is US federal public-domain, the published dataset is PUBLIC and routed `--public --license cc-by-4.0` per `.claude/rules/codes-standards-data-routing.md` §6.
- [ ] Legal + secret scan output attached to the PR; no private data, no local absolute path in any committed artifact.
- [ ] The `worldenergydata` source repo remains authority for code/descriptors/schemas/tests/report; the HF dataset is a projection only, on the dedicated surface (never a combined domain-run store).

---

## Sequencing & Gate

1. **Upstream dependency (satisfied / blocking):** the assetutilities `workflow_api`
   modules (identity/artifact/inputs/output_contract+report/metrics/publication) are
   **MERGED to assetutilities `main`** (task brief) and must be importable as
   `assetutilities.workflow_api.*` before pilot execution. Blocked-by
   workspace-hub#3433 (run-ledger contract surface `aceengineer/worldenergydata-runs`)
   must be resolved before the publish step.
2. **Plan gate:** this plan needs its OWN adversarial review (round-1 artifacts above)
   with ≥2 usable no-MAJOR provider reviews, then explicit user approval; move #927 to
   `status:plan-approved` and record `.planning/plan-approved/927.md`. The implementing
   agent must not self-approve.
3. **TDD pre-req:** confirm the assetutilities public signatures on `main` (identity /
   inputs-with-`source_snapshot` / output_contract / publication `HfPort` public+license
   args) AND decide the D2 threading option (runner `data_as_of` vs
   inputs/publication-supplied snapshot). Only then capture all RED tests; then D1→D5.
4. **Execution PUBLISHES a PUBLIC dataset to `aceengineer/*` on Hugging Face
   (outward-facing).** Higher bar than an internal merge:
   - requires **explicit owner go-ahead at run time** (separate from plan approval) — it
     puts an aceengineer-branded, public, `cc-by-4.0` dataset on the open web;
   - the HF token must have **WRITE scope**; the real `HfPort` publish is execution-only
     and never runs in CI (CI uses `InMemoryHfPort`);
   - publication is HITL with its OWN approval: `PromotionMachine` may only reach
     `accepted` after equality + Gate-A pinned-snapshot admission pass AND the owner
     authorizes the outward push.
5. **Report/ledger:** commit the rolling report + `publications.jsonl` row in the wed
   PR; commit the central plan-index row separately from clean `workspace-hub/main`.

---

## Adversarial Review Summary

*(placeholder — reviews not yet run)*

| Provider | Verdict | Notes |
|---|---|---|
| Claude (r1) | PENDING | run from repo with concise local-plan path prompt |
| Codex | PENDING | invoke directly (`env -u CLAUDECODE`) with local-plan path |
| Gemini | PENDING | availability is not approval |

This plan requires ≥1 usable no-MAJOR provider review (ideally two disjoint providers)
plus explicit user approval before implementation. Provider files under
`scripts/review/results/issue-927-round-1/` are OUTPUTS of this round — promote/act on
them only after the fanout exits.

---

## Risks and Open Questions

- **[LEAD RISK — BSEE snapshot pinning] The runner stamps `data_as_of=utc_now`; a
  dataset-backed source needs a pinned source vintage.** `runner.run_workflow`
  (runner.py:238) sets `provenance.data_as_of = utc_now_iso()`. Per the #3430 input
  contract and the #927 owner comment, a BSEE (dataset-backed) input must carry an
  authoritative source vintage + rights + schema + content hash + stable retrieval path;
  the run timestamp cannot substitute. If unaddressed, Gate A public admission FAILS.
  Resolution: D2 — a pinned `source_snapshot` (public_locator + vintage + sha256) supplied
  to the `inputs` admission layer and threaded into provenance in place of `utc_now`,
  with `data_as_of`/`run_at` excluded from the equality digest. The exact threading
  (runner param vs inputs/publication-supplied) is confirmed at Sequencing 3 against the
  assetutilities signatures.
- **[public-fixture provenance — OPEN] The committed fixture is synthetic, not a real
  BSEE extract.** `README.md` describes `sample_production.csv` as *"bundled synthetic
  Gulf of Mexico CSV data."* For a genuinely-public federal-data pilot the canonical
  source snapshot should be a REAL public-domain BSEE OGOR-A slice (redistributable
  because public-domain). Decision needed: (a) commit a small real BSEE extract as the
  pinned fixture + snapshot_identity (preferred — makes the public claim honest and the
  clean-room replay real), or (b) keep the synthetic fixture for offline CI while pinning
  the real public_locator + sha256 as the source identity (weaker: the replayed bytes are
  synthetic). Recommend (a) if a suitably small deterministic public slice exists.
- **[dependency — HARD RED-phase pre-req] assetutilities public signatures.** identity
  `run_id`/`derive_run_identity`; `inputs` admission with `source_snapshot`;
  `output_contract.output_equality_digest`; `publication.build_projection` /
  `PromotionMachine` / `HfPort`+`InMemoryHfPort` with `public`/`license` publish args —
  MUST be confirmed on assetutilities `main` before any referencing test is written.
  `run_workflow` has no `run_id` today, so AC3 depends on wiring in `identity`.
- **[determinism risk] Golden must be machine-stable.** The runner already normalizes
  xlsx container hashes (`_canonical_content_digest`) and writes timestamp-free basenames
  (`overwrite.output: True`), so the six outputs are determinism-ready — but confirm no
  CSV/JSON output embeds a run timestamp or locale-dependent float formatting; any such
  field breaks the cross-machine golden and the clean-room replay.
- **[outward-facing risk] Public HF publish is irreversible-ish AND public-by-design.**
  A pushed public `cc-by-4.0` dataset revision is world-visible; the WRITE-scope token +
  owner go-ahead gate this. CI must never hold the real token — `InMemoryHfPort` in
  tests. Confirm the wh#3433 `aceengineer/worldenergydata-runs` surface exists and is a
  run-ledger (not a queryable projection) before publish.
- **[metric definition — open]** Confirm the algorithm-scoped metric set (oil total,
  BOPD peak/avg, cumulative MMBBL, well count) and label each with units + derivation
  (BSEE column + aggregation) + quality; avoid over-claiming (these are reported
  production aggregates, not reserves/economics).
- **[report location — open]** `docs/reports/bsee-production-summary/index.html` vs a
  Pages-published path — confirm which surface the parent contract expects for the
  "rolling report in the source repository."

---

## Complexity

**T3** — spans a pinned-snapshot input-contract fix over the existing runner (the
central `data_as_of` risk), six consumed assetutilities modules (identity/artifact/
inputs/output_contract+report/metrics/publication), ≥3 external variations + an
exact-replay-equality gate, a committed determinism golden, a clean-room replay, an
externalized publication config, a rolling HTML report, and an outward-facing PUBLIC
HF publish with its own HITL gate and public-license routing. It couples determinism,
provenance/source-vintage, public admission, and an external side-effecting port —
each an independent failure surface. It is below the dm#1505 authoring burden (the
BSEE router already exists) but above T2 because the snapshot-pinning contract fix and
the public-data routing add genuine, load-bearing design surface.
