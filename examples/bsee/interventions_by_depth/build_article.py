"""Build the article page (revision 3) from the delivered tables and charts.

Every count, share, year and date in the page is read from output/*.csv,
output/*.json or cost_table.csv. Quoted source text carries its page. The page
embeds the PNG charts, so it opens offline. Run after the count, life-cycle,
cost and chart scripts; --build-commit names the commit that holds the data.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
from pathlib import Path

import pandas as pd
from report_text import CODING_CHANGE_YEAR, check_selection, long_date

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
REVISION = 3
PAGE = ROOT / "article" / f"gom-well-interventions-r{REVISION}.html"
REPO = "https://github.com/vamseeachanta/worldenergydata"
FOLDER = "examples/bsee/interventions_by_depth"
BOEM = (
    "https://www.boem.gov/sites/default/files/environmental-stewardship/"
    "Environmental-Assessment/NEPA/BOEM-EIS-2016-018-v1.pdf"
)
TAP738 = "https://www.bsee.gov/sites/bsee.gov/files/tap-technical-assessment-program/738aa1.pdf"
BANDS = ["under 100 m", "100 to 500 m", "500 to 1500 m", "1500 m and deeper"]
BAND_TEXT = {
    "under 100 m": "under 100 m",
    "100 to 500 m": "100 to 500 m",
    "500 to 1500 m": "500 to 1,500 m",
    "1500 m and deeper": "1,500 m and deeper",
}
MASTHEAD = (
    "The Deckhand Chronicles is AceEngineer's newsletter. "
    "We help build AI into everyday engineering work."
)
CLOSING = (
    "If you have run your own analysis, see a way to improve this one, or have an "
    "idea for a future issue, write to support@aceengineer.com. We read every reply "
    "and credit the ideas we use and provide results we obtained."
)
HASHTAGS = (
    "#GulfOfMexico #OffshoreWells #WellIntervention #WellLifeCycle "
    "#PetroleumEngineering #OpenData"
)
# Public text must not carry internal or machine wording.
FORBIDDEN = re.compile(
    r"\b(?:lane|desk|seat|rds02|ws014|ace-linux|vamseea)\b|[A-Z]:\\|/mnt/", re.I
)


def n(value):
    return f"{int(round(value)):,}"


def pct(value):
    return f"{value:.0f}%"


def yrs(value):
    return f"{value:.1f}"


def musd(value):
    x = value / 1e6
    return f"{x:.2g}" if x < 10 else f"{x:.0f}"


def esc(text):
    return html.escape(text, quote=False)


def file_link(name, label=None, commit="BUILD"):
    return f'<a href="{REPO}/blob/{commit}/{FOLDER}/output/{name}">{esc(label or name)}</a>'


class Data:
    """The tables the page reads, with the selection check of the README."""

    def __init__(self, out=OUT):
        self.summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        self.life = json.loads(
            (out / "life_cycle_summary.json").read_text(encoding="utf-8")
        )
        if self.life["file_date"] != self.summary["file_date"]:
            raise ValueError("life-cycle tables come from a different snapshot")
        self.units = pd.read_csv(out / "unit_type_shares.csv")
        self.last = check_selection(self.summary, {"units": self.units.period})
        self.first = int(self.summary["first_full_year"])
        self.date = self.summary["file_date"]
        self.rates = pd.read_csv(out / "rates.csv")
        self.counts = pd.read_csv(out / "counts_by_year_band_group.csv")
        self.years = pd.read_csv(out / "life_cycle_life_years.csv").set_index(
            ["group", "status"]
        )
        self.reach = pd.read_csv(out / "life_cycle_stage_reach.csv").set_index(
            ["group", "stage"]
        )
        self.ages = pd.read_csv(out / "life_cycle_event_ages.csv").set_index(
            ["well_type", "stage"]
        )
        self.weights = pd.read_csv(out / "intervention_weight_by_year.csv")
        self.checks = pd.read_csv(out / "life_cycle_reconciliation.csv").set_index(
            "stage"
        )
        self.cost = pd.read_csv(out / "cost_table.csv").set_index("scenario_id")
        self.durations = pd.read_csv(out / "permit_duration_estimates.csv")
        self.distinct = pd.read_csv(out / "approvals_per_distinct_well.csv")

    def cohort(self, kind):
        return f"{kind} wells first drilled {self.first}-{self.last}"


def headline(d):
    r = d.rates[d.rates.year.eq(d.last) & d.rates.band.isin(BANDS)]
    work = int(r.loc[r.family.eq("well work"), "permits"].sum())
    aban = int(r.loc[r.family.eq("abandonment"), "permits"].sum())
    rate = r.set_index(["band", "family"]).per_100_standing_wells
    return dict(work=work, aban=aban, total=work + aban, rate=rate)


def totals_by_year(d):
    t = d.rates.groupby(["year", "family"])[["permits", "standing_wells"]].sum()
    t["per100"] = t.permits / t.standing_wells * 100
    return t


def weight_trend(d):
    """Light and heavy rates, from the first year in which at least three in
    four well-work approvals name a classifiable unit."""
    w = d.weights[d.weights.year.le(d.last)].pivot(
        index="year", columns="weight", values="approvals"
    )
    named = (w.light + w.heavy) / w.sum(axis=1)
    ok = named.ge(0.75)
    start = next(y for y in ok.index if ok.loc[y:].all())
    rate = d.weights[d.weights.year.between(start, d.last)].pivot(
        index="year", columns="weight", values="per_100_standing_wells"
    )
    early = rate.loc[start : CODING_CHANGE_YEAR - 2]
    late = rate.loc[d.last - 2 : d.last]
    return dict(
        start=start,
        early=(start, CODING_CHANGE_YEAR - 2),
        late=(d.last - 2, d.last),
        light_range=(rate.light.min(), rate.light.max()),
        heavy_range=(rate.heavy.min(), rate.heavy.max()),
        light_early=early.light.mean(),
        light_late=late.light.mean(),
        heavy_early=early.heavy.mean(),
        heavy_late=late.heavy.mean(),
        light_last=rate.loc[d.last, "light"],
        heavy_last=rate.loc[d.last, "heavy"],
        named_last=named.loc[d.last] * 100,
    )


def per_well(d, kind):
    g = d.cohort(kind)
    r = d.reach.loc[g]
    interventions = [
        "light intervention",
        "heavy intervention",
        "intervention, light or heavy not established",
    ]
    return dict(
        wells=int(r.loc["drilling", "wells"]),
        bores=r.loc["drilling", "events_per_well"]
        + r.loc["sidetrack or bypass", "events_per_well"],
        sidetrack_share=r.loc["sidetrack or bypass", "share_percent"],
        light=r.loc["light intervention", "events_per_well"],
        heavy=r.loc["heavy intervention", "events_per_well"],
        unclassified=r.loc[interventions[2], "events_per_well"],
        interventions=sum(r.loc[s, "events_per_well"] for s in interventions),
        any_light=r.loc["light intervention", "share_percent"],
        any_heavy=r.loc["heavy intervention", "share_percent"],
        ta=r.loc["temporary abandonment", "events_per_well"],
        pa=r.loc["permanent abandonment", "events_per_well"],
        abandoned=r.loc["permanently abandoned (bore status)", "share_percent"],
        life_pa=d.years.loc[(g, "permanently abandoned"), "median_years"],
        age_standing=d.years.loc[(g, "standing"), "median_years"],
    )


def share_text(part, whole):
    """A plain fraction for a share, checked against the value."""
    share = part / whole
    for text, value in [("Three quarters", 0.75), ("Two thirds", 2 / 3), ("Half", 0.5)]:
        if abs(share - value) < 0.02:
            return text
    return f"{share:.0%}"


def figure(name, number, title, notes, alt):
    items = "".join(f"<li>{note}</li>" for note in notes)
    return (
        f'<figure id="figure-{number}"><img src="@@IMAGE:{name}@@" alt="{esc(alt)}">'
        f'<figcaption><p class="fig-title">Figure {number}. {esc(title)}</p>'
        f'<ol class="notes">{items}</ol></figcaption></figure>'
    )


def table(headers, rows, number, title, notes):
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(str(c))}</td>" for c in row) + "</tr>"
        for row in rows
    )
    items = "".join(f"<li>{note}</li>" for note in notes)
    return (
        f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
        f'<p class="fig-title">Table {number}. {esc(title)}</p>'
        f'<ol class="notes">{items}</ol></div>'
    )


def build(out=OUT, page=PAGE, build_commit="analysis/gom-interventions-by-depth"):
    d = Data(out)
    h = headline(d)
    t = totals_by_year(d)
    wt = weight_trend(d)
    dev, exp = per_well(d, "development"), per_well(d, "exploration")
    life = d.life
    yl = d.years
    date_text = long_date(d.date)
    snap = long_date(d.summary["snapshot"])
    cost = d.cost
    rigless, subsea = cost.loc["platform_rigless_work"], cost.loc["subsea_work"]
    age = d.ages
    pa_dev = yl.loc[("development wells", "permanently abandoned")]
    st_dev = yl.loc[("development wells", "standing")]
    pa_exp = yl.loc[("exploration wells", "permanently abandoned")]
    split = d.counts[d.counts.year.eq(d.last)].groupby("group").permits.sum()
    t_first = t.loc[(d.first + 1, "well work")]
    t_last = t.loc[(d.last, "well work")]
    a_last = t.loc[(d.last, "abandonment")]
    early_years = range(d.first + 1, CODING_CHANGE_YEAR - 1)
    work_early = t.loc[[(y, "well work") for y in early_years], "per100"]
    work_late = t.loc[
        [(y, "well work") for y in range(d.last - 2, d.last + 1)], "per100"
    ]
    durations = d.durations.set_index(["band", "event"]).median_est_operation_days

    def link(commit):
        return lambda name, label=None: file_link(name, label, commit)

    fl = link(build_commit)
    study = f"{REPO}/tree/{build_commit}/{FOLDER}"
    prompt_href = "#appendix-c"

    def dev_age(stage):
        return yrs(age.loc[("development", stage), "median_years"])

    def exp_age(stage):
        return yrs(age.loc[("exploration", stage), "median_years"])

    takeaway = (
        f"A Gulf of Mexico development well lives about {yrs(pa_dev.median_years)} years "
        f"from first spud to permanent abandonment (median of {n(pa_dev.wells)} abandoned "
        f"wells). Heavy, rig-based work comes early in that life and light wireline and "
        f"coiled-tubing work later. In {d.last}, BSEE approved {n(h['work'])} "
        f"interventions and {n(h['aban'])} abandonments; per standing well, interventions "
        f"are seven times as frequent in water deeper than 1,500 m as on the shelf "
        f"({yrs(h['rate'][('1500 m and deeper', 'well work')])} against "
        f"{yrs(h['rate'][('under 100 m', 'well work')])} approvals per 100 wells)."
    )
    ratio = (
        h["rate"][("1500 m and deeper", "well work")]
        / h["rate"][("under 100 m", "well work")]
    )
    if not 6.5 <= ratio < 7.5:
        raise ValueError(f"review the 'seven times' takeaway: ratio {ratio:.2f}")
    for light, heavy in [("light_early", "heavy_early"), ("light_late", "heavy_late")]:
        if not 1.6 <= wt[light] / wt[heavy] <= 2.5:
            raise ValueError("review 'about twice as frequent': " + light)
    if (
        not work_late.max() < work_early.min()
        or work_early.max() / work_early.min() > 1.3
    ):
        raise ValueError("review 'held in a narrow band' and 'lower since'")
    if not 60 <= exp["abandoned"] < 72:
        raise ValueError("review 'two in three' exploration wells abandoned")

    sections = []
    # 1. Why interventions matter ---------------------------------------------
    sections.append(f"""
