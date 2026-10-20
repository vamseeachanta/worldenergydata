"""Offline P&A consumer contracts against the committed attribution evidence."""

import importlib.util
import json
import runpy
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/modules/bsee/borehole_status"
POSTERS = ROOT / "reports/lower_tertiary/lifecycle"


def builder():
    spec = importlib.util.spec_from_file_location(
        "pa_posters", ROOT / "scripts/lower_tertiary/build_lifecycle_posters.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_poster_signal_matches_independently_counted_attributed_rows():
    """Expected counts tally each API12 row directly, without summary or model."""
    module = builder()
    rows = json.loads((DATA / "attributed.json").read_text())
    counts = Counter((row["field_id"], row["status_code"]) for row in rows)
    for facts in json.loads((POSTERS / "_facts.json").read_text()):
        signal = module.facts_to_field(facts)["risk"]["well_pa"]
        assert signal["ta_count"] == counts[(facts["id"], "TA")]
        assert signal["com_count"] == counts[(facts["id"], "COM")]
        assert signal["cost"]["status"] == "NOT_EVALUATED"
        assert signal["provenance"]["source_retrieved_at_utc"]


def test_missing_snapshot_gives_no_badge(monkeypatch, tmp_path):
    module = builder()
    monkeypatch.setattr(module, "_BOREHOLE_SUMMARY", tmp_path / "missing.json")
    monkeypatch.setattr(module, "_WELL_PA_SIGNALS", module._load_well_pa_signals())
    facts = json.loads((POSTERS / "_facts.json").read_text())[0]
    assert module.facts_to_field(facts)["risk"]["well_pa"] is None


def test_main_shares_identical_risk_between_sidecars_and_posters(monkeypatch, tmp_path):
    """Each emitted payload carries the same per-field signal, with no re-count."""
    module = builder()
    monkeypatch.setattr(module, "HERE", tmp_path)
    monkeypatch.setattr("sys.argv", ["build_lifecycle_posters.py"])
    embedded = {}

    def capture(field):
        embedded[field["id"]] = field["risk"]
        return "<!doctype html>"

    monkeypatch.setattr(module, "render", capture)
    module.main()
    explorer = json.loads((tmp_path / "_explorer.json").read_text())
    risk = json.loads((tmp_path / "_risk.json").read_text())
    assert risk["fields"] == embedded
    assert risk["fields"] == {
        field_id: field["risk"] for field_id, field in explorer["fields"].items()
    }


def test_explicit_cost_inputs_flow_to_the_consumer(monkeypatch, tmp_path):
    """Every candidate at a hypothetical 10 USD costs 10*(TA+COM) USD."""
    module = builder()
    facts = json.loads((POSTERS / "_facts.json").read_text())[0]
    path = tmp_path / "costs.json"
    path.write_text(
        json.dumps(
            {
                facts["id"]: {
                    "unit_cost_usd": {"TA": "10", "COM": "10"},
                    "source": "Synthetic hand calculation in this test",
                    "price_basis": "Hypothetical USD; not a field estimate",
                }
            }
        )
    )
    monkeypatch.setattr(module, "HERE", tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["build_lifecycle_posters.py", "--well-pa-costs", str(path)]
    )
    monkeypatch.setattr(module, "render", lambda field: "<!doctype html>")
    module.main()
    risk = json.loads((tmp_path / "_risk.json").read_text())
    signal = risk["fields"][facts["id"]]["well_pa"]
    assert signal["cost"]["status"] == "SCENARIO"
    assert signal["cost"]["total_usd"] == str(
        (signal["ta_count"] + signal["com_count"]) * 10
    )


def test_templates_render_count_provenance_and_cost_limit():
    poster = (POSTERS / "lifecycle_template.html").read_text()
    atlas = (ROOT / "reports/field-atlas/atlas_template.html").read_text()
    assert 'id="f-risk-well-pa"' in poster
    assert "RISK.well_pa.note" in poster
    assert "RISK.well_pa.provenance.status_definitions_url" in poster
    assert "risk.well_pa.note" in atlas
    assert "risk.well_pa.provenance.status_definitions_url" in atlas
    assert "Well-plugging P&amp;A is not attributed per field" not in atlas


def test_worked_example_answer_is_the_independent_hand_calculation():
    """Example answer: 2*10 + 3*20 = 80 USD for 2+3 = 5 candidate boreholes."""
    from worldenergydata.field_development.well_pa_risk import build_well_pa_signals

    example = runpy.run_path(str(ROOT / "examples/bsee/well_pa_screen.py"))
    signal = build_well_pa_signals(example["SNAPSHOT"], example["COST_INPUTS"])[
        "sample_field"
    ]
    assert signal["candidate_boreholes"] == 5
    assert signal["cost"]["total_usd"] == "80"


def test_render_keeps_supplied_cost_text_inside_the_json_script():
    module = builder()
    facts = json.loads((POSTERS / "_facts.json").read_text())[0]
    field = module.facts_to_field(facts)
    field["risk"]["well_pa"]["note"] = "</script><script>unexpected()</script>"
    html = module.render(field)
    assert "</script><script>unexpected()" not in html
    assert "\\u003c/script>\\u003cscript>unexpected()" in html
