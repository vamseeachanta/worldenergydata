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
    span is ``(end - start).days + 1``.  The justification is the reporting
    cadence itself: a week that is seven days long must count as seven, and
    ``(end - start).days`` yields six.

    .. warning:: An earlier version of this docstring justified the convention
       by saying it reproduced "the domain owner's own published totals for
       well 608124009500 (DRL 151, PND 49, total 308)".  **That attribution was
       wrong and is withdrawn.**  Those totals sit in
       ``docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md`` under a
       "Summary and Way Forward" heading that is addressed *to* the owner --
       it asks him to choose a completion method -- so it is most likely our
       own output, not his.  Reproducing it validated nothing.

       The owner's own figure for that well is **155** drilling days
       (``rig_days_by_milestone.md``), which is a calendar span counted
       *exclusively*: spud 2014-07-24 to TD 2014-12-26 is 155 days exclusive,
       156 inclusive.  So his practice points the other way, on a different
       basis.  The convention here stands on the reporting-cadence argument
       above and is ours to defend; it is not ratified by the owner.  See
       #1064 and #1072.

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
    "DEFAULT_PHASES",
    "normalize_api12",
    "union_days",
    "rig_days_by_bore",
    "rig_days_by_well",
]

# Emitted when a bore appears in the target population but has no WAR
# activity at all -- distinct from a genuine zero, and never rendered as 0.
STATUS_COVERED = "war_covered"
STATUS_NO_ACTIVITY = "no_war_activity"

#: The bore appears in WAR, but no week is coded to the activity being asked
#: about. That is an absence of evidence, not a measurement of zero: a bore
#: whose drilling predates WAR reporting shows only its later plugging weeks,
#: and "drilled in 0 days" is false. Corpus-wide this is the majority case for
#: drilling, so the day value is null and the reason is stated.
STATUS_NO_ACTIVITY_CODED = "no_activity_coded"

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


def normalize_api12(values) -> pd.Series:
    """Coerce an API well number column to its canonical 12-digit string form.

    A numeric API column stringifies with a float tail -- ``608124009500.0`` --
    which matches no population entry. Because a non-match is reported as
    "this bore has no WAR activity", the failure is silent and total: every
    bore comes back null and the result looks like a coverage gap rather than
    a dtype mismatch. Callers reach this legitimately, since concatenating
    heterogeneous WAR members widens the column to float64.
    """
    s = pd.Series(values).astype(str).str.strip()
    return s.str.replace(r"\.0+$", "", regex=True)


def _parse_war_date(values) -> pd.Series:
    """Parse a WAR bound to a timestamp, tolerating the dtypes the feed uses.

    ``format="mixed"`` because bounds arrive as a mix of ``"YYYY-MM-DD
    HH:MM:SS"`` and bare dates depending on the vintage of the return.

    Numeric columns are stringified first. Passed as integers, pandas reads
    them as **nanoseconds since the epoch**, so ``20240101`` silently becomes
    1970-01-01 and a seven-day week measures one day. As a string it parses to
    the intended date. WAR dates are never epoch offsets.
    """
    s = pd.Series(values)
    if pd.api.types.is_numeric_dtype(s):
        s = s.astype("Int64").astype(str).replace({"<NA>": None})
    return pd.to_datetime(s, errors="coerce", format="mixed")


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
            "api12": normalize_api12(war["API_WELL_NUMBER"]),
            "activity_cd": war["WELL_ACTIVITY_CD"].astype(str).str.strip().str.upper(),
            "start": _parse_war_date(war["WAR_START_DT"]),
            "end": _parse_war_date(war["WAR_END_DT"]),
        }
    )
    # Optional passengers, carried only when the caller supplied them. Absent
    # columns must not fabricate a value -- a bore whose feed lacks RIG_NAME has
    # unattributed days, which is different from days attributed to no rig.
    for source, target in (
        ("RIG_NAME", "rig_name"),
        ("DRILL_FLUID_WGT", "drill_fluid_wgt"),
    ):
        if source in war.columns:
            out[target] = war[source].values
    out = out[out["activity_cd"].ne("") & out["activity_cd"].ne("NAN")]
    out = out.dropna(subset=["start", "end"])
    # A return whose end precedes its start is malformed. Dropping it here --
    # rather than inside union_days -- keeps "no valid interval" distinguishable
    # from "zero days", so a reversed week cannot be published as a bore that
    # was drilled in no time at all. The real WAR feed contains spans down to
    # -7 days, so this is reachable. See #1114.
    return out[out["end"] >= out["start"]]


