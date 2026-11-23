"""Execute the synthetic fixture in the portfolio authoring documentation.

Expected labels, unknown inputs and the source anchor are specified in
docs/data-sources/field-development/portfolio-authoring-example.md.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCUMENT = ROOT / "docs/data-sources/field-development/portfolio-authoring-example.md"


@pytest.fixture
def documented_example(tmp_path, monkeypatch):
    """Run the named fence verbatim with all output confined to tmp_path."""

    def reject(*args, **kwargs):
        raise AssertionError("The documented example must only render fixture facts")

    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr("worldenergydata.field_development.build_fdp_html", reject)
    monkeypatch.setattr(
        "worldenergydata.field_development.recommendation.recommend", reject
    )
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("FDP_EXAMPLE_OUTPUT_DIR", str(tmp_path))
    fences = re.findall(
        r"^```python portfolio-authoring-example\n(.*?)^```$",
        DOCUMENT.read_text(encoding="utf-8"),
        flags=re.MULTILINE | re.DOTALL,
    )
    (code,) = fences
    namespace = {"__name__": "__main__"}
    exec(compile(code, str(DOCUMENT), "exec"), namespace)
    return namespace


def test_documented_portfolio_example_preserves_unknowns(documented_example, tmp_path):
    """The fixture's unknown numerical inputs must stay unknown in the page."""
    output = tmp_path / "synthetic-example.html"
    assert set(tmp_path.iterdir()) == {output}
    page = output.read_text(encoding="utf-8")
    for label in (
        "Water depth (m)",
        "Wells (scope stated below)",
        "Designed peak capacity (boe/d)",
        "Reported oil capacity (bbl/d; not a boe/d plateau)",
        "Recoverable resources (MMboe)",
        "Actual first-oil year",
    ):
        assert f"<th>{label}</th><td>Unknown</td>" in page
    sections = dict(
        re.findall(r"<h2>(.*?)</h2>(.*?)(?=<h2>|</main>)", page, flags=re.DOTALL)
    )
    for heading in (
        "Architecture",
        "Recommended concept shortlist",
        "Economics and execution",
    ):
        assert "NOT_EVALUATED" in sections[heading]
    assert '<a href="#synthetic-source">synthetic-source</a>' in page
    assert '<li id="synthetic-source">' in page
    assert "https://example.invalid/portfolio-fixture" in page
    assert "not public evidence" in page
    assert page.index("<h2>Summary</h2>") < page.index("<h2>Revision history</h2>")
    assert page.index("<h2>Revision history</h2>") < page.index(
        "<h2>Engineering rationale</h2>"
    )


def test_documented_profile_requires_input_citation(documented_example):
    """The fixture populates concept_type and cites its synthetic source."""
    profile = documented_example["profile"]
    assert profile["concept_type"] == "semisub_fps"
    del profile["input_sources"]["concept_type"]
    with pytest.raises(ValueError, match="Missing input citation: concept_type"):
        documented_example["builder"].build_profile_page(profile)
