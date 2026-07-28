"""Pins for the owner-anchor validation page (roy-rig-days-validation.html).

The page exists to state honestly how much of the domain owner's own reference
material the WAR activity-code rig-day basis reproduces.  Two failure modes
would quietly destroy that:

* a computed subtotal drifting without anyone noticing, and
* the page's *coverage* claim inflating -- presenting computed-only wellbores
  as validated, or counting a derived figure as an independent owner anchor.

These pins lock both.  They read the committed cache
(``reports/lower_tertiary/data/roy_rig_days_qa.csv``), so they never need the
370 MB raw WAR tables.
"""

import importlib.util
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "lower_tertiary" / "build_roy_rig_days_qa.py"
PAGE = REPO / "reports" / "lower_tertiary" / "roy-rig-days-validation.html"
CACHE = REPO / "reports" / "lower_tertiary" / "data" / "roy_rig_days_qa.csv"

ANCHOR_API12 = "608124009500"

# The owner's hand-worked figures for 608124009500 and what this basis returns.
# Frozen so an unannounced change to either side fails loudly.
ANCHOR_PINS = {
    "drl_milestone_excl": ("155", "151"),
    "compl_remarks": ("93", "94"),
    "dc_total": ("248", "245"),
    "war_drl": ("151", "151"),
    "war_pnd": ("49", "49"),
    "war_com": ("87", "91"),
    "war_ta": ("21", "17"),
    "war_total": ("308", "308"),
}

