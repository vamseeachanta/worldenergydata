"""Offline asset hierarchy contract; every inventory value is synthetic."""

import copy
import importlib.util
from html.parser import HTMLParser
from pathlib import Path

import pytest


@pytest.fixture
def render():
    path = (
        Path(__file__).resolve().parents[3]
        / "scripts/field_assets/render_asset_plane.py"
    )
    spec = importlib.util.spec_from_file_location("asset_plane", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_asset_plane


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags, self.links, self.parents, self.ids, self.text = [], [], {}, [], []
        self.stack = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "li":
            ident = attrs["id"]
            self.parents[ident] = self.stack[-1] if self.stack else None
            self.ids.append(ident)
            self.stack.append(ident)
        if tag == "a":
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "li":
            self.stack.pop()

    def handle_data(self, data):
        self.text.append(data)


def source():
    return [{"label": "Synthetic reference", "href": "docs/reference.html#asset"}]


@pytest.fixture
def record():
    def node(ident, parent, kind):
        return dict(id=ident, parent_id=parent, kind=kind, name=ident, sources=source())

    nodes = [
        node("facility", None, "facility"),
        node("asset-b", "facility", "asset"),
        node("component-b", "component-a", "component"),
        node("asset-a", "facility", "asset"),
        node("component-a", "asset-a", "component"),
    ]
    nodes[3]["capability"] = dict(
        label="Synthetic inspection", state="available", sources=source()
    )
    nodes[1]["capability"] = dict(
        label="Synthetic inspection", state="unavailable", sources=source()
    )
    nodes[4]["capability"] = dict(
        label="Synthetic inspection", state="unverified", sources=source()
    )
    return dict(id="synthetic-field", name="Synthetic field", nodes=nodes)


def test_literal_hierarchy_and_descriptive_capabilities(render, record):
    page = Page(render(record))
    assert page.parents == {
        "node-facility": None,
        "node-asset-a": "node-facility",
        "node-component-a": "node-asset-a",
        "node-component-b": "node-component-a",
        "node-asset-b": "node-facility",
    }
    assert page.ids == [
        "node-facility",
        "node-asset-a",
        "node-component-a",
        "node-component-b",
        "node-asset-b",
    ]
    assert sum(tag == "h1" for tag, _ in page.tags) == 1
    assert {attrs["data-state"] for _, attrs in page.tags if "data-state" in attrs} == {
        "available",
        "unavailable",
        "unverified",
    }
    assert (
        "Capability metadata is descriptive; no analysis or qualification is implied."
        in "".join(page.text)
    )
    assert page.links == ["docs/reference.html#asset"] * 8


def test_deterministic_order_and_input_immutability(render, record):
    original = copy.deepcopy(record)
    html = render(record)
    assert record == original
    assert render(record) == html
    record["nodes"].reverse()
    assert render(record) == html


@pytest.mark.parametrize("nodes", [None, []])
def test_unknown_inventory_is_visible_not_zero(render, record, nodes):
    record["nodes"] = nodes
    html = render(record)
    assert "Inventory unavailable" in html
    assert not Page(html).ids
    assert "0 assets" not in html


def test_missing_inventory(render, record):
    del record["nodes"]
    assert "Inventory unavailable" in render(record)


@pytest.mark.parametrize("sources", [None, []])
@pytest.mark.parametrize("state", ["available", "unavailable", "unverified"])
def test_missing_evidence_does_not_claim_observed_inventory(
    render, record, sources, state
):
    record["nodes"] = [record["nodes"][0], record["nodes"][3]]
    node = record["nodes"][1]
    node["sources"] = sources
    html = render(record)
    assert "Observation unavailable: source evidence missing" in html
    node["capability"].update(state=state, sources=sources)
    html = render(record)
    assert "Capability state unknown: source evidence missing" in html
    assert not any("data-state" in attrs for _, attrs in Page(html).tags)
    assert "Capability available" not in html
    assert "Capability unavailable" not in html


def test_sourced_unavailability_is_explicit(render, record):
    page = Page(render(record))
    assert "Capability unavailable: Synthetic inspection" in "".join(page.text)
    assert any(attrs.get("data-state") == "unavailable" for _, attrs in page.tags)


def test_absent_capability_is_visible(render, record):
    assert "Capability state unknown: no metadata supplied" in render(record)


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate",
        "dangling",
        "cycle",
        "bad-kind",
        "bad-parent",
        "missing-parent",
        "missing-id",
    ],
)
def test_invalid_hierarchy_is_explicit(render, record, problem):
    if problem == "duplicate":
        record["nodes"].append(copy.deepcopy(record["nodes"][0]))
    elif problem == "dangling":
        record["nodes"][1]["parent_id"] = "absent"
    elif problem == "cycle":
        record["nodes"][3]["parent_id"] = "component-b"
    elif problem == "bad-kind":
        record["nodes"][1]["kind"] = "unknown"
    elif problem == "bad-parent":
        record["nodes"][4]["parent_id"] = "facility"
    elif problem == "missing-parent":
        del record["nodes"][1]["parent_id"]
    else:
        del record["nodes"][1]["id"]
    with pytest.raises(ValueError):
        render(record)


