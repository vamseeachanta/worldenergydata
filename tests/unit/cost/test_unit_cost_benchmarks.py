"""Invented projects only: fixed arithmetic fixtures, never engineering inputs."""

import csv
import os
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256

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
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
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


def cli(root, output, *extra_args):
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
            *extra_args,
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
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
    facts = build(projects + [projects[0]])
    assert well_row(facts)["n"] == 4
    assert all(
        "invented-1" not in row["comparables"]
        for row in facts["rows"] + facts["marginal_rows"]
    )
    excluded = [row for row in facts["exclusions"] if row["project_id"] == "invented-1"]
    assert len(excluded) == 2
    assert all(
        "n=2" in row["reason"] and "no cost selected" in row["reason"]
        for row in excluded
    )


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
        newline="\n",
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


def merged_crosswalk(root, projects, *, matched=True):
    """The merged header, with invented values and only one registered ID."""
    write_csv(
        root / "project_field_crosswalk.csv",
        [
            {
                "PROJECT_ID": f"PROJECT:{p['PROJECT']}",
                "COST_PROJECT_ID": p["PROJECT_ID"] if i == 0 else "",
                "PROJECT": p["PROJECT"],
                "CATALOG_FIELD_ID": p["CATALOG_FIELD_IDS"] if matched else "",
                "MATCH_METHOD": "manual" if matched else "unmatched",
                "CONFIDENCE": "high" if matched else "",
                "PROVENANCE": "Invented source",
                "EVIDENCE": "Invented matching evidence" if matched else "",
                "REASON": "Invented catalog has no counterpart" if not matched else "",
            }
            for i, p in enumerate(projects)
        ],
    )


def test_merged_crosswalk_join_uses_exact_locator_and_cost_id(projects, tmp_path):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects)
    merged_crosswalk(root, projects)
    identity = root / "cost_project_identity.csv"
    with identity.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    write_csv(identity, rows[:1])
    loaded = load_projects(root)
    assert loaded[0]["PROJECT_ID"] == "invented-1"
    assert loaded[1]["PROJECT_ID"] == "PROJECT:Invented project 2"
    assert loaded[1]["CATALOG_FIELD_IDS"] == "invented-field-2"
    assert loaded[1]["MATCH_EVIDENCE"] == "Invented matching evidence"
    assert well_row(build(loaded))["n"] == 5


@pytest.mark.parametrize("conflict", ["COST_PROJECT_ID", "PROJECT"])
def test_merged_crosswalk_rejects_identity_conflicts(projects, tmp_path, conflict):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects[:1])
    merged_crosswalk(root, projects[:1])
    path = root / "project_field_crosswalk.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0][conflict] = "invented-conflict"
    write_csv(path, rows)
    with pytest.raises(ValueError, match="[Cc]rosswalk.*(identity|locator)"):
        load_projects(root)


def test_locator_join_does_not_fold_project_name_case(projects, tmp_path):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects[:1])
    merged_crosswalk(root, [{**projects[0], "PROJECT": "invented project 1"}])
    facts = build(load_projects(root))
    assert facts["rows"] == []
    assert (
        facts["exclusions"][0]["reason"]
        == "crosswalk locator does not match project name"
    )


@pytest.mark.parametrize("invalid", ["CAPEX_USD_MM_2026", "quantities"])
def test_cli_empty_report_fails_with_counts_and_preserves_outputs(
    projects, tmp_path, invalid
):
    root = inputs(tmp_path, projects)
    output = tmp_path / "reports"
    assert cli(root, output).returncode == 0
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    path = root / "sanctioned_projects.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        columns = (
            (invalid,)
            if invalid != "quantities"
            else (
                "WELL_COUNT",
                "SURF_KM",
                "PEAK_PRODUCTION_BOEPD",
                "RECOVERABLE_RESOURCE_MMBOE",
            )
        )
        for column in columns:
            row[column] = ""
    write_csv(path, rows)
    if invalid == "quantities":
        path = root / "project_asset_requirements.csv"
        with path.open(encoding="utf-8") as stream:
            trees = list(csv.DictReader(stream))
        write_csv(path, [{**r, "QUANTITY": ""} for r in trees])
    result = cli(root, output)
    assert result.returncode == 2
    assert "No benchmark groups" in result.stderr
    assert "5 projects;" in result.stderr
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    fresh = tmp_path / "new-reports"
    assert cli(root, fresh).returncode == 2
    assert not fresh.exists()


