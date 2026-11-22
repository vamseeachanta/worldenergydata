"""Reference markers use explicit calendar dates or an honest numeric fallback."""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy

import pytest

from tests.unit.lower_tertiary.test_lifecycle_gate_payload import (  # noqa: F401
    builder,
    facts,
)


def _markers(field):
    return [gate for gate in field["gates"] if gate["kind"] == "nowmark"]


def test_legacy_reference_is_not_today(builder, facts):
    facts["status"] = "producing"
    assert _markers(builder.facts_to_field(facts)) == [
        {
            "year": 2026.5,
            "phase": "operate",
            "lab": "Reference year",
            "dt": "2026.5",
            "kind": "nowmark",
        }
    ]


@pytest.mark.parametrize(
    "reference_date, expected_year",
    [
        ("2028-01-01", 2028.0),
        ("2028-02-29", 2028 + 59 / 366),
        ("2028-07-02", 2028.5),
        ("2027-03-01", 2027 + 59 / 365),
        ("2027-12-31", 2027 + 364 / 365),
    ],
)
def test_explicit_date_survives_render(builder, facts, reference_date, expected_year):
    facts["status"] = "producing"
    original = deepcopy(facts)
    field = builder.facts_to_field(facts, reference_date=reference_date)
    before_render = deepcopy(field)
    html = builder.render(field)
    payload = json.loads(re.search(r"const FIELD = (\{.*?\n\});", html, re.S).group(1))
    marker = _markers(payload)[0]
    assert marker == {
        "year": expected_year,
        "phase": "operate",
        "lab": "As of",
        "dt": reference_date,
        "kind": "nowmark",
    }
    assert payload == field == before_render
    assert facts == original


@pytest.mark.parametrize("reference_date", [None, "2028-02-29"])
@pytest.mark.parametrize("status, first", [("execution", 2025), ("producing", None)])
def test_marker_requires_producing_status_and_first_oil(
    builder, facts, reference_date, status, first
):
    facts["status"] = status
    facts["gates"]["first_oil"] = first
    assert _markers(builder.facts_to_field(facts, reference_date=reference_date)) == []


@pytest.mark.parametrize("reference_date", ["2015-01-01", "2045-01-01", "2050-01-01"])
def test_axis_boundaries_and_outside_dates_are_not_clamped(
    builder, facts, reference_date
):
    facts["status"] = "producing"
    field = builder.facts_to_field(facts, reference_date=reference_date)
    assert field["axis"] == {
        "start": 2015,
        "end": 2045,
        "ticks": list(range(2015, 2046, 5)),
    }
    assert _markers(field) == []


def test_missing_gates_do_not_invent_a_reference_event(builder, facts):
    facts.pop("gates")
    facts["status"] = "producing"
    field = builder.facts_to_field(facts, reference_date="2028-02-29")
    assert field["gates"] == []
    assert field["spans"] == []
    assert field["axis"] == {
        "start": 2020,
        "end": 2055,
        "ticks": list(range(2020, 2056, 5)),
    }


@pytest.mark.parametrize(
    "reference_date",
    [
        "",
        "2027-02-29",
        "2028-13-01",
        "2028-02",
        "20280229",
        "2028-W09-2",
        "2028-02-29T00:00:00",
        " 2028-02-29",
    ],
)
def test_invalid_date_is_rejected_even_without_an_eligible_marker(
    builder, facts, reference_date
):
    original = deepcopy(facts)
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        builder.facts_to_field(facts, reference_date=reference_date)
    assert facts == original


@pytest.mark.parametrize("reference_date", [None, "2028-02-29"])
def test_cli_passes_reference_date_to_poster_and_sidecar(
    builder, facts, monkeypatch, reference_date
):
    facts["status"] = "producing"
    builder.FACTS.write_text(json.dumps([facts]), encoding="utf-8")
    monkeypatch.setattr(builder, "build_index", lambda fields: "Synthetic index")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_lifecycle_posters",
            *(["--reference-date", reference_date] if reference_date else []),
        ],
    )
    builder.main()
    html = (builder.HERE / "synthetic_lifecycle.html").read_text(encoding="utf-8")
    payload = json.loads(re.search(r"const FIELD = (\{.*?\n\});", html, re.S).group(1))
    sidecar = json.loads((builder.HERE / "_explorer.json").read_text(encoding="utf-8"))
    assert sidecar["fields"]["synthetic"] == payload
    assert _markers(payload)[0]["dt"] == (reference_date or "2026.5")


def test_cli_rejects_invalid_date_before_writing(builder, monkeypatch, capsys):
    original = {path.name: path.read_bytes() for path in builder.HERE.iterdir()}
    monkeypatch.setattr(
        sys, "argv", ["build_lifecycle_posters", "--reference-date", "2027-02-29"]
    )
    with pytest.raises(SystemExit) as exc:
        builder.main()
    assert exc.value.code == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err
    assert {path.name: path.read_bytes() for path in builder.HERE.iterdir()} == original
