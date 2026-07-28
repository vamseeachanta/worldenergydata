"""Drilling and completion rig-days from BSEE WAR activity codes.

This is the single implementation of "how many days did a rig spend drilling
and completing this wellbore".  Every other consumer should call it rather
than re-deriving the number; see #1063 for why four divergent implementations
existed and what each of them got wrong.

Basis
-----
A BSEE Well Activity Report (WAR) is a *weekly* return (Form BSEE-0133,
30 CFR 250.743; Sunday 00:00 through Saturday 23:59) carrying one
``WELL_ACTIVITY_CD`` per reported operation.  Rig-days are therefore the sum
of WAR week spans attributed to the relevant activity codes -- not a calendar
span between spud and total depth, which for a suspended or batch-drilled
well measures elapsed time rather than rig time.

Two conventions are pinned deliberately, because getting either wrong moves
every published number:

``INCLUSIVE`` day counting
    A WAR week runs Sunday 00:00 to Saturday 23:59 and is *seven* days, so a
    span is ``(end - start).days + 1``.  This is the convention under which
    the domain owner's own published totals for well 608124009500 reproduce
    (DRL 151, PND 49, total 308); see the fixture test.

Adjacency merging
    Consecutive WAR weeks (Jan 1-7 then Jan 8-14) describe *continuous* rig
    time and must merge into one 14-day span.  Treating them as disjoint
    (the previous behaviour) silently lost one day per week boundary.

Grain
-----
BSEE reports at API12 -- the *wellbore*, including each sidetrack as its own
suffix.  Rolling up to API10 (the *well*) must UNION the underlying WAR weeks
rather than sum per-bore days: at each sidetrack transition a single WAR week
is attributed to both bores, so summing double-counts roughly seven days per
boundary.  Both grains are emitted so consumers can state which one they mean.

``PND`` caveat
--------------
BSEE publishes no code list for ``WELL_ACTIVITY_CD`` and ``PND`` appears in
none of their documented domains, yet it accounts for a material share of
reported weeks.  It is therefore never folded silently into another bucket:
it is emitted as its own ``pnd_days`` column, and a basis either includes it
explicitly or does not.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from worldenergydata.lower_tertiary.ops_timeline import WAR_ACTIVITY_LABELS

__all__ = [
    "WAR_ACTIVITY_LABELS",
    "Basis",
    "BASIS_DRL_COM",
    "BASIS_DRL_COM_PND",
    "BASIS_METHOD_1",
    "PRESET_BASES",
    "union_days",
    "rig_days_by_bore",
    "rig_days_by_well",
]

# Emitted when a bore appears in the target population but has no WAR
# activity at all -- distinct from a genuine zero, and never rendered as 0.
STATUS_COVERED = "war_covered"
STATUS_NO_ACTIVITY = "no_war_activity"

_REQUIRED_COLUMNS = (
    "API_WELL_NUMBER",
    "WAR_START_DT",
    "WAR_END_DT",
    "WELL_ACTIVITY_CD",
)


@dataclass(frozen=True)
class Basis:
    """A named, explicit rule for turning activity codes into D&C days.

    The whole defect class in #1063 exists because a rule was applied
    provisionally and never recorded alongside the numbers it produced, so
    every frame this module emits carries ``label`` in a ``basis`` column.
    """

    label: str
    drilling_codes: frozenset[str]
    completion_codes: frozenset[str]
    notes: str = ""

    def describe(self) -> str:
        drl = "+".join(sorted(self.drilling_codes))
        com = "+".join(sorted(self.completion_codes))
        return f"{self.label}(drilling={drl};completion={com};days=inclusive)"


#: Drilling = DRL, completion = COM.  Maps onto IADC DDR Plus Code 31, whose
#: completion phase "commence[s] once drilling is complete, and casing is set"
#: -- i.e. the DRL -> COM code transition.  PND excluded.
BASIS_DRL_COM = Basis(
    label="DRL_COM",
    drilling_codes=frozenset({"DRL"}),
    completion_codes=frozenset({"COM"}),
    notes="IADC DDR Plus Code 31 alignment; PND reported separately.",
)

#: As above but crediting PND to completion, for side-by-side reporting while
#: the meaning of PND is outstanding with BSEE (see #1065).
BASIS_DRL_COM_PND = Basis(
    label="DRL_COM_PND",
    drilling_codes=frozenset({"DRL"}),
    completion_codes=frozenset({"COM", "PND"}),
    notes="PND credited to completion; use only alongside DRL_COM.",
)

#: The domain owner's "method 1" from rig_days_summary.md: COM + PND + TA.
BASIS_METHOD_1 = Basis(
    label="METHOD_1",
    drilling_codes=frozenset({"DRL"}),
    completion_codes=frozenset({"COM", "PND", "TA"}),
    notes="Owner's method 1 (rig_days_summary.md).",
)

PRESET_BASES: dict[str, Basis] = {
    b.label: b for b in (BASIS_DRL_COM, BASIS_DRL_COM_PND, BASIS_METHOD_1)
}


def union_days(intervals) -> int:
    """Total days covered by ``intervals``, inclusive of both endpoints.

    Overlapping *and* directly adjacent intervals are merged, so consecutive
    WAR weeks count as continuous rig time.  Rows with a missing endpoint are
    skipped; an empty or all-missing input yields 0.

    Endpoints are normalised to midnight first.  WAR weeks are stamped with
    times (typically 00:01 to 23:59), and carrying those through the merge
    loses whole days to truncation: seven consecutive weeks measure
    47d23h59m, which floors to 47 rather than the 48 day-boundaries actually
    spanned.  Rig-days are a count of calendar days, not of elapsed time.
    """
    clean = sorted(
        (s.normalize(), e.normalize())
        for s, e in intervals
        if pd.notna(s) and pd.notna(e) and e >= s
    )
    if not clean:
        return 0

    one_day = pd.Timedelta(days=1)
    total = 0
    cur_start, cur_end = clean[0]
    for start, end in clean[1:]:
        if start <= cur_end + one_day:  # overlapping or back-to-back
            cur_end = max(cur_end, end)
        else:
            total += (cur_end - cur_start).days + 1
            cur_start, cur_end = start, end
    total += (cur_end - cur_start).days + 1
    return int(total)


def _prepare(war: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in _REQUIRED_COLUMNS if c not in war.columns]
    if missing:
        raise ValueError(
            f"WAR frame is missing required column(s): {', '.join(missing)}. "
            "Join mv_war_main (week bounds, API) to mv_war_main_prop "
            "(WELL_ACTIVITY_CD) on SN_WAR before calling."
        )

    out = pd.DataFrame(
        {
            "api12": war["API_WELL_NUMBER"].astype(str).str.strip(),
            "activity_cd": war["WELL_ACTIVITY_CD"].astype(str).str.strip().str.upper(),
            # format="mixed": WAR bounds arrive as a mix of "YYYY-MM-DD
            # HH:MM:SS" and bare dates depending on the vintage of the return.
            "start": pd.to_datetime(
                war["WAR_START_DT"], errors="coerce", format="mixed"
            ),
            "end": pd.to_datetime(war["WAR_END_DT"], errors="coerce", format="mixed"),
        }
    )
    out = out[out["activity_cd"].ne("") & out["activity_cd"].ne("NAN")]
    return out.dropna(subset=["start", "end"])


def _days_for(group: pd.DataFrame, codes) -> int:
    sub = group[group["activity_cd"].isin(codes)]
    return union_days(zip(sub["start"], sub["end"]))


def rig_days_by_bore(
    war: pd.DataFrame,
    basis: Basis = BASIS_DRL_COM,
    population: "list[str] | None" = None,
) -> pd.DataFrame:
    """Rig-days per API12 wellbore.

    Parameters
    ----------
    war
        WAR rows carrying ``API_WELL_NUMBER``, ``WAR_START_DT``,
        ``WAR_END_DT`` and ``WELL_ACTIVITY_CD`` (mv_war_main joined to
        mv_war_main_prop on ``SN_WAR``).
    basis
        Which activity codes constitute drilling and completion.
    population
        Optional API12 list to report on.  Bores in ``population`` with no WAR
        activity are emitted with null days and ``days_status`` of
        ``no_war_activity``, so absent coverage is never mistaken for zero.
    """
    prepared = _prepare(war)
    if population is not None:
        # Restrict before grouping: the raw WAR frame spans every well BSEE
        # has ever reported, and grouping all of them to keep a few hundred
        # dominates the runtime.
        prepared = prepared[
            prepared["api12"].isin({str(a).strip() for a in population})
        ]

    rows = []
    for api12, group in prepared.groupby("api12", sort=True):
        by_code = {
            code: union_days(zip(sub["start"], sub["end"]))
            for code, sub in group.groupby("activity_cd", sort=True)
        }
        rows.append(
            {
                "api12": api12,
                "api10": api12[:10],
                "bore_suffix": api12[10:],
                "drilling_days": _days_for(group, basis.drilling_codes),
                "completion_days": _days_for(group, basis.completion_codes),
                "pnd_days": by_code.get("PND", 0),
                "war_days_total": union_days(zip(group["start"], group["end"])),
                "war_weeks": int(len(group)),
                "days_by_code": by_code,
                "days_status": STATUS_COVERED,
            }
        )

    frame = pd.DataFrame(rows, columns=_BORE_COLUMNS)

    if population is not None:
        frame = _apply_population(frame, population)

    frame["basis"] = basis.describe()
    return frame.reset_index(drop=True)


_BORE_COLUMNS = [
    "api12",
    "api10",
    "bore_suffix",
    "drilling_days",
    "completion_days",
    "pnd_days",
    "war_days_total",
    "war_weeks",
    "days_by_code",
    "days_status",
]

_DAY_COLUMNS = ("drilling_days", "completion_days", "pnd_days", "war_days_total")


def _apply_population(frame: pd.DataFrame, population) -> pd.DataFrame:
    wanted = [str(a).strip() for a in population]
    frame = frame[frame["api12"].isin(set(wanted))]

    absent = sorted(set(wanted) - set(frame["api12"]))
    if not absent:
        return frame

    filler = pd.DataFrame(
        {
            "api12": absent,
            "api10": [a[:10] for a in absent],
            "bore_suffix": [a[10:] for a in absent],
            "drilling_days": pd.NA,
            "completion_days": pd.NA,
            "pnd_days": pd.NA,
            "war_days_total": pd.NA,
            "war_weeks": 0,
            "days_by_code": [{} for _ in absent],
            "days_status": STATUS_NO_ACTIVITY,
        },
        columns=_BORE_COLUMNS,
    )
    return pd.concat([frame, filler], ignore_index=True).sort_values("api12")


def rig_days_by_well(
    war: pd.DataFrame,
    basis: Basis = BASIS_DRL_COM,
    population: "list[str] | None" = None,
) -> pd.DataFrame:
    """Rig-days per API10 well, unioning the WAR weeks of all its bores.

    ``*_additive`` columns (the per-bore sums) are emitted alongside the union
    so the difference stays visible: it is dominated by the single WAR week
    that straddles each sidetrack transition, and is not parallel operations.
    """
    prepared = _prepare(war)
    if population is not None:
        prepared = prepared[
            prepared["api12"].isin({str(a).strip() for a in population})
        ]
    bores = rig_days_by_bore(war, basis=basis, population=population)

    covered = bores[bores["days_status"].eq(STATUS_COVERED)]
    additive = (
        covered.groupby("api10")
        .agg(
            n_bores=("api12", "count"),
            bore_suffixes=("bore_suffix", lambda s: ",".join(sorted(s))),
            drilling_days_additive=("drilling_days", "sum"),
            completion_days_additive=("completion_days", "sum"),
            pnd_days_additive=("pnd_days", "sum"),
            war_days_additive=("war_days_total", "sum"),
        )
        .reset_index()
    )

    prepared = prepared.assign(api10=prepared["api12"].str[:10])
    unions = []
    for api10, group in prepared.groupby("api10", sort=True):
        unions.append(
            {
                "api10": api10,
                "drilling_days": _days_for(group, basis.drilling_codes),
                "completion_days": _days_for(group, basis.completion_codes),
                "pnd_days": _days_for(group, {"PND"}),
                "war_days_total": union_days(zip(group["start"], group["end"])),
            }
        )

    frame = additive.merge(pd.DataFrame(unions), on="api10", how="left")
    frame["overlap_days"] = frame["war_days_additive"] - frame["war_days_total"]
    frame["days_status"] = STATUS_COVERED
    frame["basis"] = basis.describe()
    return frame