def _days_for(group: pd.DataFrame, codes) -> int:
    sub = group[group["activity_cd"].isin(codes)]
    return union_days(zip(sub["start"], sub["end"]))


def _reject_colliding_phases(phases) -> None:
    """Refuse a phase whose generated columns would shadow an existing one.

    ``phases={"drilling": ...}`` generates ``drilling_days``, overwriting the
    basis-derived drilling days with the phase's codes -- so a caller asking
    for an extra bucket would silently replace a core measurement, and the
    frame would carry two columns of the same name. ``pnd`` collides the same
    way. Raising is the only safe response: the shadowed value looks entirely
    plausible.
    """
    reserved = set(_BORE_COLUMNS) | {"basis"}
    seen: dict = {}
    for phase in phases:
        for suffix in ("_days", "_days_status"):
            column = f"{phase}{suffix}"
            if column in reserved:
                raise ValueError(
                    f"phase {phase!r} would generate column {column!r}, which "
                    "already exists and would be silently overwritten. Choose "
                    "a different phase name."
                )
            if column in seen:
                raise ValueError(
                    f"phases {seen[column]!r} and {phase!r} both generate "
                    f"column {column!r}."
                )
            seen[column] = phase


def _days_by_rig(group: pd.DataFrame) -> dict:
    """Days attributed to each rig that reported on this bore.

    Ported from the legacy ``ONGFDComponents`` (#1112), which is the only place
    that carried rig attribution. Rebuilt on the union basis: the legacy code
    summed per-rig interval days, double-counting any overlap.

    Rigs are kept as structured identities rather than a joined display string,
    so a consumer can attribute days rather than parse text. A row with no rig
    name is grouped under ``None`` -- absent attribution, not a rig called
    "unknown". A bore whose feed carries no rig column at all also yields
    ``{None: days}``, so unattributed duration has one encoding rather than two.

    Identities are matched on stripped, case-folded text, because ``"ENSCO 1"``
    and ``" ensco 1 "`` are one rig and counting them separately would credit
    the same days twice. The first spelling seen is kept for display.

    .. note:: ``sum(...values())`` does **not** equal ``war_days_total`` and is
       not meant to. Two rigs genuinely working overlapping weeks are each
       credited; this is a per-rig credit, not a partition of calendar coverage.
    """
    intervals = list(zip(group["start"], group["end"]))
    if "rig_name" not in group.columns:
        return {None: union_days(intervals)}

    buckets: dict = {}
    display: dict = {}
    for (start, end), raw in zip(intervals, group["rig_name"]):
        if pd.isna(raw):
            key = None
        else:
            text = str(raw).strip()
            key = text.casefold() or None
        if key is not None:
            display.setdefault(key, text)
        buckets.setdefault(key, []).append((start, end))

    return {
        (display[k] if k is not None else None): union_days(v)
        for k, v in buckets.items()
    }


def _max_drill_fluid_wgt(group: pd.DataFrame):
    """Heaviest drilling fluid reported on this bore, in ppg.

    Ported from the legacy ``ONGFDComponents`` (#1112). A wellbore
    characteristic, not a duration -- it travels here because this is where the
    WAR rows are already assembled.

    Returns null, never 0, when nothing was reported: a bore with no recorded
    fluid weight is not a bore drilled on water.
    """
    if "drill_fluid_wgt" not in group.columns:
        return pd.NA
    values = pd.to_numeric(group["drill_fluid_wgt"], errors="coerce").dropna()
    values = values[values > 0]
    return float(values.max()) if len(values) else pd.NA


def _days_and_status(group: pd.DataFrame, codes):
    """Days coded to ``codes``, or (null, no_activity_coded) if none are.

    Returning 0 here would assert that the rig spent no days on the activity,
    which the data does not support -- WAR simply carries nothing coded to it
    for this bore. The caller gets a null and a reason instead.
    """
    sub = group[group["activity_cd"].isin(codes)]
    if sub.empty:
        return pd.NA, STATUS_NO_ACTIVITY_CODED
    return union_days(zip(sub["start"], sub["end"])), STATUS_COVERED


