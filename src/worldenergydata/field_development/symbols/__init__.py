# ABOUTME: Custom subsea/field-layout SVG symbol library (original artwork).
# ABOUTME: Issue #574 (epic #567) — glyphs keyed by GraphSpec node `symbol`s.
"""
worldenergydata.field_development.symbols
=========================================

A small, bounded library of **original** SVG glyphs for subsea hardware and host
facilities — the symbols that standard P&ID/ISA libraries don't provide. Both
renderers (#572 block diagram, #573 plan view) reference these by the ``symbol``
key the graph mapper (#571) assigns to each node.

Each symbol is a parametric function ``f(cx, cy, size) -> str`` returning an SVG
``<g>`` fragment centred on ``(cx, cy)`` and roughly ``2*size`` across, so the
same artwork serves a small block-diagram icon and a larger map marker.

Artwork is schematic and original (simple geometric primitives) — license-clean,
no copied standard artwork. Conventions loosely follow common subsea drawing
practice (ANSI/ISA-5.1 informs style only).

Use :func:`render_symbol` to draw one, :func:`available_symbols` to list keys,
and ``export_symbols.py`` to regenerate the standalone preview SVGs in this
directory.
"""

from __future__ import annotations

from collections.abc import Callable

_DARK = "#234e78"
_ACCENT = "#a8620a"


def _wrap(cx: float, cy: float, body: str, title: str) -> str:
    return f'<g class="sym"><title>{title}</title>{body}</g>'


def _subsea_tree(cx: float, cy: float, s: float) -> str:
    # Wellhead base + two valve "bowties" on a vertical run (a wet christmas tree).
    b = (
        f'<line x1="{cx:.1f}" y1="{cy + s:.1f}" x2="{cx:.1f}" y2="{cy - s:.1f}" '
        f'stroke="{_DARK}" stroke-width="2"/>'
        f'<rect x="{cx - s * 0.7:.1f}" y="{cy + s * 0.5:.1f}" width="{s * 1.4:.1f}" '
        f'height="{s * 0.5:.1f}" fill="{_DARK}"/>'
    )
    for dy in (-0.35, 0.15):
        y = cy + s * dy
        b += (
            f'<polygon points="{cx - s * 0.5:.1f},{y - s * 0.3:.1f} '
            f"{cx + s * 0.5:.1f},{y + s * 0.3:.1f} {cx + s * 0.5:.1f},{y - s * 0.3:.1f} "
            f'{cx - s * 0.5:.1f},{y + s * 0.3:.1f}" fill="#eccff2" stroke="#6a1b80" '
            f'stroke-width="1.2"/>'
        )
    return _wrap(cx, cy, b, "Subsea tree (wet XT)")


def _dry_tree(cx: float, cy: float, s: float) -> str:
    b = (
        f'<line x1="{cx:.1f}" y1="{cy + s:.1f}" x2="{cx:.1f}" y2="{cy - s:.1f}" '
        f'stroke="#6a1b80" stroke-width="2"/>'
        f'<circle cx="{cx:.1f}" cy="{cy - s * 0.7:.1f}" r="{s * 0.4:.1f}" '
        f'fill="#eccff2" stroke="#6a1b80" stroke-width="1.2"/>'
        f'<rect x="{cx - s * 0.6:.1f}" y="{cy + s * 0.6:.1f}" width="{s * 1.2:.1f}" '
        f'height="{s * 0.4:.1f}" fill="#6a1b80"/>'
    )
    return _wrap(cx, cy, b, "Dry tree / surface wellhead")


