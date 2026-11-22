"""Exercise the actual atlas script with synthetic fields and a minimal DOM.

Node is required; its absence fails these tests rather than skipping coverage.
"""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "reports/field-atlas/atlas_template.html"

HARNESS = r"""
const vm = require('node:vm');
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor(tag, attrs) {
    this.tag = tag; this.attrs = attrs; this.value = ''; this.textContent = '';
    this.isDisabled = /\bdisabled\b/.test(attrs); this.listeners = {};
    this.id = /\bid="([^"]+)"/.exec(attrs)?.[1];
    this.children = []; this.html = '';
  }
  set innerHTML(html) {
    this.html = html;
    if (this.tag === 'select') this.value = '';
    this.children = [...html.matchAll(/data-t="([^"]+)"/g)].map(m => ({
      dataset: {t: m[1]}, classList: {toggle() {}}
    }));
  }
  get innerHTML() { return this.html; }
  get disabled() { return this.isDisabled; }
  set disabled(value) {
    this.isDisabled = value;
    if (value && document.activeElement === this) document.activeElement = document.body;
  }
  focus() { if (!this.disabled) document.activeElement = this; }
  addEventListener(event, handler) { this.listeners[event] = handler; }
  click() {
    if (this.disabled) return;
    const event = {target: this};
    if (this.onclick) this.onclick(event);
    if (this.listeners.click) this.listeners.click(event);
  }
}
const elements = Object.fromEntries(
  [...input.html.matchAll(/<([a-z]+)\b([^>]*\bid="([^"]+)"[^>]*)>/g)]
    .map(m => [m[3], new Element(m[1], m[2])])
);
const location = {hash: ''};
const document = {getElementById: id => elements[id] || null,
  body: {id: 'body'}, baseURI: 'https://example.invalid/field-atlas/'};
document.activeElement = document.body;
let resolveFeed;
const feed = {fields: input.feed};
const context = vm.createContext({
  document,
  location, URL, console, window: {addEventListener() {}},
  fetch: url => {
    if (url !== '_atlas_feed.json') throw new Error('Unexpected fetch');
    return new Promise(resolve => { resolveFeed = resolve; });
  }
});
vm.runInContext(input.source, context);
function snapshot() {
  return {
    count: elements['f-count'].textContent,
    names: [...elements['f-grid'].innerHTML.matchAll(/<h3>([^<]+)/g)].map(m => m[1]),
    links: [...elements['f-grid'].innerHTML.matchAll(/href="([^"]+)"/g)].map(m => m[1]),
    ids: [...elements['f-grid'].innerHTML.matchAll(/data-fid="([^"]+)"/g)].map(m => m[1]),
    previous: elements['f-prev']?.disabled,
    next: elements['f-next']?.disabled,
    hash: location.hash,
    focused: document.activeElement.id
  };
}
const states = [snapshot()];
(async () => {
for (const action of input.actions) {
  if (typeof action === 'string') elements[action].click();
  else if (action.focus) elements[action.focus].focus();
  else if (action.tier) elements['f-tiers'].onclick({target: {dataset: {t: action.tier}}});
  else if (action.feed) {
    resolveFeed({ok: true, json: async () => feed});
    await new Promise(resolve => setImmediate(resolve));
  } else if (action.keep !== undefined) {
    feed.fields.splice(action.keep);
    await Promise.resolve().then(() => context.render());
  } else if (action.open !== undefined) {
    const state = snapshot();
    const card = {dataset: {fid: state.ids[action.open]}};
    elements['f-grid'].listeners.click({target: {closest: selector =>
      selector === 'a' ? (action.link ? {} : null) : card}});
  }
  else {
    elements[action.id].value = action.value;
    elements[action.id].listeners.input();
  }
  states.push(snapshot());
}
process.stdout.write(JSON.stringify(states));
})().catch(error => {console.error(error); process.exitCode = 1;});
"""


