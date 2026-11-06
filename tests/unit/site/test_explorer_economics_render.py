"""Execute the shipped field renderer with synthetic stale economics, offline.

Hand-calculation source: OpenStax, Principles of Finance (2022), section 16.2,
equation 16.1 (present-value inflows minus outflows). With an immediate cost
of 100 and two units sold at p, NPV(p)=-100+2p, and breakeven p=50.
The production basis label follows the reviewed contract #976 (2026).
Node is required: a missing binary fails this release guard rather than skipping
execution of the shipped renderer.
"""

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


def render(page, performance):
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node is required to execute the shipped economics renderer")
    html = page.read_text(encoding="utf-8")
    function = "function renderField(" + html.split("function renderField(", 1)[1]
    function = function.split("function renderWells(", 1)[0]
    context = """
const PHASES = [];
const crumb = () => {};
const esc = s => String(s);
const rb = s => s;
const show = html => process.stdout.write(html);
"""
    field = {"id": "synthetic", "name": "Synthetic", "performance": performance}
    result = subprocess.run(
        [node, "-e", context + function + f"\nrenderField({{}}, {json.dumps(field)});"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
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


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
@pytest.mark.parametrize(
    "status", ["withheld", "early_life", "unavailable", None, "future"]
)
def test_rendering_never_leaks_populated_withheld_values(page, status):
    html, output = render(page, values(economics_status=status))
    assert "$-20" not in output and "$50" not in output
    assert 'href="#economics-gate"' in output
    assert 'id="economics-gate"' in html


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
@pytest.mark.parametrize(
    "changes", [{"economics_basis": None}, {"npv_mm": None}, {"breakeven_wti": "50"}]
)
def test_rendering_requires_known_basis_and_numeric_levels(page, changes):
    _, output = render(page, values(**changes))
    assert "$-20" not in output and "$50" not in output
    assert 'href="#economics-gate"' in output


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_surfaced_negative_npv_is_honestly_labelled(page):
    _, output = render(page, values())
    assert "$-20" in output and "$50" in output
    assert "NPV, life-to-date @10%" in output
    assert "LTD breakeven WTI @10%" in output


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
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
