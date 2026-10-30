"""Capability disclosures and independently calculated documentation examples."""

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def load_script(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, REPO / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capability_metadata_retains_disclosures_and_unresolved_checks():
    """Requirements: issue #1078; CFR 2025, 250.743(a); SPE-87117-MS (2004)."""
    mod = load_script("scripts/lower_tertiary/war_methodology.py")
    metadata = mod.methodology_metadata()
    assert metadata["data_limits"] == mod.WAR_METHODOLOGY
    assert metadata["basis_decision_url"] == mod.DECISION_URL
    assert metadata["coverage_floor_status"] == "NOT_EVALUATED"
    assert metadata["reference_comparability_status"] == "NOT_EVALUATED"
    assert metadata["depth_denominator_policy"] == "explicit MD or TVD required"
    assert json.loads(json.dumps(metadata)) == metadata


def test_conflicting_display_bases_are_rejected():
    mod = load_script("scripts/lower_tertiary/war_methodology.py")
    with pytest.raises(ValueError, match="mutually exclusive"):
        mod.methodology_html(calendar=True, activity=True)


def test_site_build_exports_capability_data_limits(tmp_path):
    mod = load_script("scripts/build_pages.py")
    mod.PUBLIC = tmp_path / "public"
    mod.ASSETS = mod.PUBLIC / "assets"
    mod.build(domains=["lower_tertiary"])
    path = mod.PUBLIC / "war-methodology.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    note = load_script("scripts/lower_tertiary/war_methodology.py")
    assert metadata == note.methodology_metadata()
    original = path.read_bytes()
    mod.build(domains=["lower_tertiary"])
    assert path.read_bytes() == original


def test_worked_example_uses_declared_denominators():
    """Synthetic inputs, not a published well or an acceptance criterion.

    Independent hand calculation: 2025-01-01 to 2025-02-12 is 31 + 11 =
    42 elapsed days. For selected milestone days and full-depth denominators,
    42 / 20,000 * 10,000 = 21.0 days per 10,000 ft MD, while
    42 / 15,000 * 10,000 = 28.0 days per 10,000 ft TVD.
    Scaling follows the units in SPE-87117-MS (2004), abstract paragraph 4;
    that source does not specify a denominator or validate milestone days.
    """
    from worldenergydata.bsee.analysis.drilling_intensity import bore_intensity

    days = (date(2025, 2, 12) - date(2025, 1, 1)).days
    assert days == 42
    bore = {
        "drilling_days": days,
        "basis": "milestone_calendar",
        "MAX_BH_TOTAL_MD": 20_000,
        "MAX_WELL_BORE_TVD": 15_000,
    }
    assert bore_intensity(bore, denominator="md")["days_per_10k_ft"] == 21.0
    assert bore_intensity(bore, denominator="tvd")["days_per_10k_ft"] == 28.0


def test_comparison_page_discloses_activity_basis_without_changing_counts():
    """The comparison uses activity days; the superseding default is milestone."""
    mod = load_script("scripts/lower_tertiary/build_roy_rig_days_qa.py")
    text = mod.build(mod.load_cache())
    assert text.count("WAR methodology limits") == 1
    assert "this page compares activity-code days" in text
    assert "does not apply the milestone default to the displayed figures" in text
    assert "no depth-normalized ratio is calculated" in text
    for phrase in ("Weekly boundary quantization", "Coverage floor", "20–23"):
        assert phrase in text
    assert (
        text
        == (REPO / "reports/lower_tertiary/roy-rig-days-validation.html").read_text()
    )