# Stones, 22 bores, DRL_COM basis: drilling, completion, PND, TA.
STONES_TOTALS = {"drilling": 1105, "completion": 574, "pnd": 366, "ta": 183}


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("build_roy_rig_days_qa", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rows(mod):
    return mod.load_cache()


@pytest.fixture(scope="module")
def bores(rows):
    return [r for r in rows if r["grain"] == "bore"]


@pytest.fixture(scope="module")
def anchors(mod, bores):
    return mod.resolve_anchors({b["api12"]: b for b in bores}, mod.anchor_facts())


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Population and subtotals
# ---------------------------------------------------------------------------
def test_population_is_the_owners_stones_list(mod, bores):
    population = {w["api12"] for w in mod.load_population()}
    assert len(population) == 22
    assert {b["api12"] for b in bores} == population


def test_stones_subtotals_pinned(bores):
    covered = [b for b in bores if b["days_status"] == "war_covered"]
    got = {
        "drilling": sum(int(b["drilling_days"]) for b in covered),
        "completion": sum(int(b["completion_days"]) for b in covered),
        "pnd": sum(int(b["pnd_days"]) for b in covered),
        "ta": sum(int(b["ta_days"]) for b in covered),
    }
    assert got == STONES_TOTALS


def test_uncovered_bores_report_null_never_zero(bores):
    for bore in bores:
        if bore["days_status"] != "war_covered":
            assert bore["drilling_days"] == ""
            assert bore["completion_days"] == ""


def test_well_grain_unions_rather_than_sums(rows):
    """Every sidetracked well must show the double-count the union avoids."""
    wells = [r for r in rows if r["grain"] == "well"]
    assert len(wells) == 18
    multi = [w for w in wells if int(w["overlap_days"]) > 0]
    assert len(multi) == 3
    for well in multi:
        # One WAR week is attributed to both bores at the sidetrack boundary,
        # so the per-bore sum over-reports the well by exactly that week.
        assert int(well["overlap_days"]) == 7
        summed = int(well["drilling_days_additive"]) + int(
            well["completion_days_additive"]
        )
        union = int(well["drilling_days"]) + int(well["completion_days"])
        assert union <= summed


# ---------------------------------------------------------------------------
# Anchor ledger
# ---------------------------------------------------------------------------
def test_anchor_values_pinned(anchors):
    by_id = {a["id"]: a for a in anchors}
    for anchor_id, (roy, ours) in ANCHOR_PINS.items():
        assert by_id[anchor_id]["roy"] == roy, anchor_id
        assert by_id[anchor_id]["ours"] == ours, anchor_id


def test_the_155_156_pair_is_one_figure_stated_two_ways(anchors):
    by_id = {a["id"]: a for a in anchors}
    exclusive = int(by_id["drl_milestone_excl"]["roy"])
    inclusive = int(by_id["drl_milestone_incl"]["roy"])
    assert inclusive - exclusive == 1
    # ...and only one of them is filed as owner evidence.
    assert by_id["drl_milestone_excl"]["tier"] == "owner_handworked"
    assert by_id["drl_milestone_incl"]["tier"] == "repo_legacy"


def test_com_ta_disagreement_is_a_pure_reallocation(anchors):
    """4 days move TA -> COM; the totals must still tie exactly."""
    by_id = {a["id"]: a for a in anchors}
    roy = int(by_id["war_com"]["roy"]) + int(by_id["war_ta"]["roy"])
    ours = int(by_id["war_com"]["ours"]) + int(by_id["war_ta"]["ours"])
    assert roy == ours == 108
    assert int(by_id["war_com"]["delta"]) == -int(by_id["war_ta"]["delta"]) == 4
    assert by_id["war_total"]["verdict"] == "exact"


def test_unreachable_anchor_is_reported_not_guessed(anchors):
    by_id = {a["id"]: a for a in anchors}
    assert by_id["bhp"]["ours"] is None
    assert by_id["bhp"]["verdict"] == "not checkable"


def test_agreement_verdicts_use_the_war_quantum(mod):
    assert mod._verdict("100", "100") == ("0", "exact")
    assert mod._verdict("100", "107")[1] == "within one WAR week"
    assert mod._verdict("100", "108")[1] == "materially different"
    assert mod._verdict("100", None)[1] == "not checkable"
    # Physical measurements do not get the seven-day grace.
    assert mod._verdict("28307", "28306", "value")[1] == "within rounding"
    assert mod._verdict("28307", "28000", "value")[1] == "materially different"


# ---------------------------------------------------------------------------
# The honesty guarantees
# ---------------------------------------------------------------------------
def test_exactly_one_bore_carries_an_owner_figure(anchors, page):
    """The coverage claim is the whole point of the page — it must not inflate."""
    hand = [a for a in anchors if a["tier"] == "owner_handworked"]
    assert hand, "no hand-worked anchors resolved"
    assert {a["subject"] for a in hand} == {f"{ANCHOR_API12} · Stones SN105"}
    assert page.count("hand-worked</span>") == 1
    assert page.count('<span class="d"></span>none</span>') == 21


def test_page_states_the_negative_verdict(page):
    assert "No. This is not a more established QA." in page
    assert "the independent\n  evidence base is still one wellbore" in page
    assert "they are not validated" in page
    assert "circular" in page


def test_page_carries_the_standing_caveats(page):
    for phrase in (
        "30 CFR 250.743",
        "Coverage floor of the WAR feed",
        "PND means we guessed it as\n    unknown",
        "3-day partial",
    ):
        assert phrase in page, phrase


def test_page_is_self_contained(page):
    assert page.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in page
    for forbidden in ("<link", "<script", "<img", "@import", "fonts.googleapis"):
        assert forbidden not in page, forbidden


def test_external_links_are_github_only(page):
    for url in re.findall(r'href="(https?://[^"]+)"', page):
        assert url.startswith("https://github.com/vamseeachanta/worldenergydata"), url


def test_relative_links_point_at_published_pages(page):
    rel = {
        u for u in re.findall(r'href="([^"#][^":]*)"', page) if not u.startswith("http")
    }
    assert rel == {
        "index.html",
        "wo-april-2026-qaqc-hub.html",
        "wo-april-2026-validation.html",
        "wo-april-2026-per-well-dc.html",
        "dc-drilldown.html",
    }


def test_page_is_regenerable_and_deterministic(mod, rows, page):
    assert mod.build(rows) == page


def test_cache_is_committed_and_complete(mod, rows):
    assert CACHE.exists()
    meta = [r for r in rows if r["grain"] == "meta"]
    assert len(meta) == 1
    assert meta[0]["war_first_material_month"] == "1997-10"
    assert int(meta[0]["war_returns_before_1998"]) == 867
