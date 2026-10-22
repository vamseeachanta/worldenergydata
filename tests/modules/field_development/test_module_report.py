"""Consistency, hand arithmetic and offline delivery checks for the module report."""

import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/reports/modules/wfielddevelopment"
REBUILD = "PYTHONPATH=src uv run --no-project --with pydantic --with pyyaml python docs/reports/modules/wfielddevelopment/build_report.py"
spec = importlib.util.spec_from_file_location(
    "field_report", REPORT / "build_report.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.links = []
        self.quantities = []
        self.headings = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.links.append(attrs["href"][1:])
        if "data-number" in attrs:
            self.quantities.append(attrs)
        if tag == "h2":
            self.headings.append(attrs.get("id"))


@pytest.fixture(scope="module")
def data():
    return builder.calculate()


def test_hand_anchor_weighted_score(data):
    # Public example, configured weights total 1.00. Products by criterion:
    # .16*.98 + .08*.70 + .08*.95 + .12*.55 + .06*.80 + .08*.70
    # + .24*1.00 + .18*.50 = .7888. Scale to points: .7888*100=78.88.
    # Absolute tolerance 1e-9 points; this is arithmetic, not a field benchmark.
    assert data["numbers"]["score.subsea_tieback"] == pytest.approx(78.88, abs=1e-9)


def test_hand_anchor_graph_nodes(data):
    # Three trees + one routing manifold + one existing host + one export = 6.
    assert data["numbers"]["nodes"] == 6


def test_hand_anchor_graph_edges(data):
    # Three tree-production + three tree-control + one manifold-production
    # + one host-control + one export = 9 directed connections.
    assert data["numbers"]["edges"] == 9


def test_hand_anchor_scale(data):
    # Axis-aligned host offset: 18 km * 50 pixels/km = 900 pixels.
    # Absolute tolerance 1e-9 pixels; display scale is an explicit drawing input.
    assert data["numbers"]["separation_px"] == pytest.approx(900.0, abs=1e-9)


def test_public_example_consistency(data):
    from worldenergydata.field_development import recommend, validate_concept

    concept, violations = validate_concept(builder.example_inputs())
    assert violations == []
    returned = recommend(concept)
    assert data["ranking"] == [r.concept_type.value for r in returned]
    for row in returned:
        assert data["numbers"][f"score.{row.concept_type.value}"] == pytest.approx(
            row.total_score * 100, abs=1e-9
        )
    assert data["numbers"]["water_depth_m"] == concept.water_depth_m
    assert data["numbers"]["reserves_mmboe"] == concept.recoverable_reserves_mmboe
    assert data["numbers"]["host_distance_km"] == concept.distance_to_host_km
    assert data["numbers"]["wells"] == concept.num_wells


def test_every_displayed_number_consistency(tmp_path, data):
    builder.build(tmp_path)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    page = Page(text)
    assert page.quantities
    for item in page.quantities:
        key = item["data-number"]
        precision = int(item["data-precision"])
        expected = f'{data["numbers"][key]:,.{precision}f}'
        assert item["data-display"] == expected, key
        assert f">{expected}</span>" in text, key
    # The summary value uses the displayed criterion scores and weights.
    total = sum(row["weight"] * row["score"] for row in data["criteria"])
    weight = sum(row["weight"] for row in data["criteria"])
    assert round(total / weight * 100, 1) == round(
        data["numbers"]["score.subsea_tieback"], 1
    )


def test_all_chart_samples_consistency(data):
    from worldenergydata.field_development import ConceptType, load_concept, recommend

    for point in data["sensitivity"]:
        concept = load_concept(
            builder.example_inputs() | {"distance_to_host_km": point["distance_km"]}
        )
        tieback = next(
            (
                r
                for r in recommend(concept)
                if r.concept_type == ConceptType.SUBSEA_TIEBACK
            ),
            None,
        )
        assert point["score_points"] == (
            None if tieback is None else round(tieback.total_score * 100, 1)
        )
    hard = data["numbers"]["hard_limit_km"]
    assert (
        next(p for p in data["sensitivity"] if p["distance_km"] == hard)["score_points"]
        is not None
    )
    assert (
        next(p for p in data["sensitivity"] if p["distance_km"] > hard)["score_points"]
        is None
    )


def test_rebuild_matches_committed_report(tmp_path):
    builder.build(tmp_path)
    for name in ("index.html", "changes.json"):
        committed = (REPORT / name).read_text(encoding="utf-8")
        fresh = (tmp_path / name).read_text(encoding="utf-8")
        # All calculation arrays and geometry are rounded to displayed digits.
        assert committed == fresh, f"Rebuild with: {REBUILD}"


def test_offline_structure_references_and_public_wording(tmp_path):
    builder.build(tmp_path)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    page = Page(text)
    assert len(page.headings) == 10
    assert len(page.ids) == len(set(page.ids))
    assert set(page.links) <= set(page.ids)
    assert 'class="hs-doc"' in text
    assert "Draft for maintainer review" in text
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://', text)
    assert not re.search(r"<(?:b|strong)\b", text)
    assert "showDirectoryPicker" in text
    assert "index.comments.json" in text
    assert "textContent" in text
    assert "data-limit" in text
    assert "<title>" in text and "tabindex=" in text
    assert "embedded-changes" in text
    assert "module-report-data" in text
    for word in (
        "ow" + "ner",
        "dis" + "patcher",
        "fl" + "eet",
        "ses" + "sion",
        "could",
        "should",
        "would",
    ):
        assert not re.search(rf"\b{word}\b", text, re.I), word
    assert "\r" not in text


def test_style_and_change_record(tmp_path):
    builder.build(tmp_path)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert (REPORT / "house-style.css").read_text(encoding="utf-8").strip() in text
    changes = json.loads((tmp_path / "changes.json").read_text(encoding="utf-8"))
    assert changes == builder.CHANGES
    assert changes["changes"]
    assert set(changes["changes"][0]) == {"section", "description", "reason"}


def test_comment_files_and_distance_control_without_browser(tmp_path):
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is absent; script behavior is not exercised")
    data = builder.calculate()
    harness = r"""
const assert = require('node:assert/strict');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    value: '', textContent: '', children: [], events: {}, files: [],
    options: [{value: 'summary'}],
    addEventListener(kind, callback) { this.events[kind] = callback; },
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; }, click() {}
  });
  return elements.get(id);
}
globalThis.document = {getElementById: element, createElement: () => element(Symbol())};
globalThis.window = {};
"""
    harness += (
        "element('module-report-data').textContent = "
        + json.dumps(
            json.dumps({"numbers": data["numbers"], "sensitivity": data["sensitivity"]})
        )
        + ";\n"
        + "element('embedded-changes').textContent = "
        + json.dumps(json.dumps(builder.CHANGES))
        + ";\n"
        + "element('distance').value = '18';\n"
        + builder.INTERACTION
    )
    harness += r"""
async function check() {
  assert.match(element('distance-result').textContent, /78.9 points/);
  element('distance').value = String(reportData.sensitivity.length - 1);
  element('distance').events.input();
  assert.match(element('distance-result').textContent, /excluded/);
  element('comment-section').value = 'summary';
  element('comment-text').value = '<script>Comment & text</script>';
  element('add-comment').events.click();
  const saved = commentFile();
  assert.equal(JSON.parse(saved).comments[0].text, '<script>Comment & text</script>');
  assert.equal(element('comment-list').children[0].textContent, 'summary: <script>Comment & text</script>');
  await element('save-comments').events.click();
  assert.match(element('comment-message').textContent, /unavailable/);
  let written;
  window.showDirectoryPicker = async () => ({getFileHandle: async (name, options) => {
    assert.equal(name, 'index.comments.json');
    assert.equal(options.create, true);
    return {createWritable: async () => ({write: async text => {written = text;}, close: async () => {}})};
  }});
  await element('save-comments').events.click();
  assert.deepEqual(JSON.parse(written), JSON.parse(saved));
  comments = [];
  await element('load-comments').events.change({target: {files: [{text: async () => saved}]}});
  assert.equal(comments.length, 1);
  await element('load-comments').events.change({target: {files: [{text: async () => '{}'}]}});
  assert.equal(comments.length, 1);
  assert.match(element('comment-message').textContent, /invalid/);
  element('download-comments').events.click();
  assert.match(element('comment-message').textContent, /downloaded/);
}
check().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(
        [node, "-"], input=harness, encoding="utf-8", capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
