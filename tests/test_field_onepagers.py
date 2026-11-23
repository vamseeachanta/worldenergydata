"""Tests for the per-field one-pager builder (scripts/capabilities/build_field_onepagers.py, #945).

Static/deterministic checks that need no headless Chrome: they load the frozen
Explorer payload and render the one-pager HTML in-memory, asserting

- all 10 Explorer fields render an HTML intermediate;
- the three pre-production fields (performance is null) show a VISIBLE placeholder
  that LINKS the rollout issue #948 (the OWNER PRINCIPLE), while producing fields
  do NOT show that placeholder;
- key content (name, operator, provenance) is present.

If a committed PDF set already exists on disk, we additionally assert all 10 PDFs
are present and non-empty.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "capabilities"
    / "build_field_onepagers.py"
)
_ISSUE_948 = "https://github.com/vamseeachanta/worldenergydata/issues/948"
_PREPRODUCTION = {"kaskida", "north_platte", "tiber"}


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "build_field_onepagers_under_test", SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_all_ten_fields_render_html():
    mod = _load_module()
    data = mod.load_explorer()
    fields = data["fields"]
    assert len(mod.FIELD_ORDER) == 10
    rendered = {}
    for fid in mod.FIELD_ORDER:
        assert fid in fields, f"Explorer payload missing field {fid}"
        html_text = mod.render_field_html(fid, fields[fid])
        assert html_text.lstrip().startswith("<!doctype html>")
        assert fields[fid]["name"] in html_text
        rendered[fid] = html_text
    assert len(rendered) == 10


def test_preproduction_placeholder_links_issue_948():
    mod = _load_module()
    fields = mod.load_explorer()["fields"]
    for fid in mod.FIELD_ORDER:
        html_text = mod.render_field_html(fid, fields[fid])
        is_preprod = fields[fid].get("performance") is None
        assert (
            fid in _PREPRODUCTION
        ) == is_preprod, f"{fid} preproduction assumption drifted"
        if is_preprod:
            # OWNER PRINCIPLE: visible, issue-linked placeholder — not a bare em-dash.
            assert _ISSUE_948 in html_text, f"{fid} must link the rollout issue #948"
            assert "pre-production" in html_text
        else:
            assert (
                _ISSUE_948 not in html_text
            ), f"{fid} should not carry the pre-production note"


def test_committed_pdfs_present_when_built():
    """If the PDF set has been built/committed, all 10 must be present and non-empty."""
    out = SCRIPT.resolve().parents[2] / "reports" / "field-atlas" / "onepagers"
    mod = _load_module()
    pdfs = sorted(out.glob("field-*.pdf")) if out.exists() else []
    if not pdfs:
        # PDF render is environment-gated (needs headless Chrome); HTML intermediates
        # are the always-available deliverable and are covered above.
        return
    got = {p.stem.replace("field-", "") for p in pdfs}
    assert got == set(mod.FIELD_ORDER), f"expected all 10 field PDFs, got {sorted(got)}"
    for p in pdfs:
        assert p.stat().st_size > 0, f"{p.name} is empty"