def test_marginal_groups_keep_free_text_hosts_out_of_csv(projects, tmp_path):
    from worldenergydata.cost.benchmarks import write_benchmarks

    for i, project in enumerate(projects):
        project["HOST_TYPE"] = f"Invented floating host description {i}"
    facts = build(projects)
    exact = [r for r in facts["rows"] if r["metric"] == "capex_per_well"]
    assert len(exact) == 5
    assert all(r["n"] == 1 for r in exact)
    marginal = next(
        r
        for r in facts["marginal_rows"]
        if r["metric"] == "capex_per_well" and r["group_by"] == "water_depth_band"
    )
    assert marginal["category"] == "deep"
    assert marginal["n"] == 5
    # h=(5-1)p: 10+0.4*10=14; x[2]=30; 40+0.6*60=76.
    assert (marginal["p10"], marginal["p50"], marginal["p90"]) == pytest.approx(
        (14, 30, 76)
    )
    root = inputs(tmp_path, projects)
    paths = write_benchmarks(root, tmp_path / "reports", "2026-01-01")
    with paths["csv"].open(encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == len(facts["rows"])
    assert "Marginal groups" in paths["html"].read_text(encoding="utf-8")


def test_explicit_unmatched_projects_retain_sources_and_reason(projects, tmp_path):
    from worldenergydata.cost.benchmarks import load_projects, write_benchmarks

    root = inputs(tmp_path, projects)
    merged_crosswalk(root, projects, matched=False)
    facts = build(load_projects(root))
    assert well_row(facts)["n"] == 5
    paths = write_benchmarks(root, tmp_path / "reports", "2026-01-01")
    html = paths["html"].read_text(encoding="utf-8")
    assert "Invented catalog has no counterpart" in html
    assert "unmatched" in html


@pytest.mark.parametrize(
    "reason,field_ids", [("", ""), ("Invented reason", "invented-field")]
)
def test_inconsistent_unmatched_lineage_is_excluded(projects, reason, field_ids):
    projects[0].update(
        MATCH_METHOD="unmatched", MATCH_REASON=reason, CATALOG_FIELD_IDS=field_ids
    )
    facts = build(projects[:1])
    assert not facts["rows"]
    assert facts["exclusions"]


def test_cli_explicit_derived_projects_table_and_no_nominal_fallback(
    projects, tmp_path
):
    root = inputs(tmp_path, projects)
    original = root / "sanctioned_projects.csv"
    selected = root / "sanctioned_projects_2026.csv"
    with original.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    write_csv(
        original,
        [{k: v for k, v in row.items() if k != "CAPEX_USD_MM_2026"} for row in rows],
    )
    digest = sha256(original.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    for row in rows:
        row.update(PROJECTS_SHA256=digest, INPUT_DIGEST_BASIS="sha256_utf8_lf")
    write_csv(selected, rows)
    output = tmp_path / "reports"
    result = cli(root, output, "--projects", selected.as_posix())
    assert result.returncode == 0, result.stderr
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    write_csv(original, [{**row, "SANCTIONED_CAPEX_USD_MM": "999999"} for row in rows])
    result = cli(root, output, "--projects", selected.as_posix())
    assert result.returncode == 2
    assert "source digest" in result.stderr
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    write_csv(
        selected, [{k: v for k, v in row.items() if k != "INDEX_USED"} for row in rows]
    )
    result = cli(root, output, "--projects", selected.as_posix())
    assert result.returncode == 2
    assert "INDEX_USED" in result.stderr
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize("values", [(0.1, 0.2), (-1.0, 0.0)])
def test_existing_cohort_preserves_median_arithmetic_and_domain(values):
    from worldenergydata.cost.reporting.benchmark_report import _cohort_summary

    observations = [(2020, value, {}) for value in values]
    cohort = _cohort_summary(
        ("Invented region", "deep", "total", "drilling"), observations
    )
    assert cohort["median_usd_mm"] == (values[0] + values[1]) / 2


def test_csv_retains_small_percentile_precision(projects, tmp_path):
    from worldenergydata.cost.benchmarks import write_benchmarks

    for project in projects:
        project["RECOVERABLE_RESOURCE_MMBOE"] = "5000"
    root = inputs(tmp_path, projects)
    paths = write_benchmarks(root, tmp_path / "reports", "2026-01-01")
    with paths["csv"].open(encoding="utf-8") as stream:
        row = next(r for r in csv.DictReader(stream) if r["metric"] == "capex_per_boe")
    # Intensities .02,.04,.06,.08,.20: P10=.028, P50=.06, P90=.152.
    assert tuple(float(row[key]) for key in ("p10", "p50", "p90")) == pytest.approx(
        (0.028, 0.06, 0.152)
    )


@pytest.mark.parametrize(
    "basis",
    [
        "FLOOR disclosed cost",
        "lower-bound project cost",
        "in excess of disclosed amount",
        "lower bound: disclosed cost",
        "AT LEAST disclosed amount",
        "FLOOR",
        "FLOOR: disclosed amount",
        # Curated basis wording; identifying references use invented labels.
        "pre-sanction gross estimate FLOOR: 'in excess of US$2 billion' "
        "per 44% partner Invented partner 6-K (May 2002 FEED/long-lead "
        "approval, ahead of full 2002 sanction)",
        "gross capital cost FLOOR 'more than $4 billion' at FID for the "
        "initial 6-well phase (subsea tieback to Invented host FPU)",
        "gross project cost at FID, phase 1 only. Operator stated as "
        "'LESS THAN $5 billion' — this is an UPPER BOUND, not a point estimate",
        "upper-bound disclosed amount",
        "gross cost LOWER BOUND: disclosed amount",
    ],
)
def test_bound_costs_are_excluded_from_point_percentiles(projects, basis):
    projects[0]["CAPEX_BASIS"] = basis
    facts = build(projects)
    for row in facts["rows"] + facts["marginal_rows"]:
        assert row["n"] == 4
        assert row["indicative_only"] is True
        assert "invented-1" not in row["comparables"]
    row = well_row(facts)
    # Remaining [20,30,40,100]: h=3p; P10=20+.3*10=23,
    # P50=30+.5*10=35, P90=40+.7*60=82 (inclusive interpolation).
    assert tuple(row[key] for key in ("p10", "p50", "p90")) == pytest.approx(
        (23, 35, 82)
    )
    assert any("bound" in r["reason"] for r in facts["exclusions"])


@pytest.mark.parametrize(
    "basis",
    [
        "point estimate; not a floor",
        "point estimate confirmed by at least two sources",
        "not in excess of disclosed amount",
        "floor-mounted equipment cost",
        "FLOORING equipment point cost",
        "point cost for UPPER BOUNDARY equipment",
    ],
)
def test_point_estimate_mentioning_floor_is_not_a_bound(projects, basis):
    projects[0]["CAPEX_BASIS"] = basis
    assert well_row(build(projects))["n"] == 5


def test_excluded_sole_member_cohort_does_not_abort_other_cohorts(projects):
    projects[0].update(
        REGION="Invented distinct region", CAPEX_BASIS="FLOOR: disclosed amount"
    )
    facts = build(projects)
    assert well_row(facts)["n"] == 4
    assert facts["exclusions"]


def test_crosswalk_duplicate_cost_id_is_fatal(projects, tmp_path):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects[:2])
    merged_crosswalk(root, projects[:2])
    path = root / "project_field_crosswalk.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[1]["COST_PROJECT_ID"] = rows[0]["COST_PROJECT_ID"]
    write_csv(path, rows)
    with pytest.raises(ValueError, match="[Cc]rosswalk"):
        load_projects(root)


def test_html_retains_escalation_note(projects, tmp_path):
    from worldenergydata.cost.benchmarks import write_benchmarks

    projects[0]["ESCALATION_NOTE"] = "Invented provisional partial-year index"
    root = inputs(tmp_path, projects[:1])
    paths = write_benchmarks(root, tmp_path / "reports", "2026-01-01")
    assert "Invented provisional partial-year index" in paths["html"].read_text(
        encoding="utf-8"
    )


def test_duplicate_derived_rows_are_excluded_without_selecting_a_cost(
    projects, tmp_path
):
    from worldenergydata.cost.benchmarks import load_projects, write_benchmarks

    root = inputs(tmp_path, projects)
    path = root / "sanctioned_projects.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows.append({**rows[0], "CAPEX_USD_MM_2026": "999.125"})
    write_csv(path, rows)
    facts = build(load_projects(root))
    assert well_row(facts)["n"] == 4
    assert all("invented-1" not in r["comparables"] for r in facts["rows"])
    paths = write_benchmarks(root, tmp_path / "reports", "2026-01-01")
    html = paths["html"].read_text(encoding="utf-8")
    assert "no cost selected" in html
    assert "999.125" in html


def test_project_table_cannot_supply_unjoined_crosswalk_lineage(projects, tmp_path):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects[:1])
    merged_crosswalk(root, [{**projects[0], "PROJECT": "invented project 1"}])
    path = root / "sanctioned_projects.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0].update(
        {
            k: v
            for k, v in projects[0].items()
            if k.startswith("MATCH_") or k == "CATALOG_FIELD_IDS"
        }
    )
    write_csv(path, rows)
    facts = build(load_projects(root))
    assert not facts["rows"]
    assert "crosswalk locator" in facts["exclusions"][0]["reason"]


