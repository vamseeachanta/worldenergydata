"""Synthetic examples for optional lifecycle asset-page publication.

The literal HTML below defines the expected bytes and links independently of
the publisher. No generated reports or named real facilities are needed.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

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
    metadata = json.loads(
        (builder.PUBLIC / "war-methodology.json").read_text(encoding="utf-8")
    )
    assert metadata == builder.methodology_metadata()


def test_missing_asset_directory_is_optional(lifecycle_builder):
    builder, lifecycle = lifecycle_builder
    assert not (lifecycle / "assets").exists()

    builder.build_lower_tertiary({})

    published = builder.PUBLIC / "lifecycle"
    assert (published / "index.html").read_bytes() == INDEX_HTML
    assert not (published / "assets").exists()
    metadata = json.loads(
        (builder.PUBLIC / "war-methodology.json").read_text(encoding="utf-8")
    )
    assert metadata == builder.methodology_metadata()


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


def test_revision_comparison_publishes_resolving_assumptions_links(lifecycle_builder):
    builder, lifecycle = lifecycle_builder
    source = builder.ROOT / "reports/lower_tertiary/fdas_revision_comparison.md"
    (lifecycle.parent / source.name).write_bytes(source.read_bytes())
    log = (
        builder.ROOT / "config/analysis/lower_tertiary/v50_assumptions_change_log.html"
    )
    original = log.read_bytes()

    builder.build_lower_tertiary({})

    comparison = builder.PUBLIC / "fdas-revision-comparison.html"
    published = builder.PUBLIC / "v50-assumptions-change-log.html"
    assert published.is_file()
    comparison_links = re.findall(
        r'href="([^"]+)"', comparison.read_text(encoding="utf-8")
    )
    assert "v50-assumptions-change-log.html" in comparison_links
    links = re.findall(r'href="([^"]+)"', published.read_text(encoding="utf-8"))
    assert "fdas-revision-comparison.html" in links
    source_prefix = f"https://github.com/{builder.REPO}/blob/main/"
    assert any(link.startswith(source_prefix) for link in links)
    for link in links:
        url = urlsplit(link)
        if link.startswith(source_prefix):
            assert (builder.ROOT / link.removeprefix(source_prefix)).is_file()
        elif not url.scheme and not url.netloc and url.path:
            target = (published.parent / url.path).resolve()
            assert target.is_relative_to(builder.PUBLIC.resolve())
            assert target.is_file()
    assert log.read_bytes() == original


def test_revision_comparison_refuses_missing_assumptions_log(
    lifecycle_builder, tmp_path, monkeypatch
):
    builder, lifecycle = lifecycle_builder
    comparison = lifecycle.parent / "fdas_revision_comparison.md"
    comparison.write_bytes(b"# Revision comparison\n")
    monkeypatch.setattr(builder, "ROOT", tmp_path)

    with pytest.raises(FileNotFoundError):
        builder.build_lower_tertiary({})
