"""2026 restatement contracts; synthetic figures below are arithmetic fixtures only."""

import csv
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from worldenergydata.cost.escalation import CostEscalator, build_projects, main
from worldenergydata.cost.timeseries.dataset import (
    read_sanctioned_csv,
    read_timeseries_csv,
)
from worldenergydata.cost.timeseries.normalization import DeflatorBasis, build_deflator
from worldenergydata.cost.timeseries.schema import CostObservation


ROOT = Path(__file__).resolve().parents[3]
CURATED = ROOT / "data/modules/cost/curated"


def observation(component, year, value, **extra):
    fields = dict(
        component=component,
        year=year,
        value=value,
        unit="index_test",
        figure_type="index",
        provenance="sourced",
        source_title="Synthetic index",
        source_url="https://example.org/synthetic",
        quoted_text="Synthetic test only",
        accessed_date="2026-01-01",
        notes="Synthetic, no engineering use",
        region="global" if component == "index_ucci" else "US",
    )
    fields.update(extra)
    return CostObservation(**fields)


def series(component, points):
    return [observation(component, year, value) for year, value in points.items()]


def ppi():
    # Independent growth ratios 150/100 and 300/100; mean = 2.25.
    return series("index_ppi_machinery", {2020: 100, 2026: 150}) + series(
        "index_ppi_drilling", {2020: 100, 2026: 300}
    )


def test_ppi_blend_is_mean_of_ratios_not_raw_levels():
    result = CostEscalator(ppi()).factor(2020)
    assert result.factor == 2.25
    assert "0.5" in result.index_used
    rescaled = series("index_ppi_machinery", {2020: 1000, 2026: 1500}) + ppi()[2:]
    assert CostEscalator(rescaled).factor(2020).factor == result.factor


def test_ucci_is_used_and_linked_to_ppi_at_last_held_year():
    rows = series("index_ucci", {2018: 100, 2020: 200}) + ppi()
    result = CostEscalator(rows).factor(2018)
    assert result.factor == 4.5  # (200/100) * ((1.5 + 3)/2)
    assert "index_ucci" in result.index_used
    assert "2020" in result.index_used
    assert "extrapolated" not in result.note


def test_direct_ucci_precedes_other_complete_series():
    result = CostEscalator(
        series("index_ucci", {2020: 100, 2023: 112, 2026: 125}) + ppi()
    ).factor(2020)
    assert result.factor == 1.25
    assert "ppi" not in result.index_used


def test_duplicate_quarterly_prints_are_averaged_and_order_independent():
    rows = series("index_ucci", {2020: 100, 2023: 150, 2026: 200})
    rows.append(observation("index_ucci", 2020, 300))
    assert CostEscalator(rows).factor(2020).factor == 1
    assert CostEscalator(list(reversed(rows))).factor(2020).factor == 1


def test_interior_missing_year_is_interpolated_with_both_anchors():
    rows = series("index_cpi", {2022: 100, 2024: 120, 2026: 150})
    result = CostEscalator(rows).factor(2023)
    assert result.factor == pytest.approx(150 / 110)
    assert "interpolated" in result.note
    assert {2022, 2024}.issubset(
        {a["year"] for step in result.trace for a in step["anchors"]}
    )


def test_wide_ucci_gap_selects_ppi_without_interpolating_blackout():
    rows = series("index_ucci", {2013: 229, 2019: 181.6})
    rows += series("index_ppi_machinery", {2016: 100, 2026: 150})
    rows += series("index_ppi_drilling", {2016: 100, 2026: 200})
    result = CostEscalator(rows).factor(2016)
    assert result.factor == 1.75
    assert "index_ucci" not in result.index_used


def test_ucci_stops_at_first_block_and_never_reenters():
    rows = series("index_ucci", {2010: 100, 2013: 200, 2019: 50, 2020: 25})
    rows += series("index_ppi_machinery", {2013: 100, 2026: 150})
    rows += series("index_ppi_drilling", {2013: 100, 2026: 300})
    result = CostEscalator(rows).factor(2010)
    assert result.factor == 4.5
    assert "2010:2013" in result.index_used
    assert "2013:2026" in result.index_used
    assert "2019" not in result.index_used


