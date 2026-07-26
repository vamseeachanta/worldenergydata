"""Gates for the D&C drill-down explorer (dc-drilldown.html).

Field ▸ Block ▸ Bore is the reference drill-down surface of the report-hub
design system, so these pins lock its data completeness, self-containment,
and the honesty of its outbound engineering links.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "lower_tertiary" / "build_dc_drilldown.py"
OUT = REPO / "reports" / "lower_tertiary" / "dc-drilldown.html"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("build_dc_drilldown", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def payload(mod):
    return mod.load_payload()


def test_tree_shape(payload):
    assert len(payload["bores"]) == 253
    assert len(payload["fields"]) == 11
    assert len(payload["blocks"]) == 23


def test_every_block_belongs_to_exactly_one_field(payload):
    """The two browse axes are entry points into ONE tree — not a graph."""
    by_block = {}
    for b in payload["bores"]:
        by_block.setdefault(b["block"], set()).add(b["field"])
    assert all(len(v) == 1 for v in by_block.values())


def test_rollups_tie_to_the_matrix(payload):
    drill = sum(b["drill"] for b in payload["bores"])
    compl = sum(b["compl"] for b in payload["bores"])
    assert (drill, compl, drill + compl) == (12436, 12968, 25404)
    assert sum(f["drill"] + f["compl"] for f in payload["fields"]) == 25404
    assert sum(k["drill"] + k["compl"] for k in payload["blocks"]) == 25404


def test_absent_engineering_pages_are_honest_gaps(payload):
    """Verified live 2026-07-26 — these must be null, never fabricated links."""
    links = payload["links"]
    assert links["buckskin"]["lifecycle"] is None
    for slug in ("kaskida", "north_platte", "tiber"):
        assert links[slug]["economics"] is None
    assert links["stones"]["assets"] is not None
    assert links["big_foot"]["assets"] is None


def test_committed_page_is_regenerable(mod, payload):
    assert OUT.exists()
    assert mod.build_html(payload) == OUT.read_text(encoding="utf-8")


def test_page_is_self_contained():
    text = OUT.read_text(encoding="utf-8")
    assert "<link" not in text
    assert "<img" not in text
    assert "@import" not in text
    assert "src=" not in text  # no external script/iframe sources
    assert text.count("</script>") == 1


def test_embedded_payload_parses_and_cannot_break_out():
    """The JSON payload is inlined in a <script>; a raw </ would end it early."""
    text = OUT.read_text(encoding="utf-8")
    m = re.search(r"<script>const DATA=(\{.*\});\nconst \$=", text, re.S)
    assert m, "embedded payload not found"
    raw = m.group(1)
    assert "</" not in raw
    data = json.loads(raw.replace("<\\/", "</"))
    assert len(data["bores"]) == 253


def test_page_has_both_themes_and_deep_link_router():
    text = OUT.read_text(encoding="utf-8")
    assert "@media (prefers-color-scheme:dark)" in text
    assert ':root[data-theme="dark"]' in text
    assert ':root[data-theme="light"]' in text
    for route in ("#/field/", "#/block/", "#/bore/"):
        assert route in text
