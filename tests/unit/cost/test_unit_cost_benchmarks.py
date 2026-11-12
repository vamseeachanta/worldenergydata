"""Invented projects only: fixed arithmetic fixtures, never engineering inputs."""

import csv
import os
import subprocess
import sys
from copy import deepcopy

import pytest

COLUMNS = (
    "metric",
    "unit",
    "water_depth_band",
    "region",
    "development_type",
    "host_type",
    "n",
    "p10",
    "p50",
    "p90",
    "indicative_only",
    "comparables",
    "cost_basis",
)


@pytest.fixture
def projects():
    """Five invented projects with hand-checkable per-well costs 10,20,30,40,100."""
    return [
        {
            "PROJECT_ID": f"invented-{i}",
            "PROJECT": f"Invented project {i}",
            "OPERATOR": "Invented operator",
            "REGION": "Invented region",
            "COUNTRY": "Invented country",
            "WATER_DEPTH_M": "1200",
            "FID_YEAR": "2020",
            "FIRST_OIL_YEAR": "2024",
            "SANCTIONED_CAPEX_USD_MM": str(cost * 5),
            "CAPEX_USD_MM_2026": str(cost * 10),
            "INDEX_USED": "Invented test index",
            "INDEX_BASE_YEAR": "2020",
            "ESCALATION_FACTOR": "2",
            "ACTUAL_COST_USD_MM": "",
            "CAPEX_BASIS": "gross project cost at FID",
            "WELL_COUNT": "10",
            "DEVELOPMENT_TYPE": "subsea",
            "HOST_TYPE": "FPSO",
            "SURF_KM": "20",
            "PEAK_PRODUCTION_BOEPD": "50000",
            "RECOVERABLE_RESOURCE_MMBOE": "100",
            "USD_PER_BOE": "",
            "SOURCE_TITLE": "Invented disclosure for arithmetic tests",
            "SOURCE_URL": f"https://example.org/invented/{i}",
            "PAGE_REFERENCE": "Invented table",
            "QUOTED_TEXT": "Invented test data",
            "ACCESSED_DATE": "2026-01-01",
            "CONFIDENCE": "high",
            "SOURCE_PRIORITY": "press_release",
            "NOTES": "Invented",
            "SCOPE_IS_OFFSHORE_ONLY": "True",
            "CATALOG_FIELD_IDS": f"invented-field-{i}",
            "MATCH_METHOD": "invented exact match",
            "MATCH_CONFIDENCE": "high",
            "MATCH_EVIDENCE": "Invented crosswalk evidence",
            "TREE_QUANTITY": "5",
            "TREE_SOURCE_URL": "https://example.org/trees",
            "TREE_SOURCE_LOCATOR": "Invented disclosed tree count",
        }
        for i, cost in enumerate((10, 20, 30, 40, 100), 1)
    ]


def build(projects):
    from worldenergydata.cost.benchmarks import build_benchmarks

    return build_benchmarks(projects)


def well_row(facts):
    return next(r for r in facts["rows"] if r["metric"] == "capex_per_well")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def inputs(tmp_path, projects):
    root = tmp_path / "curated"
    root.mkdir()
    extra = {
        "PROJECT_ID",
        "CATALOG_FIELD_IDS",
        "MATCH_METHOD",
        "MATCH_CONFIDENCE",
        "MATCH_EVIDENCE",
        "TREE_QUANTITY",
        "TREE_SOURCE_URL",
        "TREE_SOURCE_LOCATOR",
    }
    write_csv(
        root / "sanctioned_projects.csv",
        [{k: v for k, v in p.items() if k not in extra} for p in projects],
    )
    write_csv(
        root / "cost_project_identity.csv",
        [
            {
                "OPAQUE_ID": p["PROJECT_ID"],
                "ENTITY_KIND": "project",
                "ACTIVE": "true",
                "SOURCE_TABLE": "sanctioned_projects.csv",
                "SOURCE_RECORD_LOCATOR": f"PROJECT={p['PROJECT']}",
            }
            for p in projects
        ],
    )
    write_csv(
        root / "project_field_crosswalk.csv",
        [
            {
                "PROJECT_ID": p["PROJECT_ID"],
                "CATALOG_FIELD_IDS": p["CATALOG_FIELD_IDS"],
                "MATCH_METHOD": p["MATCH_METHOD"],
                "CONFIDENCE": p["MATCH_CONFIDENCE"],
                "EVIDENCE": p["MATCH_EVIDENCE"],
            }
            for p in projects
        ],
    )
    write_csv(
        root / "project_asset_requirements.csv",
        [
            {
                "REQUIREMENT_ID": f"invented-req-{i}",
                "PROJECT_ID": p["PROJECT_ID"],
                "ASSET_TYPE": "subsea tree",
                "QUANTITY": p["TREE_QUANTITY"],
                "QUANTITY_UNIT": "tree",
                "EVIDENCE_DERIVATION": "disclosed",
                "SOURCE_URL": p["TREE_SOURCE_URL"],
                "SOURCE_LOCATOR": p["TREE_SOURCE_LOCATOR"],
            }
            for i, p in enumerate(projects)
        ],
    )
    return root


