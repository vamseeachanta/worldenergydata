"""Architecture caption contracts for synthetic concepts (issue #942).

Expected payloads follow the caption precedence and placeholder contract in
issue #942; SVG strings are sentinels, independent of rendering geometry.
"""

import importlib.util
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
