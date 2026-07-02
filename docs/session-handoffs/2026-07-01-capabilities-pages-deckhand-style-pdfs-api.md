# Session handoff — Capabilities pages: HSE/completion, Deckhand-style redesign, PDFs, workflow-API, starting prompts

**Date:** 2026-07-01
**Repos:** worldenergydata (wed), digitalmodel (dm), deckhand
**Live pages:**
- https://vamseeachanta.github.io/worldenergydata/capabilities/
- https://vamseeachanta.github.io/digitalmodel/capabilities/

## What shipped (all PRs merged, all verified live)

### 1. Publish previously-hidden work + a new report (wed)
- HSE / marine-safety / IMO reports were 404 (never published) — added `marine_safety`, `hse`, `completion` domain builders to `scripts/build_pages.py`. (PR #673)
- New **deterministic completion report** `/completion/` — `scripts/completion/build_completion_report.py` reads the frozen `docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx` → 217 wells / 12 Lower-Tertiary fields, median drilling 38 d / completion 24 d. Byte-identical on regen. (PR #673)

### 2. Publish hidden diffraction/hydro dashboards (dm)
- `docs_dir: docs/api` means only `docs/api/**` is served; the diffraction suites lived under `docs/domains/**` (404). Copied 4 self-contained dashboards into `docs/api/hydro/` (AQWA↔OrcaWave RAO, unit-box 3-way WAMIT/AQWA/OrcaWave benchmark, OCIMF explorer, Wang passing-ship) + later riser-validation, riser-mesh, subsea cross-section. (PRs #1178, #1183)

### 3. Deckhand-style redesign + repo logos (wed #676, dm #1183)
- Dark→ then **light** theme (`--navy #0B3D91` / `--teal #0f8a7e`), fixed logo sidebar + section nav, hero, teal-accented section headers, rounded card grid, gradient CTAs. Shared `<style>` block across both repos.
- **Logos:** dm uses `assets/logo/digitalmodel_logo.svg` (inlined); wed had none → created an SVG wordmark, committed to `site_assets/worldenergydata_logo.svg`, inlined.
- **Every card = a live link** (dropped unlinked descriptor cards; methods-without-a-dashboard live only in the validation table).

### 4. Light theme + per-capability client artifacts (wed #682/#684, dm #1211/#1218)
Generator: `scripts/capabilities/build_onepagers.py` in each repo (data-driven SPECS → light A4 HTML → `google-chrome --headless --print-to-pdf`; API artifacts are pure stdlib).
- **1-page PDF per section (menu item) and per work** — wed 26 PDFs, dm 26 PDFs.
- **Self-contained workflow-API artifact per work** at `capabilities/api/<id>.{html,json}` — typed `deckhand.workflow_api.ResultEnvelope/2` (POST `/api/run` for registry-backed, GET report for surfaces) + provenance + the live report embedded via `<iframe>`.
- **Starting prompt per work** — copyable NL prompt (fires via the bot), in the API artifact + JSON (`prompt`) + PDF ("Ask Deckhand: …").
- **How to run** — hover tooltip on the card API action + a "How to run the API" (Telegram/HTTP/CLI) section in the artifact.
- Each card offers **Open · PDF · API**.

### 5. Live callable endpoint — it already exists
Investigation (see deckhand epic #521): `@the_deckhand_bot` (Hermes gateway, ace-linux-2) → `POST /api/run` (`deckhand/src/deckhand/api_server.py`, bearer+scope+ratelimit) → `<pkg>.workflow_api.run_workflow` → hosted `report_url`. So no new infra was needed.
- **digitalmodel `run_workflow` already implemented + golden-tested** (`src/digitalmodel/workflow_api/runner.py`; goldens for buckling/ffs/mooring/wall-thickness); deckhand's resolver auto-detects it. Fixed the stale "digitalmodel has no in-process API" comment (deckhand PR #526).
- **Routing already registered** (`config/deckhand/routing/capabilities.yaml`, 102 CTA refs incl. our workflows).
- **Fixed one overclaim:** `worldenergydata:fdas-field-npv` is deliberately excluded from deckhand routing (PII, deckhand#513); the wed economics cards advertised a POST to it → corrected to an honest GET report-surface (wed PR #687).

### 6. Discoverability (wed #689, dm #1236)
Linked the capabilities gallery from both READMEs and the dm docs homepage (`docs/api/index.md`).

## Open items (decisions / operator-gated — NOT code)
- **deckhand #522 (product decision):** which escalate-by-design capabilities to promote to runnable-in-chat entrypoints (paid compute). Candidates: `elastic-buckling`, `rao-tabulation`, `bsee-well-comparison`, `marine-safety-stats`. Needs taxonomy/paths (I5) + escalation config + a target channel. Awaiting confirmation.
- **deckhand #523 / #524 (operator):** create the Telegram channel, mint scoped PATs, bind chat_id, restart hermes on ace-linux-2 → then the routed `?start=src_…` deep-links + live runs go live.
- **worldenergydata #683 / digitalmodel #1213 part-1:** add one-click `?start=` "Run live" deep-links on the pages — deferred until the channel is bound (so we never ship a button that lands on a generic greeting).
- **digitalmodel #1234 (CI health):** the domain-test matrix is red on `main` from 4 shards of stale tests (reporting-backbone dropped `StandardReport`; engine dynamic-import tests; skill-catalog drift; orcaflex fixture/snapshot/license). Diagnosed per-shard; left for a domain owner (some may mask real regressions). PRs merge UNSTABLE because of this (docs/quality-gates pass; branch unprotected).

## Reach (verified)
- Consuming (pages, PDFs, API artifacts, JSON envelopes, embedded reports, prompts) works for **any client / any machine** — static CDN, no auth, iframes allowed (no X-Frame-Options), CORS `*` on JSON.
- Executing live is **gated by design** — allowlisted Telegram users/bound channels, or a scoped bearer token for `POST /api/run` — appropriate for paid compute.

## Gotchas for next session
- `git worktree add` on the digitalmodel repo is huge and **times out at 2–5 min** → use `run_in_background`.
- Local clones' `origin/main` refs go stale → `git fetch --prune` before diffing/branching.
- deckhand PR-title check (amann/action-semantic-pull-request): subject ≤ 80 chars.
- Pre-commit conflict-marker hook emits harmless null-byte warnings scanning the committed PDFs.
- dm Pages **deploy** step occasionally times out in GitHub's queue (build passes) → re-run.
