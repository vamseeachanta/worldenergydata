"""Publication checks for the shared WAR methodology limits."""

import importlib.util
from html import unescape
from pathlib import Path

import pytest

from worldenergydata.bsee.analysis.drilling_intensity import DEPTH_COLUMNS

REPO = Path(__file__).resolve().parents[3]


def load_script(relative):
    path = REPO / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_limits(text):
    """Depth names follow the normalization module's existing column symbol."""
    text = " ".join(unescape(text).split())
    for fragment in (
        "WAR methodology limits",
        "Weekly boundary quantization",
        "Sunday",
        "Saturday",
        "Coverage floor",
        "unconfirmed",
        f"measured depth (MD), {DEPTH_COLUMNS['md']}",
        f"true vertical depth (TVD), {DEPTH_COLUMNS['tvd']}",
        "no definition was found in the sources cited here",
        "Publisher-declared basis",
        "1064#issuecomment-6131101384",
        "20–23 days per 10,000 ft",
        "87117-MS",
        "comparability",
    ):
        assert fragment in text, f"missing methodology disclosure: {fragment}"


@pytest.mark.parametrize("surface", ["validation", "listing", "drilldown", "card"])
def test_selected_surfaces_disclose_all_limits(surface, tmp_path):
    if surface == "validation":
        mod = load_script("scripts/build_pages.py")
        mod.PUBLIC = tmp_path / "public"
        mod.ASSETS = mod.PUBLIC / "assets"
        mod.build(domains=["lower_tertiary"])
        text = (mod.PUBLIC / "wo-april-2026-validation.html").read_text()
    elif surface == "listing":
        mod = load_script("scripts/lower_tertiary/build_wo_per_well_dc.py")
        text = mod.build_markdown(mod.load_bores(), mod.load_vintage_diff())
    elif surface == "drilldown":
        mod = load_script("scripts/lower_tertiary/build_dc_drilldown.py")
        text = mod.build_html(mod.load_payload())
    else:
        mod = load_script("scripts/hf_export/publish_dc_days_to_hf.py")
        card = (
            "---\nconfigs:\n- config_name: parametric_economics\n"
            "  data_files: parametric_economics.parquet\n---\n"
        )
        text = mod.patch_readme(card)
    assert_limits(text)


def test_existing_dataset_card_acquires_note_once():
    mod = load_script("scripts/hf_export/publish_dc_days_to_hf.py")
    card = "---\nconfigs:\n- config_name: dc_bores\n---\nExisting card text.\n"
    updated = mod.patch_readme(card)
    assert_limits(updated)
    assert updated.startswith(card)
    assert updated.count("WAR methodology limits") == 1
    assert mod.patch_readme(updated) == updated
