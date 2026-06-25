# ABOUTME: Tests for the subsea SVG symbol library (issue #574).
# ABOUTME: Key coverage of every graph-emitted symbol + render contract + manifest.
"""Tests for ``worldenergydata.field_development.symbols``."""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    available_symbols,
    concept_to_graph,
    has_symbol,
    render_symbol,
    render_layout,
)
from worldenergydata.field_development.symbols import SYMBOLS


def test_library_covers_every_symbol_the_mapper_can_emit():
    """Every `symbol` value concept_to_graph produces must resolve to a glyph."""
    emitted: set[str] = set()
    for ct in ConceptType:
        g = concept_to_graph(
            FieldConcept(name="X", concept_type=ct, num_wells=2, num_manifolds=1)
        )
        emitted.update(n.symbol for n in g.nodes)
    missing = {s for s in emitted if not has_symbol(s)}
    assert not missing, f"symbols missing from the library: {missing}"


def test_render_symbol_returns_group_with_title():
    out = render_symbol("manifold", 40, 40, 14)
    assert out.startswith("<g") and "<title>" in out and out.endswith("</g>")


def test_unknown_key_falls_back_gracefully():
    out = render_symbol("not_a_real_symbol", 10, 10, 12)
    assert out.startswith("<g") and "not_a_real_symbol" in out


def test_available_symbols_sorted_and_nonempty():
    syms = available_symbols()
    assert syms == sorted(syms)
    assert len(syms) >= 10


def test_every_symbol_renders_nonempty_svg_group():
    for key in available_symbols():
        out = render_symbol(key, 30, 30, 16)
        assert out.count("<g") == 1 and len(out) > 30


def test_layout_embeds_symbol_titles():
    svg = render_layout(
        FieldConcept(name="X", concept_type=ConceptType.SPAR, num_wells=2)
    )
    assert "<title>Spar</title>" in svg  # host glyph
    assert "<title>Dry tree / surface wellhead</title>" in svg


def test_export_writes_one_svg_per_symbol_and_manifest(tmp_path, monkeypatch):
    # Redirect output to a tmp dir to avoid touching the committed assets.
    monkeypatch.setattr(
        "worldenergydata.field_development.symbols.export_symbols.OUT_DIR", tmp_path
    )
    import worldenergydata.field_development.symbols.export_symbols as ex

    written = ex.write_all()
    svgs = list(tmp_path.glob("*.svg"))
    assert len(svgs) == len(SYMBOLS)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["symbols"] == available_symbols()
    assert Path(written[0]).suffix == ".svg"
