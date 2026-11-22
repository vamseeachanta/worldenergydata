"""Synthetic date-to-payload contracts for lifecycle posters (issue #738).

Hand calculation: discovery 2020 to FID 2022 takes two years; FID 2022
to first oil 2025 takes three. July's midpoint is 6.5 of twelve months,
or 13/24 of a year. Applying that offset to all gates preserves both spans.
No published field facts or engineering-overlay template are loaded here.
"""

from __future__ import annotations

import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from worldenergydata.common import fields_registry

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = PROJECT_ROOT / "scripts/lower_tertiary/build_lifecycle_posters.py"

# Literal expectations from the synthetic years and hand calculation above.
DISCOVERY = {
    "year": 2020,
    "phase": "explore",
    "lab": "Discovery",
    "dt": "2020",
    "kind": "primary",
}
FID = {
    "year": 2022,
    "phase": "define",
    "lab": "FID / Sanction",
    "dt": "2022",
    "kind": "primary",
}
FIRST_OIL = {
    "year": 2025,
    "phase": "operate",
    "lab": "First oil",
    "dt": "2025",
    "kind": "now",
}
DISCOVERY_TO_FID = {"from": 2020, "to": 2022, "txt": "Discovery→FID ~2 yr"}
FID_TO_FIRST_OIL = {"from": 2022, "to": 2025, "txt": "FID→first oil ~3 yr"}


@pytest.fixture
def builder(monkeypatch, tmp_path):
    """Redirect import-time and runtime data paths before loading the builder."""
    registry_field = SimpleNamespace(
        surfaces={}, leases=(), area_blocks=(), bsee_block_note="", fdp_slug=""
    )
    registry = SimpleNamespace(
        by_id=lambda field_id: registry_field if field_id == "synthetic" else None
    )
    monkeypatch.setattr(fields_registry, "load_fields", lambda: registry)
    # The loader still reads production code, while __file__ redirects its data
    # roots, including import-time lease/decommissioning reads, to empty folders.
    # syspath_prepend also restores the builder's sys.path edits on teardown.
    monkeypatch.syspath_prepend(str(PROJECT_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("gate_payload_builder", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(tmp_path / "scripts/lower_tertiary" / BUILDER_PATH.name)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "_architecture_for", lambda field_id: {})
    monkeypatch.setattr(module, "classify_tree_type", lambda host: (None, None))
    monkeypatch.setattr(module, "classify_hpht", lambda reservoir: {})
    monkeypatch.setattr(module, "classify_decommissioning", lambda *args: {})
    monkeypatch.setattr(module, "build_landman", lambda *args: {})
    monkeypatch.setattr(module, "build_concept", lambda **kwargs: {})
    monkeypatch.setattr(module.site_nav, "inject_for", lambda html, *args: html)
    module.TEMPLATE.parent.mkdir(parents=True)
    module.TEMPLATE.write_text(
        "<script>\nconst FIELD = __FIELD_JSON__;\n</script>\n", encoding="utf-8"
    )
    return module


@pytest.fixture
def facts():
    return {
        "id": "synthetic",
        "name": "Synthetic field",
        "status": "execution",
        "current_phase": "execute",
        "working_interest": [],
        "gates": {"discovery_year": 2020, "fid_year": 2022, "first_oil": 2025},
    }


@pytest.mark.parametrize("date_format", ["year-number", "year-string", "year-month"])
def test_gate_spans_match_hand_dates(builder, facts, date_format):
    if date_format == "year-string":
        facts["gates"] = {
            "discovery_year": "2020",
            "fid_year": "2022",
            "first_oil": "2025",
        }
    elif date_format == "year-month":
        facts["gates"] = {
            "discovery_year": "2020-07",
            "fid_year": "2022-07",
            "first_oil": "2025-07",
        }
    original = deepcopy(facts)

    field = builder.facts_to_field(facts)

    expected_gates = deepcopy([DISCOVERY, FID, FIRST_OIL])
    expected_spans = deepcopy([DISCOVERY_TO_FID, FID_TO_FIRST_OIL])
    if date_format == "year-month":
        # Independent midpoint arithmetic, with twelve months per year.
        for gate, date in zip(expected_gates, ["2020-07", "2022-07", "Jul 2025"]):
            gate["year"] += 13 / 24
            gate["dt"] = date
        for span in expected_spans:
            span["from"] += 13 / 24
            span["to"] += 13 / 24
    assert field["gates"] == expected_gates
    assert field["spans"] == expected_spans
    assert facts == original


@pytest.mark.parametrize("missing_form", ["omitted", "null"])
@pytest.mark.parametrize(
    "present, expected_gates, expected_spans",
    [
        ((), [], []),
        (("discovery_year",), [DISCOVERY], []),
        (("fid_year",), [FID], []),
        (("first_oil",), [FIRST_OIL], []),
        (("discovery_year", "fid_year"), [DISCOVERY, FID], [DISCOVERY_TO_FID]),
        (("fid_year", "first_oil"), [FID, FIRST_OIL], [FID_TO_FIRST_OIL]),
        (("discovery_year", "first_oil"), [DISCOVERY, FIRST_OIL], []),
    ],
)
def test_missing_gates_are_not_invented(
    builder, facts, missing_form, present, expected_gates, expected_spans
):
    facts["gates"] = {
        key: value if key in present else None
        for key, value in facts["gates"].items()
        if key in present or missing_form == "null"
    }
    if not present and missing_form == "omitted":
        del facts["gates"]
    original = deepcopy(facts)

    field = builder.facts_to_field(facts)

    assert field["gates"] == expected_gates
    assert field["spans"] == expected_spans
    assert facts == original


@pytest.mark.parametrize(
    "dates, expected_dates, expected_years",
    [
        (("2020", "2022", "2025"), ["2020", "2022", "2025"], [2020, 2022, 2025]),
        (
            ("2020-07", "2022-07", "2025-07"),
            ["2020-07", "2022-07", "Jul 2025"],
            [2020 + 13 / 24, 2022 + 13 / 24, 2025 + 13 / 24],
        ),
        (
            ("2020", "2022-07", "2025"),
            ["2020", "2022-07", "2025"],
            [2020, 2022 + 13 / 24, 2025],
        ),
    ],
)
def test_render_preserves_gate_payload(
    builder, facts, dates, expected_dates, expected_years
):
    facts["gates"] = dict(zip(("discovery_year", "fid_year", "first_oil"), dates))
    original = deepcopy(facts)
    field = builder.facts_to_field(facts)
    field_before_render = deepcopy(field)

    html = builder.render(field)

    assert "__FIELD_JSON__" not in html
    embedded = re.search(r"const FIELD = (\{.*?\n\});", html, re.DOTALL)
    assert embedded is not None
    payload = json.loads(embedded.group(1))
    assert payload == field_before_render
    assert [gate["dt"] for gate in payload["gates"]] == expected_dates
    assert [gate["year"] for gate in payload["gates"]] == expected_years
    assert field == field_before_render
    assert facts == original
