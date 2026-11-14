"""Regression cases for the well rendering seam, using synthetic inputs only.

The independent construction hand case is 30 drilling + 20 completion rig-days:
origin 0, handover 30, end 50. Synthetic spud and TD dates are years apart.
Calendar expectations use the midpoint of each of the 12 equal monthly bins
in a year (24 half-months), independently of construction durations. These
checks qualify scale separation, not data completeness or production forecasts.
"""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.regression]

REPO = Path(__file__).resolve().parents[3]
BUILDER_PATH = REPO / "scripts/lower_tertiary/build_well_timelines.py"


@pytest.fixture
def well_case(monkeypatch):
    """All dates, counts and identifiers here are invented synthetic inputs."""
    spec = importlib.util.spec_from_file_location("well_timeline_scales", BUILDER_PATH)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    # Synthetic observation time, independent of the system clock and builder stamp.
    monkeypatch.setattr(builder, "TODAY_YEAR", 2024.5)
    facts = {
        "field_id": "synthetic_field",
        "slot": "synthetic-slot",
        "api": "synthetic-api",
        "drilling_rig_days": 30,
        "completion_rig_days": 20,
        "spud_date": "2001-01-01",
        "td_date": "2011-06-30",
        "first_oil": "2012-04-09",
        "workovers": [
            {"date": "2017-10-23", "type": "Synthetic workover"},
            {"date": "2021-02-03", "type": "Synthetic inspection"},
        ],
    }
    field = {"display_name": "Synthetic Field"}
    original = deepcopy((facts, field))

    payload = builder.facts_to_well(facts, field)

    assert (facts, field) == original
    yield builder, payload
    # Include nested workover records in the input-preservation contract.
    assert (facts, field) == original


def _calendar_midmonth(iso_date):
    """Independent calendar oracle: count half-month bins from the year origin."""
    parsed = date.fromisoformat(iso_date)
    return parsed.year + float(Fraction(2 * parsed.month - 1, 24))


def test_calendar_gap_does_not_extend_rig_day_axis(well_case):
    _, payload = well_case

    # Literal expectations from the module's independent 30 + 20 = 50 hand case.
    assert payload["cAxis"]["start"] == 0
    assert payload["cAxis"]["end"] == 50
    assert payload["cSpans"] == [
        {"from": 0, "to": 30, "txt": "Drill · 30 rig-days"},
        {"from": 30, "to": 50, "txt": "Complete · 20 rig-days"},
    ]
    assert payload["cGates"] == [
        {"x": 0, "lab": "Spud", "dt": "Jan 2001", "kind": ""},
        {"x": 30, "lab": "TD reached", "dt": "Jun 2011", "kind": ""},
        {"x": 50, "lab": "Completed", "dt": "Apr 2012", "kind": "now"},
    ]
    assert payload["cAxis"]["ticks"][0]["v"] == 0
    assert payload["cAxis"]["ticks"][-1]["v"] == 50
    assert 'href="../synthetic_field_lifecycle.html"' in payload["sub"]


def test_production_markers_use_calendar_basis(well_case):
    _, payload = well_case

    # Hand check: April, October and February midpoints are respectively
    # 7/24, 19/24 and 3/24 of a year. No rig-day value enters this oracle.
    expected = {
        "First oil": _calendar_midmonth("2012-04-09"),
        "Synthetic workover": _calendar_midmonth("2017-10-23"),
        "Synthetic inspection": _calendar_midmonth("2021-02-03"),
        "Today": 2024.5,  # Synthetic observation time from the fixture.
    }
    gates = payload["pGates"]
    assert [gate["lab"] for gate in gates] == list(expected)
    assert [gate["x"] for gate in gates] == pytest.approx(list(expected.values()))
    assert payload["pSpans"][0]["from"] == pytest.approx(expected["First oil"])
    assert all(
        payload["pAxis"]["start"] <= gate["x"] <= payload["pAxis"]["end"]
        for gate in gates
    )


def test_well_payload_roundtrips_through_render(well_case, tmp_path, monkeypatch):
    builder, payload = well_case
    template = tmp_path / "well_template.html"
    prefix = '<script type="application/json" id="well-payload">'
    suffix = "</script>"
    template.write_text(prefix + "__WELL_JSON__" + suffix, encoding="utf-8")
    monkeypatch.setattr(builder, "TEMPLATE", template)
    original = deepcopy(payload)

    rendered = builder.render(payload)

    assert rendered.startswith(prefix)
    assert rendered.endswith(suffix)
    assert "__WELL_JSON__" not in rendered
    assert json.loads(rendered.removeprefix(prefix).removesuffix(suffix)) == payload
    assert payload == original