<h2 id="s1">1. Why interventions matter</h2>
<p>A well intervention is any job that goes back into a completed well to keep it working. The
Bureau of Ocean Energy Management (BOEM) describes it this way in its Gulf of Mexico
environmental study: completed and
producing wells "may require periodic reentry that is designed to maintain or restore a desired
flow rate", and the same work is used to test another reservoir zone, recomplete to it, or plug
part of the well (<a href="{BOEM}">BOEM 2016-018</a>, section 3.1.3.5, p. 3-37). The study
expects a producing well to have "seven workovers or other well activities during its lifetime"
(p. 3-38).</p>
<p><strong>Light and heavy.</strong> A light intervention works through the well's existing
tubing with wireline or coiled tubing, from the platform, a liftboat or a vessel, without a rig.
A heavy intervention brings in a rig or a hydraulic workover unit that can pull the tubing out of
the well. On a subsea well, a workover traditionally "require[s] that a rig be moved on location"
(BOEM, p. 3-37); purpose-built intervention vessels that run wireline or coiled tubing are "very
cost effective in decommissioning subsea wells compared to using a drilling rig"
(<a href="{TAP738}">BSEE TAP-738</a>, 2015, p. 5-21).</p>
<p><strong>What it costs and saves.</strong> Most jobs take days, not months: the Gulf median
is 7 days, within a range of 1 day to several months (BOEM, p. 3-37). The day rate is set by
what has to be brought to the well. In the study's cost cases (2015 dollars), a rigless spread
on a shelf platform costs about USD {n(64530)} a day and a light well-work job USD
{musd(rigless.low_usd)} to {musd(rigless.high_usd)} million; a subsea well that needs a
drillship or semisubmersible costs about USD {n(674600)} a day and USD {musd(subsea.low_usd)}
to {musd(subsea.high_usd)} million (TAP-738, Table 8-2, p. 8-12, and p. 8-18; the cost
method is in Appendix B). Choosing the lighter route saves rig days: a typical deepwater
intervention takes 12 to 15 days with a rig against eight to 10 days with a vessel-deployed
wireline system (TAP-738, p. 6-9). An intervention also keeps an existing well producing,
which is the reason operators do one.</p>
<p>This article follows the wells first: how long a Gulf well lasts and what happens to it on
the way (section 2). It then counts the interventions by water depth (section 3) and prices
them by access type (section 4).</p>
""")

    # 2. Life of a well ----------------------------------------------------------
    life_notes = [
        f"One well is one API10 number. Life runs from the first non-cancelled spud of any of its bores to permanent abandonment (every bore that is not superseded by a sidetrack or bypass is permanently abandoned, at the latest such date), or to {date_text} for a well still standing. {n(life['wells_without_first_spud'])} wells without a spud date and {n(life['life_not_established'])} with an abandonment date before spud are left out.",
        "Development and exploration follow the regulator's well type on the original hole. Wells of other or no stated type are counted in the totals and not shown.",
        f"Source: BSEE borehole and permit-to-modify raw data, files of {snap}. Data: {fl('life_cycle_life_histogram.csv')}, {fl('life_cycle_life_years.csv')}.",
    ]
    stage_notes = [
        f"Left: wells first drilled from {d.first} to {d.last}, whose whole life lies inside the permit record ({n(dev['wells'])} development and {n(exp['wells'])} exploration wells). A stage is reached when the well has at least one bore or approved permit of that kind up to {date_text}.",
        "Light: the permit names a wireline unit, coiled tubing, an intervention vessel, a liftboat or a recorded non-rig operation. Heavy: a platform rig, a hydraulic workover or snubbing unit, a jack-up rig, a drillship or a semisubmersible. Not classified: no unit or another unit type is named (Appendix A).",
        f"Right: age of the well, in years after first spud, at every sidetrack or bypass spud and every approved permit from {d.first} to {date_text}, for all wells. Older wells add only their later events, so the panel shows when this work happens across today's wells, not one well followed from birth.",
        f"Data: {fl('life_cycle_stage_reach.csv')}, {fl('life_cycle_event_ages.csv')}; reconciliation with the permit counts: {fl('life_cycle_reconciliation.csv')}.",
    ]
    rows = [
        ["Wells", n(dev["wells"]), n(exp["wells"])],
        [
            "Bores drilled per well (original hole plus sidetracks and bypasses)",
            f"{dev['bores']:.2f}",
            f"{exp['bores']:.2f}",
        ],
        [
            "Light intervention approvals per well",
            f"{dev['light']:.2f}",
            f"{exp['light']:.2f}",
        ],
        [
            "Heavy intervention approvals per well",
            f"{dev['heavy']:.2f}",
            f"{exp['heavy']:.2f}",
        ],
        [
            "Intervention approvals, unit not classified, per well",
            f"{dev['unclassified']:.2f}",
            f"{exp['unclassified']:.2f}",
        ],
        [
            "All intervention approvals per well",
            f"{dev['interventions']:.2f}",
            f"{exp['interventions']:.2f}",
        ],
        [
            "Temporary abandonment approvals per well",
            f"{dev['ta']:.2f}",
            f"{exp['ta']:.2f}",
        ],
        [
            "Permanent abandonment approvals per well",
            f"{dev['pa']:.2f}",
            f"{exp['pa']:.2f}",
        ],
        [
            "Permanently abandoned by " + date_text,
            pct(dev["abandoned"]),
            pct(exp["abandoned"]),
        ],
        [
            "Median life of those abandoned (years)",
            yrs(dev["life_pa"]),
            yrs(exp["life_pa"]),
        ],
        [
            "Median age of those standing (years)",
            yrs(dev["age_standing"]),
            yrs(exp["age_standing"]),
        ],
    ]
    table_notes = [
        f"Wells first drilled from {d.first} to {d.last}; counts run to {date_text}, so a young well has had less time for work than an old one. Per-well figures are means; approvals are permits, not completed jobs, and one job can have more than one approval.",
        f"Totals reconcile with the permit counts of section 3: over {life['window']}, {n(d.checks.loc['intervention, all', 'published_permits'])} intervention, {n(d.checks.loc['temporary abandonment', 'published_permits'])} temporary and {n(d.checks.loc['permanent abandonment', 'published_permits'])} permanent abandonment approvals, of which {n(d.checks.not_assigned.sum())} name a well with no spud date.",
        f"Data: {fl('life_cycle_stage_reach.csv')}, {fl('life_cycle_life_years.csv')}.",
    ]
    sections.append(f"""
