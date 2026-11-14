"""Navigation contracts for the existing intervention brief.

Expected routes come from the Workover/Insights placement contract in issue
778 and the public layout in scripts/build_pages.py: well pages live under
lifecycle/wells, and the reused brief lives under intervention-db. No engineering
calculation or numerical acceptance limit is introduced here.
"""

from __future__ import annotations

import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
WELLS = ROOT / "reports/lower_tertiary/lifecycle/wells"
BRIEF = "intervention-db/intervention-stats-brief.html"


class Navigation(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.ids = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if "id" in attrs:
            self.ids.append(attrs["id"])


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def well_payload(html):
    return json.JSONDecoder().raw_decode(html.split("const WELL = ", 1)[1])[0]


def workover_card(well):
    return next(card for card in well["cards"] if card["t"] == "Workover")


@pytest.fixture(scope="module")
def registry():
    path = WELLS / "_wells.json"
    assert path.is_file(), "committed well registry is required for navigation tests"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["wells"], "the well registry must contain navigation cases"
    return data


@pytest.fixture
def timeline():
    return load_script(
        "timeline_intervention_test", "scripts/lower_tertiary/build_well_timelines.py"
    )


@pytest.fixture
def site(tmp_path, monkeypatch):
    module = load_script("site_intervention_test", "scripts/build_pages.py")
    monkeypatch.setattr(module, "PUBLIC", tmp_path / "public")
    monkeypatch.setattr(module, "ASSETS", module.PUBLIC / "assets")
    return module


def test_generated_workover_card_links_brief_without_changing_events(
    timeline, registry
):
    """Every committed well retains its events and gains the overview link."""
    for facts in registry["wells"]:
        field = registry["fields"][facts["field_id"]]
        card = workover_card(timeline.facts_to_well(facts, field))
        expected_events = [
            f"{timeline._pretty(event['date'])} · {event['type']}"
            for event in facts.get("workovers", [])
        ] or ["none to date"]
        assert card["li"][:-1] == expected_events
        nav = Navigation(card["li"][-1])
        assert nav.links == [f"../../{BRIEF}#serviceability"]
        assert "overview" in card["li"][-1].lower()


def test_workover_overview_is_available_without_recorded_events(timeline, registry):
    facts = dict(registry["wells"][0], workovers=[])
    card = workover_card(
        timeline.facts_to_well(facts, registry["fields"][facts["field_id"]])
    )
    assert card["li"][0] == "none to date"
    assert Navigation(card["li"][-1]).links == [f"../../{BRIEF}#serviceability"]


def assert_serviceability_target(page, href, public):
    route = urlsplit(href)
    assert not route.scheme and not route.netloc
    target = (page.parent / route.path).resolve()
    assert target == public / BRIEF
    assert route.fragment == "serviceability"
    assert Navigation(target.read_text(encoding="utf-8")).ids.count(route.fragment) == 1


def test_published_well_and_insights_routes_reach_existing_brief(site, registry):
    """Resolve hrefs from deployed directories, rather than source directories."""
    site.build(domains=["capabilities", "lower_tertiary"])
    public = site.PUBLIC.resolve()
    assert (public / BRIEF).read_bytes() == (ROOT / "docs" / BRIEF).read_bytes()
    for facts in registry["wells"]:
        name = f"{facts['field_id']}_{facts['slot']}_well.html"
        page = public / "lifecycle/wells" / name
        card = workover_card(well_payload(page.read_text(encoding="utf-8")))
        links = Navigation("".join(card["li"])).links
        assert links == [f"../../{BRIEF}#serviceability"]
        assert_serviceability_target(page, links[0], public)
    insights = public / "capabilities/insights.html"
    links = [
        href
        for href in Navigation(insights.read_text(encoding="utf-8")).links
        if BRIEF in href
    ]
    assert links, "the retained Insights hub must surface the intervention brief"
    for href in links:
        assert_serviceability_target(insights, href, public)
    landing = public / "index.html"
    links = [
        href
        for href in Navigation(landing.read_text(encoding="utf-8")).links
        if BRIEF in href
    ]
    assert links == [f"{BRIEF}#serviceability"]
    assert_serviceability_target(landing, links[0], public)


def test_landing_intervention_card_is_omitted_when_brief_is_absent(site):
    site.PUBLIC.mkdir()
    assert BRIEF not in site._insights_section()


def test_landing_intervention_card_is_present_when_brief_exists(site):
    brief = site.PUBLIC / BRIEF
    brief.parent.mkdir(parents=True)
    brief.write_text(
        '<h2 id="serviceability">Serviceability</h2>', encoding="utf-8", newline="\n"
    )
    links = Navigation(site._insights_section()).links
    assert links == [f"{BRIEF}#serviceability"]


@pytest.mark.parametrize("include_capabilities", [True, False])
def test_partial_build_publishes_workover_target(
    site, tmp_path, monkeypatch, include_capabilities
):
    """A clean domain build publishes every well's linked brief independently."""
    if not include_capabilities:
        reports = tmp_path / "reports"
        reports.mkdir()
        monkeypatch.setattr(site, "REPORTS", reports)
    assert not site.PUBLIC.exists()
    site.build(domains=["lower_tertiary"])
    public = site.PUBLIC.resolve()
    target = public / BRIEF
    assert target.is_file(), "partial builds must publish the Workover target"
    assert target.read_bytes() == (ROOT / "docs" / BRIEF).read_bytes()
    assert_serviceability_target(
        public / "index.html", f"{BRIEF}#serviceability", public
    )
    if include_capabilities:
        pages = list((public / "lifecycle/wells").glob("*_well.html"))
        assert pages, "the partial build must include committed well pages"
        for page in pages:
            card = workover_card(well_payload(page.read_text(encoding="utf-8")))
            links = Navigation("".join(card["li"])).links
            assert links == [f"../../{BRIEF}#serviceability"]
            assert_serviceability_target(page, links[0], public)


def test_module_import_does_not_require_well_registry(monkeypatch):
    original_read = Path.read_text

    def read_without_registry(path, *args, **kwargs):
        if path == WELLS / "_wells.json":
            raise FileNotFoundError("well registry is unavailable")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_without_registry)
    module = load_script(
        "navigation_without_registry", Path(__file__).relative_to(ROOT)
    )
    assert module.BRIEF == BRIEF
