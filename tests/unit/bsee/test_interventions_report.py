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
        code_commit="CODECOMMIT",
    ).read_text(encoding="utf-8")
    folder = "examples/bsee/interventions_by_depth"
    assert f"/blob/DATACOMMIT/{folder}/output/rates.csv" in page
    assert f"/blob/CHARTCOMMIT/{folder}/output/05_well_life.png" in page
    assert f"/blob/DATACOMMIT/{folder}/output/05_well_life.png" not in page
    # The study link and the reproduction prompt name the code commit: the
    # builder and scripts that made this page, not the commit of the charts.
    assert f"/tree/CODECOMMIT/{folder}" in page
    assert "repository at commit CODECOMMIT" in page
    assert "/tree/CHARTCOMMIT/" not in page
    assert "/tree/DATACOMMIT/" not in page
    assert "commit CHARTCOMMIT" not in page
    assert "events 2005 to 2026)" in page


def test_article_refuses_a_chart_pin_without_a_code_pin(tmp_path):
    import build_article

    with pytest.raises(ValueError, match="code commit"):
        build_article.build(
            out=EXAMPLE / "output",
            page=tmp_path / "page.html",
            build_commit="DATACOMMIT",
            chart_commit="CHARTCOMMIT",
        )
    assert not (tmp_path / "page.html").exists()


def test_article_rejects_event_ages_with_mixed_windows(output_copy, tmp_path):
    import build_article

    ages = pd.read_csv(output_copy / "life_cycle_event_ages.csv")
    ages.loc[0, "event_window"] = "1948-2026"
    ages.to_csv(output_copy / "life_cycle_event_ages.csv", index=False)
    with pytest.raises(ValueError, match="more than one window"):
        build_article.build(out=output_copy, page=tmp_path / "page.html")
    assert not (tmp_path / "page.html").exists()


