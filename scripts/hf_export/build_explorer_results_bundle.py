#!/usr/bin/env python3
# ABOUTME: Re-packages committed Field Explorer (#939) analysis JSON into a clean,
# ABOUTME: versioned, hashed results bundle + dataset card for the worldenergydata HF
# ABOUTME: dataset projection (#965, consuming the #927/#3427 dataset contract). Stdlib
# ABOUTME: only, no BSEE re-run, no network, no HF token. NaN/inf are sanitized to null.

"""Build the Field Explorer results bundle for Hugging Face publication.

This is the safe, disjoint first slice of #965: it ONLY re-packages already-committed
analysis JSON into a projection that conforms to the dedicated `worldenergydata` HF
dataset contract owned by #927 / workspace-hub#3427. It does not perform any HF push
(that step is HF_TOKEN-gated and out of scope here) and embeds no build timestamp
(the artifact must be reproducible byte-for-byte from the committed sources, so it does
not churn on every build).

Inputs (committed analysis results produced by the Explorer program #939):
  - reports/lower_tertiary/lifecycle/_explorer.json  (10 LT fields + 56 wells)
  - reports/field-atlas/_atlas_feed.json             (84 countries / 2,032 fields)

Outputs:
  - reports/field-atlas/results/explorer_results_bundle.json
  - reports/field-atlas/results/README.md            (dataset card / manifest)
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

# Bundle schema version. Bump on any breaking change to the projection shape.
SCHEMA_VERSION = "1.0.0"

# Dedicated Hugging Face dataset for this repository (never a combined domain-run
# store) — per the #927 / workspace-hub#3427 locked decision.
HF_DATASET = "worldenergydata"
PROJECTION = "field_explorer_results"

REPO = Path(__file__).resolve().parents[2]
EXPLORER_JSON = REPO / "reports" / "lower_tertiary" / "lifecycle" / "_explorer.json"
ATLAS_JSON = REPO / "reports" / "field-atlas" / "_atlas_feed.json"
OUT_DIR = REPO / "reports" / "field-atlas" / "results"
OUT_BUNDLE = OUT_DIR / "explorer_results_bundle.json"
OUT_CARD = OUT_DIR / "README.md"


def sanitize(obj):
    """Recursively replace non-finite floats (NaN/Infinity) with None.

    Python's json module tolerates these tokens, but strict JSON consumers and the
    Hugging Face dataset viewer reject them, so they must be nulled before publication.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_source(path: Path) -> tuple[dict, str, int]:
    """Load a JSON source and return (parsed, sha256_of_raw_bytes, byte_count)."""
    raw = path.read_bytes()
    return json.loads(raw), sha256_bytes(raw), len(raw)


def build_bundle() -> dict:
    explorer, exp_hash, exp_bytes = load_source(EXPLORER_JSON)
    atlas, atlas_hash, atlas_bytes = load_source(ATLAS_JSON)

    fields = explorer.get("fields", {})
    wells_block = explorer.get("wells", {})
    wells = wells_block.get("wells", [])
    countries = atlas.get("countries", [])
    atlas_fields = atlas.get("fields", [])

    # Per-field provenance passthrough (the source already embeds provenance strings).
    field_provenance = {fid: fdata.get("provenance") for fid, fdata in fields.items()}

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "hf_dataset": HF_DATASET,
        "projection": PROJECTION,
        "description": (
            "Field Explorer (#939) analysis results, re-packaged as a public, "
            "Hugging-Face-consumable dataset projection. Conforms to the dedicated "
            "worldenergydata HF dataset contract (#927 / workspace-hub#3427): "
            "public-data-only, content-hashed, schema-valid, immutably revisioned "
            "at publish time."
        ),
        # Provenance to the exact source snapshots. Content hashes (not a build
        # timestamp or a floating git ref) pin the inputs, so the bundle is
        # reproducible byte-for-byte and only changes when a source changes.
        "sources": [
            {
                "role": "field_detail",
                "path": "reports/lower_tertiary/lifecycle/_explorer.json",
                "sha256": exp_hash,
                "bytes": exp_bytes,
                "generated_by": explorer.get("meta", {}).get("generated_by"),
                "source_issue": explorer.get("meta", {}).get("issue"),
            },
            {
                "role": "global_funnel",
                "path": "reports/field-atlas/_atlas_feed.json",
                "sha256": atlas_hash,
                "bytes": atlas_bytes,
                "generated_by": atlas.get("meta", {}).get("generated_by"),
                "source_issue": atlas.get("meta", {}).get("issue"),
                "source_dataset": atlas.get("meta", {}).get("source"),
            },
        ],
        "record_counts": {
            "fields": len(fields),
            "wells": len(wells),
            "countries": len(countries),
            "atlas_fields": len(atlas_fields),
        },
        "field_provenance": field_provenance,
        "fields": fields,
        "wells": wells_block,
        "atlas": {
            "countries": countries,
            "fields": atlas_fields,
        },
    }
    return sanitize(bundle)