<h2 id="s2">2. The life of a Gulf of Mexico well</h2>
<p>BSEE's borehole file lists every well drilled in the Gulf, with its spud date, its sidetracks
and bypasses, and the date each bore was permanently abandoned. Its permit-to-modify file lists
every approved intervention and abandonment from {d.first} on. Together they give each well a
life story. Of the {n(life['dated_wells'])} Gulf wells with a spud date,
{n(life['permanently_abandoned'])} are permanently abandoned and {n(life['standing'])} still
stand.</p>
{figure('05_well_life', 1, 'How long Gulf of Mexico wells last', life_notes,
        'Two histograms of well life in five-year bins: development wells spread from 0 to 60 years, exploration wells mostly under 5 years.')}
<ul>
<li>Exploration wells have short lives: {n(pa_exp.under_1_year)} of the {n(pa_exp.wells)} abandoned exploration wells were plugged within a year of spud (median {yrs(pa_exp.median_years)} years).</li>
<li>Development wells that have been abandoned lived a median {yrs(pa_dev.median_years)} years, the middle half between {yrs(pa_dev.q25_years)} and {yrs(pa_dev.q75_years)} years. The {n(st_dev.wells)} development wells still standing are a median {yrs(st_dev.median_years)} years old.</li>
</ul>
{figure('06_well_life_stages', 2, 'The life of a well, stage by stage', stage_notes,
        'Left: share of wells reaching each stage, development and exploration. Right: median and middle half of well age at each event.')}
{table(['Per well', f'Development, first drilled {d.first}-{d.last}', f'Exploration, first drilled {d.first}-{d.last}'],
       rows, 1, 'A Gulf of Mexico well in numbers', table_notes)}