def test_cpi_is_last_resort_when_one_ppi_series_is_missing():
    rows = series("index_ppi_machinery", {2020: 100, 2026: 200})
    rows += series("index_cpi", {2020: 100, 2026: 125})
    result = CostEscalator(rows).factor(2020)
    assert result.factor == 1.25
    assert result.index_used.startswith("index_cpi")
    assert "last resort" in result.note


def test_covered_cpi_precedes_extrapolated_ppi():
    rows = series("index_ppi_machinery", {2020: 100, 2025: 125})
    rows += series("index_ppi_drilling", {2020: 100, 2025: 125})
    rows += series("index_cpi", {2020: 100, 2026: 120})
    result = CostEscalator(rows).factor(2020)
    assert result.factor == 1.2
    assert "extrapolated" not in result.note


@pytest.mark.parametrize(
    "base,target,expected", [(2020, 2026, 1.3), (2019, 2025, 125 / 95)]
)
def test_extrapolation_is_linear_explicit_and_traceable(base, target, expected):
    result = CostEscalator(series("index_cpi", {2020: 100, 2025: 125})).factor(
        base, target
    )
    assert result.factor == pytest.approx(expected)
    assert "extrapolated" in result.note
    assert "extrapolated" in json.dumps(result.trace)


def test_same_year_is_unchanged():
    result = CostEscalator(ppi()).factor(2026)
    assert result.factor == 1


@pytest.mark.parametrize(
    "values,reverse", [(range(100, 170, 10), True), (range(170, 100, -10), False)]
)
def test_monotonic_indices_give_opposite_factor_direction(values, reverse):
    rows = series("index_cpi", dict(zip(range(2020, 2027), values)))
    factors = [CostEscalator(rows).factor(year).factor for year in range(2020, 2027)]
    assert factors == sorted(factors, reverse=reverse)
    assert factors[-1] == 1


def test_observed_downturn_is_retained():
    result = CostEscalator(series("index_cpi", {2020: 125, 2026: 100})).factor(2020)
    assert result.factor == 0.8


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_invalid_index_values_raise(value):
    with pytest.raises(ValueError, match="positive|finite"):
        CostEscalator(series("index_cpi", {2020: value, 2026: 150}))


@pytest.mark.parametrize(
    "extra",
    [
        {"currency": "GBP"},
        {"price_basis": "real", "basis_year": 2020},
        {"provenance": "assumed"},
        {"figure_type": "fleet_average"},
        {"region": "regional"},
    ],
)
def test_incompatible_index_anchors_raise(extra):
    with pytest.raises(ValueError):
        CostEscalator([observation("index_cpi", 2020, 100, **extra)])


def test_index_anchor_cannot_carry_a_money_unit():
    with pytest.raises(ValueError, match="unit"):
        CostEscalator([observation("index_cpi", 2020, 100, unit="usd_per_day")])


@pytest.mark.parametrize(
    "component,region",
    [("index_ucci", "US"), ("index_cpi", "global"), ("index_ppi_machinery", "global")],
)
def test_index_regions_are_component_specific(component, region):
    with pytest.raises(ValueError, match="region"):
        CostEscalator([observation(component, 2020, 100, region=region)])


def test_explicit_year_conflict_with_reviewed_decision_is_rejected(tmp_path):
    with (CURATED / "sanctioned_projects.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["COST_STATEMENT_YEAR"] = "2026" if row["FID_YEAR"] == "2005" else ""
    path = tmp_path / "projects.csv"
    write_csv(path, rows)
    with pytest.raises(ValueError, match="conflict"):
        build_projects(
            path,
            CURATED / "cost_component_timeseries.csv",
            CURATED / "sanctioned_project_cost_years.csv",
        )


def test_real_module_cli_is_reproducible_in_an_isolated_child(tmp_path):
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(ROOT / path)
        for path in (
            "src",
            "packages/worldenergydata-cost/src",
            "packages/worldenergydata-core/src",
        )
    )
    output = tmp_path / "module-output.csv"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.cost.escalation",
            "--projects",
            str(CURATED / "sanctioned_projects.csv"),
            "--indices",
            str(CURATED / "cost_component_timeseries.csv"),
            "--statement-years",
            str(CURATED / "sanctioned_project_cost_years.csv"),
            "--output",
            str(output),
        ],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stderr
    assert "derived nominal costs: 70" in result.stdout
    assert (
        output.read_bytes() == (CURATED / "sanctioned_projects_2026.csv").read_bytes()
    )


