"""Synthetic Abandon-card evidence gaps, independent of production labels.

These checks qualify rendering only; supplied status and milestone labels do
not establish P&A filings, remaining liability or a verified final well status.
"""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.regression]

REPO = Path(__file__).resolve().parents[3]
CONTEXT_HREF = "../norms/abandon.html"


def _load(name, script):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def timeline():
    return _load("abandon_contract_timeline", "lower_tertiary/build_well_timelines.py")


@pytest.fixture
def well():
    return {
        "field_id": "synthetic_field",
        "slot": "synthetic-slot",
        "api": "synthetic-api",
        "drilling_rig_days": 30,
        "completion_rig_days": 20,
        "spud_date": "2001-01-01",
        "td_date": "2011-06-30",
        "first_oil": "2012-04-09",
        "workovers": [{"date": "2017-10-23", "type": "Synthetic workover"}],
    }


def _abandon(payload):
    cards = [card for card in payload["cards"] if card["t"] == "Abandon"]
    assert len(cards) == 1
    return cards[0]


class _Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.hrefs = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href"))


def _assert_abandon_bullets(card, observed_milestones=()):
    assert card["li"] == [
        *observed_milestones,
        "P&A filing status not established",
        "Liability not evaluated",
        '<a href="../norms/abandon.html">P&A engineering context →</a>',
    ]


@pytest.mark.parametrize("status", ["producing", None, "abandoned", "inconsistent"])
@pytest.mark.parametrize(
    "gap", ["P&A filing status not established", "Liability not evaluated"]
)
def test_status_does_not_establish_filing_or_liability(timeline, well, status, gap):
    if status is not None:
        well["status"] = status
    if status == "inconsistent":
        well["status"] = "producing"
        well["workovers"].append({"date": "2020-02-03", "type": "Plug & abandon"})
    field = {"display_name": "Synthetic Field"}
    original = deepcopy((well, field))

    card = _abandon(timeline.facts_to_well(well, field))

    assert set(card) == {"t", "big", "li"}
    assert card["big"] == "—"
    assert gap in card["li"]
    assert _Links("".join(card["li"])).hrefs == [CONTEXT_HREF]
    _assert_abandon_bullets(card)
    assert not any(
        text in " ".join(card["li"]).lower()
        for text in ("no p&a", "still producing", "verified", "filed")
    )
    assert (well, field) == original


def test_dated_operation_preserves_evidence_gaps(timeline, well):
    well["workovers"] = [
        {"date": "2020-02-03", "type": "Observed plugging operation (synthetic)"}
    ]
    payload = timeline.facts_to_well(well, {"display_name": "Synthetic Field"})
    card = _abandon(payload)
    _assert_abandon_bullets(card)
    workover = next(card for card in payload["cards"] if card["t"] == "Workover")
    milestone = "Feb 2020 · Observed plugging operation (synthetic)"
    assert workover["li"][0] == milestone

    # This insertion checks template compatibility only; facts_to_well does
    # not populate Abandon milestones. Replace it with generator-driven
    # coverage when #770 wires observed milestones into the Abandon card.
    # The operation label does not establish filing or liability evidence.
    card["li"].insert(0, workover["li"][0])
    _assert_abandon_bullets(card, observed_milestones=[milestone])
    rendered = timeline.render(payload)
    restored, _ = json.JSONDecoder().raw_decode(rendered.split("const WELL = ", 1)[1])
    _assert_abandon_bullets(_abandon(restored), observed_milestones=[milestone])


@pytest.mark.parametrize("estimate", ["0", "$12", "£12", "€12", "USD", "MUSD", "MMbbl"])
def test_liability_check_rejects_estimates(timeline, well, estimate):
    card = _abandon(timeline.facts_to_well(well, {"display_name": "Synthetic Field"}))
    card["li"].append(f"Liability estimate (synthetic): {estimate}")

    with pytest.raises(AssertionError):
        _assert_abandon_bullets(card)


