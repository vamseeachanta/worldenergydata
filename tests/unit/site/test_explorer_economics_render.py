"""Execute the template and an independent build with synthetic economics.

Hand-calculation source: OpenStax, Principles of Finance (2022), section 16.2,
equation 16.1 (present-value inflows minus outflows). With an immediate cost
of 100 and two units sold at p, NPV(p)=-100+2p, and breakeven p=50.
The production basis label follows the reviewed contract #976 (2026).
Node is required: a missing binary fails this release guard rather than skipping
execution of the template and generated renderer.
"""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PAGES = [
    REPO / "reports/field-atlas/atlas_template.html",
    REPO / "reports/field-atlas/index.html",
]
PAGE_IDS = ["template", "generated-synthetic"]


@pytest.fixture
def page(request, tmp_path, monkeypatch):
    """Keep both renderer modes without restoring the withdrawn public roster."""
    notices = [
        PAGES[1],
        REPO / "reports/field-atlas/results/explorer_results_bundle.json",
    ]
    before = [path.read_bytes() for path in notices]
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(name, raising=False)
    if request.param == PAGES[0]:
        yield request.param
    else:
        spec = importlib.util.spec_from_file_location(
            "independent_atlas", REPO / "scripts/field_atlas/build_field_atlas.py"
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        roster = tmp_path / "roster.json"
        roster.write_text(
            json.dumps([{"name": "Synthetic field", "has_lifecycle": False}]),
            encoding="utf-8",
            newline="\n",
        )
        feed = tmp_path / "feed.json"
        feed.write_text('{"countries": []}', encoding="utf-8", newline="\n")
        monkeypatch.setattr(builder, "ROSTER", roster)
        monkeypatch.setattr(builder, "FEED", feed)
        html = builder.build()
        assert "Synthetic field" in html
        assert "function renderField(" in html
        output = tmp_path / "independent-atlas.html"
        output.write_text(html, encoding="utf-8", newline="\n")
        yield output
    for path, original in zip(notices, before):
        assert path.read_bytes() == original, "Committed availability notice changed"


def test_committed_atlas_is_a_notice_without_embedded_records():
    html = PAGES[1].read_text(encoding="utf-8")
    assert "held privately pending redistribution-terms review" in html
    assert 'id="economics-gate"' in html
    for marker in ("<script", "<table", "function renderField(", '"name":', '"block":'):
        assert marker not in html


def render(page, performance):
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node is required to execute the shipped economics renderer")
    html = page.read_text(encoding="utf-8")
    function = "function renderField(" + html.split("function renderField(", 1)[1]
    function = function.split("function renderWells(", 1)[0]
    # Include the shipped API, as the browser integration tests do. renderField
    # now mounts that API after writing the economics panel.
    visualization = html.split("// HF visualization API (#966).", 1)[1].split(
        "// End HF visualization API.", 1
    )[0]
    context = """
const assert = require('node:assert/strict');
const PHASES = [];
const crumb = () => {};
const esc = s => String(s);
const rb = s => s;
const show = html => process.stdout.write(html);
const target = {
  isConnected: true,
  children: [],
  replaceChildren(...children) { this.children = children; },
};
const $ = id => { assert.equal(id, 'x-hf-viz'); return target; };
const document = {
  getElementById: id => {
    assert.equal(id, 'hf-viz-config');
    return {textContent: '{}'};  // Unconfigured service: exercise offline fallback.
  },
  createElement: tag => ({tag}),
};
let fetchCalls = 0;
const fetch = async () => { fetchCalls++; throw new Error('Unexpected network call'); };
"""
    field = {"id": "synthetic", "name": "Synthetic", "performance": performance}
    checks = """
assert.equal(fetchCalls, 0, 'unconfigured visualization must stay offline');
assert.ok(target.children.some(child => child.tag === 'a' &&
  child.href.endsWith('/issues/966')), 'shipped API must render its fallback');
"""
    result = subprocess.run(
        [
            node,
            "-e",
            context
            + visualization
            + function
            + f"\nrenderField({{}}, {json.dumps(field)});"
            + checks,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return html, result.stdout


def values(**changes):
    """Independent hand example: NPV(p)=-100+2p; p=40 gives -20, BE=50."""
    return {
        "economics_status": "surfaced",
        "economics_basis": "life_to_date_pretax_npv_at_10pct",
        "npv_mm": -20.0,
        "breakeven_wti": 50.0,
        "sens_mm_per_dollar": 2.0,
        **changes,
    }


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS, indirect=True)
@pytest.mark.parametrize(
    "status", ["withheld", "early_life", "unavailable", None, "future"]
)
def test_rendering_never_leaks_populated_withheld_values(page, status):
    html, output = render(page, values(economics_status=status))
    assert "$-20" not in output and "$50" not in output
    assert 'href="#economics-gate"' in output
    assert 'id="economics-gate"' in html


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS, indirect=True)
@pytest.mark.parametrize(
    "changes", [{"economics_basis": None}, {"npv_mm": None}, {"breakeven_wti": "50"}]
)
def test_rendering_requires_known_basis_and_numeric_levels(page, changes):
    _, output = render(page, values(**changes))
    assert "$-20" not in output and "$50" not in output
    assert 'href="#economics-gate"' in output


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS, indirect=True)
def test_surfaced_negative_npv_is_honestly_labelled(page):
    _, output = render(page, values())
    assert "$-20" in output and "$50" in output
    assert "NPV, life-to-date @10%" in output
    assert "LTD breakeven WTI @10%" in output


@pytest.mark.parametrize("page", PAGES, ids=PAGE_IDS, indirect=True)
@pytest.mark.parametrize("boundary", ["html", "node"])
def test_rendering_decodes_utf8_under_legacy_locale(page, monkeypatch, boundary):
    """Exercise real HTML reads and Node output with cp1252 defaults."""
    if boundary == "html":
        monkeypatch.setattr(
            "io.text_encoding", lambda encoding, stacklevel=2: encoding or "cp1252"
        )
    else:
        monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")
    _, output = render(page, values(economics_status="withheld"))
    assert "n/a — economics withheld" in output


def test_rendering_requires_node(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda command: None)
    with pytest.raises(pytest.fail.Exception, match="Node is required"):
        render(PAGES[0], values())
