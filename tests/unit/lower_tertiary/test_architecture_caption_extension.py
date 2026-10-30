"""Architecture caption contracts for synthetic concepts (issue #942).

Expected payloads follow the caption precedence and placeholder contract in
issue #942; SVG strings are sentinels, independent of rendering geometry.
"""

import importlib.util
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock

import pytest

from worldenergydata.common import fields_registry
from worldenergydata.field_development.models import FieldConcept

# Ascend from tests/unit/lower_tertiary to the repository root.
REPO = Path(__file__).resolve().parents[3]
BUILDER_PATH = REPO / "scripts/lower_tertiary/build_lifecycle_posters.py"
SYNTHETIC_ID = "synthetic_extension"
SVG_SENTINEL = "<svg><!-- synthetic layout sentinel --></svg>"


@pytest.fixture
def builder(monkeypatch):
    """Load the real helper without registry, liability or lease source data."""
    monkeypatch.setattr(fields_registry, "load_fields", Mock(return_value=None))
    exists = Path.exists
    source_names = {"regional_liability.csv", "leases.xlsx", "leases_v21_kc.csv"}
    monkeypatch.setattr(
        Path,
        "exists",
        lambda path: False if path.name in source_names else exists(path),
    )
    monkeypatch.syspath_prepend(str(REPO / "src"))
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "architecture_caption_builder", BUILDER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_new_authored_id_uses_concept_name(builder, monkeypatch):
    concept = FieldConcept(name="Synthetic subsea concept")
    lookup = Mock(return_value=concept)
    render = Mock(return_value=SVG_SENTINEL)
    monkeypatch.setattr(builder, "concept_for", lookup)
    monkeypatch.setattr(builder, "render_layout", render)
    assert SYNTHETIC_ID not in builder._ARCH_CAPTION

    payload = builder._architecture_for(SYNTHETIC_ID)

    assert payload == {
        "caption": "Synthetic subsea concept",
        "svg": SVG_SENTINEL,
        "source": "render_layout",
    }
    lookup.assert_called_once_with(SYNTHETIC_ID)
    render.assert_called_once_with(concept)


def test_authored_caption_override_wins(builder, monkeypatch):
    concept = FieldConcept(name="Synthetic subsea concept")
    monkeypatch.setattr(builder, "concept_for", Mock(return_value=concept))
    render = Mock(return_value=SVG_SENTINEL)
    monkeypatch.setattr(builder, "render_layout", render)
    monkeypatch.setattr(
        builder, "_ARCH_CAPTION", {SYNTHETIC_ID: "Synthetic caption override"}
    )

    assert builder._architecture_for(SYNTHETIC_ID) == {
        "caption": "Synthetic caption override",
        "svg": SVG_SENTINEL,
        "source": "render_layout",
    }
    render.assert_called_once_with(concept)


def test_missing_concept_remains_placeholder(builder, monkeypatch):
    lookup = Mock(return_value=None)
    render = Mock(side_effect=AssertionError("Missing concepts must not render"))
    monkeypatch.setattr(builder, "concept_for", lookup)
    monkeypatch.setattr(builder, "render_layout", render)

    # The documented placeholder links the FDP-authoring backlog, issue #962.
    assert builder._architecture_for(SYNTHETIC_ID) == {
        "svg": None,
        "pending_issue": 962,
    }
    lookup.assert_called_once_with(SYNTHETIC_ID)
    render.assert_not_called()


class _PosterParser(HTMLParser):
    """Inspect the HTML parsing boundaries, independently of serialization."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts = []
        self.headings = []
        self.tags = []
        self._in_script = False
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "script":
            self.scripts.append("")
            self._in_script = True
        if tag == "h3":
            self.headings.append("")
            self._in_heading = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False
        if tag == "h3":
            self._in_heading = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1] += data
        if self._in_heading:
            self.headings[-1] += data


def _synthetic_field(builder, monkeypatch, name):
    concept = FieldConcept(name=name)
    monkeypatch.setattr(builder, "concept_for", lambda field_id: concept)
    return {
        "id": SYNTHETIC_ID,
        "name": "Synthetic field",
        "architecture": builder._architecture_for(SYNTHETIC_ID),
    }


@pytest.mark.parametrize(
    "name",
    [
        '</script><script>void "synthetic"</script>',
        '</ScRiPt ><img src=x onerror="void 0">',
        "<!--<script>synthetic</script>",
        'Synthetic café & <layout> "caption"',
    ],
)
def test_concept_name_cannot_break_script_embedding(builder, monkeypatch, name):
    field = _synthetic_field(builder, monkeypatch, name)
    parser = _PosterParser()

    parser.feed(builder.render(field))

    assert len(parser.scripts) == 1
    embedded = parser.scripts[0].split("const FIELD = ", 1)[1]
    decoded, _ = json.JSONDecoder().raw_decode(embedded)
    assert decoded["architecture"]["caption"] == name
    assert decoded["architecture"]["svg"] == field["architecture"]["svg"]
    assert "<svg" in decoded["architecture"]["svg"]


@pytest.mark.parametrize(
    "name",
    [
        "Synthetic <b>concept</b>",
        'Synthetic <img src=x onerror="void 0">',
        'Synthetic &amp; < > "quotes" café',
    ],
)
def test_architecture_caption_is_literal_text(builder, monkeypatch, name):
    field = _synthetic_field(builder, monkeypatch, name)
    page = _PosterParser()
    page.feed(builder.render(field))
    script = page.scripts[0]
    start = script.index("if (FIELD.architecture) {")
    end = script.index("// Lease & landman panel", start)
    # Execute the real panel renderer; only its DOM insertion target is replaced.
    program = (
        "const FIELD = JSON.parse(process.argv[2]);\n"
        'const panel = {innerHTML: ""};\n'
        'const $ = id => { if (id !== "f-arch") throw Error(id); return panel; };\n'
        + script[start:end]
        + "\nprocess.stdout.write(panel.innerHTML);\n"
    )
    result = subprocess.run(
        ["node", "-", json.dumps(field)],
        input=program,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    panel = _PosterParser()
    panel.feed(result.stdout)

    assert panel.headings == [f"Architecture — {name}"]
    assert not {"b", "img", "script"}.intersection(panel.tags)
    assert field["architecture"]["svg"] in result.stdout
