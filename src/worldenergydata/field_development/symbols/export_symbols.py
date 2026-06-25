# ABOUTME: Regenerates the standalone preview SVGs + manifest for the symbol lib.
# ABOUTME: Issue #574 — run to refresh symbols/*.svg after editing symbols.py.
"""
Write one standalone preview SVG per symbol plus a ``manifest.json`` index.

Run: ``uv run python -m worldenergydata.field_development.symbols.export_symbols``

The library in ``symbols.py`` is the source of truth; these files are generated
artifacts (handy for docs/design review). A unit test asserts the manifest lists
exactly the library's keys, so they can't drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.field_development.symbols import (
    SYMBOLS,
    available_symbols,
    render_symbol,
)

OUT_DIR = Path(__file__).parent
BOX = 80.0  # preview canvas


def _preview_svg(key: str) -> str:
    glyph = render_symbol(key, BOX / 2, BOX / 2, size=24.0)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BOX:.0f}" '
        f'height="{BOX:.0f}" viewBox="0 0 {BOX:.0f} {BOX:.0f}">'
        f'<rect width="100%" height="100%" fill="white"/>{glyph}</svg>\n'
    )


def write_all() -> list[Path]:
    written: list[Path] = []
    for key in available_symbols():
        p = OUT_DIR / f"{key}.svg"
        p.write_text(_preview_svg(key), encoding="utf-8")
        written.append(p)
    manifest = {
        "count": len(SYMBOLS),
        "symbols": available_symbols(),
        "note": "Original schematic artwork — generated from symbols.py.",
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    written.append(OUT_DIR / "manifest.json")
    return written


if __name__ == "__main__":
    paths = write_all()
    print(f"wrote {len(paths)} files to {OUT_DIR}")