<h3>The life story of a development well</h3>
<p>A development well is drilled, and {pct(dev['sidetrack_share'])} of those drilled since
{d.first} have been sidetracked or bypassed, usually early (median
{dev_age('sidetrack or bypass')} years after spud). Read across today's wells (Figure 2,
right), heavy work with a rig or workover unit comes next, at a median age of
{dev_age('heavy intervention')} years; {pct(dev['any_heavy'])} of development wells drilled
since {d.first} have had at least one heavy intervention approved. Light wireline and
coiled-tubing work follows as the well ages, at a median {dev_age('light intervention')} years. Temporary abandonment comes at a median
{dev_age('temporary abandonment')} years and permanent abandonment at
{dev_age('permanent abandonment')} years. Development wells drilled since {d.first} have had
{dev['interventions']:.1f} intervention approvals each so far, against BOEM's
expectation of seven workovers or other well activities in a lifetime; the ones still standing
are a median {yrs(dev['age_standing'])} years old. An exploration well's story is short: two in
three of those drilled since {d.first} are already permanently abandoned, most within a year
of spud, and its heavy work comes early (median age {exp_age('heavy intervention')} years).</p>
""")

    # 3. Interventions by depth ---------------------------------------------------
    aban_shallow = int(
        d.rates.loc[
            d.rates.year.eq(d.last)
            & d.rates.band.eq("under 100 m")
            & d.rates.family.eq("abandonment"),
            "permits",
        ].item()
    )
    work_split = {
        b: int(
            d.rates.loc[
                d.rates.year.eq(d.last)
                & d.rates.band.eq(b)
                & d.rates.family.eq("well work"),
                "permits",
            ].item()
        )
        for b in BANDS
    }
    approvals_notes = [
        f"Approved permits to modify existing wells, counted by approval year and the well's water depth. Initial completions and new-hole preparation are excluded; abandonment of unstated type is kept. {d.last + 1} runs to {long_date(d.date, year=False)}.",
        f"From {CODING_CHANGE_YEAR}, the feed moves well work from the OTHER code to WORKOVER; part of the fall in well work after {CODING_CHANGE_YEAR - 1} reflects that change, and the early years have incomplete electronic coverage.",
        f"Data: {fl('counts_by_year_band_group.csv')}, {fl('rates.csv')}.",
    ]
    rate_notes = [
        "Approvals in a year divided by the wells standing on 1 January of that year, per 100 wells. Wells first drilled during the year can add approvals but not stock, so this is a rate of approvals against the opening stock, not the share of wells worked on.",
        f"Data: {fl('rates.csv')}, {fl('standing_wells.csv')}; light and heavy by year: {fl('intervention_weight_by_year.csv')}.",
    ]
    sections.append(f"""
