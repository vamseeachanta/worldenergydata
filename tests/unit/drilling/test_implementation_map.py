"""Evidence checks for the six package-local calculation/grouping families."""

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

from worldenergydata.drilling import BatchDrillingEconomics

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path("packages/worldenergydata-drilling/src/worldenergydata/drilling")
MAP = ROOT / PACKAGE / "docs/implementation-map.json"


def test_all_six_family_enrollments():
    """Verify actual definition locations, digests, evidence and review status."""
    inventory = json.loads(MAP.read_text())
    assert inventory["repository"] == "worldenergydata"
    assert re.fullmatch(r"[0-9a-f]{40}", inventory["revision"])
    assert {family["id"] for family in inventory["families"]} == {
        "duration",
        "mobilization-allocation",
        "break-even-comparison",
        "campaign-cost",
        "anchored-time-window-grouping",
        "log-space-learning-fit",
    }
    for family in inventory["families"]:
        assert family["counted"] is False
        assert family["status"] == "pending_review"
        assert family["qualification"] == "NOT_EVALUATED"
        assert family["equation"] and family["source"] and family["limits"]
        for entry in family["implementations"]:
            current = (ROOT / entry["path"]).read_bytes()
            assert hashlib.sha256(current).hexdigest() == entry["file_sha256"]
            tree = ast.parse(current)
            cls_name, method_name = entry["symbol"].split(".")
            cls = next(
                n
                for n in tree.body
                if isinstance(n, ast.ClassDef) and n.name == cls_name
            )
            method = next(
                n
                for n in cls.body
                if isinstance(n, ast.FunctionDef) and n.name == method_name
            )
            assert (entry["line"], entry["end_line"]) == (
                method.lineno,
                method.end_lineno,
            )
        for evidence in family["tests"]:
            path, *nodes = evidence.split("::")
            definitions = ast.parse((ROOT / path).read_text()).body
            for node in nodes:
                definition = next(
                    n
                    for n in definitions
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == node
                )
                if isinstance(definition, ast.ClassDef):
                    definitions = definition.body
    allocation = next(
        f for f in inventory["families"] if f["id"] == "mobilization-allocation"
    )
    assert (
        allocation["equation"] == "allocated_cost_usd_per_well = mob_cost_usd / n_wells"
    )
    assert allocation["source"]["section"] == "2.2, Average fixed cost"


def test_family_discovery_evidence():
    """Retained search matches identify definitions and explicit API delegates.

    This checks retained evidence in shallow checkouts as well. The recorded
    git-grep query can be replayed against the full revision; same-name search
    is bounded evidence and cannot prove algorithmic uniqueness.
    """
    inventory = json.loads(MAP.read_text())
    for family in inventory["families"]:
        discovery = family["duplicate_discovery"]
        assert discovery["revision"] == inventory["revision"]
        assert discovery["results"] and discovery["conclusion"]
        assert {(item["path"], item["line"]) for item in discovery["results"]} == {
            (entry["path"], entry["line"]) for entry in family["implementations"]
        }
        for item in discovery["results"]:
            content = (ROOT / item["path"]).read_bytes()
            assert hashlib.sha256(content).hexdigest() == item["file_sha256"]
            line = content.decode().splitlines()[item["line"] - 1]
            assert re.search(discovery["pattern"], line)
            assert item["classification"] in {"implementation", "api_delegate"}


@pytest.mark.parametrize(
    "cost,wells,expected", [(1200, 1, 1200), (1200, 3, 400), (0, 3, 0)]
)
def test_mobilization_hand_calculation(cost, wells, expected):
    """OpenStax, Principles of Accounting Vol. 2 (2019), section 2.2, AFC.

    Equal fixed-cost allocation: total fixed cost divided by unit count.
    Synthetic inputs in USD and wells: 1200/1 = 1200; 1200/3 = 400;
    0/3 = 0 USD/well. These are arithmetic examples, not field calibration.
    All quotients are exactly representable, so equality needs no tolerance.
    """
    assert BatchDrillingEconomics().mobilization_savings(cost, wells) == expected


@pytest.mark.parametrize("wells", [0, -1])
def test_mobilization_nonpositive_count(wells):
    """economics.py, mobilization_savings guard at the enrolled pin rejects N<=0.

    Zero and minus one exercise the boundary and a representative invalid count;
    1200 USD is the synthetic fixed cost from the hand calculation above.
    """
    with pytest.raises(ValueError, match="n_wells_batch must be > 0"):
        BatchDrillingEconomics().mobilization_savings(1200, wells)


def test_duration_and_campaign_cost_hand_calculations():
    """Synthetic arithmetic, economics.py Duration and Campaign total sections.

    T(N)=8*N**(-1) when LC=1/2; thus T(1)=8, T(2)=4, T(4)=2 days.
    With two wells, 30 USD mobilization and 2 USD/day, cost=30+2*(8+4)=54 USD.
    This tests the recorded formula, not individual/cumulative duration validity.
    """
    from worldenergydata.drilling import DrillCampaign, DrillingSite

    calc = BatchDrillingEconomics()
    for position, expected in [(1, 8), (2, 4), (4, 2)]:
        assert calc.learning_curve_time(8, position, 0.5) == pytest.approx(expected)
    well = DrillingSite(
        well_id="",
        field_name="",
        location_coords=(0, 0),
        water_depth_ft=0,
        planned_md_ft=0,
        well_type="",
    )
    campaign = DrillCampaign(
        campaign_id="",
        rig_name="",
        wells=[well, well],
        rig_day_rate_usd=2,
        mobilization_cost_usd=30,
        learning_curve_factor=0.5,
    )
    assert calc.campaign_total_cost(campaign, 8) == pytest.approx(54)
    # No learning: 30+2*(8+8)=62 USD, independently summing both durations.
    campaign.learning_curve_factor = 1
    assert calc.campaign_total_cost(campaign, 8) == 62
