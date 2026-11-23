"""Offline acceptance criteria for the provisional international evidence view."""

import json
import re
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/data-sources"
COUNTRIES = {
    "Norway",
    "UK",
    "Brazil",
    "Canada",
    "Mexico",
    "Australia",
    "Spain",
    "West Africa/Nigeria",
    "Netherlands",
    "Denmark",
    "India",
    "Argentina",
    "Colombia",
    "New Zealand",
}
DIMENSIONS = (
    "source",
    "raw",
    "production",
    "wells",
    "scheduler",
    "chain",
    "report",
    "blocker",
)
ISSUES = "https://api.github.com/repositories/574746314/issues/"


@pytest.fixture
def matrix():
    return json.loads(
        (DOCS / "country-materialization.json").read_text(encoding="utf-8")
    )


def test_coverage_and_evidence(matrix):
    assert set(matrix["countries"]) == COUNTRIES
    assert re.fullmatch(r"[0-9a-f]{40}", matrix["base_revision"])
    date.fromisoformat(matrix["as_of"])
    assert set(matrix["legend"]) == {
        "code_present",
        "configured",
        "historical_report",
        "verified_snapshot",
        "NOT_EVALUATED",
    }
    for row in matrix["countries"].values():
        assert set(row) == {*DIMENSIONS, "issues"}
        for dim in DIMENSIONS:
            cell = row[dim]
            assert cell["basis"].strip() and cell["status"] in matrix["legend"]
            if cell["status"] == "NOT_EVALUATED":
                assert cell["evidence"] is None
            elif cell["evidence"].startswith(ISSUES):
                assert cell["evidence"].removeprefix(ISSUES).isdigit()
            else:
                path = (DOCS / cell["evidence"]).resolve()
                assert path.is_relative_to(ROOT) and path.is_file()
            if cell["status"] == "verified_snapshot":
                snapshot = cell["inventory"]
                date.fromisoformat(snapshot["observed_at"])
                assert snapshot["scope"].strip()
                assert re.fullmatch(r"[0-9a-f]{64}", snapshot["sha256"])


def test_configuration_cannot_promote_current_holdings(matrix):
    jobs = {
        "Norway": "sodir_refresh",
        "UK": "ukcs_refresh",
        "Brazil": "brazil_anp_refresh",
        "Spain": "spain_cores_refresh",
    }
    for country, row in matrix["countries"].items():
        assert row["raw"]["status"] == "NOT_EVALUATED"
        job = row["scheduler"]
        if country in jobs:
            assert job["status"] == "configured"
            assert jobs[country] in job["basis"]
            assert f"- name: {jobs[country]}\n" in (DOCS / job["evidence"]).read_text()
        else:
            assert job["status"] == "NOT_EVALUATED"


def test_spain_preserves_history_and_density_limit(matrix):
    row = matrix["countries"]["Spain"]
    raw = row["raw"]
    assert raw["location"] == "data/spain/cores"
    assert raw["history"]["status"] == "historical_report"
    assert raw["history"]["evidence"] == ISSUES + "918"
    assert raw["history"]["basis"].strip()
    assert raw["evidence"] is None
    assert "density" in row["blocker"]["basis"].lower()
    assert "rights" in row["blocker"]["basis"].lower()


def test_chain_scope_and_reconciliation(matrix):
    rows = matrix["countries"]
    for country in ("Norway", "UK", "Brazil", "Canada", "Australia", "Spain"):
        assert rows[country]["chain"]["status"] == "code_present"
        assert rows[country]["chain"]["evidence"].endswith("/reference_chain.py")
    assert "fixture" in rows["Norway"]["report"]["basis"].lower()
    assert "screening" in rows["Australia"]["chain"]["basis"].lower()
    assert "water" in rows["Mexico"]["chain"]["basis"].lower()
    assert "#459" in rows["Brazil"]["blocker"]["basis"]
    assert {
        713,
        716,
        717,
        718,
        719,
        720,
        721,
        722,
        753,
        763,
        806,
        807,
        809,
        810,
        831,
        917,
        919,
    } <= {n for row in rows.values() for n in row["issues"]}
    assert matrix["reconciliation"].endswith("/pulls/1566")


def test_html_matches_each_country_dimension_and_reference(matrix):
    page = ElementTree.parse(DOCS / "country-materialization.html")
    table = page.find(".//table[@id='coverage']")
    assert [
        th.attrib["data-dimension"] for th in table.findall("thead/tr/th")[1:]
    ] == list(DIMENSIONS)
    rows = table.findall("tbody/tr")
    assert [tr.findtext("th/a") for tr in rows] == list(matrix["countries"])
    for tr in rows:
        row = matrix["countries"][tr.findtext("th/a")]
        assert [a.get("href") for a in tr.findall("th/small/a")] == [
            ISSUES + str(n) for n in row["issues"]
        ]
        cells = tr.findall("td")
        assert len(cells) == len(DIMENSIONS)
        for dim, td in zip(DIMENSIONS, cells):
            fact = row[dim]
            facts = [fact, fact["history"]] if "history" in fact else [fact]
            blocks = td.findall("div")
            assert len(blocks) == len(facts)
            for block, expected in zip(blocks, facts):
                assert block.findtext("b") == expected["status"]
                assert block.findtext("span") == expected["basis"]
                assert [a.get("href") for a in block.findall("a")] == (
                    [expected["evidence"]] if expected["evidence"] else []
                )
            assert td.findtext("code") == fact.get("location")
    text = " ".join(page.getroot().itertext())
    for value in [
        matrix["as_of"],
        matrix["base_revision"],
        "Provisional",
        *matrix["legend"].values(),
    ]:
        assert value in text
    assert page.find(f".//a[@href='{matrix['reconciliation']}']") is not None
    assert page.find(".//script") is None


def test_brazil_discrepancy_and_spain_inventory_sources(matrix):
    brazil = matrix["countries"]["Brazil"]
    assert {459, 917} <= set(brazil["issues"])
    contract = json.loads(
        (DOCS / brazil["blocker"]["evidence"]).read_text(encoding="utf-8")
    )
    record = next(s for s in contract["sources"] if s["module_id"] == "brazil_anp")
    assert record["blocker_issue"] == "#459"
    assert record["freshness_status"] == "blocked"
    assert matrix["issue_base"] == ISSUES
    assert 909 in matrix["countries"]["Spain"]["issues"]
    page = ElementTree.parse(DOCS / "country-materialization.html")
    assert matrix["reconciliation_note"] in " ".join(page.getroot().itertext())