def test_existing_named_readers_and_derived_composite_key():
    projects = read_sanctioned_csv(CURATED / "sanctioned_projects.csv")
    observations = read_timeseries_csv(CURATED / "cost_component_timeseries.csv")
    assert len(projects) == 80
    assert len({project.project for project in projects}) == 80
    assert all(
        observation.component.value.startswith(
            ("index_", "rig_", "vessel_", "surf_", "oil_")
        )
        for observation in observations
    )
    with (CURATED / "sanctioned_projects_2026.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    keys = {(row["PROJECT"], row["NOMINAL_COST_COLUMN"]) for row in rows}
    assert len(keys) == len(rows) == 83


def test_cli_selects_adjacent_held_sidecar_outside_repo_cwd(tmp_path):
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(ROOT / path)
        for path in (
            "src",
            "packages/worldenergydata-cost/src",
            "packages/worldenergydata-core/src",
        )
    )
    output = tmp_path / "automatic-years.csv"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.cost.escalation",
            "--projects",
            str(CURATED / "sanctioned_projects.csv"),
            "--indices",
            str(CURATED / "cost_component_timeseries.csv"),
            "--output",
            str(output),
        ],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stderr
    assert (
        output.read_bytes() == (CURATED / "sanctioned_projects_2026.csv").read_bytes()
    )


def test_failed_write_preserves_existing_output(tmp_path, monkeypatch):
    output = tmp_path / "existing.csv"
    preserved = b"preserved previous result\n"
    output.write_bytes(preserved)

    def failed_write(self, rows):
        raise OSError("simulated write failure")

    monkeypatch.setattr(csv.DictWriter, "writerows", failed_write)
    with pytest.raises(OSError, match="simulated"):
        main(
            [
                "--projects",
                str(CURATED / "sanctioned_projects.csv"),
                "--indices",
                str(CURATED / "cost_component_timeseries.csv"),
                "--statement-years",
                str(CURATED / "sanctioned_project_cost_years.csv"),
                "--output",
                str(output),
            ]
        )
    assert output.read_bytes() == preserved
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("explicit,conflict", [(2017, False), (2026, True)])
def test_actual_statement_year_agreement_and_conflict(tmp_path, explicit, conflict):
    with (CURATED / "sanctioned_projects.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["ACTUAL_COST_STATEMENT_YEAR"] = (
            str(explicit) if row["PROJECT"] == "Kraken" else ""
        )
    path = tmp_path / "projects.csv"
    write_csv(path, rows)
    if conflict:
        with pytest.raises(ValueError, match="conflict"):
            build_projects(
                path,
                CURATED / "cost_component_timeseries.csv",
                CURATED / "sanctioned_project_cost_years.csv",
            )
    else:
        result = build_projects(
            path,
            CURATED / "cost_component_timeseries.csv",
            CURATED / "sanctioned_project_cost_years.csv",
        )
        [actual] = [
            row
            for row in result
            if row["PROJECT"] == "Kraken"
            and row["NOMINAL_COST_COLUMN"] == "ACTUAL_COST_USD_MM"
        ]
        assert actual["INDEX_BASE_YEAR"] == "2017"
        assert "$2.5bn (first oil 2017)" in actual["ESCALATION_NOTE"]


