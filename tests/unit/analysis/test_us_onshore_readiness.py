"""Readiness expectations are enumerated from #911, not computed by the report.

Worked classification: configured TX land endpoint + reported TX regulator
files = configured-only land row and downloaded regulator row. A later error
observation replaces only the regulator status. Neither fact proves title,
freshness, or completeness. This is categorical reasoning, with no coefficients.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from worldenergydata.analysis.us_onshore_readiness import (
    build_matrix,
    load_catalog,
    render_markdown,
)

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "config/us_onshore_readiness.json"


def test_required_downloaded_and_derived_sources():
    """#909 evidence snapshot reports these directories; #911 requires all five."""
    rows = {row["source_id"]: row for row in build_matrix(load_catalog(CATALOG))}
    for source in ("texas_rrc", "kansas_kgs", "oklahoma_occ", "colorado_ecmc"):
        assert rows[source]["status"] == "downloaded"
        assert rows[source]["evidence_scope"] == "reported inventory"
    assert rows["pressure_screen"]["status"] == "derived"
    assert all(row["qualification"] == "NOT_EVALUATED" for row in rows.values())
    assert all(row["freshness"] == "unknown" for row in rows.values())
    assert all(row["completeness"] == "unknown" for row in rows.values())


def test_all_configured_state_endpoints_and_county_references_are_separate():
    """Expected states come independently from config/landman.yml, state_endpoints."""
    config = yaml.safe_load((ROOT / "config/landman.yml").read_text())
    rows = build_matrix(load_catalog(CATALOG))
    land = {
        row["state"]: row for row in rows if row["source_id"].startswith("landman_")
    }
    assert set(land) == set(config["state_endpoints"])
    assert all(row["status"] == "configured-only" for row in land.values())
    by_id = {row["source_id"]: row for row in rows}
    assert by_id["blm_mlrs"]["status"] == "configured-only"
    assert by_id["county_reference"]["status"] == "configured-only"
    assert by_id["county_title"]["status"] == "missing"
    assert by_id["texas_rrc"]["domain"] == "regulator"
    assert land["TX"]["source_id"] != by_id["texas_rrc"]["source_id"]


# Hand classifications of config/landman.yml state_endpoints data_types:
# mineral_leases supports lease/mineral coverage, not mineral ownership;
# lease_info supports a lease reference, not a qualified title instrument.
# Spacing units, spacing orders and coastal permits retain distinct meanings.
@pytest.mark.parametrize(
    "state,domain,coverage",
    [
        (
            "TX",
            "land/lease/mineral + regulator",
            {"abstract_info", "survey_plats", "lease", "mineral", "permits"},
        ),
        ("NM", "land/lease + regulator", {"township_range", "lease", "wells"}),
        ("OK", "regulator + lease reference", {"permits", "production", "lease"}),
        ("ND", "regulator", {"wells", "production", "spacing_units"}),
        ("CO", "regulator", {"permits", "production", "spacing_orders"}),
        ("WY", "regulator", {"wells", "production", "permits"}),
        (
            "LA",
            "regulator + lease reference",
            {"wells", "production", "lease", "coastal_permits"},
        ),
        ("UT", "regulator", {"wells", "production", "permits"}),
    ],
)
def test_state_endpoint_domains_and_coverage_follow_cited_types(
    state, domain, coverage
):
    rows = {row["source_id"]: row for row in build_matrix(load_catalog(CATALOG))}
    row = rows[f"landman_{state}"]
    assert row["domain"] == domain
    assert set(row["coverage"]) == coverage


@pytest.mark.parametrize(
    "state,gap",
    [
        ("TX", "Mineral ownership and title instruments"),
        ("NM", "Mineral ownership and title instruments"),
        ("OK", "Mineral ownership and title instruments"),
        ("ND", "Lease records, mineral ownership and title instruments"),
        ("CO", "Lease records, mineral ownership and title instruments"),
        ("WY", "Lease records, mineral ownership and title instruments"),
        ("LA", "Mineral ownership and title instruments"),
        ("UT", "Lease records, mineral ownership and title instruments"),
    ],
)
def test_state_endpoint_land_gaps_require_discovery(state, gap):
    rows = {row["source_id"]: row for row in build_matrix(load_catalog(CATALOG))}
    row = rows[f"landman_{state}"]
    assert row["discovery_required"] is True
    assert f"{gap} are not configured here and need discovery." in row["limitations"]
    assert row["status"] == "configured-only"
    assert row["qualification"] == "NOT_EVALUATED"


def test_arkansas_gaps_topics_priorities_and_existing_issues():
    """#911 acceptance checklist provides gaps and links; no implied acquisition."""
    rows = build_matrix(load_catalog(CATALOG))
    by_id = {row["source_id"]: row for row in rows}
    assert by_id["arkansas_regulator"]["status"] == "missing"
    assert by_id["arkansas_regulator"]["discovery_required"] is True
    assert by_id["eia_us"]["status"] == "partial/error"
    assert by_id["mineral_title"]["qualification"] == "NOT_EVALUATED"
    assert {"#708", "#266", "#680", "#681", "#462"} <= {
        issue for row in rows for issue in row["issues"]
    }
    assert {
        "wells",
        "production",
        "permits",
        "pressure",
        "infrastructure",
        "HSE",
        "lease",
        "mineral",
        "title",
    } <= {tag for row in rows for tag in row["coverage"]}
    first = {row["source_id"] for row in rows if row["priority"] == "first"}
    assert {"arkansas_regulator", "blm_mlrs", "county_title", "eia_us"} <= first
    assert all(row["reason"] and row["limitations"] and row["evidence"] for row in rows)


