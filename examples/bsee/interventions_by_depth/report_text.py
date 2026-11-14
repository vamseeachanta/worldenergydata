"""Report figures and sentences derived from the delivered aggregates.

The README, PR body and chart captions take every year, date and count from the
output tables, summary.json and manifest.json through this module, so a rerun on
another snapshot or year selection cannot leave stale numbers in the prose.
CODING_CHANGE_YEAR is the single named interpretive setting.
"""

from __future__ import annotations

from datetime import date


# First year of the move from OTHER to WORKOVER primary codes in the APM feed
# (an interpretation of primary_code_by_year.csv, not a BSEE-published date).
CODING_CHANGE_YEAR = 2021

WELL_WORK_GROUPS = [
    "workover and recompletion",
    "production enhancement",
    "other well work",
]
ABANDONMENT_GROUPS = [
    "temporary abandonment",
    "permanent abandonment",
    "abandonment unspecified",
]


def long_date(value, year=True):
    """'2026-11-13' -> '13 November 2026' (or '13 November')."""
    d = date.fromisoformat(str(value))
    return f"{d.day} {d:%B}" + (f" {d.year}" if year else "")


def join_and(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def check_selection(summary, tables):
    """Reject year-tagged tables built for a different last full year.

    `tables` maps a table name to its year or period column values. Periods
    are either the last full year or a pooled range ending in it.
    """
    last = int(summary["last_full_year"])
    if not int(summary["first_full_year"]) <= CODING_CHANGE_YEAR <= last:
        raise ValueError(
            f"CODING_CHANGE_YEAR {CODING_CHANGE_YEAR} is outside "
            f"{summary['first_full_year']}-{last}"
        )
    for name, values in tables.items():
        ends = {int(str(v).split("-")[-1]) for v in values}
        if ends != {last}:
            raise ValueError(
                f"{name} is built for {sorted(ends)}; summary.json selects {last}"
            )
    return last


def family_totals(rates, last):
    """Approvals in the last full year by family, from rates.csv."""
    year = rates[rates.year.eq(last)]
    totals = {
        family: int(year.loc[year.family.eq(family), "permits"].sum())
        for family in ("well work", "abandonment")
    }
    totals["all"] = totals["well work"] + totals["abandonment"]
    return totals


def abandonment_split(counts, last):
    """Temporary / permanent / unspecified approvals in the last full year."""
    year = counts[counts.year.eq(last)]
    return {
        group: int(year.loc[year.group.eq(group), "permits"].sum())
        for group in ABANDONMENT_GROUPS
    }


def coding_change(primary, first, last):
    """OTHER and WORKOVER counts either side of the coding change."""
    years = range(first, last + 1)

    def series(code):
        f = primary[primary.APM_OP_CD.eq(code)].set_index("year").approvals
        return f.reindex(years, fill_value=0).astype(int)

    other, workover = series("OTHER"), series("WORKOVER")
    before = range(first, CODING_CHANGE_YEAR)
    after = range(CODING_CHANGE_YEAR, last + 1)
    zero_from = next(
        (y for y in after if other.loc[y:last].eq(0).all()),
        None,
    )
    listed = [y for y in after if zero_from is None or y < zero_from]
    return dict(
        before=(first, CODING_CHANGE_YEAR - 1),
        other_min=int(other.loc[list(before)].min()),
        other_max=int(other.loc[list(before)].max()),
        other_after=[(y, int(other.loc[y])) for y in listed],
        zero_from=zero_from,
        workover_before=float(workover.loc[list(before)].mean()),
        workover_after=float(workover.loc[list(after)].mean()),
        after=(CODING_CHANGE_YEAR, last),
    )


def coding_sentence(primary, first, last):
    c = coding_change(primary, first, last)
    pieces = [f"{n:,} in {y}" for y, n in c["other_after"]]
    if c["zero_from"] is not None:
        pieces.append(f"zero from {c['zero_from']}")
    return (
        f"Primary OTHER approvals numbered {c['other_min']:,}–{c['other_max']:,} "
        f"per year in {c['before'][0]}–{c['before'][1]}, then {join_and(pieces)}, "
        f"while WORKOVER approvals averaged {c['workover_before']:,.0f} per year in "
        f"{c['before'][0]}–{c['before'][1]} and {c['workover_after']:,.0f} in "
        f"{c['after'][0]}–{c['after'][1]}."
    )


def coding_caption(primary, first, last):
    c = coding_change(primary, first, last)
    end = (
        f"0 from {c['zero_from']}"
        if c["zero_from"] is not None
        else f"{c['other_after'][-1][1]} in {last}"
    )
    return (
        f"OTHER fell from {c['other_min']}-{c['other_max']}/year "
        f"({c['before'][0]}-{c['before'][1]}) to {end} as WORKOVER averaged "
        f"{c['workover_before']:.0f} then {c['workover_after']:.0f}/year; "
        "coding changes limit long-run comparisons."
    )


def permanent_caption(counts, last):
    split = abandonment_split(counts, last)
    total = sum(split.values())
    return (
        "Permanent-abandonment costs apply only to that subtype "
        f"({split['permanent abandonment']:,} of {total:,} abandonment approvals "
        f"in {last})."
    )


def unit_panel_total(units, last, event="permanent abandonment"):
    """Approvals in one chart-04 panel (each band's categories sum to it)."""
    f = units[units.period.astype(str).eq(str(last)) & units.event.eq(event)]
    return int(f.drop_duplicates(["band"]).total_approvals.sum())


def reconciliation(summary, mapping, totals):
    """Primary-code arithmetic for the last full year; raises if it fails."""
    last = int(summary["last_full_year"])
    m = mapping.set_index(["primary_code", "group"]).last_full_year_permits

    def get(code, group=None):
        f = m.xs(code, level=0) if code in m.index.get_level_values(0) else m[:0]
        return int(f.sum() if group is None else f.get(group, 0))

    nh = "new hole excluded"
    work_codes = get("WORKOVER") + get("ENHANCE")
    nh_work = get("WORKOVER", nh) + get("ENHANCE", nh)
    abandon = get("ABANDON")
    nh_abandon = get("ABANDON", nh)
    comp_zone = get("COMP", "workover and recompletion")
    comp_initial = get("COMP", "initial completion excluded")
    other = sum(get(c, "other well work") for c in ("OTHER", "INFORM", "UTIL"))
    work = work_codes - nh_work + comp_zone + other
    if work != totals["well work"] or abandon - nh_abandon != totals["abandonment"]:
        raise ValueError("primary-code reconciliation does not match rates.csv")
    new_hole = mapping[mapping.group.eq(nh) & mapping.last_full_year_permits.gt(0)]
    breakdown = join_and(
        f"{r.last_full_year_permits:,} {r.primary_code}" for r in new_hole.itertuples()
    )
    raw = summary["checkpoint_raw_last_full_year"]
    all_codes = int(mapping.last_full_year_permits.sum())
    raw_note = (
        "equal to the raw archive rows for that year"
        if sum(raw.values()) == all_codes
        else f"from {sum(raw.values()):,} raw archive rows before deduplication and region selection"
    )
    eor = summary.get("checkpoint_eor_last_full_year", {})
    eor_text = (
        f" End-of-operations reports dated {last} number {eor.get('W', 0):,} W, "
        f"{eor.get('A', 0):,} A and {eor.get('C', 0):,} C."
        if eor
        else ""
    )
    return (
        f"In {last}, deduplicated Gulf approvals number **{work_codes:,} WORKOVER + "
        f"ENHANCE; {abandon:,} ABANDON; {all_codes:,} all codes**, {raw_note}. "
        f"Exclusions are {int(new_hole.last_full_year_permits.sum()):,} new-hole "
        f"preparations ({breakdown}) and {comp_initial:,} COMP without ZONE. "
        f"Retaining {comp_zone:,} COMP/ZONE and {other:,} OTHER/INFORM/UTIL gives "
        f"{work_codes:,} − {nh_work:,} + {comp_zone:,} + {other:,} = "
        f"{work:,} well work, and {abandon:,} − {nh_abandon:,} = "
        f"{abandon - nh_abandon:,} abandonment.{eor_text}"
    )
