#!/usr/bin/env python3
"""ABOUTME: Generate the GoM field-atlas browse page (Country→Domain→Region→Play→Field).
ABOUTME: Reads _roster.json (120 concept-matched fields) → interactive filter page (epic #764, issue #766).

The atlas is the browse funnel / front-of-house: it scales the flat capabilities list
into a filterable field catalog with honest density tiers (rich = has a life-cycle hub;
sample = concept data only; roadmap = name/block only). Rich fields open in place via
the Explorer shell (issue #946) and still link straight to their life-cycle poster.
The long tail (the full 1,390-field GoM atlas) is noted, not rendered as links.

The page markup lives in ``reports/field-atlas/atlas_template.html`` (same
convention as ``lifecycle_template.html``); this script substitutes the embedded
roster and injects the nav-spine crumb. The shell fetches
``../lifecycle/_explorer.json`` at runtime, so local preview needs an HTTP
server (``python3 -m http.server`` from ``public/``) — the funnel itself works
without it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import site_nav  # noqa: E402  (nav-spine helper, issue #850)

# Field identity resolves through THE canonical registry (config/fields.yml via
# worldenergydata.common.fields_registry) — no local name→id map lives here (#755).
from worldenergydata.common.fields_registry import load_fields  # noqa: E402

HERE = Path(__file__).resolve().parents[2] / "reports/field-atlas"
ROSTER = HERE / "_roster.json"
TEMPLATE_PATH = HERE / "atlas_template.html"


def build() -> str:
    fields = json.loads(ROSTER.read_text())
    registry = load_fields()
    for f in fields:
        f["lifecycle_id"] = (
            registry.resolve(f["name"]) if f.get("has_lifecycle") else None
        )
    roster_json = json.dumps(fields, ensure_ascii=False)
    template = TEMPLATE_PATH.read_text()
    return site_nav.inject_for(
        template.replace("__ROSTER_JSON__", roster_json), "atlas"
    )


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "index.html").write_text(build())
    print(
        f"  wrote {HERE / 'index.html'}  ({len(json.loads(ROSTER.read_text()))} fields)"
    )


if __name__ == "__main__":
    main()