def cli(root, output):
    env = os.environ.copy()
    # No Git subprocesses are used; the CLI only reads the supplied CSV files.
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.cost.benchmarks",
            "benchmarks",
            "--data-dir",
            str(root),
            "--output-dir",
            str(output),
            "--report-date",
            "2026-01-01",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_percentiles_count_and_no_input_mutation(projects):
    before = deepcopy(projects)
    row = well_row(build(projects))
    assert (row["n"], row["p10"], row["p50"], row["p90"]) == (5, 14, 30, 76)
    assert row["indicative_only"] is False
    assert row["comparables"] == ";".join(f"invented-{i}" for i in range(1, 6))
    assert row["cost_basis"] == "USD_2026"
    assert projects == before


@pytest.mark.parametrize(
    "values,want", [([10], (10, 10, 10)), ([10, 30], (12, 20, 28))]
)
def test_shared_percentile_summary_handles_small_samples(values, want):
    from worldenergydata.cost.reporting.benchmark_report import percentile_summary

    assert percentile_summary(values) == pytest.approx(want)


@pytest.mark.parametrize(
    "field", ["REGION", "DEVELOPMENT_TYPE", "HOST_TYPE", "WATER_DEPTH_M"]
)
def test_unknown_group_keys_are_not_inferred(projects, field):
    projects[-1][field] = ""
    rows = [r for r in build(projects)["rows"] if r["metric"] == "capex_per_well"]
    assert sorted(r["n"] for r in rows) == [1, 4]
    column = "water_depth_band" if field == "WATER_DEPTH_M" else field.lower()
    assert (
        next(r for r in rows if r[column] == "unknown")["comparables"] == "invented-5"
    )
    assert all(r["indicative_only"] for r in rows)


@pytest.mark.parametrize(
    "depth,band",
    [
        (0, "shallow"),
        (300, "shallow"),
        (301, "mid"),
        (1000, "mid"),
        (1001, "deep"),
        (2000, "deep"),
        (2001, "ultra_deep"),
    ],
)
def test_depth_band_boundaries(projects, depth, band):
    projects[0]["WATER_DEPTH_M"] = str(depth)
    assert well_row(build(projects[:1]))["water_depth_band"] == band


def test_all_metric_denominators_and_unit_conversions(projects):
    rows = {r["metric"]: r for r in build(projects[:1])["rows"]}
    expected = {
        "capex_per_well": (10, "USD_MM_2026/well"),
        "capex_per_tree": (20, "USD_MM_2026/tree"),
        "capex_per_surf_km": (5, "USD_MM_2026/km"),
        "capex_per_kboed": (2, "USD_MM_2026/kboe/d"),
        "capex_per_boe": (1, "USD_2026/boe"),
    }
    assert set(rows) == set(expected)
    for metric, (value, unit) in expected.items():
        assert (rows[metric]["p50"], rows[metric]["unit"]) == (value, unit)


@pytest.mark.parametrize("value", ["", "0", "-1", "nan", "inf"])
def test_missing_or_invalid_quantity_excludes_only_its_metric(projects, value):
    projects[-1]["WELL_COUNT"] = value
    facts = build(projects)
    assert well_row(facts)["n"] == 4
    assert well_row(facts)["indicative_only"] is True
    assert next(r for r in facts["rows"] if r["metric"] == "capex_per_boe")["n"] == 5
    assert any(
        e["project_id"] == "invented-5"
        and e["metric"] == "capex_per_well"
        and "WELL_COUNT" in e["reason"]
        for e in facts["exclusions"]
    )


@pytest.mark.parametrize(
    "column",
    [
        "CAPEX_USD_MM_2026",
        "INDEX_USED",
        "INDEX_BASE_YEAR",
        "ESCALATION_FACTOR",
        "SOURCE_URL",
        "CATALOG_FIELD_IDS",
    ],
)
def test_missing_cost_or_lineage_never_falls_back(projects, column):
    projects[0][column] = ""
    facts = build(projects[:1])
    assert facts["rows"] == []
    assert any(column in e["reason"] for e in facts["exclusions"])


def test_duplicate_project_cannot_inflate_group_count(projects):
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        build(projects + [projects[0]])


@pytest.mark.parametrize(
    "missing", ["CAPEX_USD_MM_2026", "project_field_crosswalk.csv"]
)
def test_cli_missing_input_stops_before_writing(projects, tmp_path, missing):
    root = inputs(tmp_path, projects)
    if missing.endswith(".csv"):
        (root / missing).unlink()
    else:
        path = root / "sanctioned_projects.csv"
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        write_csv(path, [{k: v for k, v in r.items() if k != missing} for r in rows])
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode != 0
    assert missing in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("asset_type", ["dry tree", "subsea tree"])