#: Additional activity phases emitted alongside drilling and completion.
#:
#: Ported from the legacy ``ONGFDComponents`` (#1112), which measured sidetrack
#: and abandonment as separate phases. That capability was real and is absent
#: from the drilling/completion split; the legacy *arithmetic* was not ported,
#: because it inferred days from gaps between WAR reports.
#:
#: Temporary and permanent abandonment stay separate. They are different
#: operational outcomes, and collapsing them would discard the distinction the
#: legacy code was careful to keep.
#:
#: Every code here has ``provenance: unknown`` or ``published_other_domain`` in
#: ``war_activity_codes.yml`` -- the phase name is our reading of the token, not
#: a BSEE definition. See #1065.
#:
#: .. warning:: Phase columns are **not additive with basis columns**. Under
#:    ``BASIS_METHOD_1`` completion includes ``TA``, so the same days appear in
#:    both ``completion_days`` and ``temp_abandonment_days``. Nothing sums them
#:    internally, and a consumer must not either: they answer different
#:    questions over the same weeks.
DEFAULT_PHASES: dict[str, frozenset[str]] = {
    "sidetrack": frozenset({"ST"}),
    "temp_abandonment": frozenset({"TA"}),
    "perm_abandonment": frozenset({"PA"}),
}


def rig_days_by_bore(
    war: pd.DataFrame,
    basis: Basis = BASIS_DRL_COM,
    population: "list[str] | None" = None,
    phases: "dict[str, frozenset[str]] | None" = None,
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
    phases = DEFAULT_PHASES if phases is None else phases
    _reject_colliding_phases(phases)
    prepared = _prepare(war)
    if population is not None:
        # Restrict before grouping: the raw WAR frame spans every well BSEE
        # has ever reported, and grouping all of them to keep a few hundred
        # dominates the runtime.
        prepared = prepared[prepared["api12"].isin(set(normalize_api12(population)))]

    rows = []
    for api12, group in prepared.groupby("api12", sort=True):
        by_code = {
            code: union_days(zip(sub["start"], sub["end"]))
            for code, sub in group.groupby("activity_cd", sort=True)
        }
        drilling_days, drilling_status = _days_and_status(group, basis.drilling_codes)
        completion_days, completion_status = _days_and_status(
            group, basis.completion_codes
        )
        row = {
            "api12": api12,
            "api10": api12[:10],
            "bore_suffix": api12[10:],
            "drilling_days": drilling_days,
            "completion_days": completion_days,
            # pnd_days stays numeric: it is a diagnostic breakdown of the
            # weeks we do hold, not a claim about the bore's history.
            "pnd_days": by_code.get("PND", 0),
            "war_days_total": union_days(zip(group["start"], group["end"])),
            "war_weeks": int(len(group)),
            "days_by_code": by_code,
            "days_status": STATUS_COVERED,
            "drilling_days_status": drilling_status,
            "completion_days_status": completion_status,
            "rig_days_by_rig": _days_by_rig(group),
            "max_drill_fluid_wgt": _max_drill_fluid_wgt(group),
        }
        for phase, codes in phases.items():
            days, status = _days_and_status(group, codes)
            row[f"{phase}_days"] = days
            row[f"{phase}_days_status"] = status
        rows.append(row)

    # Phase columns are configurable, so the schema is built rather than fixed.
    # Passing a fixed `columns=` list would SILENTLY DROP every phase key --
    # pd.DataFrame ignores dict keys absent from an explicit column list.
    columns = list(_BORE_COLUMNS)
    for phase in phases:
        columns += [f"{phase}_days", f"{phase}_days_status"]

    if population is not None:
        # Build covered and uncovered rows into ONE frame. Concatenating an
        # all-NA filler frame instead raises a pandas FutureWarning about
        # dtype determination, and would change dtypes under a later pandas.
        rows += _absent_rows(rows, population, phases)

    frame = pd.DataFrame(rows, columns=columns)
    if population is not None:
        frame = frame.sort_values("api12")

    # Mixing real values with pd.NA leaves an `object` column, so a consumer
    # gets Python ints from one call and objects from another depending only on
    # whether any bore was uncovered. Pin the nullable types instead.
    day_columns = ["drilling_days", "completion_days", "pnd_days", "war_days_total"]
    day_columns += [f"{phase}_days" for phase in phases]
    for column in day_columns:
        frame[column] = frame[column].astype("Int64")
    frame["max_drill_fluid_wgt"] = frame["max_drill_fluid_wgt"].astype("Float64")

    frame["basis"] = basis.describe()
    return frame.reset_index(drop=True)


def _absent_rows(rows, population, phases) -> list:
    """Filler rows for requested bores that WAR says nothing about.

    Null days with ``no_war_activity`` -- absent coverage, never a zero.
    """
    present = {r["api12"] for r in rows}
    absent = sorted(set(normalize_api12(population)) - present)

    filler = []
    for api12 in absent:
        row = {
            "api12": api12,
            "api10": api12[:10],
            "bore_suffix": api12[10:],
            "drilling_days": pd.NA,
            "completion_days": pd.NA,
            "pnd_days": pd.NA,
            "war_days_total": pd.NA,
            "war_weeks": 0,
            "days_by_code": {},
            "days_status": STATUS_NO_ACTIVITY,
            "drilling_days_status": STATUS_NO_ACTIVITY,
            "completion_days_status": STATUS_NO_ACTIVITY,
            "rig_days_by_rig": {},
            "max_drill_fluid_wgt": pd.NA,
        }
        for phase in phases:
            row[f"{phase}_days"] = pd.NA
            row[f"{phase}_days_status"] = STATUS_NO_ACTIVITY
        filler.append(row)
    return filler


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
    "drilling_days_status",
    "completion_days_status",
    "rig_days_by_rig",
    "max_drill_fluid_wgt",
]

