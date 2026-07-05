"""Tests for the per-domain static-site builder (scripts/build_pages.py, P2 #528).

These verify the per-domain build isolation contract:
- a full build (no args) renders the whole site;
- ``--domains lower_tertiary`` builds just that domain + the landing index and
  leaves a pre-seeded foreign-domain file untouched (incremental compose);
- ``--clean`` wipes the tree;
- the landing index is always regenerated.

The builder writes to module-level ``PUBLIC``/``ASSETS`` paths under the repo;
we redirect those to a tmp dir so tests never touch the working tree.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_pages.py"


@pytest.fixture
def bp(tmp_path, monkeypatch):
    """Import build_pages with PUBLIC/ASSETS redirected to a tmp dir."""
    spec = importlib.util.spec_from_file_location("build_pages_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    public = tmp_path / "public"
    monkeypatch.setattr(mod, "PUBLIC", public)
    monkeypatch.setattr(mod, "ASSETS", public / "assets")
    return mod


def test_full_build_renders_whole_site(bp):
    bp.build()
    public = bp.PUBLIC
    assert (public / "index.html").exists()
    assert (public / "assets" / "style.css").exists()
    # Lower-Tertiary surface present.
    assert (public / "portfolio.html").exists()
    assert (public / "benchmark.html").exists()
    econ = list(public.glob("economics-*.html"))
    assert econ, "expected per-field economics pages"


def test_partial_build_only_touches_its_domain(bp):
    public = bp.PUBLIC
    # Seed a foreign domain's output as if restored from cache.
    (public / "subsea").mkdir(parents=True)
    seeded = public / "subsea" / "index.html"
    seeded.write_text("<html>seeded subsea</html>", encoding="utf-8")

    bp.build(domains=["lower_tertiary"])

    # Foreign domain output survives the incremental build.
    assert seeded.read_text(encoding="utf-8") == "<html>seeded subsea</html>"
    # Lower-Tertiary + landing index were (re)built.
    assert (public / "index.html").exists()
    assert (public / "portfolio.html").exists()


def test_index_always_regenerated(bp):
    public = bp.PUBLIC
    bp.build(domains=["lower_tertiary"])
    first = (public / "index.html").read_text(encoding="utf-8")
    # Rebuild with no domains: index must still be (re)written over the tree.
    (public / "index.html").unlink()
    bp.build(domains=[])
    assert (public / "index.html").exists()
    assert (public / "index.html").read_text(encoding="utf-8") == first


def test_clean_wipes_tree(bp):
    public = bp.PUBLIC
    (public / "subsea").mkdir(parents=True)
    (public / "subsea" / "index.html").write_text("stale", encoding="utf-8")
    bp.build(clean=True)
    assert not (public / "subsea").exists()
    assert (public / "index.html").exists()


def test_unknown_domain_raises(bp):
    with pytest.raises(SystemExit):
        bp.build(domains=["does_not_exist"])


def test_field_development_domain_publishes_self_contained_surfaces(bp):
    public = bp.PUBLIC
    bp.build(domains=["field_development"])
    fd = public / "field-development"
    # Single self-contained pages copied flat.
    assert (fd / "showcase.html").exists()
    assert (fd / "playbook.html").exists()
    # Multi-page report sets copied as whole trees (index + per-field pages).
    assert (fd / "portfolio" / "index.html").exists()
    assert (fd / "bsee-matched" / "index.html").exists()
    assert len(list((fd / "bsee-matched").glob("*.html"))) > 50
    # The showcase carries real generated schematics (inline SVG).
    assert (fd / "showcase.html").read_text(encoding="utf-8").count("<svg") >= 2
    # JSON sidecars are not published.
    assert not list(fd.rglob("*.json"))


def test_field_development_publishes_spain_cores_without_json_sidecar(
    bp, tmp_path, monkeypatch
):
    reports = tmp_path / "reports"
    src = reports / "field_development"
    src.mkdir(parents=True)
    (src / "spain_cores.html").write_text(
        "<!doctype html><html><body>Spain CORES</body></html>",
        encoding="utf-8",
    )
    (src / "spain_cores.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bp, "REPORTS", reports)

    bp.build(domains=["field_development"])

    fd = bp.PUBLIC / "field-development"
    index = (bp.PUBLIC / "index.html").read_text(encoding="utf-8")
    assert (fd / "spain-cores.html").exists()
    assert not (fd / "spain_cores.json").exists()
    assert 'href="field-development/spain-cores.html"' in index
    assert "Spain CORES" in index
    assert "Field-Development Playbook" in index
    assert "Offshore Field-Development Playbook" not in index


def test_landing_links_the_field_development_showcase(bp):
    bp.build()  # full build
    index = (bp.PUBLIC / "index.html").read_text(encoding="utf-8")
    assert "Offshore Field-Development Playbook" in index
    assert 'href="field-development/showcase.html"' in index
    assert 'href="field-development/playbook.html"' in index


def test_pressure_atlas_domain_publishes_self_contained(bp):
    # Registry consistency: the domain is registered and has its reports dir.
    assert "pressure-atlas" in bp.DOMAINS
    assert (Path(bp.REPORTS) / "pressure-atlas").is_dir()

    bp.build()  # full build renders every registered domain

    published = bp.PUBLIC / "pressure-atlas" / "index.html"
    assert published.exists(), "pressure-atlas domain did not publish index.html"

    # Real, traceable tokens straight from reports/pressure-atlas/_pressure.json:
    # the atlas title, plus either the top onshore field (HUGOTON GAS AREA) or
    # Anchor's disclosed 25,000-psi reservoir pressure. Proves the page shipped
    # self-contained with honest data, not an empty shell.
    text = published.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "pressure atlas" in lowered
    assert "hugoton" in lowered or "25,000" in text


def test_registry_keys_match_reports_dirs(bp):
    # Each registered domain key should correspond to a reports/<domain>/ dir.
    reports = Path(bp.REPORTS)
    for name in bp.DOMAINS:
        assert (
            reports / name
        ).is_dir(), f"DOMAINS key {name!r} has no reports/{name}/ dir"
