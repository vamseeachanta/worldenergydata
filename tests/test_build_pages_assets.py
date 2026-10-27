"""Synthetic examples for optional lifecycle asset-page publication.

The literal HTML below defines the expected bytes and links independently of
the publisher. No generated reports or named real facilities are needed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_pages.py"
INDEX_HTML = (
    b'<!doctype html><a href="assets/fixture_assets.html#facility">'
    b"Synthetic field assets</a>\r\n"
)
ASSET_HTML = """<!doctype html>
<meta charset="utf-8">
<a href="../index.html">Lifecycle gallery</a>
<section id="facility">
  <a href="#asset">Facility → asset</a>
  <section id="asset">
    <a href="#component">Asset → component</a>
    <section id="component">
      <a href="../../index.html#engineering">Component → engineering</a>
    </section>
  </section>
</section>
""".replace(
    "\n", "\r\n"
).encode(
    "utf-8"
)


@pytest.fixture
def lifecycle_builder(tmp_path, monkeypatch):
    """Redirect every report and publication path to a synthetic tree."""
    spec = importlib.util.spec_from_file_location(
        "build_pages_assets_under_test", SCRIPT
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    public = tmp_path / "public"
    reports = tmp_path / "reports"
    monkeypatch.setattr(builder, "PUBLIC", public)
    monkeypatch.setattr(builder, "ASSETS", public / "assets")
    monkeypatch.setattr(builder, "REPORTS", reports)
    lifecycle = reports / "lower_tertiary" / "lifecycle"
    lifecycle.mkdir(parents=True)
    (lifecycle / "index.html").write_bytes(INDEX_HTML)
    return builder, lifecycle


def test_lifecycle_asset_pages_publish_without_link_rewrite(lifecycle_builder):
    builder, lifecycle = lifecycle_builder
    assets = lifecycle / "assets"
    assets.mkdir()
    (assets / "fixture_assets.html").write_bytes(ASSET_HTML)

    builder.build_lower_tertiary({})

    published = builder.PUBLIC / "lifecycle"
    assert (published / "index.html").read_bytes() == INDEX_HTML
    page = (published / "assets" / "fixture_assets.html").read_bytes()
    assert page == ASSET_HTML
    assert b'href="../index.html"' in page
    assert b'href="#asset"' in page
    assert b'href="#component"' in page
    assert b'href="../../index.html#engineering"' in page


def test_missing_asset_directory_is_optional(lifecycle_builder):
    builder, lifecycle = lifecycle_builder
    assert not (lifecycle / "assets").exists()

    builder.build_lower_tertiary({})

    published = builder.PUBLIC / "lifecycle"
    assert (published / "index.html").read_bytes() == INDEX_HTML
    assert not (published / "assets").exists()


def test_asset_templates_are_not_published(lifecycle_builder):
    builder, lifecycle = lifecycle_builder
    assets = lifecycle / "assets"
    assets.mkdir()
    (assets / "fixture_assets.html").write_bytes(ASSET_HTML)
    (assets / "lifecycle_template.html").write_bytes(b"<html>Template only</html>\n")
    (assets / "notes.txt").write_bytes(b"Unpublished notes\n")

    builder.build_lower_tertiary({})

    published = builder.PUBLIC / "lifecycle" / "assets"
    assert {path.name for path in published.iterdir()} == {"fixture_assets.html"}
    assert (published / "fixture_assets.html").read_bytes() == ASSET_HTML
