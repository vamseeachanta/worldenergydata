"""Synthetic history-to-card cases for observed abandonment milestones.

The observations establish display labels and dates only. Calendar marker
positions use independent half-month arithmetic; rig-days stay at 30 + 20.
No archive, workbook or authoritative final-status data is required.
"""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TA = {"date": "2020-02-03", "type": "Temporary abandonment"}
PA = {"date": "2022-10-23", "type": "Plug & abandon"}


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts/lower_tertiary" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def builders(monkeypatch):
    facts = _load("abandonment_facts_test", "build_wells_facts.py")
    timeline = _load("abandonment_timeline_test", "build_well_timelines.py")
    monkeypatch.setattr(timeline, "TODAY_YEAR", 2024.5)
    return facts, timeline


def _well(events):
    return {
        "field_id": "synthetic_field",
        "slot": "synthetic-slot",
        "api": "synthetic-api",
        "drilling_rig_days": 30,
        "completion_rig_days": 20,
        "spud_date": "2001-01-01",
        "td_date": "2011-06-30",
        "first_oil": "2012-04-09",
        "workovers": events,
    }


def _card(payload, title):
    return next(card for card in payload["cards"] if card["t"] == title)


@pytest.mark.parametrize("event", [TA, PA])
def test_parser_preserves_exact_abandonment_label_and_date(builders, event):
    facts, _ = builders
    assert facts.parse_workovers(f"{event['type']} {event['date']}") == [event]


def test_parser_preserves_mixed_semicolon_history(builders):
    facts, _ = builders
    assert facts.parse_workovers(
        " Workover 2018-01-02; Temporary abandonment 2020-02-03; "
        "Plug & abandon 2022-10-23; Sidetrack 2023-01-04 "
    ) == [
        {"date": "2018-01-02", "type": "Workover"},
        TA,
        PA,
        {"date": "2023-01-04", "type": "Sidetrack"},
    ]


@pytest.mark.parametrize(
    "history",
    ["Plug / abandon 2022-10-23", "Plug & abandon 2022-10-23 unparsed suffix"],
)
def test_parser_does_not_relabel_partial_history_entries(builders, history):
    facts, _ = builders
    # An unsupported entry must not become a misleading recognized milestone.
    assert facts.parse_workovers(history + "; Workover 2023-01-04") == [
        {"date": "2023-01-04", "type": "Workover"}
    ]


@pytest.mark.parametrize("events", [[TA], [PA], [TA, PA]])
def test_abandonment_observations_reach_card_and_calendar(builders, events):
    facts, timeline = builders
    history = "; ".join(f"{event['type']} {event['date']}" for event in events)
    well = _well(facts.parse_workovers(history))
    field = {"display_name": "Synthetic Field"}
    original = deepcopy((well, field))

    payload = timeline.facts_to_well(well, field)

    abandon = _card(payload, "Abandon")
    assert abandon["big"] == (
        f"{len(events)} observed milestone" + ("s" if len(events) != 1 else "")
    )
    assert abandon["li"][:-1] == [
        f"{event['date']} · {event['type']}" for event in events
    ]
    assert "final well status is not established" in abandon["li"][-1].lower()
    assert _card(payload, "Workover")["big"] == "0 events"
    assert _card(payload, "Workover")["li"][0] == "none to date"
    assert "overview" in _card(payload, "Workover")["li"][-1]
    gates = payload["pGates"][1:-1]
    assert [gate["lab"] for gate in gates] == [event["type"] for event in events]
    expected_positions = {
        "Temporary abandonment": 2020 + 3 / 24,
        "Plug & abandon": 2022 + 19 / 24,
    }
    assert [gate["x"] for gate in gates] == pytest.approx(
        [expected_positions[event["type"]] for event in events]
    )
    assert payload["cAxis"]["end"] == 50
    assert payload["current"] == "produce"
    assert (well, field) == original


def test_only_exact_abandonment_labels_leave_workover_card(builders):
    _, timeline = builders
    ordinary = [
        {"date": "2018-01-02", "type": "Workover"},
        {"date": "2019-06-07", "type": "Abandonment inspection"},
        {"date": "2021-04-05", "type": "Plug & abandon review"},
        {"date": "2023-03-04", "type": "temporary abandonment"},
    ]
    events = [ordinary[0], ordinary[1], TA, ordinary[2], PA, ordinary[3]]
    well = _well(events)
    original = deepcopy(well)

    payload = timeline.facts_to_well(well, {"display_name": "Synthetic Field"})

    workover = _card(payload, "Workover")
    assert workover["big"] == "4 events"
    assert workover["li"][:-1] == [
        f"{timeline._pretty(event['date'])} · {event['type']}" for event in ordinary
    ]
    assert [gate["lab"] for gate in payload["pGates"][1:-1]] == [
        event["type"] for event in events
    ]
    assert well == original


@pytest.mark.parametrize("history", ["", "   ", "Workover 2020-01-02"])
def test_absence_of_abandonment_history_does_not_assert_status(builders, history):
    facts, timeline = builders
    well = _well(facts.parse_workovers(history))
    if not history.strip():
        assert well["workovers"] == []

    payload = timeline.facts_to_well(well, {"display_name": "Synthetic Field"})

    assert _card(payload, "Abandon") == {
        "t": "Abandon",
        "big": "—",
        "li": ["No abandonment milestone in the supplied history."],
    }


def test_observed_card_roundtrips_through_render(builders, tmp_path, monkeypatch):
    _, timeline = builders
    well = _well([TA, PA])
    payload = timeline.facts_to_well(well, {"display_name": "Synthetic Field"})
    original = deepcopy(payload)
    template = tmp_path / "template.html"
    template.write_text("__WELL_JSON__", encoding="utf-8")
    monkeypatch.setattr(timeline, "TEMPLATE", template)

    restored = json.loads(timeline.render(payload))

    assert restored == original == payload
    assert "2022-10-23 · Plug & abandon" in _card(restored, "Abandon")["li"]
