"""Offline checks for the interventions report, charts and verifier.

The tests copy the delivered output tables to a temporary directory; they
never read raw archives or the network.
"""

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/bsee/interventions_by_depth"
sys.path.insert(0, str(EXAMPLE))
from count_interventions import BANDS  # noqa: E402

STEMS = [
    "01_approved_interventions",
    "02_rates_per_standing_well",
    "03_cost_per_event",
    "04_unit_types_by_depth",
    "05_well_life",
    "06_well_life_stages",
]


@pytest.fixture
def output_copy(tmp_path):
    out = tmp_path / "output"
    shutil.copytree(EXAMPLE / "output", out)
    return out


def summary_of(out):
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", [f"{s}{x}" for s in STEMS for x in (".png", ".svg")])
def test_verifier_requires_every_chart_before_writing_a_receipt(output_copy, name):
    import verify_outputs

    (output_copy / "verification.json").unlink()
    (output_copy / name).unlink()
    with pytest.raises(AssertionError, match="missing chart"):
        verify_outputs.verify(output_copy)
    assert not (output_copy / "verification.json").exists()


def test_note_headline_follows_consistent_aggregates(output_copy, tmp_path):
    import write_results_note

    last = summary_of(output_copy)["last_full_year"]
    rates = pd.read_csv(output_copy / "rates.csv")
    work = rates.year.eq(last) & rates.family.eq("well work")
    before = int(rates.loc[work, "permits"].sum())
    abandonment = int(
        rates.loc[rates.year.eq(last) & rates.family.eq("abandonment"), "permits"].sum()
    )
    rates.loc[work & rates.band.eq(BANDS[0]), "permits"] += 100
    rates.to_csv(output_copy / "rates.csv", index=False)
    mapping = pd.read_csv(output_copy / "code_mapping.csv")
    row = mapping.primary_code.eq("WORKOVER") & mapping.group.eq(
        "workover and recompletion"
    )
    mapping.loc[row, "last_full_year_permits"] += 100
    mapping.to_csv(output_copy / "code_mapping.csv", index=False)
    readme = tmp_path / "README.md"
    write_results_note.main(out=output_copy, readme=readme)
    text = readme.read_text(encoding="utf-8")
    assert (
        f"In {last}, **{before + 100:,} well-work approvals + {abandonment:,} "
        f"abandonment approvals = {before + 100 + abandonment:,} events**"
    ) in text
    assert f"{before:,} well-work approvals" not in text
    assert "31 Oct" not in text


def test_note_rejects_aggregates_that_do_not_reconcile(output_copy, tmp_path):
    import write_results_note

    last = summary_of(output_copy)["last_full_year"]
    rates = pd.read_csv(output_copy / "rates.csv")
    shallow = rates.year.eq(last) & rates.band.eq(BANDS[0])
    rates.loc[shallow & rates.family.eq("well work"), "permits"] += 100
    rates.to_csv(output_copy / "rates.csv", index=False)
    readme = tmp_path / "README.md"
    with pytest.raises(ValueError, match="reconciliation"):
        write_results_note.main(out=output_copy, readme=readme)
    assert not readme.exists()


def test_note_and_charts_reject_a_changed_year(output_copy, tmp_path):
    import plot_charts
    import write_results_note

    summary = summary_of(output_copy)
    summary["last_full_year"] -= 1
    summary["partial_year"] -= 1
    (output_copy / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    charts = {p.name: p.read_bytes() for p in output_copy.glob("0*")}
    readme = tmp_path / "README.md"
    with pytest.raises(ValueError, match="selects"):
        write_results_note.main(out=output_copy, readme=readme)
    assert not readme.exists()
    with pytest.raises(ValueError, match="selects"):
        plot_charts.plot(output_copy)
    assert {p.name: p.read_bytes() for p in output_copy.glob("0*")} == charts


def synthetic_primary():
    rows = []
    for year, other, workover in [
        (2019, 300, 100),
        (2020, 200, 100),
        (2021, 50, 300),
        (2022, 0, 300),
        (2023, 0, 300),
        (2024, 0, 300),
    ]:
        rows += [(year, "OTHER", other), (year, "WORKOVER", workover)]
    frame = pd.DataFrame(rows, columns=["year", "APM_OP_CD", "approvals"])
    return frame[frame.approvals.gt(0)]


def test_coding_change_text_is_derived_from_the_table():
    from report_text import coding_caption, coding_sentence

    primary = synthetic_primary()
    assert coding_sentence(primary, 2019, 2024) == (
        "Primary OTHER approvals numbered 200–300 per year in 2019–2020, then "
        "50 in 2021 and zero from 2022, while WORKOVER approvals averaged 100 "
        "per year in 2019–2020 and 300 in 2021–2024."
    )
    assert coding_caption(primary, 2019, 2024).startswith(
        "OTHER fell from 200-300/year (2019-2020) to 0 from 2022"
    )


def test_cost_caption_counts_follow_the_selected_year():
    from report_text import permanent_caption

    counts = pd.DataFrame(
        {
            "year": [2023] * 3 + [2024] * 3,
            "group": [
                "temporary abandonment",
                "permanent abandonment",
                "abandonment unspecified",
            ]
            * 2,
            "permits": [1, 2, 3, 10, 20, 30],
        }
    )
    assert "(20 of 60 abandonment approvals in 2024)" in permanent_caption(counts, 2024)
    assert "(2 of 6 abandonment approvals in 2023)" in permanent_caption(counts, 2023)


def test_selection_check_accepts_pooled_periods_and_rejects_other_years():
    from report_text import check_selection

    summary = {"first_full_year": 2005, "last_full_year": 2024}
    assert check_selection(summary, {"t": ["2024", "2020-2024"]}) == 2024
    with pytest.raises(ValueError, match="selects 2024"):
        check_selection(summary, {"t": ["2025", "2021-2025"]})


def test_article_pins_data_links_and_chart_links_to_their_own_commits(tmp_path):
    import build_article

    page = build_article.build(
        out=EXAMPLE / "output",
        page=tmp_path / "page.html",
        build_commit="DATACOMMIT",
        chart_commit="CHARTCOMMIT",
    ).read_text(encoding="utf-8")
    folder = "examples/bsee/interventions_by_depth"
    assert f"/blob/DATACOMMIT/{folder}/output/rates.csv" in page
    assert f"/blob/CHARTCOMMIT/{folder}/output/05_well_life.png" in page
    assert f"/blob/DATACOMMIT/{folder}/output/05_well_life.png" not in page
    assert f"/tree/CHARTCOMMIT/{folder}" in page
    assert "repository at commit CHARTCOMMIT" in page
    assert "events 2005 to 2026)" in page


def test_article_rejects_event_ages_with_mixed_windows(output_copy, tmp_path):
    import build_article

    ages = pd.read_csv(output_copy / "life_cycle_event_ages.csv")
    ages.loc[0, "event_window"] = "1948-2026"
    ages.to_csv(output_copy / "life_cycle_event_ages.csv", index=False)
    with pytest.raises(ValueError, match="more than one window"):
        build_article.build(out=output_copy, page=tmp_path / "page.html")
    assert not (tmp_path / "page.html").exists()