_DAY_COLUMNS = ("drilling_days", "completion_days", "pnd_days", "war_days_total")


# _apply_population() lived here. Superseded by _absent_rows(), which builds
# covered and uncovered bores into a single frame instead of concatenating an
# all-NA filler -- that concat raised a pandas FutureWarning and would have
# changed result dtypes on a later pandas.


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
        prepared = prepared[prepared["api12"].isin(set(normalize_api12(population)))]
    bores = rig_days_by_bore(war, basis=basis, population=population)

    # Group over ALL requested bores, not just covered ones. Restricting to
    # covered bores dropped an uncovered bore's well from the output entirely,
    # even though the bore itself was correctly reported at API12 grain -- and
    # raised KeyError when every requested bore was uncovered.
    def _sum_or_null(s):
        # min_count=1: an all-null group must stay null. pandas sums an all-NA
        # group to 0, which would restate "we do not know this bore's drilling
        # days" as "this bore was drilled in zero days" -- the exact confusion
        # days_status exists to prevent.
        return s.sum(min_count=1)

    additive = (
        bores.groupby("api10")
        .agg(
            n_bores=("api12", "count"),
            # min_count=1 keeps an all-null group null, but a group of
            # [7, <null>] still sums to 7 -- pandas needs only one valid value.
            # So an additive total over a partially covered well is a LOWER
            # BOUND, not an exact figure. n_bores_covered makes that visible
            # instead of leaving the consumer to assume completeness.
            n_bores_covered=("days_status", lambda s: int(s.eq(STATUS_COVERED).sum())),
            bore_suffixes=("bore_suffix", lambda s: ",".join(sorted(s))),
            drilling_days_additive=("drilling_days", _sum_or_null),
            completion_days_additive=("completion_days", _sum_or_null),
            pnd_days_additive=("pnd_days", _sum_or_null),
            war_days_additive=("war_days_total", _sum_or_null),
        )
        .reset_index()
    )

    prepared = prepared.assign(api10=prepared["api12"].str[:10])
    unions = []
    for api10, group in prepared.groupby("api10", sort=True):
        drilling_days, drilling_status = _days_and_status(group, basis.drilling_codes)
        completion_days, completion_status = _days_and_status(
            group, basis.completion_codes
        )
        unions.append(
            {
                "api10": api10,
                "drilling_days": drilling_days,
                "completion_days": completion_days,
                "pnd_days": _days_for(group, {"PND"}),
                "war_days_total": union_days(zip(group["start"], group["end"])),
                "drilling_days_status": drilling_status,
                "completion_days_status": completion_status,
            }
        )

    union_frame = pd.DataFrame(unions, columns=_UNION_COLUMNS)
    frame = additive.merge(union_frame, on="api10", how="left")
    frame["overlap_days"] = frame["war_days_additive"] - frame["war_days_total"]
    # A well with no covered bore has no union row; it is uncovered, not a well
    # whose bores took zero days.
    frame["days_status"] = (
        frame["war_days_total"]
        .notna()
        .map({True: STATUS_COVERED, False: STATUS_NO_ACTIVITY})
    )
    frame["basis"] = basis.describe()
    return frame


#: Declared explicitly so an empty ``unions`` list still merges on ``api10``
#: instead of raising KeyError -- reachable whenever every requested bore is
#: uncovered.
_UNION_COLUMNS = [
    "api10",
    "drilling_days",
    "completion_days",
    "pnd_days",
    "war_days_total",
    "drilling_days_status",
    "completion_days_status",
]