def render_card(bundle: dict) -> str:
    rc = bundle["record_counts"]
    src = bundle["sources"]
    lines = [
        "---",
        "# Hugging Face dataset card (front-matter placeholder).",
        "license: other  # public BSEE / public-disclosure basis; confirm at publish.",
        f"pretty_name: World Energy Field Explorer results ({PROJECTION})",
        "tags:",
        "  - energy",
        "  - offshore",
        "  - field-development",
        "---",
        "",
        "# World Energy Field Explorer — HF results projection",
        "",
        f"**Schema version:** `{bundle['schema_version']}`  ",
        f"**Dedicated HF dataset:** `{bundle['hf_dataset']}` (never a combined "
        "domain-run store)  ",
        f"**Projection:** `{bundle['projection']}`",
        "",
        bundle["description"],
        "",
        "## Provenance / contract",
        "",
        "This projection re-packages already-committed Field Explorer (#939) analysis "
        "results. It consumes — and does not re-derive — the dedicated "
        "`worldenergydata` Hugging Face dataset contract owned by "
        "[#927](https://github.com/vamseeachanta/worldenergydata/issues/927) and "
        "[workspace-hub#3427](https://github.com/vamseeachanta/workspace-hub/issues/3427): "
        "public-data-only, immutable revisions, run identity, content hashes, and "
        "provenance to the exact source snapshot + code revision.",
        "",
        "### Source snapshots (content-hashed)",
        "",
        "| role | path | sha256 | bytes | generated_by | source issue |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s in src:
        lines.append(
            "| {role} | `{path}` | `{sha}` | {bytes} | `{gen}` | {iss} |".format(
                role=s["role"],
                path=s["path"],
                sha=s["sha256"][:16] + "…",
                bytes=s["bytes"],
                gen=s.get("generated_by"),
                iss=s.get("source_issue"),
            )
        )
    lines += [
        "",
        "## Record counts",
        "",
        f"- **fields** (Lower-Tertiary detail): {rc['fields']}",
        f"- **wells** (producing): {rc['wells']}",
        f"- **countries** (global funnel): {rc['countries']}",
        f"- **atlas_fields** (deduped global fields): {rc['atlas_fields']}",
        "",
        "## Bundle shape",
        "",
        "- `schema_version` — projection schema version.",
        "- `sources[]` — source snapshot provenance (path, sha256, bytes, "
        "generated_by, source issue).",
        "- `record_counts` — field / well / country / atlas-field counts.",
        "- `field_provenance` — per-field provenance strings (passthrough).",
        "- `fields` — 10 Lower-Tertiary field payloads (metrics, economics, "
        "reservoir, risk/HPHT/decommission, landman, concept).",
        "- `wells` — per-field roll-ups + 56 producing-well records.",
        "- `atlas` — global funnel: countries + deduped fields.",
        "",
        "### Economics basis (read before using `performance.npv_mm` / "
        "`performance.breakeven_wti`)",
        "",
        "Per-field economics are **life-to-date, pre-tax, 10%-discounted** "
        "(`performance.economics_basis == \"life_to_date_pretax_npv_at_10pct\"`): the "
        "full sunk capital is charged against only the oil produced **to date**, not "
        "against full-cycle EUR. These are **not** full-cycle economics. "
        "For a field early in its life that is legitimately deep-negative, so such "
        "values are **withheld** — `npv_mm`, `breakeven_wti` and `sens_mm_per_dollar` "
        "are `null` and `performance.economics_status == \"early_life\"`. Only fields "
        "with `economics_status == \"surfaced\"` carry a client-credible life-to-date "
        "number (and it may still be negative — an expected life-to-date artifact for "
        "high-up-front-capital deepwater fields). A credible full-cycle recompute is "
        "tracked in worldenergydata#973.",
        "",
        "All non-finite floats (NaN/Infinity) are sanitized to `null` for strict-JSON "
        "and HF-viewer compatibility.",
        "",
        "## Publishing (gated next step — out of scope for this slice)",
        "",
        "The actual push to the dedicated `worldenergydata` Hugging Face dataset "
        "(`huggingface_hub.upload_*`) requires an `HF_TOKEN` and an "
        "adversarially-reviewed plan + explicit user approval (see #965). At publish "
        "time the run is pinned to an immutable HF revision and the exact code "
        "revision is recorded per the #927 / #3427 contract. This exporter performs "
        "no network calls and no authentication.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    bundle = build_bundle()

    serialized = json.dumps(
        bundle, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    )
    # Hard guard: strict JSON must contain no NaN/Infinity tokens.
    assert "NaN" not in serialized, "NaN token leaked into bundle serialization"
    assert "Infinity" not in serialized, "Infinity token leaked into bundle"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_BUNDLE.write_text(serialized + "\n", encoding="utf-8")
    OUT_CARD.write_text(render_card(bundle), encoding="utf-8")

    rc = bundle["record_counts"]
    print(f"wrote {OUT_BUNDLE.relative_to(REPO)} ({len(serialized)} bytes)")
    print(f"wrote {OUT_CARD.relative_to(REPO)}")
    print(f"record_counts: {rc}")


if __name__ == "__main__":
    main()