def _manifold(cx: float, cy: float, s: float) -> str:
    b = (
        f'<rect x="{cx - s:.1f}" y="{cy - s * 0.6:.1f}" width="{s * 2:.1f}" '
        f'height="{s * 1.2:.1f}" rx="3" fill="#ffe9c7" stroke="{_ACCENT}" '
        f'stroke-width="1.5"/>'
    )
    for dx in (-0.6, -0.2, 0.2, 0.6):  # header stubs
        x = cx + s * 2 * dx / 2
        b += (
            f'<line x1="{x:.1f}" y1="{cy + s * 0.6:.1f}" x2="{x:.1f}" '
            f'y2="{cy + s:.1f}" stroke="{_ACCENT}" stroke-width="1.5"/>'
        )
    return _wrap(cx, cy, b, "Subsea manifold")


def _plet(cx: float, cy: float, s: float) -> str:
    b = (
        f'<rect x="{cx - s * 0.8:.1f}" y="{cy - s * 0.5:.1f}" width="{s * 1.6:.1f}" '
        f'height="{s:.1f}" fill="#ffe9c7" stroke="{_ACCENT}" stroke-width="1.5"/>'
        f'<line x1="{cx + s * 0.8:.1f}" y1="{cy:.1f}" x2="{cx + s * 1.3:.1f}" '
        f'y2="{cy:.1f}" stroke="{_ACCENT}" stroke-width="2"/>'
    )
    return _wrap(cx, cy, b, "PLET (pipeline end termination)")


def _export(cx: float, cy: float, s: float) -> str:
    b = (
        f'<polygon points="{cx - s:.1f},{cy - s * 0.5:.1f} {cx + s * 0.3:.1f},'
        f"{cy - s * 0.5:.1f} {cx + s * 0.3:.1f},{cy - s:.1f} {cx + s:.1f},{cy:.1f} "
        f"{cx + s * 0.3:.1f},{cy + s:.1f} {cx + s * 0.3:.1f},{cy + s * 0.5:.1f} "
        f'{cx - s:.1f},{cy + s * 0.5:.1f}" fill="#dddddd" stroke="#555" '
        f'stroke-width="1.2"/>'
    )
    return _wrap(cx, cy, b, "Export")


def _existing_host(cx: float, cy: float, s: float) -> str:
    b = (
        f'<rect x="{cx - s:.1f}" y="{cy - s * 0.7:.1f}" width="{s * 2:.1f}" '
        f'height="{s * 1.4:.1f}" fill="#cde2f7" stroke="{_DARK}" stroke-width="1.5" '
        f'stroke-dasharray="5 3"/>'
        f'<line x1="{cx - s * 0.5:.1f}" y1="{cy - s * 0.7:.1f}" x2="{cx - s * 0.5:.1f}" '
        f'y2="{cy - s * 1.1:.1f}" stroke="{_DARK}" stroke-width="2"/>'
        f'<line x1="{cx + s * 0.5:.1f}" y1="{cy - s * 0.7:.1f}" x2="{cx + s * 0.5:.1f}" '
        f'y2="{cy - s * 1.1:.1f}" stroke="{_DARK}" stroke-width="2"/>'
    )
    return _wrap(cx, cy, b, "Existing host (tieback)")


def _deck_legs(
    cx: float, cy: float, s: float, body_fill: str, title: str, legs: str
) -> str:
    deck = (
        f'<rect x="{cx - s:.1f}" y="{cy - s:.1f}" width="{s * 2:.1f}" '
        f'height="{s * 0.7:.1f}" fill="{body_fill}" stroke="{_DARK}" '
        f'stroke-width="1.5"/>'
    )
    return _wrap(cx, cy, deck + legs, title)


def _fixed_jacket(cx: float, cy: float, s: float) -> str:
    legs = (
        f'<polygon points="{cx - s * 0.8:.1f},{cy - s * 0.3:.1f} '
        f"{cx + s * 0.8:.1f},{cy - s * 0.3:.1f} {cx + s * 0.4:.1f},{cy + s:.1f} "
        f'{cx - s * 0.4:.1f},{cy + s:.1f}" fill="none" stroke="{_DARK}" '
        f'stroke-width="1.3"/>'
        f'<line x1="{cx - s * 0.6:.1f}" y1="{cy - s * 0.3:.1f}" x2="{cx + s * 0.2:.1f}" '
        f'y2="{cy + s:.1f}" stroke="{_DARK}" stroke-width="1"/>'
        f'<line x1="{cx + s * 0.6:.1f}" y1="{cy - s * 0.3:.1f}" x2="{cx - s * 0.2:.1f}" '
        f'y2="{cy + s:.1f}" stroke="{_DARK}" stroke-width="1"/>'
    )
    return _deck_legs(cx, cy, s, "#cde2f7", "Fixed jacket platform", legs)