def synthetic_fields(count, start=0):
    return [
        {
            "name": f"Example {index:03d}",
            "country": "USA",
            "domain": "offshore",
            "region": "US Gulf of Mexico",
            "density_tier": "rich",
            "lifecycle_id": f"field_{index:03d}",
        }
        for index in reversed(range(start, start + count))
    ]


def render_fields(count, actions=(), *, fields=None, feed=()):
    """Execute complete template startup and user events with synthetic data."""
    node = shutil.which("node")
    assert node is not None, "Node is required to verify atlas pagination"
    fields = synthetic_fields(count) if fields is None else fields
    html = TEMPLATE.read_text(encoding="utf-8")
    source = re.search(r"<script>\s*(.*?)</script>", html, re.DOTALL).group(1)
    source = source.replace("__ROSTER_JSON__", json.dumps(fields)).replace(
        "__COUNTRIES_JSON__", "[]"
    )
    result = subprocess.run(
        [node, "-e", HARNESS],
        input=json.dumps(
            {"html": html, "source": source, "actions": actions, "feed": feed}
        ),
        capture_output=True,
        encoding="utf-8",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("count", [0, 1, 60, 61, 121])
def test_field_results_have_bounded_pages(count):
    state = render_fields(count)[0]
    assert len(state["names"]) == min(count, 60)
    assert state["names"] == [f"Example {i:03d}" for i in range(min(count, 60))]
    pages = (count + 59) // 60
    suffix = "field" if count == 1 else "fields"
    page = 1 if count else 0
    assert state["count"] == f"{count} {suffix} · page {page} of {pages}"
    assert state["previous"] is True
    assert state["next"] is (count <= 60)


@pytest.mark.parametrize(
    "action",
    [
        {"id": "f-country", "value": "USA"},
        {"id": "f-domain", "value": "offshore"},
        {"id": "f-region", "value": "US Gulf of Mexico"},
        {"id": "f-play", "value": ""},
        {"id": "f-search", "value": "Example"},
        {"tier": "rich"},
    ],
)
def test_filter_input_resets_the_page(action):
    # The synthetic tier event keeps focus on search to check that its handler
    # does not move focus; it does not simulate a browser focusing a tier button.
    control = action.get("id", "f-search")
    start, second, focused, reset = render_fields(
        121, ["f-next", {"focus": control}, action]
    )
    assert second["count"] == "121 fields · page 2 of 3"
    assert focused["focused"] == reset["focused"] == control
    assert reset["names"] == start["names"]
    assert reset["count"] == "121 fields · page 1 of 3"
    assert reset["previous"] is True


def test_pages_preserve_tier_order_and_every_field_once():
    fields = synthetic_fields(121)
    tiers = ["rich", "sample", "roadmap"]
    for index, field in enumerate(fields):
        field["density_tier"] = tiers[index % 3]
    expected = sorted(fields, key=lambda f: (tiers.index(f["density_tier"]), f["name"]))
    states = render_fields(
        121, ["f-prev", "f-next", "f-next", "f-next", "f-prev"], fields=fields
    )
    assert states[0] == states[1]
    assert states[3] == states[4]
    assert states[2] == states[5]
    assert states[3]["next"] is True
    pages = [states[0], states[2], states[3]]
    assert [name for page in pages for name in page["names"]] == [
        field["name"] for field in expected
    ]
    assert len({name for page in pages for name in page["names"]}) == 121


@pytest.mark.parametrize("count", [61, 121])
@pytest.mark.parametrize("control", ["f-prev", "f-next"])
def test_keyboard_focus_moves_to_enabled_control_at_page_boundary(count, control):
    page_count = (count + 59) // 60
    setup = ["f-next"] * (page_count - 1) if control == "f-prev" else []
    states = render_fields(
        count, [*setup, {"focus": control}, *[control] * (page_count - 1), control]
    )
    focused_states = states[len(setup) + 1 : -2]
    assert all(state["focused"] == control for state in focused_states)
    boundary = states[-2]
    fallback = "f-next" if control == "f-prev" else "f-prev"
    assert boundary["focused"] == fallback
    assert boundary["previous" if control == "f-prev" else "next"] is True
    page = 1 if control == "f-prev" else page_count
    assert boundary["count"] == f"{count} fields · page {page} of {page_count}"
    assert states[-1] == boundary


@pytest.mark.parametrize("control", ["f-prev", "f-next"])
def test_pointer_paging_preserves_focus_elsewhere(control):
    setup = ["f-next"] if control == "f-prev" else []
    states = render_fields(61, [*setup, {"focus": "f-search"}, control])
    assert states[-1]["focused"] == "f-search"


def test_keyboard_paging_can_reverse_direction_at_each_boundary():
    states = render_fields(61, [{"focus": "f-next"}, "f-next", "f-prev", "f-next"])
    assert [state["focused"] for state in states[1:]] == [
        "f-next",
        "f-prev",
        "f-next",
        "f-prev",
    ]


def test_later_page_cards_keep_lifecycle_and_delegated_navigation():
    _, second, linked, opened = render_fields(
        61, ["f-next", {"open": 0, "link": True}, {"open": 0}]
    )
    assert second["names"] == ["Example 060"]
    assert second["links"] == ["../lifecycle/field_060_lifecycle.html"]
    assert linked["hash"] == ""
    assert opened["hash"] == "#/field/field_060"


def test_search_empty_and_restore_reset_paging():
    states = render_fields(
        121,
        [
            "f-next",
            {"id": "f-search", "value": "missing"},
            {"id": "f-search", "value": " Example "},
        ],
    )
    assert states[2]["names"] == []
    assert states[2]["count"] == "0 fields · page 0 of 0"
    assert states[2]["previous"] is states[2]["next"] is True
    assert states[3] == states[0]


def test_feed_completion_preserves_current_page():
    states = render_fields(
        121,
        [
            {"id": "f-country", "value": "USA"},
            "f-next",
            "f-next",
            {"focus": "f-country"},
            {"feed": True},
        ],
        feed=synthetic_fields(61, start=121),
    )
    assert states[-1]["count"] == "182 fields · page 3 of 4"
    assert states[-1]["names"] == [f"Example {i:03d}" for i in range(120, 180)]
    assert states[-1]["next"] is False
    assert states[-2]["focused"] == states[-1]["focused"] == "f-country"


@pytest.mark.parametrize("remaining", [0, 1, 60, 61])
def test_async_feed_refresh_clamps_out_of_range_page(remaining):
    states = render_fields(
        0,
        [
            {"id": "f-country", "value": ""},
            {"feed": True},
            "f-next",
            "f-next",
            {"keep": remaining},
        ],
        feed=synthetic_fields(121),
    )
    assert states[-2]["count"] == "121 fields · page 3 of 3"
    last = states[-1]
    page_count = (remaining + 59) // 60
    suffix = "field" if remaining == 1 else "fields"
    assert last["count"] == f"{remaining} {suffix} · page {page_count} of {page_count}"
    expected_size = (remaining - 1) % 60 + 1 if remaining else 0
    assert len(last["names"]) == expected_size
    assert last["next"] is True
    assert last["previous"] is (remaining <= 60)


def test_paging_controls_have_native_keyboard_and_status_semantics():
    class Tags(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = []

        def handle_starttag(self, tag, attrs):
            self.tags.append((tag, dict(attrs)))

    parser = Tags()
    parser.feed(TEMPLATE.read_text(encoding="utf-8"))
    by_id = {attrs["id"]: (tag, attrs) for tag, attrs in parser.tags if "id" in attrs}
    for name in ("f-prev", "f-next"):
        tag, attrs = by_id[name]
        assert tag == "button"
        assert attrs["type"] == "button"
        assert attrs["aria-controls"] == "f-grid"
    assert by_id["f-count"][1]["role"] == "status"
    assert by_id["f-count"][1]["aria-live"] == "polite"
    assert (
        "nav",
        {"class": "pager", "aria-label": "Field result pages"},
    ) in parser.tags
