"""Reader-support contracts for the benchmark's report-hub design."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from worldenergydata.production.unified.benchmark_report import render_benchmark_html

REPO = Path(__file__).resolve().parents[4]
REPORT = REPO / "reports" / "field_benchmark"


class _Page(HTMLParser):
    """Collect container text, links and identifiers without layout assumptions."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.stack = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "links": []}
        self.nodes.append(node)
        if tag == "a":
            for parent in self.stack:
                parent["links"].append(node)
        if tag not in {"meta", "br", "hr", "link", "img", "input"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in reversed(range(len(self.stack))):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, text):
        for node in self.stack:
            node["text"] += text

    def labelled(self, label):
        nodes = [n for n in self.nodes if n["attrs"].get("aria-label") == label]
        assert len(nodes) == 1, f"expected one {label}"
        return nodes[0]


@pytest.fixture(params=["empty", "mixed", "concepts"])
def benchmark_facts(request):
    if request.param == "empty":
        return {}
    result = {
        "rows": [
            {
                "region": status,
                "field_name": f"Example {status}",
                "provenance": status,
                "peak_oil_bbl": 1234.0,
                "govt_take": 12.3,
                "disc_posttax_cf_usd": 5678.0,
            }
            for status in ("real", "seed")
        ],
        "region_status": {"real": "real", "seed": "seed", "empty": "screening-only"},
        "skipped_empty": ["empty"],
    }
    if request.param == "concepts":
        result["concept_mix"] = {"example": {"unknown": 1}}
    return result


def test_themes_and_sticky_navigation():
    text = render_benchmark_html({})
    for rule in (
        ':root[data-theme="light"]',
        ':root[data-theme="dark"]',
        "@media (prefers-color-scheme: dark)",
    ):
        assert rule in text
    assert re.search(
        r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*"
        r':root:not\(\[data-theme="light"\]\)\s*\{',
        text,
    )
    assert re.search(r"position:\s*sticky", text)
    assert re.search(r"overflow-x:\s*auto", text)


def test_capability_navigation_and_breadcrumb(benchmark_facts):
    page = _Page(render_benchmark_html(benchmark_facts))
    nav = page.labelled("Capabilities")
    targets = {link["attrs"]["href"] for link in nav["links"]}
    assert {"../field-atlas/index.html", "../capabilities/insights.html"} <= targets
    for target in targets:
        if not target.startswith("#"):
            assert (REPORT / target).resolve().is_file()
    breadcrumb = page.labelled("Breadcrumb")
    assert "benchmark" in breadcrumb["text"].lower()
    assert any(n["attrs"].get("aria-current") == "page" for n in page.nodes)


def test_guided_path_resolves_and_omits_missing_concepts(benchmark_facts):
    page = _Page(render_benchmark_html(benchmark_facts))
    paths = [n for n in page.nodes if "path" in n["attrs"].get("class", "").split()]
    assert len(paths) == 1
    assert "Guided reading path" in paths[0]["text"]
    links = paths[0]["links"]
    assert links and all(link["text"].strip() for link in links)
    targets = [link["attrs"].get("href") for link in links]
    assert {"#provenance", "#benchmark", "#source"} <= set(targets)
    assert ("#concepts" in targets) == bool(benchmark_facts.get("concept_mix"))
    ids = [n["attrs"]["id"] for n in page.nodes if "id" in n["attrs"]]
    assert len(ids) == len(set(ids))
    for node in page.nodes:
        href = node["attrs"].get("href", "")
        if href.startswith("#"):
            assert href[1:] in ids


def test_legend_explains_actual_evidence_states(benchmark_facts):
    page = _Page(render_benchmark_html(benchmark_facts))
    legend = page.labelled("Evidence badge legend")["text"].lower()
    for label, explanation in (
        ("Real regulatory data", "ingested public regulatory production"),
        ("Illustrative seed", "synthetic adapter data, not measured"),
        ("Screening-only", "registered region with no production rows"),
    ):
        items = [
            n["text"]
            for n in page.nodes
            if n["tag"] == "li" and n["text"].strip().startswith(label)
        ]
        assert len(items) == 1
        assert explanation in " ".join(items[0].split())
    assert "reconciled" not in legend


def test_source_footer_acknowledges_mixed_inputs(benchmark_facts):
    text = render_benchmark_html(benchmark_facts)
    footers = [n for n in _Page(text).nodes if n["tag"] == "footer"]
    assert len(footers) == 1
    assert any(
        link["attrs"].get("href") == "_facts.json"
        and "provenance" in link["text"].lower()
        for link in footers[0]["links"]
    )
    assert "illustrative" in footers[0]["text"].lower()
    assert "Public regulatory data only" not in text
    assert "src=" not in text and 'href="http' not in text


def test_committed_page_matches_retained_facts():
    facts = json.loads((REPORT / "_facts.json").read_text(encoding="utf-8"))
    assert (REPORT / "index.html").read_text(encoding="utf-8") == render_benchmark_html(
        facts
    )
