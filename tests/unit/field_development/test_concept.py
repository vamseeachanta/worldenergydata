"""Unit tests for the concept/development block builder (issue #759)."""

from __future__ import annotations

from worldenergydata.field_development.concept import build_concept


def _c(**kw):
    base = dict(
        concept_label="FPSO",
        host_type="FPSO (BW Pioneer)",
        play="Wilcox",
        first_oil="Feb 2012",
        fid_year=None,
        fdp_slug="chinook",
        has_fdp=True,
        fdp_issue=962,
    )
    base.update(kw)
    return build_concept(**base)


def test_producer_shows_first_oil_and_fdp_link():
    c = _c()
    assert c["milestone"] == {"label": "First oil", "value": "Feb 2012"}
    assert c["fdp_href"] == "../field-development/portfolio/chinook.html"


def test_none_fid_year_with_first_oil_is_fine():
    # cascade_chinook has fid_year=None but first_oil set (#759 review edge case).
    c = _c(fid_year=None, first_oil="Feb 2012")
    assert c["milestone"]["label"] == "First oil"


def test_pre_production_shows_sanction_year():
    c = _c(first_oil=None, fid_year=2024, has_fdp=False, fdp_slug="kaskida")
    assert c["milestone"] == {"label": "Sanctioned", "value": "2024"}
    # No FDP page -> placeholder (fdp_href None, issue carried).
    assert c["fdp_href"] is None and c["fdp_issue"] == 962


def test_no_milestone_when_no_dates():
    c = _c(first_oil=None, fid_year=None)
    assert c["milestone"] is None


def test_type_falls_back_to_host():
    c = _c(concept_label=None, host_type="Spar")
    assert c["type"] == "Spar"