def test_note_refuses_a_summary_without_a_partial_year(output_copy, tmp_path):
    import write_results_note

    # A 31 December snapshot publishes no partial year; the README wording
    # names one, so the note must stop with a stated reason, writing nothing.
    summary = summary_of(output_copy)
    summary["partial_year"] = None
    (output_copy / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    readme = tmp_path / "README.md"
    with pytest.raises(ValueError, match="no partial year"):
        write_results_note.main(out=output_copy, readme=readme)
    assert not readme.exists()


def test_article_states_the_approval_status_assumption(tmp_path):
    import re

    import build_article

    page = build_article.build(
        out=EXAMPLE / "output", page=tmp_path / "page.html"
    ).read_text(encoding="utf-8")
    # The permit table has no approval-status field: the README marks "every
    # row is an approved permit" and the approval-date reading as assumed.
    # The standalone article must carry both, in its counting rules.
    rules = page[page.index('id="appendix-a"') : page.index('id="appendix-b"')]
    text = " ".join(re.sub(r"<[^>]+>", " ", rules).split())
    assert "no separate approval-status field" in text
    assert "Assumed, to be confirmed" in text
    assert "ACC_STATUS_DATE" in text
    assert "approval date" in text


def test_note_runs_without_dataframe_map(output_copy, tmp_path, monkeypatch):
    import write_results_note

    # requirements.txt allows pandas 2.0, which has no DataFrame.map (added in
    # 2.1.0); the note must use API that the declared minimum provides.
    readme = tmp_path / "README.md"
    write_results_note.main(out=output_copy, readme=readme)
    expected = readme.read_bytes()
    readme.unlink()
    monkeypatch.delattr(pd.DataFrame, "map", raising=False)  # absent before 2.1
    write_results_note.main(out=output_copy, readme=readme)
    assert readme.read_bytes() == expected


def test_article_refuses_a_summary_without_a_partial_year(output_copy, tmp_path):
    import build_article

    # The figure 1 notes name the partial year; a 31 December snapshot has
    # none, so the build stops with a stated reason and writes no page.
    summary = summary_of(output_copy)
    summary["partial_year"] = None
    (output_copy / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="no partial year"):
        build_article.build(out=output_copy, page=tmp_path / "page.html")
    assert not (tmp_path / "page.html").exists()


# Review copy r4 fix-up: pre-review gate findings -------------------------------


@pytest.fixture(scope="module")
def r4_page(tmp_path_factory):
    import build_article

    page = tmp_path_factory.mktemp("r4") / "page.html"
    build_article.build(
        out=EXAMPLE / "output",
        page=page,
        build_commit="DATACOMMIT",
        chart_commit="CHARTCOMMIT",
        code_commit="CODECOMMIT",
        build_date="2026-11-14",
    )
    return page.read_text(encoding="utf-8")


def plain(fragment):
    import html
    import re

    fragment = re.sub(r'src="data:[^"]*"', "", fragment)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def between(page, start, end):
    begin = page.index(start)
    return page[begin : page.index(end, begin)]


def test_article_embeds_the_deckhand_opening_graphic(r4_page):
    import base64
    import re

    assets = EXAMPLE / "article" / "assets"
    for name in ["opening.svg", "opening.png", "opening-alt.txt"]:
        assert (assets / name).is_file(), name
    alt = (assets / "opening-alt.txt").read_text(encoding="utf-8").strip()
    png = base64.b64encode((assets / "opening.png").read_bytes()).decode()
    slot = re.search(r'<div id="deckhand-opening"[^>]*>(.*?)</div>', r4_page, re.S)
    assert slot, "opening slot missing"
    assert 'aria-hidden="true"' not in slot.group(0)
    img = slot.group(1)
    assert f'src="data:image/png;base64,{png}"' in img
    assert f'alt="{alt}"' in img
    # The graphic heads the page, before the masthead and the title.
    assert r4_page.index('id="deckhand-opening"') < r4_page.index('class="masthead"')


def test_section_1_names_our_scenarios_and_the_derived_day_rate(r4_page):
    s1 = plain(between(r4_page, 'id="s1"', 'id="s2"'))
    page = plain(r4_page)
    assert "study's cost cases" not in page
    assert "our scenarios, built from TAP-738 day rates and BOEM durations" in s1
    for number in ["0.53", "0.98", "4.7", "9.4"]:
        assert number in s1
    assert (
        "USD 64,530 a day, derived from a TAP-738 P&A spread "
        "(Table 8-2: USD 225,856 over 84 hours)"
    ) in page


def test_cost_method_and_figure_6_state_rig_mobilisation_is_excluded(r4_page):
    rule = "Rig mobilisation is excluded from the drillship or semisubmersible row"
    appendix_b = plain(between(r4_page, 'id="appendix-b"', 'id="appendix-c"'))
    figure_6 = plain(between(r4_page, 'id="figure-6"', "</figure>"))
    assert rule in appendix_b
    assert rule in figure_6
    assert "mobilisation is added only for the platform spreads" in appendix_b
    assert "add mobilisation:" not in appendix_b


def test_version_line_carries_the_build_date_and_the_data_date(r4_page):
    version = plain(between(r4_page, '<p class="version">', "</p>"))
    assert version.startswith(
        "Revision 4, 14 November 2026. Data: BSEE raw well data, files of "
        "13 November 2026."
    )


def test_takeaway_compares_heavy_and_light_ages_and_separates_populations(r4_page):
    takeaway = plain(between(r4_page, "<blockquote>", "</blockquote>"))
    assert "rig-based" not in takeaway
    assert "median 13.3 years" in takeaway and "24.1 years" in takeaway
    assert "hydraulic workover" in takeaway
    assert "23.0" in takeaway and "33.0" in takeaway
    assert "different populations" in takeaway
    assert "1,500 m and deeper" in takeaway
    assert "deeper than 1,500 m" not in takeaway


def test_sign_off_names_prepared_checked_and_approved(r4_page):
    assert (
        '<p class="signoff">Prepared: Petroleum Engineer Deckhand, Data Analyst '
        "Deckhand. Checked: Editor Deckhand. Approved: Vamsee Achanta (pending, "
        "C6 review copy r4).</p>"
    ) in r4_page


def test_references_follow_the_sign_off(r4_page):
    import build_article

    refs = between(r4_page, 'id="references"', 'id="appendix-a"')
    assert r4_page.index('class="signoff"') < r4_page.index('id="references"')
    for url in [
        build_article.BOEM,
        build_article.TAP738,
        "https://espis.boem.gov/final%20reports/5179.pdf",
        "https://www.data.bsee.gov/Main/RawData.aspx",
        "https://www.data.bsee.gov/Well/eWellAPM/Default.aspx",
    ]:
        assert f'href="{url}"' in refs, url
    text = plain(refs)
    assert "Gulf of Mexico OCS Oil and Gas Lease Sales 2017-2022" in text
    assert "Decommissioning Methodology and Cost Evaluation" in text
    assert "July 2015" in text
    assert "MAG-PLAN Alaska Update" in text


@pytest.mark.parametrize("number", [1, 2, 3, 5])
def test_a_lead_in_sentence_comes_before_figures_1_2_3_and_5(r4_page, number):
    before = r4_page[: r4_page.index(f'<figure id="figure-{number}"')]
    last_paragraph = before[before.rindex("<p>") :]
    assert plain(last_paragraph).startswith(f"Figure {number} shows ")


def test_readable_part_is_800_words_or_fewer_and_keeps_the_owner_order(r4_page):
    import build_article

    assert build_article.readable_words(r4_page) <= 800
    order = [
        'id="s1">1. Why interventions matter',
        'id="s2">2. The life of a Gulf of Mexico well',
        'id="figure-1"',
        'id="figure-3"',
        "<h3>What the rate means</h3>",
        'id="s5">5. Abandonment',
    ]
    positions = [r4_page.index(marker) for marker in order]
    assert positions == sorted(positions)
    assert "next article" in plain(between(r4_page, 'id="s5"', 'id="charts"'))


def test_readable_words_counts_sections_without_figures_or_table():
    import build_article

    page = (
        '<h2 id="s1">1. One two</h2><p>three four</p>'
        '<figure id="figure-1"><img alt="x y z"><figcaption>a b c</figcaption></figure>'
        '<div class="tablewrap"><table><tr><td>d e</td></tr></table></div>'
        '<h2 id="charts">Charts</h2><p>not counted</p>'
    )
    assert build_article.readable_words(page) == 5


def test_build_stops_when_the_readable_part_is_too_long(tmp_path, monkeypatch):
    import build_article

    monkeypatch.setattr(build_article, "READABLE_WORD_LIMIT", 100)
    page = tmp_path / "page.html"
    with pytest.raises(ValueError, match="readable part"):
        build_article.build(out=EXAMPLE / "output", page=page)
    assert not page.exists()


def test_shelf_is_defined_at_first_use_and_the_quote_is_the_sources(r4_page):
    body = plain(r4_page[r4_page.index("<body>") :])
    first = body.index("shelf")
    assert body[first:].startswith("shelf (under 100 m water depth)")
    assert "traditionally" not in body
    assert '"require[s] that a rig be moved on location"' in body


def test_changes_panel_comes_from_changes_md_and_is_hidden_in_print(r4_page):
    import re

    import build_article

    items = build_article.changes_since_r2()
    assert len(items) >= 5
    panel = between(r4_page, '<aside id="changes"', "</aside>")
    assert 'class="no-print"' in panel
    assert re.search(
        r"@media print\s*\{[^}]*\.no-print\s*\{\s*display:\s*none", r4_page
    )
    text = plain(panel)
    for item in items:
        assert plain(item) in text
    assert r4_page.index('<aside id="changes"') < r4_page.index('id="s1"')


def test_changes_panel_refuses_a_changes_file_without_the_section(tmp_path):
    import build_article

    changes = tmp_path / "changes.md"
    changes.write_text(
        "# Article revisions\n\n## Revision 4\n\n- x\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="What changed since revision 2"):
        build_article.changes_since_r2(changes)


def test_charts_carry_no_title_that_repeats_the_page_caption(output_copy, monkeypatch):
    import matplotlib.figure
    import plot_charts
    import plot_life_cycle

    seen = {}
    save = matplotlib.figure.Figure.savefig

    def record(fig, fname, *args, **kwargs):
        title = fig._suptitle.get_text() if fig._suptitle is not None else ""
        panels = [ax.get_title(loc="left") for ax in fig.axes]
        seen[Path(str(fname)).stem] = (title, panels)
        return save(fig, fname, *args, **kwargs)

    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", record)
    plot_charts.plot(output_copy)
    plot_life_cycle.plot(output_copy)
    assert sorted(seen) == sorted(STEMS)
    for stem, (title, panels) in seen.items():
        assert title == "", f"{stem} carries the title {title!r}"
        for panel in panels:
            assert "permits to modify" not in panel, f"{stem}: {panel!r}"


def test_reusable_prompt_is_the_last_appendix_and_the_link_reaches_it(r4_page):
    import re

    heads = [plain(h) for h in re.findall(r"<h2\b[^>]*>.*?</h2>", r4_page, re.S)]
    assert heads[-1] == "Appendix D. Reusable prompt"
    assert heads[-2] == "Appendix C. Detail behind sections 2 and 3"
    assert '<a href="#appendix-d">reusable prompt</a>' in r4_page
    assert '<h2 id="appendix-d">Appendix D. Reusable prompt</h2>' in r4_page


# Fix round 2: the 33.0-year value is an age at approval, not a well count ------


def test_takeaway_states_the_33_year_median_counts_approvals_not_wells(r4_page):
    takeaway = plain(between(r4_page, "<blockquote>", "</blockquote>"))
    assert "wells abandoned under approvals" not in takeaway
    assert "33.0-year median age at permanent-abandonment approval" in takeaway
    assert "17,904 permanent-abandonment approvals" in takeaway
    assert "counts approvals, not wells" in takeaway
    # The 23.0-year life is the median over the abandoned development wells
    # with an established life (fix round 3 states both counts; see below).
    assert "16,860 development wells abandoned so far" in takeaway


def test_section_2_gives_abandonment_ages_as_ages_at_approval(r4_page):
    s2 = plain(between(r4_page, 'id="s2"', 'id="s3"'))
    assert "permanent abandonment at 33.0" not in s2
    assert "permanent-abandonment approval at 33.0" in s2
    assert "temporary-abandonment approval at 32.3" in s2
    assert "count approvals, not wells" in s2


def test_takeaway_approval_count_comes_from_the_event_ages_table(tmp_path, output_copy):
    import build_article

    ages = pd.read_csv(output_copy / "life_cycle_event_ages.csv")
    pa = ages.well_type.eq("development") & ages.stage.eq("permanent abandonment")
    ages.loc[pa, "events"] = 12345
    ages.to_csv(output_copy / "life_cycle_event_ages.csv", index=False)
    page = tmp_path / "page.html"
    build_article.build(out=output_copy, page=page, build_date="2026-11-14")
    takeaway = plain(
        between(page.read_text(encoding="utf-8"), "<blockquote>", "</blockquote>")
    )
    assert "12,345 permanent-abandonment approvals" in takeaway


def test_opening_graphic_carries_this_title_and_no_chart():
    import re

    import build_article

    assets = EXAMPLE / "article" / "assets"
    svg = (assets / "opening.svg").read_text(encoding="utf-8")
    alt = (assets / "opening-alt.txt").read_text(encoding="utf-8").strip()
    r2_title = "approvals each year and cost per event by access type"
    assert "<image" not in svg, "no chart picture inside the graphic"
    assert r2_title not in svg and r2_title not in alt
    assert "chart" not in alt
    words = [
        w
        for text in re.findall(r'<text[^>]*class="slot-title"[^>]*>([^<]*)</text>', svg)
        for w in text.split()
    ]
    assert " ".join(words) == build_article.TITLE
    assert build_article.TITLE in alt
    assert f"<h1>{build_article.TITLE}</h1>" in (
        EXAMPLE / "article" / "gom-well-interventions-r4.html"
    ).read_text(encoding="utf-8")


# Fix round 3: both counts behind the 23.0-year life ---------------------------


def test_takeaway_states_abandoned_wells_and_wells_with_an_established_life(r4_page):
    takeaway = plain(between(r4_page, "<blockquote>", "</blockquote>"))
    assert (
        "16,860 development wells abandoned so far, of which 16,858 have an "
        "established life" in takeaway
    )
    assert "the 23.0-year median is over those 16,858" in takeaway
    assert "median of 16,860" not in takeaway
    assert "life of the 16,860" not in takeaway


def test_established_life_count_comes_from_the_life_table(tmp_path, output_copy):
    import build_article

    years = pd.read_csv(output_copy / "life_cycle_life_years.csv")
    row = years.group.eq("development wells") & years.status.eq("permanently abandoned")
    years.loc[row, "life_not_established"] = 5
    years.to_csv(output_copy / "life_cycle_life_years.csv", index=False)
    page = tmp_path / "page.html"
    build_article.build(out=output_copy, page=page, build_date="2026-11-14")
    takeaway = plain(
        between(page.read_text(encoding="utf-8"), "<blockquote>", "</blockquote>")
    )
    assert "16,860 development wells abandoned so far, of which 16,855" in takeaway
    assert "over those 16,855" in takeaway


# Fix round 3: the reproduction prompt pins the builder that made the page -----

GIT_BINDINGS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")


def git_env():
    """The environment without inherited Git repository bindings."""
    import os

    return {k: v for k, v in os.environ.items() if k not in GIT_BINDINGS}


def git(cwd, *args, binary=False):
    import subprocess

    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(cwd), *args],
        capture_output=True,
        env=git_env(),
        check=True,
    )
    return result.stdout if binary else result.stdout.decode().strip()


