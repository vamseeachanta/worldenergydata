# ABOUTME: Build the client-facing field-development capability showcase HTML.
# ABOUTME: Issue #567 — thin glue over field_development.showcase.
"""Build the field-development **capability showcase** — a single self-contained
HTML page for clients that (1) explains the playbook pipeline, (2) shows real
generated schematics for exemplar fields across offshore areas, and (3)
quantifies how many fields we can schematize today, by area.

Run:
    PYTHONPATH=... .venv/bin/python scripts/field_development/build_capability_showcase.py

Output: reports/field_development/showcase/index.html (self-contained, no assets).
"""

from __future__ import annotations

from pathlib import Path

from worldenergydata.field_development.showcase import build_showcase_html
from worldenergydata.field_development.subseaiq import load_subseaiq_fields

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "field_development" / "showcase" / "index.html"

# Curated exemplars (one verified field per area) — produced + render-checked by
# the showcase-exemplar-curation workflow; each engine pick was made blind (the
# field's as-built concept stripped) and matched the real concept.
EXEMPLARS: list[dict] = [
    {
        "area": "Gulf of Mexico",
        "field_name": "Thunder Horse",
        "blurb": "BP's iconic Thunder Horse in 1,829 m of Gulf of Mexico water — the "
        "engine independently picks its as-built semisub FPS concept from "
        "stripped parameters, both schematics rendering clean.",
    },
    {
        "area": "North Sea & NW Europe",
        "field_name": "Rosebank",
        "blurb": "Rosebank, the UK's largest undeveloped field in 1,128 m West of "
        "Shetland — the engine picks FPSO from raw parameters, matching the "
        "selected concept.",
    },
    {
        "area": "Brazil",
        "field_name": "Lula (Tupi)",
        "blurb": "Lula (Tupi), Brazil's 2,140 m pre-salt giant — from depth and "
        "reservoir parameters alone the engine reproduces Petrobras's real "
        "FPSO selection.",
    },
    {
        "area": "West Africa",
        "field_name": "Egina",
        "blurb": "Egina, Total's 1,550 m flagship Nigerian deepwater FPSO — the "
        "engine recovers its FPSO concept blind.",
    },
    {
        "area": "Asia-Pacific",
        "field_name": "Bayu-Undan",
        "blurb": "Bayu-Undan, the Timor Sea gas-condensate hub feeding Darwin LNG — "
        "a label-stripped probe reproduces its as-built fixed-jacket concept.",
    },
]


def main() -> int:
    fields = load_subseaiq_fields(enrich_facilities=True)
    html = build_showcase_html(EXEMPLARS, fields)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(html, encoding="utf-8")
    print(f"wrote {_OUT} ({len(html):,} bytes, {len(EXEMPLARS)} exemplars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