<h2 id="s3">3. Interventions by water depth</h2>
<p>In {d.last}, BSEE approved {n(h['work'])} interventions (well work) and
{n(h['aban'])} abandonments, {n(h['total'])} approvals in all. By water depth, the
interventions were {'; '.join(f"{BAND_TEXT[b]}: {n(work_split[b])}" for b in BANDS)}.
The abandonments were
{n(split['temporary abandonment'])} temporary, {n(split['permanent abandonment'])} permanent and
{n(split['abandonment unspecified'])} of unstated type. {share_text(aban_shallow, h['aban'])} of
the abandonment approvals ({n(aban_shallow)} of {n(h['aban'])}) were for wells in less than 100 m
of water.</p>
{figure('01_approved_interventions', 3, 'Approved permits to modify, by water depth', approvals_notes,
        'Stacked bars of approved permits by year and water-depth band, well work and abandonment.')}
{figure('02_rates_per_standing_well', 4, 'Approvals per 100 standing wells', rate_notes,
        'Lines of approvals per 100 standing wells by year and water-depth band, well work and abandonment.')}
<h3>What the rate means</h3>
<p>Figure 4 asks how often a standing well gets an approval in a year. A rate of
{yrs(h['rate'][('1500 m and deeper', 'well work')])} at 1,500 m and deeper in {d.last} means
about {h['rate'][('1500 m and deeper', 'well work')] / 100:.1f} intervention approvals for every
standing deepwater well; {yrs(h['rate'][('under 100 m', 'well work')])} on the shelf means about
one for every {100 / h['rate'][('under 100 m', 'well work')]:.0f} standing shelf wells. The rate
takes out the shrinking number of wells: {n(t.loc[(d.first, 'well work'), 'standing_wells'])}
wells stood on 1 January {d.first} and {n(t_last.standing_wells)} on 1 January {d.last}.</p>
<ul>
<li><strong>Is intervention going up or down?</strong> Per standing well, it held in a narrow
band for many years and has been lower since {d.last - 2}. Across all depths, intervention approvals ran at {yrs(work_early.min())} to
{yrs(work_early.max())} per 100 standing wells a year from {d.first + 1} to
{CODING_CHANGE_YEAR - 2}, and at {yrs(work_late.min())} to {yrs(work_late.max())} from
{d.last - 2} to {d.last}. The count fell further, from {n(t_first.permits)} in {d.first + 1}
to {n(t_last.permits)} in {d.last}, mostly because there are fewer wells. Part of the recent step down
is the coding change in note 2 of Figure 3.</li>
<li><strong>Light or heavy?</strong> From {wt['start']}, at least three in four intervention
approvals name a unit that can be classified ({wt['named_last']:.0f}% in {d.last}). Since then
light work has run at {yrs(wt['light_range'][0])} to {yrs(wt['light_range'][1])} approvals per
100 standing wells a year and heavy work at {yrs(wt['heavy_range'][0])} to
{yrs(wt['heavy_range'][1])}. Light work averaged {yrs(wt['light_early'])} in
{wt['early'][0]}-{wt['early'][1]} and {yrs(wt['light_late'])} in
{wt['late'][0]}-{wt['late'][1]}; heavy work averaged {yrs(wt['heavy_early'])} and
{yrs(wt['heavy_late'])}. Light work is about twice as frequent as heavy work, and both are
{'lower' if wt['light_late'] < wt['light_early'] and wt['heavy_late'] < wt['heavy_early'] else 'mixed'}
in the last three years than in {wt['early'][0]}-{wt['early'][1]}.</li>
<li><strong>Deeper water, more work per well.</strong> In {d.last} the intervention rate rises
with depth ({'; '.join(f"{BAND_TEXT[b]}: {yrs(h['rate'][(b, 'well work')])}" for b in BANDS)}).
Deepwater wells are fewer and more often subsea, and the operators' own
estimates put the job at a median {durations[('1500 m and deeper', 'well work')]:.0f} days
there against {durations[('under 100 m', 'well work')]:.0f} on the shelf.</li>
<li><strong>Abandonment</strong> ran at {yrs(a_last.per100)} approvals per 100 standing wells
in {d.last}, against {yrs(t_last.per100)} for interventions. Abandonment is counted here and
studied in the next article.</li>
</ul>
{figure('04_unit_types_by_depth', 5, f'Units named on {d.last} approvals, by depth',
        [f"Share of {d.last} approvals by the unit type the permit names, through the regulator's rig lookup; a named unit is not proof of the unit used.", f"Data: {fl('unit_type_shares.csv')}."],
        'Horizontal 100 percent bars of unit types by water depth for well work and permanent abandonment.')}