def _compliant_tower(cx: float, cy: float, s: float) -> str:
    legs = (
        f'<rect x="{cx - s * 0.35:.1f}" y="{cy - s * 0.3:.1f}" width="{s * 0.7:.1f}" '
        f'height="{s * 1.3:.1f}" fill="none" stroke="{_DARK}" stroke-width="1.2"/>'
        f'<line x1="{cx - s * 0.35:.1f}" y1="{cy:.1f}" x2="{cx + s * 0.35:.1f}" '
        f'y2="{cy + s * 0.5:.1f}" stroke="{_DARK}" stroke-width="0.9"/>'
        f'<line x1="{cx + s * 0.35:.1f}" y1="{cy:.1f}" x2="{cx - s * 0.35:.1f}" '
        f'y2="{cy + s * 0.5:.1f}" stroke="{_DARK}" stroke-width="0.9"/>'
    )
    return _deck_legs(cx, cy, s, "#cde2f7", "Compliant tower", legs)


def _tlp(cx: float, cy: float, s: float) -> str:
    legs = (
        f'<rect x="{cx - s * 0.8:.1f}" y="{cy + s * 0.4:.1f}" width="{s * 1.6:.1f}" '
        f'height="{s * 0.4:.1f}" fill="#cde2f7" stroke="{_DARK}" stroke-width="1.2"/>'
    )
    for dx in (-0.55, 0.55):  # taut vertical tendons
        x = cx + s * dx
        legs += (
            f'<line x1="{x:.1f}" y1="{cy - s * 0.3:.1f}" x2="{x:.1f}" '
            f'y2="{cy + s * 0.4:.1f}" stroke="{_DARK}" stroke-width="1.6"/>'
        )
    return _deck_legs(cx, cy, s, "#cde2f7", "TLP (tension leg platform)", legs)


def _spar(cx: float, cy: float, s: float) -> str:
    legs = (
        f'<rect x="{cx - s * 0.3:.1f}" y="{cy - s * 0.3:.1f}" width="{s * 0.6:.1f}" '
        f'height="{s * 1.5:.1f}" rx="3" fill="#cde2f7" stroke="{_DARK}" '
        f'stroke-width="1.5"/>'
    )
    return _deck_legs(cx, cy, s, "#cde2f7", "Spar", legs)


def _semisub_fps(cx: float, cy: float, s: float) -> str:
    legs = ""
    for dx in (-0.65, 0.65):
        x = cx + s * dx
        legs += (
            f'<line x1="{x:.1f}" y1="{cy - s * 0.3:.1f}" x2="{x:.1f}" '
            f'y2="{cy + s * 0.6:.1f}" stroke="{_DARK}" stroke-width="1.6"/>'
        )
    legs += (  # two pontoons
        f'<rect x="{cx - s:.1f}" y="{cy + s * 0.6:.1f}" width="{s * 0.7:.1f}" '
        f'height="{s * 0.4:.1f}" fill="#cde2f7" stroke="{_DARK}" stroke-width="1.2"/>'
        f'<rect x="{cx + s * 0.3:.1f}" y="{cy + s * 0.6:.1f}" width="{s * 0.7:.1f}" '
        f'height="{s * 0.4:.1f}" fill="#cde2f7" stroke="{_DARK}" stroke-width="1.2"/>'
    )
    return _deck_legs(cx, cy, s, "#cde2f7", "Semisubmersible FPS", legs)