@pytest.mark.parametrize(
    "amount",
    [
        "USD 12 million",
        "125,000",
        "12 million",
        "$12",
        "&pound;12",
        "€12",
        "EUR 12",
        "GBP 12",
        "<strong>USD</strong> <span>12 million</span>",
        "12 euros",
    ],
)
def test_liability_check_rejects_separate_cost_bullet(timeline, well, amount):
    card = _abandon(timeline.facts_to_well(well, {"display_name": "Synthetic Field"}))
    unit = "dollars" if amount == "125,000" else "synthetic"
    card["li"].append(f"Estimated remaining P&A cost ({unit}): {amount}")

    assert "P&A filing status not established" in card["li"]
    assert "Liability not evaluated" in card["li"]
    with pytest.raises(AssertionError):
        _assert_abandon_bullets(card)


def test_abandon_contract_rejects_changed_context_link(timeline, well):
    card = _abandon(timeline.facts_to_well(well, {"display_name": "Synthetic Field"}))
    card["li"][-1] = (
        '<a href="../norms/abandon.html?unit=USD&amp;value=12">'
        "P&A engineering context →</a>"
    )

    with pytest.raises(AssertionError):
        _assert_abandon_bullets(card)


def test_status_inputs_preserve_other_cards_and_scales(timeline, well):
    field = {"display_name": "Synthetic Field"}
    original = deepcopy((well, field))
    without_status = timeline.facts_to_well(well, field)
    with_status = timeline.facts_to_well(dict(well, status="abandoned"), field)

    for key in ("cards", "cAxis", "pAxis"):
        assert without_status[key] == with_status[key]
    assert without_status["cAxis"]["start"] == 0
    assert without_status["cAxis"]["end"] == 50
    assert [card["t"] for card in without_status["cards"]] == [
        "Drill · done",
        "Complete · done",
        "Produce · now",
        "Workover",
        "Abandon",
    ]
    assert (well, field) == original


def test_abandon_gaps_survive_template_render(timeline, well):
    payload = timeline.facts_to_well(well, {"display_name": "Synthetic Field"})
    original = deepcopy(payload)

    rendered = timeline.render(payload)
    restored, _ = json.JSONDecoder().raw_decode(rendered.split("const WELL = ", 1)[1])

    assert "__WELL_JSON__" not in rendered
    assert restored == original == payload
    _assert_abandon_bullets(_abandon(restored))
    assert _Links("".join(_abandon(restored)["li"])).hrefs == [CONTEXT_HREF]


def test_context_link_resolves_in_source_and_published_layout(
    timeline, well, tmp_path, monkeypatch
):
    card = _abandon(timeline.facts_to_well(well, {"display_name": "Synthetic Field"}))
    hrefs = _Links("".join(card["li"])).hrefs
    assert hrefs == [CONTEXT_HREF]
    href = hrefs[0]
    lifecycle = REPO / "reports/lower_tertiary/lifecycle"
    source_wells = sorted((lifecycle / "wells").glob("*_well.html"))
    assert source_wells, "Source well pages are required for the context link"
    target = (source_wells[0].parent / href).resolve()
    assert target == lifecycle / "norms/abandon.html"
    assert target.is_file()

    site = _load("abandon_contract_site", "build_pages.py")
    monkeypatch.setattr(site, "PUBLIC", tmp_path / "public")
    monkeypatch.setattr(site, "ASSETS", site.PUBLIC / "assets")
    site.build(domains=["lower_tertiary"])
    published_wells = sorted((site.PUBLIC / "lifecycle/wells").glob("*_well.html"))
    assert published_wells, "Published well pages are required for the context link"
    published = (published_wells[0].parent / href).resolve()
    assert published == site.PUBLIC / "lifecycle/norms/abandon.html"
    assert published.read_bytes() == target.read_bytes()