""")

    # 4. Cost --------------------------------------------------------------------
    sections.append(f"""
<h2 id="s4">4. Cost per intervention, by access type</h2>
<p>Cost follows how the well is reached, not depth alone. A dry-tree platform well can be worked
from a rigless spread or casing jacks; a subsea well needs a vessel, a drillship or a
semisubmersible. Figure 6 gives low, base and high cases per event in 2015 dollars from the
BSEE and BOEM cost studies; the method and every source page are in Appendix B.</p>
{figure('03_cost_per_event', 6, 'Cost per event, by well and access type',
        ["Scenario costs per event in USD million (2015), two significant figures; spread rows exclude the source's allowances, the deep-platform row is a published total that includes them.", f"Data: {fl('cost_table.csv')}."],
        'Horizontal ranges of low, base and high cost per event for each well and access type.')}
<h2 id="s5">5. Abandonment</h2>
<p>Abandonment approvals appear in this article only as counts and rates. The next article
covers abandonment, temporary and permanent, in the same depth: why wells are left temporarily
abandoned, how long they stay that way, and what permanent abandonment costs.</p>
""")

    charts = [
        ("05_well_life", "life_cycle_life_histogram.csv", "Figure 1"),
        ("06_well_life_stages", "life_cycle_stage_reach.csv", "Figure 2"),
        ("01_approved_interventions", "counts_by_year_band_group.csv", "Figure 3"),
        ("02_rates_per_standing_well", "rates.csv", "Figure 4"),
        ("04_unit_types_by_depth", "unit_type_shares.csv", "Figure 5"),
        ("03_cost_per_event", "cost_table.csv", "Figure 6"),
    ]
    chart_list = "".join(
        f"<li>{label}: {fl(stem + '.png', 'PNG')} · {fl(stem + '.svg', 'SVG')} · data {fl(data)}</li>"
        for stem, data, label in charts
    )
    sections.append(f"""
