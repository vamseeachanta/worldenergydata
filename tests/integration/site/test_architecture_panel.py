# ABOUTME: Architecture-drawing panel gate (issue #969, epic #942) — asserts the
# ABOUTME: per-field `architecture` payload (plan-view SVG for 3, placeholder for 7).

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
EXPLORER = REPO / "reports/lower_tertiary/lifecycle/_explorer.json"

# Exactly the 3 LT fields with a committed, authored FieldConcept (real geometry).
AUTHORED = {"cascade_chinook", "julia", "stones"}
# The FDP-authoring backlog issue the concept-less placeholder links (#759/#962).
PENDING_ISSUE = 962
# PDF-portability forbidden constructs (.claude/rules/svg-pdf-portability.md).
FORBIDDEN_SVG = ("<pattern", "clip-path", "clipPath", "<filter", "<mask", "url(#")
# Raw-SVG-in-`<script>const FIELD=…` embed safety (r2 finding #2).
SCRIPT_BREAKERS = ("</script", "`", "${")


def _explorer():
    return json.loads(EXPLORER.read_text(encoding="utf-8"))


def _fields():
    return _explorer()["fields"]


def _authored_svgs():
    fields = _fields()
    return {fid: fields[fid]["architecture"]["svg"] for fid in AUTHORED}


# --- 1. key present on every field -----------------------------------------
def test_architecture_key_present_all_fields():
    fields = _fields()
    missing = [fid for fid, f in fields.items() if "architecture" not in f]
    assert not missing, f"fields without an architecture key: {missing}"


# --- 2. real SVG for the authored three ------------------------------------
def test_architecture_svg_for_authored_three():
    fields = _fields()
    for fid in AUTHORED:
        arch = fields[fid]["architecture"]
        assert arch["svg"], f"{fid}: architecture.svg empty"
        assert arch["svg"].startswith("<svg"), f"{fid}: svg does not start with <svg"
        assert arch["source"] == "render_layout", fid
        assert arch.get("caption"), f"{fid}: architecture caption missing"
    # r2 DECISION (§3.3): honest scope — the Chinook-only tieback concept.
    assert (
        fields["cascade_chinook"]["architecture"]["caption"] == "Chinook subsea tieback"
    )


# --- 3. placeholder for the other seven ------------------------------------
def test_architecture_placeholder_for_seven():
    fields = _fields()
    placeholder = {fid for fid in fields if fid not in AUTHORED}
    assert len(placeholder) == 7, placeholder
    for fid in placeholder:
        arch = fields[fid]["architecture"]
        assert arch["svg"] is None, f"{fid}: expected placeholder (svg None)"
        assert arch["pending_issue"] == PENDING_ISSUE, fid


# --- 4. embedded SVG is PDF-portable ---------------------------------------
def test_architecture_svg_pdf_portable():
    bad = []
    for fid, svg in _authored_svgs().items():
        for token in FORBIDDEN_SVG:
            if token in svg:
                bad.append((fid, token))
    assert not bad, f"PDF-non-portable constructs in architecture SVG: {bad}"


# --- 5. the sidecar JSON is valid (no NaN/Infinity literals) ---------------
def test_explorer_json_no_nan_inf():
    raw = EXPLORER.read_text(encoding="utf-8")
    for token in ("NaN", "Infinity", "-Infinity"):
        assert token not in raw, f"{token} literal in _explorer.json (invalid JSON)"


# --- 8. the concept-source helper ------------------------------------------
def test_portfolio_concepts_helper():
    from worldenergydata.field_development.models import FieldConcept
    from worldenergydata.field_development.portfolio_concepts import concept_for

    for fid in AUTHORED:
        c = concept_for(fid)
        assert isinstance(c, FieldConcept), f"{fid}: expected a FieldConcept"
    fields = _fields()
    for fid in fields:
        if fid not in AUTHORED:
            assert concept_for(fid) is None, f"{fid}: expected None"
    assert concept_for("does_not_exist") is None


# --- 9. raw-SVG embed cannot forge a </script> terminator ------------------
def test_architecture_svg_no_script_terminator():
    bad = []
    for fid, svg in _authored_svgs().items():
        for token in SCRIPT_BREAKERS:
            if token in svg:
                bad.append((fid, token))
    assert not bad, f"script-breaking tokens in architecture SVG: {bad}"


# --- sanity: the SVG survives JSON round-trip inside the poster embed -------
def test_architecture_svg_matches_render_layout():
    from worldenergydata.field_development.layout import render_layout
    from worldenergydata.field_development.portfolio_concepts import concept_for

    fields = _fields()
    for fid in AUTHORED:
        expected = render_layout(concept_for(fid))
        assert fields[fid]["architecture"]["svg"] == expected, fid


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