def test_explicit_actual_year_precedes_unknown_fid_fallback(tmp_path):
    with (CURATED / "sanctioned_projects.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    [row] = [row for row in rows if row["ACTUAL_COST_USD_MM"] == "4300.0"]
    row.update(FID_YEAR="", ACTUAL_COST_STATEMENT_YEAR="2026")
    path = tmp_path / "projects.csv"
    write_csv(path, [row])
    result = build_projects(path, CURATED / "cost_component_timeseries.csv")
    [actual] = [
        row for row in result if row["NOMINAL_COST_COLUMN"] == "ACTUAL_COST_USD_MM"
    ]
    assert actual["INDEX_BASE_YEAR"] == "2026"
    assert float(actual["CAPEX_USD_MM_2026"]) == 4300


def test_statement_sidecar_requires_named_columns(tmp_path):
    sidecar = tmp_path / "invalid-years.csv"
    sidecar.write_text("PROJECT\nSynthetic\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sidecar.*column"):
        build_projects(
            CURATED / "sanctioned_projects.csv",
            CURATED / "cost_component_timeseries.csv",
            sidecar,
        )


def test_no_anchors_and_nonpositive_extrapolation_fail():
    with pytest.raises(ValueError, match="index|coverage"):
        CostEscalator([]).factor(2020)
    with pytest.raises(ValueError, match="index|positive|coverage"):
        CostEscalator(series("index_cpi", {2024: 100, 2025: 10})).factor(2024)


def test_extrapolation_beyond_one_year_is_rejected():
    with pytest.raises(ValueError, match="coverage|index"):
        CostEscalator(series("index_cpi", {2020: 100, 2024: 120})).factor(2020)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_held_projects_preserve_nominal_and_complete_every_disclosed_capex():
    with (CURATED / "sanctioned_projects.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        original = list(csv.DictReader(handle))
    derived = build_projects(
        CURATED / "sanctioned_projects.csv",
        CURATED / "cost_component_timeseries.csv",
        CURATED / "sanctioned_project_cost_years.csv",
    )
    assert len(derived) == len(original) + sum(
        bool(row["ACTUAL_COST_USD_MM"]) for row in original
    )
    primary = [
        row
        for row in derived
        if row["NOMINAL_COST_COLUMN"] == "SANCTIONED_CAPEX_USD_MM"
    ]
    assert len(primary) == len(original)
    for source, result in zip(original, primary):
        assert all(result[key] == value for key, value in source.items())
        if source["SANCTIONED_CAPEX_USD_MM"]:
            assert float(result["CAPEX_USD_MM_2026"]) > 0
            assert float(result["CAPEX_USD_MM_2026"]) == pytest.approx(
                float(source["SANCTIONED_CAPEX_USD_MM"])
                * float(result["ESCALATION_FACTOR"])
            )
            assert result["INDEX_USED"] and json.loads(result["INDEX_TRACE"])
            assert "PARTIAL YEAR" in result["ESCALATION_NOTE"]
            assert len(result["TIMESERIES_SHA256"]) == 64
            assert len(result["PROJECTS_SHA256"]) == 64
            assert len(result["STATEMENT_YEARS_SHA256"]) == 64
            for step in json.loads(result["INDEX_TRACE"]):
                for anchor in step["anchors"]:
                    assert anchor["sources"]
                    assert all(
                        source["source_url"].startswith("https://")
                        for source in anchor["sources"]
                    )
        else:
            assert result["CAPEX_USD_MM_2026"] == ""
            assert result["ESCALATION_FACTOR"] == ""
    assert sum(bool(row["CAPEX_USD_MM_2026"]) for row in derived) == 70
    for result in derived:
        if result["CAPEX_USD_MM_2026"]:
            assert float(result["CAPEX_USD_MM_2026"]) == pytest.approx(
                float(result[result["NOMINAL_COST_COLUMN"]])
                * float(result["ESCALATION_FACTOR"])
            )


def test_actual_costs_have_separate_years_and_fallbacks():
    rows = build_projects(
        CURATED / "sanctioned_projects.csv",
        CURATED / "cost_component_timeseries.csv",
        CURATED / "sanctioned_project_cost_years.csv",
    )
    actual = [row for row in rows if row["NOMINAL_COST_COLUMN"] == "ACTUAL_COST_USD_MM"]
    assert len(actual) == 3
    by_value = {float(row["ACTUAL_COST_USD_MM"]): row for row in actual}
    assert by_value[2500]["INDEX_BASE_YEAR"] == "2017"
    assert by_value[3350]["INDEX_BASE_YEAR"] == "2009"
    assert by_value[4300]["INDEX_BASE_YEAR"] == "2019"
    assert "FID year fallback" in by_value[4300]["ESCALATION_NOTE"]
    assert "Chronology inversion" in by_value[3350]["ESCALATION_NOTE"]
    assert all(
        "unknown and path-dependent" in by_value[value]["ESCALATION_NOTE"]
        for value in (3350, 4300)
    )


def test_explicit_statement_year_precedes_fid_and_works_without_fid(tmp_path):
    with (CURATED / "sanctioned_projects.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        row = next(csv.DictReader(handle))
    row.update(COST_STATEMENT_YEAR="2026", FID_YEAR="")
    path = tmp_path / "projects.csv"
    write_csv(path, [row])
    [result] = build_projects(path, CURATED / "cost_component_timeseries.csv")
    assert result["INDEX_BASE_YEAR"] == "2026"
    assert result["ESCALATION_FACTOR"] == "1.0"
    assert float(result["CAPEX_USD_MM_2026"]) == float(row["SANCTIONED_CAPEX_USD_MM"])


@pytest.mark.parametrize("gap,covered", [(3, True), (4, False)])
def test_interpolation_limit_counts_missing_years(gap, covered):
    rows = series("index_cpi", {2020: 100, 2021 + gap: 150, 2026: 200})
    if covered:
        result = CostEscalator(rows).factor(2021)
        assert "interpolated" in result.note
    else:
        with pytest.raises(ValueError, match="index|coverage"):
            CostEscalator(rows).factor(2021)


def test_one_covered_and_one_extrapolated_ppi_is_explicit():
    rows = series("index_ppi_machinery", {2020: 100, 2026: 150})
    rows += series("index_ppi_drilling", {2020: 100, 2025: 125})
    result = CostEscalator(rows).factor(2020)
    assert result.factor == pytest.approx(0.5 * 1.5 + 0.5 * 1.3)
    assert "extrapolated" in result.note


@pytest.mark.parametrize(
    "updates",
    [
        {"FID_YEAR": "", "COST_STATEMENT_YEAR": ""},
        {"COST_STATEMENT_YEAR": "2020.5"},
        {"SANCTIONED_CAPEX_USD_MM": "nan"},
        {"SANCTIONED_CAPEX_USD_MM": "-1"},
        {"CURRENCY": "GBP"},
        {"PRICE_BASIS": "real"},
    ],
)
def test_invalid_project_input_fails_instead_of_inventing_costs(tmp_path, updates):
    with (CURATED / "sanctioned_projects.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        row = next(csv.DictReader(handle))
    row.update(updates)
    path = tmp_path / "projects.csv"
    write_csv(path, [row])
    with pytest.raises(ValueError):
        build_projects(path, CURATED / "cost_component_timeseries.csv")


def test_known_statement_dates_and_fid_fallback_are_auditable():
    rows = build_projects(
        CURATED / "sanctioned_projects.csv",
        CURATED / "cost_component_timeseries.csv",
        CURATED / "sanctioned_project_cost_years.csv",
    )
    later = [
        row
        for row in rows
        if row["FID_YEAR"] == "2005" and row["SANCTIONED_CAPEX_USD_MM"]
    ]
    assert len(later) == 1
    assert later[0]["INDEX_BASE_YEAR"] == "2009"
    assert "statement year" in later[0]["ESCALATION_NOTE"]
    assert "FID year fallback" in rows[0]["ESCALATION_NOTE"]


def test_reviewed_statement_year_decisions_are_pinned():
    rows = build_projects(
        CURATED / "sanctioned_projects.csv",
        CURATED / "cost_component_timeseries.csv",
        CURATED / "sanctioned_project_cost_years.csv",
    )
    expected = {
        "Tahiti (Phase 1)": 2009,
        "Gorgon (incl. Jansz-Io)": 2009,
        "Jubilee Phase 1": 2010,
        "Tamar (Phase 1)": 2011,
        "Peregrino Phase 2": 2014,
        "KG-D6 integrated (R-Cluster + Satellites + MJ)": 2019,
        "Mozambique LNG (Area 1)": 2020,
        "Baleine (Phases 1-3 programme)": 2023,
        "Kraken": 2013,
    }
    for project, year in expected.items():
        [row] = [
            row
            for row in rows
            if row["PROJECT"] == project
            and row["NOMINAL_COST_COLUMN"] == "SANCTIONED_CAPEX_USD_MM"
        ]
        assert int(row["INDEX_BASE_YEAR"]) == year
        assert "statement year" in row["ESCALATION_NOTE"]
    [fallback] = [row for row in rows if row["PROJECT"] == "Mad Dog Phase 2 (Argos)"]
    assert fallback["INDEX_BASE_YEAR"] == "2016"
    assert "FID year fallback" in fallback["ESCALATION_NOTE"]


@pytest.mark.parametrize("defect", ["unmatched", "duplicate", "unsupported_year"])
def test_statement_sidecar_rejects_stale_or_ambiguous_evidence(tmp_path, defect):
    with (CURATED / "sanctioned_project_cost_years.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        records = list(csv.DictReader(handle))
    if defect == "unmatched":
        records[0]["SOURCE_URL"] = "https://example.org/missing"
    elif defect == "duplicate":
        records.append(records[0])
    else:
        records[0]["COST_STATEMENT_YEAR"] = "2026"
    sidecar = tmp_path / "years.csv"
    write_csv(sidecar, records)
    with pytest.raises(ValueError, match="statement|evidence|sidecar"):
        build_projects(
            CURATED / "sanctioned_projects.csv",
            CURATED / "cost_component_timeseries.csv",
            sidecar,
        )


def test_cli_reproduces_committed_table_and_protects_inputs(tmp_path):
    output = tmp_path / "derived.csv"
    args = [
        "--projects",
        str(CURATED / "sanctioned_projects.csv"),
        "--indices",
        str(CURATED / "cost_component_timeseries.csv"),
        "--statement-years",
        str(CURATED / "sanctioned_project_cost_years.csv"),
    ]
    assert main(args + ["--output", str(output)]) == 0
    assert (
        output.read_bytes() == (CURATED / "sanctioned_projects_2026.csv").read_bytes()
    )
    with pytest.raises(ValueError, match="input|overwrite"):
        main(args + ["--output", str(CURATED / "sanctioned_projects.csv")])


def test_held_index_factor_matches_independent_arithmetic():
    rows = read_timeseries_csv(CURATED / "cost_component_timeseries.csv")
    result = CostEscalator(rows).factor(2009)
    expected = (229 / 206) * 0.5 * (332.822 / 263.7667 + 396.3942 / 433.7167)
    assert result.factor == pytest.approx(expected)
    assert "PARTIAL YEAR" in result.note


def test_interpolated_ucci_coverage_is_flagged_even_between_held_endpoints():
    rows = read_timeseries_csv(CURATED / "cost_component_timeseries.csv")
    result = CostEscalator(rows).factor(2006)
    assert "interpolated" in result.note and "2007" in result.note
    assert any(
        step.get("interpolated_coverage_years") == [2007] for step in result.trace
    )


def test_historical_caveats_are_not_presented_as_current_null_findings():
    rows = build_projects(
        CURATED / "sanctioned_projects.csv",
        CURATED / "cost_component_timeseries.csv",
        CURATED / "sanctioned_project_cost_years.csv",
    )
    for row in rows:
        if row["CAPEX_USD_MM_2026"]:
            assert "historical source context" in row["ESCALATION_NOTE"]
            assert "populated nominal label takes precedence" in row["ESCALATION_NOTE"]


@pytest.mark.parametrize("year,ucci", [(2010, 207), (2013, 229)])
def test_held_blackout_uses_2013_join_not_2020(year, ucci):
    rows = read_timeseries_csv(CURATED / "cost_component_timeseries.csv")
    result = CostEscalator(rows).factor(year)
    expected = (229 / ucci) * 0.5 * (332.822 / 263.7667 + 396.3942 / 433.7167)
    assert result.factor == pytest.approx(expected)
    assert "2013:2026" in result.index_used
    assert "2010:2020" not in result.index_used


def test_held_ucci_averaging_matches_existing_normalization():
    rows = read_timeseries_csv(CURATED / "cost_component_timeseries.csv")
    existing = build_deflator(rows, DeflatorBasis.UCCI)
    calculator = CostEscalator(rows)
    for year in existing.values:
        target = 2013 if year <= 2013 else 2020
        result = calculator.factor(year, target)
        assert result.factor == pytest.approx(
            existing.values[target] / existing.values[year]
        )


def test_newline_conventions_do_not_change_input_identity(tmp_path):
    paths = []
    for name in [
        "sanctioned_projects.csv",
        "cost_component_timeseries.csv",
        "sanctioned_project_cost_years.csv",
    ]:
        path = tmp_path / name
        path.write_bytes(
            (CURATED / name)
            .read_bytes()
            .replace(b"\r\n", b"\n")
            .replace(b"\n", b"\r\n")
        )
        paths.append(path)
    assert build_projects(*paths) == build_projects(
        CURATED / "sanctioned_projects.csv",
        CURATED / "cost_component_timeseries.csv",
        CURATED / "sanctioned_project_cost_years.csv",
    )
