"""Suites 1-2 — project_economics member packaging & namespace resolution (#714).

Asserts the carved-out ``worldenergydata-project_economics`` member resolves under the
shared ``worldenergydata`` namespace, that the fiscal decks ship as package
data reachable via ``importlib.resources``, and that the cross-member consumers
(bsee, lower_tertiary) still import after the carve.
"""

from importlib import resources
from pathlib import Path


def test_project_economics_resolves_from_its_own_member():
    import worldenergydata.project_economics as project_economics

    parts = Path(project_economics.__file__).resolve().parts
    assert "worldenergydata-project_economics" in parts
    # and NOT from the old bsee member location
    assert "worldenergydata-bsee" not in parts


def test_namespace_spans_multiple_members():
    """The shared ``worldenergydata`` namespace must resolve subpackages from
    DIFFERENT physical members — the functional proof that its ``__path__``
    spans them. (Asserting on ``__file__`` of resolved submodules, not on the
    ``__path__`` list itself, which is a synthesized import-hook finder under
    PEP 660 editable installs.)"""
    import worldenergydata
    import worldenergydata.common as common
    import worldenergydata.project_economics as project_economics

    assert isinstance(list(worldenergydata.__path__), list) and worldenergydata.__path__
    assert (
        "worldenergydata-project_economics"
        in Path(project_economics.__file__).resolve().parts
    )
    assert "worldenergydata-core" in Path(common.__file__).resolve().parts


def test_fiscal_decks_ship_as_package_data():
    decks = resources.files("worldenergydata.project_economics.fiscal.decks")
    names = {e.name for e in decks.iterdir()}
    assert {"us_gom.yml", "norway.yml", "uk.yml"} <= names, names
    # each is a readable file
    for stem in ("us_gom", "norway", "uk"):
        content = decks.joinpath(f"{stem}.yml").read_text(encoding="utf-8")
        assert "schema_version" in content


def test_project_economics_public_api_surface():
    import worldenergydata.project_economics as project_economics

    for sym in (
        "get_fiscal_terms",
        "FiscalTerms",
        "RoyaltyTerms",
        "available_countries",
        "calculate_npv",
        "AssumptionsManager",
    ):
        assert hasattr(project_economics, sym), sym


def test_cross_member_consumers_still_import():
    """bsee.analysis + lower_tertiary.portfolio_economics import project_economics; they must
    still import after the carve (they now depend on the project_economics member)."""
    import worldenergydata.bsee  # noqa: F401
    from worldenergydata.lower_tertiary import portfolio_economics  # noqa: F401
