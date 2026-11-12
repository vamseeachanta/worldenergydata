"""Offline tests for the sanction-versus-outturn check and the public-only factor."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from worldenergydata.cost.escalation import CostEscalator
from worldenergydata.cost.outturn_check import (
    COLUMNS,
    build_outturn_checks,
    main,
)
from worldenergydata.cost.timeseries.dataset import read_timeseries_csv

CURATED = Path("data/modules/cost/curated")
INDICES = CURATED / "cost_component_timeseries.csv"
TRAILS = CURATED / "cost_revision_trails.csv"
HEADER = (
    "PROJECT,IN_SANCTIONED_SET,STATEMENT_DATE,VALUE_MM,CURRENCY,KIND,BASIS,"
    "PROVENANCE,CONFIDENCE,SOURCE_TITLE,SOURCE_URL,QUOTED_TEXT,ACCESSED_DATE,NOTES"
)


def _held(component: str, year: int) -> float:
    [value] = [
        row.value
        for row in read_timeseries_csv(INDICES)
        if row.component.value == component and row.year == year
    ]
    return value


def _trail(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "trails.csv"
    path.write_text("\n".join((HEADER, *lines)) + "\n", encoding="utf-8")
    return path


def _row(project: str, when: str, value: str, currency: str, kind: str) -> str:
    url = f"https://example.test/{kind}"
    return f"{project},yes,{when},{value},{currency},{kind},b,operator,high,t,{url},q,2026-07-15,"


def test_public_only_factor_never_uses_ucci() -> None:
    escalator = CostEscalator(read_timeseries_csv(INDICES))
    default = escalator.factor(2009, 2012)
    public = escalator.factor(2009, 2012, public_only=True)
    assert "index_ucci" in default.index_used
    assert "index_ucci" not in public.index_used
    expected = 0.5 * (
        _held("index_ppi_machinery", 2012) / _held("index_ppi_machinery", 2009)
        + _held("index_ppi_drilling", 2012) / _held("index_ppi_drilling", 2009)
    )
    assert public.factor == pytest.approx(expected)
    assert "public series only" in public.note


def test_public_only_factor_same_year_and_reverse() -> None:
    escalator = CostEscalator(read_timeseries_csv(INDICES))
    assert escalator.factor(2015, 2015, public_only=True).factor == pytest.approx(1.0)
    forward = escalator.factor(2010, 2020, public_only=True).factor
    assert forward != pytest.approx(1.0)
    backward = escalator.factor(2020, 2010, public_only=True).factor
    assert 0 < backward and backward != pytest.approx(1.0)


def test_held_trails_give_at_least_three_public_comparisons() -> None:
    rows = build_outturn_checks(TRAILS, INDICES)
    assert [row["PROJECT"] for row in rows] == sorted(row["PROJECT"] for row in rows)
    evaluated = {row["PROJECT"]: row for row in rows if row["STATUS"] == "EVALUATED"}
    assert len(evaluated) >= 3
    assert all(row["REASON"] for row in rows if row["STATUS"] != "EVALUATED")
    assert all(
        row["SANCTION_SOURCE_URL"].startswith("http")
        and row["FINAL_SOURCE_URL"].startswith("http")
        and "index_ucci" not in row["INDEX_USED"]
        for row in evaluated.values()
    )

    big_foot = evaluated["Big Foot"]
    factor = 0.5 * (
        _held("index_ppi_machinery", 2018) / _held("index_ppi_machinery", 2010)
        + _held("index_ppi_drilling", 2018) / _held("index_ppi_drilling", 2010)
    )
    assert float(big_foot["SANCTION_USD_MM"]) == 4000.0
    assert float(big_foot["FINAL_USD_MM"]) == 5100.0
    assert float(big_foot["INDEX_FACTOR"]) == pytest.approx(factor)
    assert float(big_foot["ESCALATED_SANCTION_USD_MM"]) == pytest.approx(4000 * factor)
    assert float(big_foot["STATED_CHANGE"]) == pytest.approx(0.275)
    assert float(big_foot["FINAL_OVER_ESCALATED_SANCTION"]) == pytest.approx(
        5100 / (4000 * factor) - 1
    )


def test_non_usd_and_incomplete_trails_are_not_evaluated(tmp_path: Path) -> None:
    trails = _trail(
        tmp_path,
        _row("A", "2012-03", "100", "NOK", "sanction_estimate"),
        _row("A", "2016", "150", "NOK", "final_outturn"),
        _row("B", "2012", "100", "USD", "sanction_estimate"),
        _row("C", "2012", "100", "USD", "sanction_estimate"),
        _row("C", "2013", "110", "USD", "sanction_estimate"),
        _row("C", "2016", "150", "USD", "final_outturn"),
        _row("D", "2016", "100", "USD", "sanction_estimate"),
        _row("D", "2012", "150", "USD", "final_outturn"),
        _row("E", "2012", "100", "USD", "sanction_estimate"),
        _row("E", "2015", "120", "USD", "final_forecast"),
        _row("E", "2016-06", "150", "USD", "final_outturn"),
        _row("F", "1980", "100", "USD", "sanction_estimate"),
        _row("F", "1985", "150", "USD", "final_outturn"),
    )
    rows = {row["PROJECT"]: row for row in build_outturn_checks(trails, INDICES)}
    assert "not in USD" in rows["A"]["REASON"]
    assert "no final" in rows["B"]["REASON"]
    assert "2 sanction estimates" in rows["C"]["REASON"]
    assert "precedes" in rows["D"]["REASON"]
    assert "no usable index coverage" in rows["F"]["REASON"]
    assert rows["E"]["STATUS"] == "EVALUATED"
    assert rows["E"]["FINAL_YEAR"] == "2016"
    assert rows["E"]["FINAL_KIND"] == "final_outturn"
    assert all(rows[name]["INDEX_FACTOR"] == "" for name in "ABCDF")


def test_cli_writes_table_and_protects_inputs(tmp_path: Path, capsys) -> None:
    output = tmp_path / "out.csv"
    assert main(["--output", str(output)]) == 0
    assert "evaluated" in capsys.readouterr().out
    with output.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == COLUMNS
        assert sum(row["STATUS"] == "EVALUATED" for row in reader) >= 3
    assert main(["--output", str(TRAILS)]) == 2


def test_published_table_matches_held_inputs() -> None:
    """Statuses and statement figures are stable; index columns move on refresh."""
    stable = (
        "PROJECT",
        "STATUS",
        "REASON",
        "SANCTION_YEAR",
        "SANCTION_USD_MM",
        "FINAL_YEAR",
        "FINAL_KIND",
        "FINAL_USD_MM",
        "INDEX_USED",
    )
    with Path("reports/cost/sanction_vs_outturn.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        published = [
            {key: row[key] for key in stable} for row in csv.DictReader(handle)
        ]
    rebuilt = [
        {key: row[key] for key in stable}
        for row in build_outturn_checks(TRAILS, INDICES)
    ]
    assert published == rebuilt