def test_tree_quantities_require_unambiguous_disclosed_subsea_rows(
    projects, tmp_path, asset_type
):
    root = inputs(tmp_path, projects[:1])
    path = root / "project_asset_requirements.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["ASSET_TYPE"] = asset_type
    if asset_type == "subsea tree":
        rows.append({**rows[0], "REQUIREMENT_ID": "invented-overlap"})
    write_csv(path, rows)
    from worldenergydata.cost.benchmarks import load_projects

    facts = build(load_projects(root))
    assert not any(r["metric"] == "capex_per_tree" for r in facts["rows"])
    assert any(
        e["metric"] == "capex_per_tree" and e["reason"] for e in facts["exclusions"]
    )


def test_cli_csv_contract_html_lineage_escaping_and_repeatability(projects, tmp_path):
    projects[0]["SOURCE_TITLE"] = '<img src=x onerror="invalid()"> Invented source'
    projects[-1]["WELL_COUNT"] = ""
    root = inputs(tmp_path, projects)
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode == 0, result.stderr
    csv_path = output / "unit_cost_benchmarks.csv"
    with csv_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames) == COLUMNS
        rows = list(reader)
    well = next(r for r in rows if r["metric"] == "capex_per_well")
    assert (well["n"], well["indicative_only"], well["p50"]) == ("4", "true", "25.0")
    html = (output / "unit_cost_benchmarks.html").read_text(encoding="utf-8")
    for text in (
        "linear interpolation",
        "Revision history",
        "USD_2026",
        "SHA-256",
        "WELL_COUNT",
        "PEAK_PRODUCTION_BOEPD",
        "RECOVERABLE_RESOURCE_MMBOE",
        "Invented crosswalk evidence",
        "Invented test index",
        "indicative",
    ):
        assert text in html
    for project in projects:
        assert project["PROJECT_ID"] in html
        assert project["SOURCE_URL"] in html
        assert project["CATALOG_FIELD_IDS"] in html
    assert "<img src=x" not in html
    assert "&lt;img" in html
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert cli(root, output).returncode == 0
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    (root / "project_field_crosswalk.csv").unlink()
    assert cli(root, output).returncode != 0
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize(
    "column,value",
    [
        ("CAPEX_USD_MM_2026", "nan"),
        ("CAPEX_USD_MM_2026", "inf"),
        ("CAPEX_USD_MM_2026", "0"),
        ("CAPEX_USD_MM_2026", "-1"),
        ("ESCALATION_FACTOR", "nan"),
        ("ESCALATION_FACTOR", "0"),
    ],
)
def test_invalid_numerator_or_factor_is_excluded(projects, column, value):
    projects[0][column] = value
    facts = build(projects[:1])
    assert facts["rows"] == []
    assert any(column in e["reason"] for e in facts["exclusions"])


def test_nonfinite_derived_intensity_is_excluded(projects):
    projects[0]["SURF_KM"] = "1e-320"
    facts = build(projects[:1])
    assert not any(r["metric"] == "capex_per_surf_km" for r in facts["rows"])
    assert any(
        e["metric"] == "capex_per_surf_km" and "finite" in e["reason"]
        for e in facts["exclusions"]
    )


def test_empty_percentile_input_is_rejected():
    from worldenergydata.cost.reporting.benchmark_report import percentile_summary

    with pytest.raises(ValueError):
        percentile_summary([])


def test_conflicting_crosswalk_metadata_is_rejected(projects, tmp_path):
    root = inputs(tmp_path, projects[:1])
    path = root / "project_field_crosswalk.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows.append({**rows[0], "MATCH_METHOD": "conflicting method"})
    write_csv(path, rows)
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode != 0
    assert "crosswalk" in result.stderr.lower()
    assert not output.exists()


def test_project_ids_supplied_on_project_rows_do_not_need_new_registry_rows(
    projects, tmp_path
):
    root = inputs(tmp_path, projects[:1])
    path = root / "sanctioned_projects.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["PROJECT_ID"] = "invented-1"
    write_csv(path, rows)
    identity = root / "cost_project_identity.csv"
    identity.write_text(
        "OPAQUE_ID,ENTITY_KIND,ACTIVE,SOURCE_TABLE,SOURCE_RECORD_LOCATOR\n",
        encoding="utf-8",
    )
    from worldenergydata.cost.benchmarks import load_projects

    assert well_row(build(load_projects(root)))["comparables"] == "invented-1"


def test_unregistered_project_is_explained_without_discarding_registered_projects(
    projects, tmp_path
):
    root = inputs(tmp_path, projects)
    identity = root / "cost_project_identity.csv"
    rows = list(csv.DictReader(identity.open(encoding="utf-8")))
    write_csv(identity, rows[:-1])
    from worldenergydata.cost.benchmarks import load_projects

    facts = build(load_projects(root))
    assert well_row(facts)["n"] == 4
    assert any(
        "PROJECT_ID" in e["reason"] and e.get("project_name") == "Invented project 5"
        for e in facts["exclusions"]
    )


def test_small_positive_figures_are_not_published_as_zero(projects, tmp_path):
    projects[0]["RECOVERABLE_RESOURCE_MMBOE"] = "100000"
    root = inputs(tmp_path, projects[:1])
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode == 0, result.stderr
    with (output / "unit_cost_benchmarks.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    resource = next(r for r in rows if r["metric"] == "capex_per_boe")
    assert float(resource["p50"]) == pytest.approx(0.001)
