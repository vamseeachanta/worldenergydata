"""Tracked brand tokens as the single source for the capability generator (#908).

Both one-pager templates (PDF + interactive API) previously duplicated the same
:root token block. They now read it from one tracked file,
reports/capabilities/assets/tokens.css, so the navy/teal identity lives in one
editable place that non-generated pages can also link. Byte-identical output.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_TOKENS = _REPO / "reports" / "capabilities" / "assets" / "tokens.css"
_GEN = _REPO / "scripts" / "capabilities" / "build_onepagers.py"


def _load():
    spec = importlib.util.spec_from_file_location("onepagers_brand", _GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tokens_css_tracked_and_navy_teal():
    assert _TOKENS.exists(), "reports/capabilities/assets/tokens.css must exist"
    css = _TOKENS.read_text(encoding="utf-8")
    assert "--navy:#0B3D91" in css
    assert "--teal:#0f8a7e" in css


def test_generator_reads_tracked_tokens():
    mod = _load()
    # module reads the tracked file into _TOKENS
    assert mod._TOKENS == _TOKENS.read_text(encoding="utf-8").strip()
    # and a rendered page carries the resolved tokens
    spec = next(s for s in mod.SPECS if s.get("kind") == "work")
    html = mod._render_api_html(spec, mod._api_envelope(spec))
    assert ":root{--navy:#0B3D91" in html