def published_pins(page):
    """The data, chart and code pins and the revision date of a built page."""
    import re
    from datetime import datetime

    folder = "examples/bsee/interventions_by_depth"
    blob = r"/blob/([0-9a-f]{40})/" + folder + r"/output/[^\"]+\."
    data = set(re.findall(blob + r"csv\"", page))
    charts = set(re.findall(blob + r"(?:png|svg)\"", page))
    study = set(re.findall(r"/tree/([0-9a-f]{40})/" + folder + '"', page))
    prompt = re.findall(r"repository at commit ([0-9a-f]{40}), folder " + folder, page)
    revision = re.search(r"Revision \d+, (\d{1,2} [A-Z][a-z]+ \d{4})\.", page)
    assert len(data) == 1, f"data pins {data}"
    assert len(charts) == 1, f"chart pins {charts}"
    assert len(prompt) == 1, f"prompt pins {prompt}"
    assert study == set(prompt), f"study link {study} against prompt {prompt}"
    assert revision, "revision line missing"
    return {
        "data": data.pop(),
        "chart": charts.pop(),
        "code": prompt[0],
        "date": datetime.strptime(revision.group(1), "%d %B %Y").date().isoformat(),
    }


def test_published_prompt_pins_the_builder_that_made_the_page(tmp_path):
    """The prompt's code pin holds today's scripts and rebuilds the page as committed.

    Fails when build_article.py, any other study script, changes.md or the
    opening graphic changed after the commit the page names, and when the
    builder at that commit, run on the tables at that commit with the page's
    own pins and date, does not give the committed page byte for byte.
    """
    import io
    import subprocess
    import sys
    import tarfile

    folder = "examples/bsee/interventions_by_depth"
    committed = (EXAMPLE / "article" / "gom-well-interventions-r4.html").read_bytes()
    pins = published_pins(committed.decode("utf-8"))
    code = pins["code"]
    assert pins["chart"] != pins["data"]
    git(EXAMPLE, "cat-file", "-e", f"{code}^{{commit}}")

    # 1. Nothing the builder runs or reads, besides the tables, changed after
    #    the pinned commit.
    inputs = ["*.py", "article/changes.md", "article/assets"]
    changed = git(EXAMPLE, "diff", "--name-only", code, "--", *inputs)
    assert changed == "", f"changed after the prompt's code pin {code[:8]}: {changed}"
    assert (
        git(EXAMPLE, "ls-files", "--others", "--exclude-standard", "--", "*.py") == ""
    )

    # 2. The tables at the code pin are the tables at the data pin.
    tables = git(EXAMPLE, "diff", "--name-only", pins["data"], code, "--", "output")
    assert not [
        t
        for t in tables.splitlines()
        if t.endswith((".csv", ".json")) and not t.endswith("verification.json")
    ], tables

    # 3. The pinned builder, on the pinned tree, rebuilds the committed page.
    #    git archive run in a subdirectory keeps only that subdirectory, so it
    #    runs from the top of the repository.
    tree = tmp_path / "pinned"
    top = git(EXAMPLE, "rev-parse", "--show-toplevel")
    archive = git(top, "archive", "--format=tar", f"{code}:{folder}", binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        names = tar.getnames()
        assert "build_article.py" in names, "the code pin holds no builder"
        tar.extractall(tree, filter="data")
    rebuilt = tmp_path / "rebuilt.html"
    run = subprocess.run(
        [
            sys.executable,
            "build_article.py",
            "--build-commit",
            pins["data"],
            "--chart-commit",
            pins["chart"],
            "--code-commit",
            code,
            "--build-date",
            pins["date"],
            "--page",
            str(rebuilt),
        ],
        cwd=tree,
        env=git_env(),
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    page = rebuilt.read_bytes()
    assert b"age at permanent-abandonment approval" in page
    assert b"wells abandoned under approvals" not in page
    assert page == committed, "the pinned builder does not reproduce the page"


def test_last_code_commit_is_the_newest_change_to_the_scripts(tmp_path):
    import build_article

    repo = tmp_path / "repo"
    study = repo / "study"
    (study / "output").mkdir(parents=True)
    git(tmp_path, "init", "-q", str(repo))

    def commit(message):
        git(repo, "add", "-A")
        git(
            repo,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--no-verify",
            "-q",
            "-m",
            message,
        )
        return git(repo, "rev-parse", "HEAD")

    (study / "build_article.py").write_text("print(1)\n", encoding="utf-8")
    (study / "output" / "rates.csv").write_text("a\n1\n", encoding="utf-8")
    first = commit("scripts")
    (study / "output" / "rates.csv").write_text("a\n2\n", encoding="utf-8")
    commit("tables only")
    assert build_article.last_code_commit(study) == first

    (study / "report_text.py").write_text("X = 1\n", encoding="utf-8")
    second = commit("a second script")
    assert build_article.last_code_commit(study) == second

    (study / "build_article.py").write_text("print(2)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="uncommitted"):
        build_article.last_code_commit(study)


def test_command_line_defaults_the_code_pin_to_the_last_script_commit(
    tmp_path, monkeypatch
):
    import build_article

    monkeypatch.setattr(build_article, "last_code_commit", lambda folder: "GITCODE")
    page = tmp_path / "page.html"
    build_article.main(
        [
            "--build-commit",
            "DATACOMMIT",
            "--chart-commit",
            "CHARTCOMMIT",
            "--build-date",
            "2026-11-14",
            "--page",
            str(page),
        ]
    )
    text = page.read_text(encoding="utf-8")
    assert "repository at commit GITCODE" in text
    assert "/tree/GITCODE/" in text
