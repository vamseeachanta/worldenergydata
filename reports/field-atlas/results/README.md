---
# Hugging Face dataset card (front-matter placeholder).
license: other  # public BSEE / public-disclosure basis; confirm at publish.
pretty_name: World Energy Field Explorer results (field_explorer_results)
tags:
  - energy
  - offshore
  - field-development
---

# World Energy Field Explorer — HF results projection

**Schema version:** `1.0.0`  
**Dedicated HF dataset:** `worldenergydata` (never a combined domain-run store)  
**Projection:** `field_explorer_results`

Field Explorer (#939) analysis results, re-packaged as a public, Hugging-Face-consumable dataset projection. Conforms to the dedicated worldenergydata HF dataset contract (#927 / workspace-hub#3427): public-data-only, content-hashed, schema-valid, immutably revisioned at publish time.

## Provenance / contract

This projection re-packages already-committed Field Explorer (#939) analysis results. It consumes — and does not re-derive — the dedicated `worldenergydata` Hugging Face dataset contract owned by [#927](https://github.com/vamseeachanta/worldenergydata/issues/927) and [workspace-hub#3427](https://github.com/vamseeachanta/workspace-hub/issues/3427): public-data-only, immutable revisions, run identity, content hashes, and provenance to the exact source snapshot + code revision.

### Source snapshots (content-hashed)

| role | path | sha256 | bytes | generated_by | source issue |
| --- | --- | --- | --- | --- | --- |
| field_detail | `reports/lower_tertiary/lifecycle/_explorer.json` | `355d8734fbb626fc…` | 108573 | `scripts/lower_tertiary/build_lifecycle_posters.py` | 946 |
| global_funnel | `reports/field-atlas/_atlas_feed.json` | `50e039377705d8ee…` | 602153 | `scripts/field_atlas/build_atlas_feed.py` | 947 |

## Record counts

- **fields** (Lower-Tertiary detail): 10
- **wells** (producing): 56
- **countries** (global funnel): 84
- **atlas_fields** (deduped global fields): 2032

## Bundle shape

- `schema_version` — projection schema version.
- `sources[]` — source snapshot provenance (path, sha256, bytes, generated_by, source issue).
- `record_counts` — field / well / country / atlas-field counts.
- `field_provenance` — per-field provenance strings (passthrough).
- `fields` — 10 Lower-Tertiary field payloads (metrics, economics, reservoir, risk/HPHT/decommission, landman, concept).
- `wells` — per-field roll-ups + 56 producing-well records.
- `atlas` — global funnel: countries + deduped fields.

### Economics basis (read before using `performance.npv_mm` / `performance.breakeven_wti`)

Per-field economics are **life-to-date, pre-tax, 10%-discounted** (`performance.economics_basis == "life_to_date_pretax_npv_at_10pct"`): the full sunk capital is charged against only the oil produced **to date**, not against full-cycle EUR. These are **not** full-cycle / sanctioned economics. For a field early in its life that is legitimately deep-negative, so such values are **withheld** — `npv_mm`, `breakeven_wti` and `sens_mm_per_dollar` are `null` and `performance.economics_status == "early_life"`. Only fields with `economics_status == "surfaced"` carry a client-credible life-to-date number (and it may still be negative — an expected life-to-date artifact for high-up-front-capital deepwater fields). A credible full-cycle recompute is tracked in worldenergydata#973.

All non-finite floats (NaN/Infinity) are sanitized to `null` for strict-JSON and HF-viewer compatibility.

## Publishing (gated next step — out of scope for this slice)

The actual push to the dedicated `worldenergydata` Hugging Face dataset (`huggingface_hub.upload_*`) requires an `HF_TOKEN` and an adversarially-reviewed plan + explicit user approval (see #965). At publish time the run is pinned to an immutable HF revision and the exact code revision is recorded per the #927 / #3427 contract. This exporter performs no network calls and no authentication.