def _hull(cx: float, cy: float, s: float, title: str, tanks: bool) -> str:
    # Ship-shaped hull (FPSO / FLNG).
    b = (
        f'<path d="M {cx - s:.1f} {cy - s * 0.5:.1f} L {cx + s * 0.7:.1f} '
        f"{cy - s * 0.5:.1f} L {cx + s:.1f} {cy:.1f} L {cx + s * 0.7:.1f} "
        f'{cy + s * 0.5:.1f} L {cx - s:.1f} {cy + s * 0.5:.1f} Z" '
        f'fill="#cde2f7" stroke="{_DARK}" stroke-width="1.5"/>'
    )
    if tanks:
        for dx in (-0.5, 0.0, 0.45):
            b += (
                f'<circle cx="{cx + s * dx:.1f}" cy="{cy:.1f}" r="{s * 0.22:.1f}" '
                f'fill="none" stroke="{_DARK}" stroke-width="1"/>'
            )
    return _wrap(cx, cy, b, title)


def _fpso(cx: float, cy: float, s: float) -> str:
    return _hull(cx, cy, s, "FPSO", tanks=False)


def _flng(cx: float, cy: float, s: float) -> str:
    return _hull(cx, cy, s, "FLNG", tanks=True)


def _onshore_terminal(cx: float, cy: float, s: float) -> str:
    b = (
        f'<line x1="{cx - s:.1f}" y1="{cy + s * 0.6:.1f}" x2="{cx + s:.1f}" '
        f'y2="{cy + s * 0.6:.1f}" stroke="#7a5" stroke-width="2.5"/>'  # shoreline
    )
    for dx in (-0.5, 0.1, 0.6):
        b += (
            f'<rect x="{cx + s * dx:.1f}" y="{cy - s * 0.2:.1f}" width="{s * 0.35:.1f}" '
            f'height="{s * 0.6:.1f}" fill="#cde2f7" stroke="{_DARK}" stroke-width="1"/>'
        )
    return _wrap(cx, cy, b, "Onshore terminal")


def _nui(cx: float, cy: float, s: float) -> str:
    legs = ""
    for dx in (-0.5, 0.5):
        x = cx + s * dx
        legs += (
            f'<line x1="{x:.1f}" y1="{cy - s * 0.3:.1f}" x2="{x:.1f}" '
            f'y2="{cy + s:.1f}" stroke="{_DARK}" stroke-width="1.4"/>'
        )
    return _deck_legs(cx, cy, s, "#dfeaf7", "NUI / minimal facility", legs)


SYMBOLS: dict[str, Callable[[float, float, float], str]] = {
    "subsea_tree": _subsea_tree,
    "dry_tree": _dry_tree,
    "manifold": _manifold,
    "plet": _plet,
    "export": _export,
    "existing_host": _existing_host,
    "onshore_terminal": _onshore_terminal,
    "fixed_jacket": _fixed_jacket,
    "compliant_tower": _compliant_tower,
    "tlp": _tlp,
    "spar": _spar,
    "semisub_fps": _semisub_fps,
    "fpso": _fpso,
    "flng": _flng,
    "nui": _nui,
}


def available_symbols() -> list[str]:
    """Sorted list of symbol keys this library provides."""
    return sorted(SYMBOLS)


def has_symbol(key: str) -> bool:
    return key in SYMBOLS


def render_symbol(key: str, cx: float, cy: float, size: float = 14.0) -> str:
    """Return an SVG ``<g>`` fragment for ``key`` centred at ``(cx, cy)``.

    Falls back to a neutral circle for an unknown key so a renderer never breaks
    on a new node type (the test suite asserts full coverage of emitted keys).
    """
    fn = SYMBOLS.get(key)
    if fn is None:
        return (
            f'<g class="sym"><title>{key}</title>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size * 0.5:.1f}" '
            f'fill="#eee" stroke="#999" stroke-width="1.2"/></g>'
        )
    return fn(cx, cy, size)