def test_deep_valid_chain_uses_linear_parent_lookups(render):
    class CountedNode(dict):
        parent_reads = 0

        def __getitem__(self, key):
            if key == "parent_id":
                type(self).parent_reads += 1
            return super().__getitem__(key)

    nodes = [
        CountedNode(id="facility", parent_id=None, kind="facility", name="Synthetic"),
        CountedNode(id="asset", parent_id="facility", kind="asset", name="Synthetic"),
    ]
    parent = "asset"
    for number in range(1500):
        ident = f"component-{number}"
        nodes.append(
            CountedNode(id=ident, parent_id=parent, kind="component", name="Synthetic")
        )
        parent = ident
    page = Page(render(dict(id="synthetic", name="Synthetic", nodes=nodes[::-1])))
    assert page.ids == [f'node-{node["id"]}' for node in nodes]
    assert page.parents[f"node-{parent}"] == "node-component-1498"
    assert CountedNode.parent_reads <= 4 * len(nodes)


def test_disconnected_component_cycle_is_rejected(render, record):
    record["nodes"].extend(
        [
            dict(id="cycle-a", parent_id="cycle-b", kind="component", name="Synthetic"),
            dict(id="cycle-b", parent_id="cycle-a", kind="component", name="Synthetic"),
        ]
    )
    with pytest.raises(ValueError, match="Cycle in hierarchy"):
        render(record)


@pytest.mark.parametrize("target", ["observation", "capability"])
@pytest.mark.parametrize(
    "href",
    [
        "docs/field%20survey.pdf",
        "https://example.org/field%20survey.pdf",
        "docs/reference%23section%3F.pdf?edition=1#source",
    ],
)
def test_escaped_path_preserved_in_each_evidence_channel(render, record, target, href):
    owner = record["nodes"][3]
    if target == "capability":
        owner = owner["capability"]
    owner["sources"][0]["href"] = href
    assert href in Page(render(record)).links


@pytest.mark.parametrize("target", ["observation", "capability"])
@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "http://example.org/source",
        "//example.org/source",
        "../outside.html",
        "docs/%2e%2e/outside.html",
        "https://example.org/\nsource",
        "https://example.org\\@other.invalid/source",
        "https://example.org:bad/source",
        "https:///source",
        "data:text/html,test",
        "/absolute.html",
        "#fragment",
        "docs/field survey.pdf",
        "docs/%09survey.pdf",
        "docs/%0asurvey.pdf",
        "docs/%7fsurvey.pdf",
        "docs/%252e%252e/outside.html",
        "docs/%2e%2e%2foutside.html",
        "%2fabsolute.html",
        "docs/%5csource.pdf",
        "https://example.org%2fother.invalid/source",
    ],
)
def test_unsafe_links_rejected_in_each_evidence_channel(render, record, target, href):
    owner = record["nodes"][3]
    if target == "capability":
        owner = owner["capability"]
    owner["sources"][0]["href"] = href
    with pytest.raises(ValueError):
        render(record)


def test_https_links_and_all_supplied_text_are_escaped(render, record):
    attack = '<script>alert("x")</script> & <img src=x onerror=alert(1)>'
    record["name"] = attack
    node = record["nodes"][3]
    for owner in (node, node["capability"]):
        owner["label" if owner is node["capability"] else "name"] = attack
        owner["sources"] = [
            {"label": attack, "href": 'https://example.org/ref?a=1&b="x"'}
        ]
    html = render(record)
    page = Page(html)
    assert not {"script", "img", "iframe", "style"} & {tag for tag, _ in page.tags}
    assert all(not key.startswith("on") for _, attrs in page.tags for key in attrs)
    assert "&lt;script&gt;" in html and "&amp;" in html
    assert "".join(page.text).count(attack) == 5
    assert 'https://example.org/ref?a=1&b="x"' in page.links


@pytest.mark.parametrize(
    "change",
    [
        {"capability": {"label": "Synthetic", "state": "ready", "sources": source()}},
        {"sources": [{"label": "", "href": "docs/ref.html"}]},
        {"sources": "not a list"},
        {"id": '<img src="x">'},
        {"name": None},
    ],
)
def test_malformed_metadata_rejected(render, record, change):
    record["nodes"][3].update(change)
    with pytest.raises(ValueError):
        render(record)
