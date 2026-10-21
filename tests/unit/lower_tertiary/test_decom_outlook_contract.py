"""Decommissioning outlook contracts and independently calculated examples."""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIFECYCLE = ROOT / "reports/lower_tertiary/lifecycle"


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/lower_tertiary" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def outlook():
    return load_script("build_decom_outlook")


def test_hand_calculation(outlook):
    """Synthetic 1,000 ft, two bores: d=1000*0.3048=304.8 m (NIST
    SP 811, 2008, Appendix B.8, foot). Repository cost_model.py, _COST_FACTORS
    well_p_and_a and _REGION_MULTIPLIERS gom: c=8+0.015*304.8=12.572 MUSD;
    two bores cost 25.144 MUSD. This tests arithmetic, not cost calibration.
    """
    record = outlook.build_record(
        {"water_depth_ft": 1000, "gates": {"projected_cop_year": 2040}},
        {"validated_economics": {"wellbores": 2}},
    )
    assert record["water_depth_m"] == pytest.approx(304.8)
    assert record["pa_per_well_musd"] == pytest.approx(12.572)
    assert record["pa_estimate_musd"] == pytest.approx(25.144)
    assert record["projected_cop_year"] == 2040
    assert record["bsee_decom_band"] is None
    assert record["bsee_reason"]
    assert "uncalibrated" in record["basis"].lower()
    assert record["regulations"]
    assert record["provenance"]["source_digests"]


@pytest.mark.parametrize("depth", [None, -1, float("nan"), float("inf"), True])
def test_unusable_depth_is_not_priced(outlook, depth):
    record = outlook.build_record(
        {"water_depth_ft": depth}, {"validated_economics": {"wellbores": 2}}
    )
    assert record["pa_per_well_musd"] is None
    assert record["pa_estimate_musd"] is None
    assert record["pa_reason"]


@pytest.mark.parametrize("count", [None, -1, 1.5, True])
def test_unknown_or_invalid_count_does_not_become_zero(outlook, count):
    record = outlook.build_record(
        {"water_depth_ft": 1000}, {"validated_economics": {"wellbores": count}}
    )
    assert record["wellbores"] is None
    assert record["pa_estimate_musd"] is None
    assert record["pa_per_well_musd"] is not None


def test_zero_count_is_preserved(outlook):
    """Zero explicitly recorded bores times any per-bore cost equals zero."""
    record = outlook.build_record(
        {"water_depth_ft": 1000}, {"validated_economics": {"wellbores": 0}}
    )
    assert record["wellbores"] == 0
    assert record["pa_estimate_musd"] == 0


def test_committed_sidecar_reproduces_inputs(outlook):
    import yaml

    facts = json.loads((LIFECYCLE / "_facts.json").read_text())
    registry = yaml.safe_load(
        (ROOT / "config/ong_field_development/fields_registry.yml").read_text()
    )["fields"]
    actual = json.loads((LIFECYCLE / "_decommissioning.json").read_text())
    generated_on = next(iter(actual["fields"].values()))["provenance"]["generated_on"]
    expected = outlook.build_outlook(facts, registry, generated_on=generated_on)
    assert actual == expected
    assert set(actual["fields"]) == {field["id"] for field in facts}


def test_cop_gate_and_optional_poster_card():
    builder = load_script("build_lifecycle_posters")
    fact = json.loads((LIFECYCLE / "_facts.json").read_text())[0]
    payload = builder.facts_to_field(fact)
    cop = fact.get("gates", {}).get("projected_cop_year")
    gates = [g for g in payload["gates"] if g["lab"] == "Projected COP"]
    assert bool(gates) == (cop is not None)
    if cop is not None:
        assert gates[0]["phase"] == "abandon"
        assert gates[0]["year"] == builder._year(cop)
    html = builder.render(payload)
    assert 'id="f-decommissioning-card" hidden' in html
    assert "if (FIELD.decommissioning)" in html
    assert "../decommissioning/pa-liability-wave.html" in html
    assert "../decommissioning/regional-liability.html" in html


def test_well_uses_field_depth_and_does_not_invent_filing(outlook):
    builder = load_script("build_well_timelines")
    contract = json.loads((LIFECYCLE / "wells/_wells.json").read_text())
    well = contract["wells"][0]
    field = contract["fields"][well["field_id"]]
    record = outlook.build_record({"water_depth_ft": 1000}, {})
    card = builder.facts_to_well(well, field, record)["cards"][-1]
    assert card["big"] == "$12.6M est."
    assert "../norms/abandon.html" in " ".join(card["li"])
    assert "filing status not evaluated" in " ".join(card["li"])
    missing = builder.facts_to_well(well, field)["cards"][-1]
    assert missing["big"] == "—"


def test_published_sidecar_and_posters_match(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "pages_decom", ROOT / "scripts/build_pages.py"
    )
    pages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pages)
    pages.PUBLIC = tmp_path / "public"
    pages.ASSETS = pages.PUBLIC / "assets"
    pages.build(domains=["lower_tertiary", "decommissioning"])
    data = json.loads((pages.PUBLIC / "lifecycle/_decommissioning.json").read_text())
    explorer = json.loads((pages.PUBLIC / "lifecycle/_explorer.json").read_text())
    for field_id, record in data["fields"].items():
        assert explorer["fields"][field_id]["decommissioning"] == record
    for target in ("pa-liability-wave.html", "regional-liability.html"):
        assert (pages.PUBLIC / "decommissioning" / target).exists()


@pytest.mark.parametrize("present", [False, True])
def test_poster_card_renders_without_interpreting_source_html(outlook, present):
    """The 25.1 MUSD display follows test_hand_calculation; null hides the card.
    A minimal DOM executes the actual template block without opening a browser.
    """
    if shutil.which("node") is None:
        pytest.skip("Node is unavailable for the template execution check")
    record = outlook.build_record(
        {"water_depth_ft": 1000}, {"validated_economics": {"wellbores": 2}}
    )
    record["regulations"][0]["name"] = "<untrusted source text>"
    template = (LIFECYCLE / "lifecycle_template.html").read_text()
    block = (
        "if (FIELD.decommissioning) {"
        + template.split("if (FIELD.decommissioning) {", 1)[1].split(
            "\nif (FIELD.economics_href)", 1
        )[0]
    )
    program = """
const nodes = {};
const make = () => ({hidden:true, textContent:'', children:[],
  append(...items) { this.children.push(...items); }});
const $ = id => nodes[id] || (nodes[id] = make());
const document = {createElement: make};
$("f-decommissioning-card");
"""
    program += (
        "const FIELD = "
        + json.dumps({"decommissioning": record if present else None})
        + ";\n"
    )
    program += block + "\nprocess.stdout.write(JSON.stringify(nodes));"
    result = subprocess.run(
        ["node", "-e", program], check=True, capture_output=True, text=True
    )
    nodes = json.loads(result.stdout)
    assert nodes["f-decommissioning-card"]["hidden"] is not present
    if present:
        rows = [
            child["textContent"] for child in nodes["f-decommissioning"]["children"]
        ]
        assert "$25.1M" in rows
        assert (
            "<untrusted source text>"
            in nodes["f-decommissioning-regulations"]["children"][0]["textContent"]
        )