def observation(source="texas_rrc", status="partial/error"):
    return {
        "source_id": source,
        "status": status,
        "evidence": "inventory:public-batch",
        "observed_at": "2026-10-20T00:00:00Z",
        "limitations": "Incomplete batch",
    }


def test_inventory_updates_one_source_without_upgrading_readiness():
    """Hand result: TX regulator becomes error; TX land endpoint stays configured."""
    catalog = load_catalog(CATALOG)
    original = copy.deepcopy(catalog)
    rows = {row["source_id"]: row for row in build_matrix(catalog, [observation()])}
    assert rows["texas_rrc"]["status"] == "partial/error"
    assert rows["texas_rrc"]["evidence_scope"] == "supplied inventory"
    assert rows["landman_TX"]["status"] == "configured-only"
    assert rows["texas_rrc"]["qualification"] == "NOT_EVALUATED"
    assert catalog == original


@pytest.mark.parametrize(
    "status",
    [
        "downloaded",
        "derived",
        "configured-only",
        "partial/error",
        "missing",
        "private/legacy",
    ],
)
def test_observation_status_vocabulary(status):
    rows = build_matrix(load_catalog(CATALOG), [observation(status=status)])
    row = next(row for row in rows if row["source_id"] == "texas_rrc")
    assert row["status"] == status
    assert row["qualification"] == "NOT_EVALUATED"
    if status == "private/legacy":
        assert row["public_ingest"] == "quarantined"


@pytest.mark.parametrize(
    "change",
    [
        {"source_id": "unknown"},
        {"status": "ready"},
        {"evidence": " "},
        {"observed_at": "yesterday"},
        {"observed_at": "2026-10-20T00:00:00"},
        {"limitations": ""},
        {"freshness": "fresh"},
        {"status": []},
        {"source_id": []},
        {"observed_at": None},
    ],
)
def test_rejects_unsupported_or_unevidenced_observations(change):
    with pytest.raises(ValueError):
        build_matrix(load_catalog(CATALOG), [observation() | change])


def test_rejects_duplicate_observations():
    with pytest.raises(ValueError, match="duplicate"):
        build_matrix(load_catalog(CATALOG), [observation(), observation()])


def test_catalog_rejects_duplicate_ids_and_invalid_status(tmp_path):
    catalog = load_catalog(CATALOG)
    for rows in ([catalog[0], catalog[0]], [catalog[0] | {"status": "ready"}]):
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps({"sources": rows}))
        with pytest.raises(ValueError):
            load_catalog(path)


def test_markdown_includes_evidence_and_escapes_cells():
    rows = build_matrix(load_catalog(CATALOG), [observation() | {"evidence": "a|b\nc"}])
    text = render_markdown(rows)
    assert "a\\|b c" in text
    assert "NOT_EVALUATED" in text
    assert "reported inventory" in text
    assert "County recorder/title" in text


def test_cli_json_and_markdown_with_worked_inventory(tmp_path):
    """The example's independent answer is TX partial/error, land configured-only."""
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps({"observations": [observation()]}))
    command = [
        sys.executable,
        "-m",
        "worldenergydata.analysis.us_onshore_readiness",
        "--catalog",
        str(CATALOG),
        "--inventory",
        str(path),
    ]
    result = subprocess.run(
        command + ["--format", "json"], check=True, capture_output=True, text=True
    )
    rows = {row["source_id"]: row for row in json.loads(result.stdout)}
    assert rows["texas_rrc"]["status"] == "partial/error"
    assert rows["landman_TX"]["status"] == "configured-only"
    markdown = subprocess.run(command, check=True, capture_output=True, text=True)
    assert "partial/error" in markdown.stdout


def test_cli_rejects_unknown_sources(tmp_path):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps({"observations": [observation(source="unknown")]}))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.analysis.us_onshore_readiness",
            "--catalog",
            str(CATALOG),
            "--inventory",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unknown source" in result.stderr


@pytest.mark.parametrize("payload", [{}, {"sources": []}, {"sources": "wrong"}, []])
def test_catalog_rejects_invalid_structure(tmp_path, payload):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_catalog(path)


def test_duplicate_json_keys_are_rejected(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"sources": [], "sources": []}')
    with pytest.raises(ValueError, match="duplicate JSON"):
        load_catalog(path)


def test_worked_example_is_executable():
    payload = json.loads(
        (ROOT / "docs/data-sources/onshore/readiness-example.json").read_text()
    )
    rows = {
        row["source_id"]: row
        for row in build_matrix(load_catalog(CATALOG), payload["observations"])
    }
    assert rows["texas_rrc"]["status"] == "partial/error"
    assert rows["landman_TX"]["status"] == "configured-only"
    assert rows["county_title"]["status"] == "missing"
    assert rows["texas_rrc"]["prior_evidence"]["status"] == "downloaded"


def test_committed_matrix_matches_catalog():
    expected = render_markdown(build_matrix(load_catalog(CATALOG)))
    path = ROOT / "docs/data-sources/onshore/source-readiness-matrix.md"
    assert path.read_text() == expected