<h2 id="charts">Charts and data</h2>
<ul>{chart_list}</ul>
<p>To try it out or adapt the analysis, see <a href="{prompt_href}">reusable prompt</a>.</p>
<p class="closing">{esc(CLOSING)}</p>
<p class="signoff">Petroleum Engineer Deckhand and Data Analyst Deckhand. Approval: pending.</p>
<p class="hashtags">{esc(HASHTAGS)}</p>
""")

    # Appendices ---------------------------------------------------------------------
    sections.append(f"""
<h2 id="appendix-a">Appendix A. Counting rules</h2>
<ol>
<li><strong>Wells and life.</strong> One well is one API10 number in BSEE's borehole file,
region G, with cancelled bores removed. A well starts at the earliest spud date of its bores. It
ends when every bore that is not superseded (status ST or BP) is permanently abandoned (PA) with
a date; the end is the latest of those dates. Otherwise it stands at {date_text}. Development (D)
and exploration (E) follow the well type of the original hole (suffix ST00BP00).</li>
<li><strong>Drilling.</strong> Each bore with a spud date: the original hole and each sidetrack
or bypass. Permits that prepare new hole (PLUGBACK, sidetrack, bypass or deepen) are excluded
from the permit counts so that drilling is not counted twice.</li>
<li><strong>Permits.</strong> One approved permit to modify (one submission ID) is one event.
WORKOVER, ENHANCE, COMP with ZONE, OTHER, INFORM and UTIL are interventions (well work). ABANDON
with PERMABAN is permanent abandonment, else with TEMPABAN temporary abandonment, else of unstated
type. COMP without ZONE (initial completion) is excluded. Approvals from {d.first} to
{date_text} are counted; the feed begins part-way through {d.first - 1}.</li>
<li><strong>Light or heavy.</strong> From the unit type the permit names (rig ID joined to the
regulator's rig lookup). Light: wireline (WL), coiled tubing (CT), intervention vessel (WI),
liftboat (LB), recorded non-rig operation (NR). Heavy: hydraulic workover or snubbing unit (HW,
SB), platform rig (PF), jack-up rig (JU), drillship or semisubmersible (DS, SS, SD). Not
classified: no unit named, or another type (barge, submersible, unmatched). These groups keep
the unit categories of the permit counts, except that the combined "liftboat / jack-up" category
is divided by its two source codes. Mapping: {fl('intervention_weight_mapping.csv')}.</li>
<li><strong>Water depth</strong> is the well's depth in feet times 0.3048, in four bands: under
100 m, 100 to 500 m, 500 to 1,500 m, and 1,500 m and deeper.</li>
<li><strong>Standing wells</strong> on 1 January use the same start and end rule as item 1.</li>
</ol>
<h2 id="appendix-b">Appendix B. Cost method</h2>
<p>Spread scenarios multiply a published day rate by low, base and high durations and add
mobilisation: rigless platform spread USD {n(64530)} a day (derived from TAP-738, Table 8-2, p. 8-12),
casing jacks USD {n(68424)} a day (Table 8-3, p. 8-14), drillship or semisubmersible USD
{n(674600)} a day (p. 8-18). Well-work durations are 7, 10.5 and 14 days (BOEM 2016-018 p. 3-37
median; one to two weeks from the BOEM Alaska update, 2012, p. 108). The deepwater dry-tree
abandonment row is TAP-738's published per-well total (Table 8-4, p. 8-15). Costs are 2015
dollars, not escalated, and are scenarios, not bids. The full table, every input and its source
page are in the <a href="{study}">full study</a> ({fl('cost_table.csv')}).</p>
<h2 id="appendix-c">Appendix C. Reusable prompt</h2>
<p>This prompt rebuilds the life of every Gulf of Mexico well and the intervention counts from
BSEE's public raw data, and adapts them to your own field or depth range. To have a study of
your own wells done for you instead, see below.</p>
<h3>What you need to run this</h3>
<ul>
<li>Data required: BSEE raw data, BoreholeRawData.zip and eWellAPMRawData.zip (and eWellEORRawData.zip and eWellWARRawData.zip for the cross-checks), from data.bsee.gov.</li>
<li>Data required to adapt: a list of API numbers, or a lease, area or depth range.</li>
<li>Paid or behind an account: nothing.</li>
<li>Changes over time: BSEE refreshes the files daily, so a new download gives slightly different recent counts.</li>
</ul>
<h3>Reproduce the published result</h3>
<pre>Using the worldenergydata repository at commit {build_commit}, folder {FOLDER}:
download the four BSEE archives with download_data.py --snapshot {d.summary['snapshot']}
(or use a later snapshot and expect small changes in recent years), then run
count_interventions.py, well_life_cycle.py, build_cost_basis.py, estimate_costs.py,
plot_charts.py, plot_life_cycle.py and build_article.py. Check that
output/life_cycle_reconciliation.csv shows the same published and counted totals,
and that {d.last} gives {n(h['work'])} intervention and {n(h['aban'])} abandonment approvals.</pre>
<h3>Adapt it to your project</h3>
<pre>Filter the borehole and permit tables to your wells before the life-cycle step.
Report, per well: life in years, bores drilled, light and heavy interventions,
temporary and permanent abandonment approvals, with the counting rules of Appendix A.
Keep approvals separate from completed jobs, and state the unit rule you use.</pre>
<p>Data set: BSEE Data Center raw well data (public), files of {snap}.</p>
<p>To have a study of your own wells done for you, write to support@aceengineer.com.</p>
""")

    toc = "".join(
        f'<li><a href="#{a}">{esc(t_)}</a></li>'
        for a, t_ in [
            ("s1", "Why interventions matter"),
            ("s2", "The life of a Gulf of Mexico well"),
            ("s3", "Interventions by water depth"),
            ("s4", "Cost per intervention, by access type"),
            ("s5", "Abandonment"),
            ("charts", "Charts and data"),
        ]
    )
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gulf of Mexico well interventions: the life of a well (revision {REVISION})</title>
<style>
body {{ font-family: Georgia, 'Times New Roman', serif; color: #1d2733; max-width: 860px; margin: 2rem auto; padding: 0 1rem; line-height: 1.55; }}
h1, h2, h3, .label, .fig-title, table, .notes, .masthead, .version {{ font-family: 'Segoe UI', Arial, sans-serif; }}
h1 {{ font-size: 1.9rem; line-height: 1.2; margin: .3rem 0 1rem; }}
h2 {{ margin-top: 2.4rem; border-top: 1px solid #d5dde5; padding-top: 1rem; }}
.masthead {{ font-size: .9rem; color: #4f6d7a; }}
.label {{ font-size: .85rem; letter-spacing: .04em; text-transform: uppercase; color: #245476; }}
blockquote {{ border-left: 4px solid #245476; margin: 1rem 0; padding: .4rem 1rem; background: #f4f8fb; }}
.version {{ font-size: .9rem; color: #4f6d7a; }}
figure {{ margin: 1.5rem 0; }}
figure img {{ width: 100%; height: auto; border: 1px solid #e3e8ee; background: #fff; }}
.fig-title {{ font-weight: 600; margin: .4rem 0 .2rem; }}
.notes {{ font-size: .85rem; color: #3c4a57; margin-top: .2rem; }}
.tablewrap {{ overflow-x: auto; margin: 1.5rem 0; }}
table {{ border-collapse: collapse; font-size: .9rem; width: 100%; }}
th, td {{ border-bottom: 1px solid #d5dde5; padding: .35rem .5rem; text-align: left; }}
td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
pre {{ white-space: pre-wrap; background: #f4f8fb; padding: .8rem; font-size: .85rem; }}
#deckhand-opening {{ min-height: 0; }}
.hashtags, .signoff {{ font-size: .9rem; color: #4f6d7a; }}
</style>
</head>
<body>
<div id="deckhand-opening" class="deckhand-slot" aria-hidden="true"></div>
<p class="masthead">{esc(MASTHEAD)}</p>
<p class="label">Energy Street · Well interventions</p>
<h1>Gulf of Mexico well interventions: the life of a well, then the work by water depth</h1>
<blockquote>{esc(takeaway)}</blockquote>
<p class="version">Revision {REVISION}, {date_text}. Data: BSEE raw well data, files of {snap}.
<a href="{study}">Read the full study</a>.</p>
<p><strong>In this article</strong></p>
<ol>{toc}</ol>
{''.join(sections)}
</body>
</html>
"""
    for name in [c[0] for c in charts]:
        data = base64.b64encode((out / f"{name}.png").read_bytes()).decode()
        page_html = page_html.replace(
            f"@@IMAGE:{name}@@", f"data:image/png;base64,{data}"
        )
    if re.search(r"@@[^@\s]+@@", page_html):
        raise ValueError("unresolved page token")
    text = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "", page_html)
    if FORBIDDEN.search(text):
        raise ValueError(f"forbidden public wording: {FORBIDDEN.search(text).group(0)}")
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(page_html, encoding="utf-8", newline="\n")
    return page


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--page", type=Path, default=PAGE)
    parser.add_argument(
        "--build-commit",
        default="analysis/gom-interventions-by-depth",
        help="commit that holds the data and charts; links and the prompt pin to it",
    )
    args = parser.parse_args()
    print(build(args.out, args.page, args.build_commit))
