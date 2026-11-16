"""Offline tests for the sanction-versus-outturn check and the public-only factor.

Reference index values used as independent expectations are complete-year
annual means of the monthly BLS series, read from FRED on 2026-11-12:

- PPI oil and gas field machinery, PCU333132333132 (Dec 1980=100),
  https://fred.stlouisfed.org/series/PCU333132333132
  2010: 247.05; 2013: 263.7667; 2017: 265.425; 2018: 268.025
- PPI drilling oil and gas wells, PCU213111213111 (Dec 1985=100),
  https://fred.stlouisfed.org/series/PCU213111213111
  2010: 325.9333; 2013: 433.7167; 2017: 323.5667; 2018: 332.3167

They are literals here, not read from the held CSV, so a corrupted held row or
a wrong reduction fails these tests.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from worldenergydata.cost.escalation import CostEscalator
from worldenergydata.cost.outturn_check import (
    COLUMNS,
    COMPARABLE_QUALIFIERS,
    build_outturn_checks,
    main,
)
from worldenergydata.cost.timeseries.dataset import read_timeseries_csv

CURATED = Path("data/modules/cost/curated")
INDICES = CURATED / "cost_component_timeseries.csv"
TRAILS = CURATED / "cost_revision_trails.csv"
QUALIFIERS = CURATED / "cost_revision_trail_qualifiers.csv"
TRAIL_HEADER = (
    "PROJECT,IN_SANCTIONED_SET,STATEMENT_DATE,VALUE_MM,CURRENCY,KIND,BASIS,"
    "PROVENANCE,CONFIDENCE,SOURCE_TITLE,SOURCE_URL,QUOTED_TEXT,ACCESSED_DATE,NOTES"
)
QUALIFIER_HEADER = "TRAIL_PROJECT,STATEMENT_DATE,KIND,QUALIFIER,EVIDENCE,REVIEWED_DATE"

MACHINERY = {2010: 247.05, 2013: 263.7667, 2017: 265.425, 2018: 268.025}
DRILLING = {2010: 325.9333, 2013: 433.7167, 2017: 323.5667, 2018: 332.3167}
# 0.5 * (265.425 / 263.7667 + 323.5667 / 433.7167)
FACTOR_2013_2017 = 0.8761597
# 0.5 * (268.025 / 247.05 + 332.3167 / 325.9333)
FACTOR_2010_2018 = 1.0522434
# 0.5 * (247.05 / 268.025 + 325.9333 / 332.3167): reverse direction, not 1/forward
FACTOR_2018_2010 = 0.9512668


def _blend(base: int, target: int) -> float:
    return 0.5 * (
        MACHINERY[target] / MACHINERY[base] + DRILLING[target] / DRILLING[base]
    )


def _write(path: Path, header: str, lines: tuple[str, ...]) -> Path:
    path.write_text("\n".join((header, *lines)) + "\n", encoding="utf-8")
    return path


def _row(project: str, when: str, value: str, currency: str, kind: str) -> str:
    url = f"https://example.test/{kind}"
    return (
        f"{project},yes,{when},{value},{currency},{kind},b,operator,high,t,"
        f"{url},q,2026-07-15,"
    )


def _wording(project: str, when: str, kind: str, qualifier: str = "exact") -> str:
    return f"{project},{when},{kind},{qualifier},source wording,2026-11-12"


def _case(tmp_path: Path, trail: tuple[str, ...], wording: tuple[str, ...]):
    trails = _write(tmp_path / "trails.csv", TRAIL_HEADER, trail)
    qualifiers = _write(tmp_path / "qualifiers.csv", QUALIFIER_HEADER, wording)
    return {
        row["PROJECT"]: row for row in build_outturn_checks(trails, INDICES, qualifiers)
    }


def test_reference_literals_are_self_consistent() -> None:
    assert _blend(2013, 2017) == pytest.approx(FACTOR_2013_2017, abs=5e-7)
    assert _blend(2010, 2018) == pytest.approx(FACTOR_2010_2018, abs=5e-7)
    assert _blend(2018, 2010) == pytest.approx(FACTOR_2018_2010, abs=5e-7)


def test_public_only_factor_matches_cited_reference_values() -> None:
    escalator = CostEscalator(read_timeseries_csv(INDICES))
    forward = escalator.factor(2010, 2018, public_only=True)
    assert forward.factor == pytest.approx(FACTOR_2010_2018, abs=5e-7)
    assert "index_ucci" not in forward.index_used
    assert "public series only" in forward.note
    assert escalator.factor(2013, 2017, public_only=True).factor == pytest.approx(
        FACTOR_2013_2017, abs=5e-7
    )


def test_public_only_reverse_and_same_year_factors() -> None:
    escalator = CostEscalator(read_timeseries_csv(INDICES))
    backward = escalator.factor(2018, 2010, public_only=True).factor
    assert backward == pytest.approx(FACTOR_2018_2010, abs=5e-7)
    # An arithmetic mean of ratios is not reciprocal; the product exceeds one.
    assert backward * FACTOR_2010_2018 == pytest.approx(1.0009642, abs=2e-6)
    assert escalator.factor(2015, 2015, public_only=True).factor == pytest.approx(1.0)


def test_default_path_still_uses_ucci_where_covered() -> None:
    escalator = CostEscalator(read_timeseries_csv(INDICES))
    assert "index_ucci" in escalator.factor(2009, 2012).index_used
    assert "index_ucci" not in escalator.factor(2009, 2012, public_only=True).index_used


def test_held_trails_give_at_least_three_supported_comparisons() -> None:
    rows = build_outturn_checks(TRAILS, INDICES, QUALIFIERS)
    assert [row["PROJECT"] for row in rows] == sorted(row["PROJECT"] for row in rows)
    evaluated = {row["PROJECT"]: row for row in rows if row["STATUS"] == "EVALUATED"}
    assert len(evaluated) >= 3
    assert all(row["REASON"] for row in rows if row["STATUS"] != "EVALUATED")
    for row in evaluated.values():
        assert row["SANCTION_QUALIFIER"] in COMPARABLE_QUALIFIERS
        assert row["FINAL_QUALIFIER"] in COMPARABLE_QUALIFIERS
        assert row["SANCTION_SOURCE_URL"].startswith("http")
        assert row["FINAL_SOURCE_URL"].startswith("http")
        assert "index_ucci" not in row["INDEX_USED"]

    kraken = evaluated["Kraken"]
    assert float(kraken["SANCTION_USD_MM"]) == 3200.0
    assert float(kraken["FINAL_USD_MM"]) == 2500.0
    assert (kraken["SANCTION_YEAR"], kraken["FINAL_YEAR"]) == ("2013", "2017")
    assert float(kraken["INDEX_FACTOR"]) == pytest.approx(FACTOR_2013_2017, abs=5e-7)
    assert float(kraken["ESCALATED_SANCTION_USD_MM"]) == pytest.approx(
        2803.71, abs=0.01
    )
    assert float(kraken["STATED_CHANGE"]) == pytest.approx(-0.21875)
    assert float(kraken["FINAL_OVER_ESCALATED_SANCTION"]) == pytest.approx(
        -0.108325, abs=1e-5
    )


def test_bounded_and_unsupported_statements_are_not_evaluated() -> None:
    rows = {
        row["PROJECT"]: row for row in build_outturn_checks(TRAILS, INDICES, QUALIFIERS)
    }
    big_foot = rows["Big Foot"]
    assert big_foot["STATUS"] == "NOT_EVALUATED"
    assert "not supported by its cited source" in big_foot["REASON"]
    assert "30 April 2015" in big_foot["REASON"]
    ten = rows["TEN (Tweneboa-Enyenra-Ntomme)"]
    assert ten["STATUS"] == "NOT_EVALUATED"
    assert "final statement is an upper bound" in ten["REASON"]
    peregrino = rows["Peregrino Phase 2"]
    assert peregrino["STATUS"] == "NOT_EVALUATED"
    assert "within the original USD 3 billion" in peregrino["REASON"]
    mariner = rows["Mariner"]
    assert mariner["STATUS"] == "NOT_EVALUATED"
    assert "sanction statement is a lower bound" in mariner["REASON"]
    assert "final statement is a lower bound" in mariner["REASON"]
    for row in (big_foot, ten, peregrino, mariner):
        assert row["INDEX_FACTOR"] == "" and row["FINAL_USD_MM"] == ""


def test_corrected_final_statement_sources_are_held() -> None:
    with TRAILS.open(encoding="utf-8", newline="") as handle:
        finals = {
            row["PROJECT"]: row
            for row in csv.DictReader(handle)
            if row["KIND"] == "final_outturn"
        }
    mariner, peregrino = finals["Mariner"], finals["Peregrino Phase 2"]
    assert (
        mariner["SOURCE_URL"] == "https://www.equinor.com/news/archive/2019-08-mariner"
    )
    assert "more than $7.7 billion" in mariner["QUOTED_TEXT"]
    assert mariner["ACCESSED_DATE"] == "2026-11-12"
    assert (
        peregrino["SOURCE_URL"]
        == "https://www.equinor.com/news/20221013-peregrino-phase-2-on-stream"
    )
    assert "within the original USD 3 billion" in peregrino["QUOTED_TEXT"]


def test_unreviewed_wording_is_not_evaluated(tmp_path: Path) -> None:
    trail = (
        _row("A", "2010", "100", "USD", "sanction_estimate"),
        _row("A", "2018", "150", "USD", "final_outturn"),
        _row("B", "2010", "100", "USD", "sanction_estimate"),
        _row("B", "2018", "150", "USD", "final_outturn"),
    )
    rows = _case(
        tmp_path,
        trail,
        (
            _wording("A", "2010", "sanction_estimate"),
            _wording("B", "2010", "sanction_estimate"),
            _wording("B", "2018", "final_outturn", "approximate"),
        ),
    )
    assert rows["A"]["REASON"] == "final statement wording not reviewed"
    assert rows["B"]["STATUS"] == "EVALUATED"
    assert rows["B"]["FINAL_QUALIFIER"] == "approximate"
    assert float(rows["B"]["INDEX_FACTOR"]) == pytest.approx(FACTOR_2010_2018, abs=5e-7)
    assert float(rows["B"]["ESCALATED_SANCTION_USD_MM"]) == pytest.approx(
        105.22434, abs=1e-4
    )


def test_structural_exclusions(tmp_path: Path) -> None:
    trail = (
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
        _row("G", "2012", "100", "USD", "final_outturn"),
    )
    wording = (
        _wording("E", "2012", "sanction_estimate"),
        _wording("E", "2016-06", "final_outturn"),
        _wording("F", "1980", "sanction_estimate"),
        _wording("F", "1985", "final_outturn"),
    )
    rows = _case(tmp_path, trail, wording)
    assert "not in USD" in rows["A"]["REASON"]
    assert "no final" in rows["B"]["REASON"]
    assert "2 sanction estimates" in rows["C"]["REASON"]
    assert "precedes" in rows["D"]["REASON"]
    assert "no usable index coverage" in rows["F"]["REASON"]
    assert "0 sanction estimates" in rows["G"]["REASON"]
    assert rows["E"]["STATUS"] == "EVALUATED"
    assert (rows["E"]["FINAL_YEAR"], rows["E"]["FINAL_KIND"]) == (
        "2016",
        "final_outturn",
    )
    assert all(rows[name]["INDEX_FACTOR"] == "" for name in "ABCDFG")


def test_reversed_dates_within_one_year_are_not_evaluated(tmp_path: Path) -> None:
    trail = (
        _row("A", "2016-12", "100", "USD", "sanction_estimate"),
        _row("A", "2016-01", "150", "USD", "final_outturn"),
        _row("B", "2016-12", "100", "USD", "sanction_estimate"),
        _row("B", "2016", "150", "USD", "final_outturn"),
        _row("C", "2016-03-20", "100", "USD", "sanction_estimate"),
        _row("C", "2016-03-05", "150", "USD", "final_outturn"),
        _row("D", "2012", "100", "USD", "sanction_estimate"),
        _row("D", "2016-09", "120", "USD", "final_forecast"),
        _row("D", "2016-10", "150", "USD", "final_outturn"),
    )
    wording = (
        _wording("B", "2016-12", "sanction_estimate"),
        _wording("B", "2016", "final_outturn"),
        _wording("D", "2012", "sanction_estimate"),
        _wording("D", "2016-10", "final_outturn"),
    )
    rows = _case(tmp_path, trail, wording)
    assert "precedes" in rows["A"]["REASON"]
    assert "precedes" in rows["C"]["REASON"]
    assert rows["B"]["STATUS"] == "EVALUATED"  # year-only final: same year allowed
    assert float(rows["B"]["INDEX_FACTOR"]) == pytest.approx(1.0)
    assert rows["D"]["FINAL_USD_MM"] == "150.0"  # latest by date, not by text


def test_qualifier_table_is_validated(tmp_path: Path) -> None:
    trail = (
        _row("A", "2010", "100", "USD", "sanction_estimate"),
        _row("A", "2018", "150", "USD", "final_outturn"),
    )
    good = _wording("A", "2010", "sanction_estimate")
    for bad, message in (
        (_wording("Z", "2010", "sanction_estimate"), "matches no trail statement"),
        (_wording("A", "2018", "final_outturn", "roughly"), "unknown qualifier"),
        ("A,2018,final_outturn,exact,,2026-11-12", "lacks evidence"),
        (good, "duplicate qualifier row"),
    ):
        with pytest.raises(ValueError, match=message):
            _case(tmp_path, trail, (good, bad))


def test_held_qualifier_table_covers_every_usd_pair() -> None:
    """No held USD sanction/final pair is left unreviewed."""
    rows = build_outturn_checks(TRAILS, INDICES, QUALIFIERS)
    assert not [row["PROJECT"] for row in rows if "not reviewed" in row["REASON"]]
    with QUALIFIERS.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    # The crosswalk inventory treats any PROJECT-bearing CSV as a cost register.
    assert "PROJECT" not in header and "PROJECT_ID" not in header


def test_evaluated_rows_carry_retrieval_dates_and_index_sources() -> None:
    evaluated = [
        row
        for row in build_outturn_checks(TRAILS, INDICES, QUALIFIERS)
        if row["STATUS"] == "EVALUATED"
    ]
    assert evaluated
    for row in evaluated:
        assert row["SANCTION_ACCESSED_DATE"] and row["FINAL_ACCESSED_DATE"]
        assert row["SANCTION_CONFIDENCE"] and row["FINAL_CONFIDENCE"]
        trace = json.loads(row["INDEX_TRACE"])
        assert trace
        for step in trace:
            for anchor in step["anchors"]:
                for source in anchor["sources"]:
                    assert source["source_url"].startswith("https://")
                    assert source["accessed_date"]


def test_cli_writes_table_and_protects_inputs(tmp_path: Path, capsys) -> None:
    output = tmp_path / "out.csv"
    assert main(["--output", str(output)]) == 0
    assert "evaluated" in capsys.readouterr().out
    with output.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == COLUMNS
        assert sum(row["STATUS"] == "EVALUATED" for row in reader) >= 3
    for source in (TRAILS, INDICES, QUALIFIERS):
        assert main(["--output", str(source)]) == 2


def test_cli_refuses_output_hardlinked_to_an_input(tmp_path: Path) -> None:
    copies = {}
    for name, source in (
        ("trails", TRAILS),
        ("indices", INDICES),
        ("qualifiers", QUALIFIERS),
    ):
        copies[name] = tmp_path / f"{name}.csv"
        copies[name].write_bytes(source.read_bytes())
    args = [item for name, path in copies.items() for item in (f"--{name}", str(path))]
    for source in copies.values():
        link = tmp_path / f"link-{source.name}"
        try:
            os.link(source, link)
        except OSError:
            pytest.skip("hard links are not available on this file system")
        before = source.read_bytes()
        assert main([*args, "--output", str(link)]) == 2
        assert source.read_bytes() == before


def test_published_table_matches_held_inputs() -> None:
    """Every column, derived arithmetic included, equals a rebuild from held inputs."""
    with Path("reports/cost/sanction_vs_outturn.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == COLUMNS
        published = list(reader)
    assert published == build_outturn_checks(TRAILS, INDICES, QUALIFIERS)
