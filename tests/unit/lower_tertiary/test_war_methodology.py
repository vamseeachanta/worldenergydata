"""Publication checks for the shared WAR methodology limits."""

import importlib.util
from html import unescape
from html.parser import HTMLParser
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
        "1064#issuecomment-6132640847",
        "Milestone basis is the default",
        "retained side by side",
        "confirmation across the wider well population",
        "reports submitted since April 2004",
        "reported, not confirmed",
        "per 1,000 ft",
        "per 10,000 ft",
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
    assert text.count("WAR methodology limits") == 1
    assert_source_list(text)


def test_existing_dataset_card_acquires_note_once():
    mod = load_script("scripts/hf_export/publish_dc_days_to_hf.py")
    card = "---\nconfigs:\n- config_name: dc_bores\n---\nExisting card text.\n"
    updated = mod.patch_readme(card)
    assert_limits(updated)
    assert updated.startswith(card)
    assert updated.count("WAR methodology limits") == 1
    assert mod.patch_readme(updated) == updated


class NoteParser(HTMLParser):
    """Record note ancestry, source items and balanced surrounding tags."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.ancestors = []
        self.items = 0
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "war-methodology" in attributes.get("class", "").split():
            self.ancestors.append(list(self.stack))
        if tag == "li" and any(
            "war-methodology" in attr.get("class", "").split() for _, attr in self.stack
        ):
            self.items += 1
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append((tag, attributes))

    def handle_startendtag(self, tag, attrs):
        """Self-closing SVG elements do not enter the ancestor stack."""

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append(tag)
        else:
            self.stack.pop()


def assert_source_list(text):
    """Each selected surface renders three distinct source items."""
    if "<section" in text:
        parser = NoteParser()
        parser.feed(text)
        assert parser.items == 3
    else:
        note = text.split("## WAR methodology limits", 1)[1]
        assert len([line for line in note.splitlines() if line.startswith("- ")]) == 3


def test_note_uses_superseding_milestone_decision():
    note = load_script("scripts/lower_tertiary/war_methodology.py").WAR_METHODOLOGY
    text = " ".join(note.split())
    assert "1064#issuecomment-6132640847" in text
    assert "6131101384" not in text
    assert "Milestone basis is the default" in text
    assert "total-depth date minus spud date" in text
    assert "every reported day from total depth onward, all activity codes" in text
    assert "unreported gaps left out" in text
    assert "retained side by side" in text
    assert "confirmation across the wider well population" in text
    assert "before any published figure is replaced" in text


def test_coverage_floor_is_reported_not_confirmed():
    note = load_script("scripts/lower_tertiary/war_methodology.py").WAR_METHODOLOGY
    text = " ".join(note.split())
    assert "reports submitted since April 2004" in text
    assert "reported, not confirmed from an agency page" in text
    assert "Makefile, comment above the data target, attributed to issue 1066" in text
    assert "Historical completeness" in text
    assert "Missing historical reports shall not be interpreted as zero days" in text


def test_depth_units_distinguish_legacy_and_learning_ratios():
    note = load_script("scripts/lower_tertiary/war_methodology.py").WAR_METHODOLOGY
    text = " ".join(note.split())
    assert "legacy Days/10K ratios are per 10,000 ft" in text
    assert "learning-series ratios are per 1,000 ft" in text


def test_drilldown_note_is_last_panel_inside_main_container():
    mod = load_script("scripts/lower_tertiary/build_dc_drilldown.py")
    text = mod.build_html(mod.load_payload())
    parser = NoteParser()
    parser.feed(text)
    assert len(parser.ancestors) == 1
    assert any(
        tag == "div" and attrs.get("class") == "wrap"
        for tag, attrs in parser.ancestors[0]
    )
    assert not parser.errors
    assert not parser.stack
    assert text.index('class="panel war-methodology"') < text.index(
        "<script>const DATA="
    )
    after_note = text.split('class="panel war-methodology"', 1)[1]
    assert '<section class="panel' not in after_note


def test_sources_are_markdown_and_html_lists():
    mod = load_script("scripts/lower_tertiary/war_methodology.py")
    assert_source_list(mod.WAR_METHODOLOGY)
    assert_source_list(mod.methodology_html())


def test_html_source_items_are_escaped():
    mod = load_script("scripts/lower_tertiary/war_methodology.py")
    mod.WAR_METHODOLOGY = "## WAR methodology limits\n\n- <unsafe>&source"
    assert "<ul><li>&lt;unsafe&gt;&amp;source</li></ul>" in mod.methodology_html()


def test_existing_dataset_card_replaces_old_note_once():
    mod = load_script("scripts/hf_export/publish_dc_days_to_hf.py")
    card = "---\nconfigs:\n- config_name: dc_bores\n---\nExisting card text.\n"
    old_note = (
        "## WAR methodology limits\n\nPublisher-declared basis: "
        "the owner decision ratifies activity-coded drilling days and "
        "completion-coded days only.\n"
    )
    suffix = "\n## Other metadata\nRetained metadata.\n"
    updated = mod.patch_readme(card + old_note + suffix)
    assert updated.count("WAR methodology limits") == 1
    assert old_note not in updated
    assert suffix.strip() in updated
    assert_limits(updated)
    assert_source_list(updated)
    assert mod.patch_readme(updated) == updated