def test_project_names_strip_only_outer_whitespace(projects, tmp_path):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects[:1])
    merged_crosswalk(root, projects[:1])
    path = root / "sanctioned_projects.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["PROJECT"] = " Invented project 1 "
    write_csv(path, rows)
    assert well_row(build(load_projects(root)))["n"] == 1


@pytest.mark.parametrize("use_derived", [False, True])
def test_changed_input_bytes_stop_generation_before_writing(
    projects, tmp_path, monkeypatch, use_derived
):
    import worldenergydata.cost.benchmarks as module

    root = inputs(tmp_path, projects)
    selected = None
    if use_derived:
        source = root / "sanctioned_projects.csv"
        with source.open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        digest = sha256(source.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        for row in rows:
            row.update(PROJECTS_SHA256=digest, INPUT_DIGEST_BASIS="sha256_utf8_lf")
        selected = root / "sanctioned_projects_2026.csv"
        write_csv(selected, rows)
    original_load = module.load_projects

    def changing_load(*args):
        loaded = original_load(*args)
        path = root / "sanctioned_projects.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        return loaded

    monkeypatch.setattr(module, "load_projects", changing_load)
    output = tmp_path / "reports"
    with pytest.raises(ValueError, match="Input bytes changed"):
        module.write_benchmarks(root, output, "2026-01-01", selected)
    assert not output.exists()


@pytest.mark.parametrize(
    "defect",
    [
        "stale_source",
        "missing_columns",
        "blank_digest",
        "invalid_digest",
        "wrong_digest",
        "wrong_basis",
    ],
)
def test_selected_table_rejects_invalid_source_provenance(projects, tmp_path, defect):
    from worldenergydata.cost.benchmarks import write_benchmarks

    root = inputs(tmp_path, projects)
    source = root / "sanctioned_projects.csv"
    with source.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    digest = sha256(source.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    for row in rows:
        row.update(PROJECTS_SHA256=digest, INPUT_DIGEST_BASIS="sha256_utf8_lf")
    if defect == "stale_source":
        source.write_bytes(source.read_bytes() + b"\n")
    elif defect == "missing_columns":
        for row in rows:
            del row["PROJECTS_SHA256"]
            del row["INPUT_DIGEST_BASIS"]
    else:
        column, value = {
            "blank_digest": ("PROJECTS_SHA256", ""),
            "invalid_digest": ("PROJECTS_SHA256", "invalid"),
            "wrong_digest": ("PROJECTS_SHA256", "0" * 64),
            "wrong_basis": ("INPUT_DIGEST_BASIS", "raw_bytes"),
        }[defect]
        # Invalid evidence on a later row must also prevent publication.
        rows[-1][column] = value
    selected = root / "sanctioned_projects_2026.csv"
    write_csv(selected, rows)
    output = tmp_path / "reports"
    write_benchmarks(root, output, "2026-01-01")
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    result = cli(root, output, "--projects", selected.as_posix())
    assert result.returncode == 2
    assert "provenance" in result.stderr or "digest" in result.stderr
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize("line_ending", ["\n", "\r\n", "\r"])
def test_selected_table_source_digest_uses_utf8_and_normalized_newlines(
    projects, tmp_path, line_ending
):
    from worldenergydata.cost.benchmarks import load_projects

    root = inputs(tmp_path, projects)
    source = root / "sanctioned_projects.csv"
    with source.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["NOTES"] = "Invented café"
    write_csv(source, rows)
    normalized = source.read_text(encoding="utf-8")
    source.write_bytes(normalized.replace("\n", line_ending).encode("utf-8"))
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    for row in rows:
        row.update(PROJECTS_SHA256=digest, INPUT_DIGEST_BASIS="sha256_utf8_lf")
    selected = root / "sanctioned_projects_2026.csv"
    write_csv(selected, rows)
    assert well_row(build(load_projects(root, selected)))["n"] == 5


@pytest.mark.parametrize(
    "column,metric",
    [
        ("WELL_COUNT", "capex_per_well"),
        ("SURF_KM", "capex_per_surf_km"),
        ("PEAK_PRODUCTION_BOEPD", "capex_per_kboed"),
        ("RECOVERABLE_RESOURCE_MMBOE", "capex_per_boe"),
    ],
)
@pytest.mark.parametrize("value", ["unknown", "nan", "inf", "0", "-1", ""])
def test_cli_invalid_quantity_excludes_only_affected_metric(
    projects, tmp_path, column, metric, value
):
    from worldenergydata.cost.benchmarks import load_projects

    projects[-1][column] = value
    root = inputs(tmp_path, projects)
    # The boundary must preserve the source value for metric-local validation.
    assert load_projects(root)[-1][column] == value
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode == 0, result.stderr
    with (output / "unit_cost_benchmarks.csv").open(encoding="utf-8") as stream:
        rows = {r["metric"]: r for r in csv.DictReader(stream)}
    expected = {r["metric"]: r for r in build(projects)["rows"]}
    assert rows.keys() == expected.keys()
    for name, row in rows.items():
        assert row["n"] == ("4" if name == metric else "5")
        assert row["comparables"] == expected[name]["comparables"]
        assert row["indicative_only"] == str(expected[name]["indicative_only"]).lower()
        for percentile in ("p10", "p50", "p90"):
            assert float(row[percentile]) == expected[name][percentile]
    html = (output / "unit_cost_benchmarks.html").read_text(encoding="utf-8")
    assert f"missing or invalid {column}" in html or (
        f"{column} must be finite and positive" in html
    )


@pytest.mark.parametrize("value", ["unknown", "nan", "inf", "-1", ""])
def test_cli_invalid_depth_uses_unknown_band_without_losing_metrics(
    projects, tmp_path, value
):
    from worldenergydata.cost.benchmarks import load_projects

    projects[-1]["WATER_DEPTH_M"] = value
    root = inputs(tmp_path, projects)
    assert load_projects(root)[-1]["WATER_DEPTH_M"] == value
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode == 0, result.stderr
    with (output / "unit_cost_benchmarks.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    expected = build(projects)["rows"]
    assert len(rows) == len(expected) == 10
    assert sum(int(row["n"]) for row in rows) == 25
    for row, want in zip(rows, expected, strict=True):
        assert row["water_depth_band"] == want["water_depth_band"]
        assert row["comparables"] == want["comparables"]
        if row["water_depth_band"] == "unknown":
            assert row["n"] == "1"
            assert row["comparables"] == "invented-5"
        else:
            assert row["water_depth_band"] == "deep"
            assert row["n"] == "4"
        for percentile in ("p10", "p50", "p90"):
            assert float(row[percentile]) == want[percentile]


@pytest.mark.parametrize(
    "column,value,error",
    [
        ("FID_YEAR", "unknown", "could not convert"),
        ("FIRST_OIL_YEAR", "unknown", "could not convert"),
        ("SANCTIONED_CAPEX_USD_MM", "unknown", "could not convert"),
        ("ACTUAL_COST_USD_MM", "unknown", "could not convert"),
        ("USD_PER_BOE", "unknown", "could not convert"),
        ("ACCESSED_DATE", "unknown", "Invalid isoformat"),
        ("CONFIDENCE", "unknown", "DisclosureConfidence"),
        ("SOURCE_PRIORITY", "unknown", "SourcePriority"),
        ("CAPEX_BASIS", "", "capex_basis"),
        ("PROJECT_ID", "invented-conflict", "identity registry disagree"),
    ],
)
def test_cli_invalid_quantity_does_not_suppress_metadata_errors(
    projects, tmp_path, column, value, error
):
    root = inputs(tmp_path, projects)
    output = tmp_path / "reports"
    assert cli(root, output).returncode == 0
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    path = root / "sanctioned_projects.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[-1].update(WELL_COUNT="nan", SURF_KM="unknown", WATER_DEPTH_M="unknown")
    if column == "PROJECT_ID":
        for row in rows:
            row[column] = ""
    rows[-1][column] = value
    write_csv(path, rows)
    result = cli(root, output)
    assert result.returncode == 2
    assert error in result.stderr
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize("column", ["SOURCE_URL", "WELL_COUNT", "ACCESSED_DATE"])
def test_cli_invalid_quantity_does_not_suppress_missing_headers(
    projects, tmp_path, column
):
    projects[-1]["WELL_COUNT"] = "nan"
    root = inputs(tmp_path, projects)
    path = root / "sanctioned_projects.csv"
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    write_csv(path, [{k: v for k, v in row.items() if k != column} for row in rows])
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode == 2
    assert column in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "column,value", [("SOURCE_URL", "invalid"), ("SOURCE_TITLE", "")]
)
def test_cli_invalid_quantity_does_not_bypass_source_exclusions(
    projects, tmp_path, column, value
):
    projects[-1].update(WELL_COUNT="nan", SURF_KM="unknown", WATER_DEPTH_M="unknown")
    projects[-1][column] = value
    root = inputs(tmp_path, projects)
    output = tmp_path / "reports"
    result = cli(root, output)
    assert result.returncode == 0, result.stderr
    with (output / "unit_cost_benchmarks.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 5
    assert all(row["n"] == "4" for row in rows)
    assert all("invented-5" not in row["comparables"] for row in rows)
    html = (output / "unit_cost_benchmarks.html").read_text(encoding="utf-8")
    assert column in html
