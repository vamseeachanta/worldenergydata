"""Synthetic Abandon-card evidence gaps, independent of production labels.

These checks qualify rendering only; supplied status and milestone labels do
not establish P&A filings, remaining liability or a verified final well status.
"""

from __future__ import annotations

import importlib.util
import json
import re
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
    assert not re.search(r"[\d$£€]|\b(?:USD|MUSD|MMbbl)\b", " ".join(card["li"]))
    assert not any(
        text in " ".join(card["li"]).lower()
        for text in ("no p&a", "still producing", "verified", "filed")
    )
    assert (well, field) == original


def test_status_inputs_preserve_other_cards_and_scales(timeline, well):
    field = {"display_name": "Synthetic Field"}
    original = deepcopy((well, field))
    without_status = timeline.facts_to_well(well, field)
    with_status = timeline.facts_to_well(dict(well, status="abandoned"), field)

    assert without_status == with_status
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
    assert "P&A filing status not established" in _abandon(restored)["li"]
    assert "Liability not evaluated" in _abandon(restored)["li"]
    assert _Links("".join(_abandon(restored)["li"])).hrefs == [CONTEXT_HREF]


def test_context_link_resolves_in_source_and_published_layout(
    timeline, well, tmp_path, monkeypatch
):
    card = _abandon(timeline.facts_to_well(well, {"display_name": "Synthetic Field"}))
    assert _Links("".join(card["li"])).hrefs == [CONTEXT_HREF]
    lifecycle = REPO / "reports/lower_tertiary/lifecycle"
    target = (lifecycle / "wells" / CONTEXT_HREF).resolve()
    assert target == lifecycle / "norms/abandon.html"
    assert target.is_file()

    site = _load("abandon_contract_site", "build_pages.py")
    monkeypatch.setattr(site, "PUBLIC", tmp_path / "public")
    monkeypatch.setattr(site, "ASSETS", site.PUBLIC / "assets")
    site.build(domains=["lower_tertiary"])
    published = (site.PUBLIC / "lifecycle/wells" / CONTEXT_HREF).resolve()
    assert published == site.PUBLIC / "lifecycle/norms/abandon.html"
    assert published.read_bytes() == target.read_bytes()
