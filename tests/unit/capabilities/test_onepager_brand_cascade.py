"""Exercise the optional stylesheet contract without choosing a brand design."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

# The root is above tests/unit/capabilities in this file's repository layout.
REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def builder():
    script = REPO / "scripts/capabilities/build_onepagers.py"
    spec = importlib.util.spec_from_file_location("onepager_brand_builder", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def card_spec():
    """Supply independent content rather than copying a published card."""
    return {
        "id": "synthetic-card",
        "kind": "section",
        "title": "Synthetic capability",
        "std": "Synthetic source; no measured data",
        "path": "synthetic-card.html",
        "blurb": "Synthetic content for stylesheet tests.",
        "figures": [],
        "bullets": ["Synthetic deliverable"],
    }


@pytest.fixture
def brand_css():
    """Independent resource-free example; quotes and whitespace are deliberate."""
    return """/* Synthetic theme rules; no brand palette is selected. */
:root[data-theme="light"] .brand-probe,
html[data-theme='light'] .brand-probe {
  --cascade-probe: light;
  color: inherit;
}

:root[data-theme='dark'] .brand-probe,
html[data-theme="dark"] .brand-probe {
  --cascade-probe: dark;
  color: inherit;
}
"""


@pytest.fixture
def default_tokens():
    """Read the independent stylesheet asset, not the renderer's token value."""
    tokens = REPO / "reports/capabilities/assets/tokens.css"
    return tokens.read_text(encoding="utf-8").strip()


@pytest.fixture
def branded_card(builder, card_spec, brand_css, tmp_path):
    return builder.build_onepager(card_spec, tmp_path / "cards", brand_css=brand_css)


def test_brand_stylesheet_follows_default_tokens(
    branded_card, brand_css, default_tokens
):
    document = branded_card.read_text(encoding="utf-8")
    # The documented API appends a brand block after the complete default block.
    default_style, brand_style = re.findall(
        r"<style[^>]*>(.*?)</style>", document, re.DOTALL
    )
    assert default_tokens in default_style
    # These selectors identify default layout rules in build_onepagers._TEMPLATE.
    assert "body{" in default_style
    assert ".top{" in default_style
    assert ".cta{" in default_style
    assert brand_style == brand_css
    assert document.index(default_tokens) < document.index(brand_css)


def test_theme_selectors_survive_inlining(branded_card, brand_css):
    # Exact UTF-8 bytes from the independent fixture include both theme selectors,
    # their quote forms, declarations, blank lines and the trailing newline.
    expected_block = f"<style>{brand_css}</style>".encode("utf-8")
    assert expected_block in branded_card.read_bytes()


@pytest.mark.parametrize("explicit_empty", [False, True], ids=["omitted", "empty"])
def test_default_card_has_no_extra_brand_block(
    builder, card_spec, default_tokens, tmp_path, explicit_empty
):
    arguments = {"brand_css": ""} if explicit_empty else {}
    source = builder.build_onepager(card_spec, tmp_path / "cards", **arguments)
    document = source.read_text(encoding="utf-8")
    # The default API call emits only the default style block.
    (default_style,) = re.findall(r"<style[^>]*>(.*?)</style>", document, re.DOTALL)
    assert default_tokens in default_style
    assert "body{" in default_style
    assert ".top{" in default_style
    assert ".cta{" in default_style
    assert "brand-probe" not in document
