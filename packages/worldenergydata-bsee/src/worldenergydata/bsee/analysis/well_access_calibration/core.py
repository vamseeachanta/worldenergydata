"""Pure empirical calibration on normalized BSEE tables.

Equations and policy provenance: docs/bsee/well_access_calibration.md.
Intervals are half-open; coverage and confidence thresholds are required inputs.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict

import pandas as pd

# Schema and circularity policy: digitalmodel well_access/intervention_rates.py,
# revision 84aa1f6 (2026); analog code policy: issue #510 implementation plan.
TYPES = {
    "light_well_intervention": "lwi_vessel",
    "workover": "modu",
    "recompletion": "modu",
}
DRY_TREE_CODES = {"SPAR", "TLP", "MTLP"}
# BSEE API suffix convention reused from lower_tertiary.ops_timeline.detect_reentries.
WELLBORE_DIGITS = 12


def _ids(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.slice(stop=WELLBORE_DIGITS)


def _dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, format="mixed", errors="raise")


def _number(value, name, *, positive=False):
    number = float(value)
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(f"Invalid {name}")
    return number


def _parameters(parameters):
    p = dict(parameters)
    for name in ("coverage_basis", "analog_basis"):
        if not isinstance(p.get(name), str) or not p[name].strip():
            raise ValueError(f"{name} is required")
    p["start"] = pd.Timestamp(p["observation_start"])
    p["end"] = pd.Timestamp(p["observation_end"])
    if pd.isna(p["start"]) or pd.isna(p["end"]) or p["start"] >= p["end"]:
        raise ValueError("Invalid observation window")
    for name in ("days_per_year", "min_events", "min_exposure_years"):
        p[name] = _number(p[name], name, positive=True)
    p["event_gap_days"] = _number(p["event_gap_days"], "event_gap_days")
    edges = [_number(v, "band edge") for v in p["band_edges_yr"]]
    if (
        len(edges) < 2
        or edges[0] != 0
        or any(b <= a for a, b in itertools.pairwise(edges))
    ):
        raise ValueError("Age bands must increase from zero")
    p["band_edges_yr"] = edges
    codes = set(p["dry_tree_codes"])
    if not codes or not codes <= DRY_TREE_CODES:
        raise ValueError("Only verified dry-tree codes are permitted")
    p["dry_tree_codes"] = sorted(codes)
    return p


def select_analogs(wells, dry_tree_codes):
    """Require well-level tree evidence; a lease hosting a SPAR is insufficient."""
    df = wells.copy()
    if df[["API_WELL_NUMBER", "LEASE_NUMBER", "tree_type"]].isna().any().any():
        raise ValueError("Missing analog identity or tree evidence")
    df["well"] = _ids(df["API_WELL_NUMBER"])
    if not df["well"].str.fullmatch(r"\d{12}").all():
        raise ValueError("Analog API must identify a wellbore")
    if df["well"].duplicated().any():
        raise ValueError("Duplicate analog wellbore")
    df = df[df["tree_type"].isin(dry_tree_codes)].copy()
    df["first"] = _dates(df["first_production"])
    if df["first"].isna().any():
        raise ValueError("First production evidence is required")
    if "last_observed" in df:
        df["last"] = _dates(df["last_observed"])
        if df["last"].isna().any() or (df["last"] < df["first"]).any():
            raise ValueError("Invalid last observation")
    return df.sort_values("well")


def extract_events(war, wells, event_gap_days):
    """Merge same-type windows, count clusters, measure union of report spans.

    Duplicate reports and overlapping weekly windows must not inflate durations.
    Suffix changes count only when an earlier completion is actually observed.
    """
    df = war.copy().drop_duplicates()
    df["well"] = _ids(df["API_WELL_NUMBER"])
    df = df[df["well"].isin(wells["well"])].copy()
    df["start"] = _dates(df["WAR_START_DT"])
    df["end"] = _dates(df["WAR_END_DT"])
    if df[["start", "end"]].isna().any().any() or (df["end"] < df["start"]).any():
        raise ValueError("Invalid WAR report interval")
    # Canonical war_activity_codes.yml (2026): raw WAR tokens are not
    # definitions. Accept only independently reviewed normalized event labels.
    df["kind"] = df.get("INTERVENTION_TYPE", pd.Series("", index=df.index)).fillna("")
    selected = df["kind"] != ""
    if not df.loc[selected, "kind"].isin(TYPES).all():
        raise ValueError("Unknown normalized intervention type")
    if selected.any() and (
        "CLASSIFICATION_BASIS" not in df
        or df.loc[selected, "CLASSIFICATION_BASIS"].fillna("").str.strip().eq("").any()
    ):
        raise ValueError("Explicit event labels require classification evidence")
    df["kind"] = df["kind"].replace("", None)
    # Reuse the existing rig vocabulary and name classifier.
    if "RIG_NAME" in df:
        from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
            RigType,
            classify_rig_type,
        )

        light = {
            RigType.WIRELINE_UNIT,
            RigType.COIL_TUBING_UNIT,
            RigType.LIFT_BOAT,
            RigType.SNUBBING_UNIT,
        }
        mask = df["RIG_NAME"].fillna("").map(classify_rig_type).isin(light)
        df.loc[mask & df["kind"].isna(), "kind"] = "light_well_intervention"
    df = df.sort_values(["well", "start", "end", "API_WELL_NUMBER"])
    for _, group in df.groupby("well", sort=True):
        firsts = group.groupby("API_WELL_NUMBER")["start"].min().sort_values()
        for api, first in firsts.items():
            suffix = str(api)[WELLBORE_DIGITS:]
            if suffix.strip("0") and (firsts < first).any():
                matches = (df["API_WELL_NUMBER"] == api) & (df["start"] == first)
                # Explicit activity takes precedence over inferred suffix evidence.
                df.loc[matches & df["kind"].isna(), "kind"] = "recompletion"
    events = []
    for (well, kind), group in df.dropna(subset=["kind"]).groupby(["well", "kind"]):
        cluster = None
        for row in group.sort_values(["start", "end"]).itertuples():
            if cluster is None or row.start > cluster["end"] + pd.Timedelta(
                days=event_gap_days
            ):
                if cluster is not None:
                    events.append(cluster)
                cluster = {
                    "well": well,
                    "kind": kind,
                    "start": row.start,
                    "end": row.end,
                    "duration_days": (row.end - row.start) / pd.Timedelta(days=1),
                }
            else:
                cluster["duration_days"] += max(
                    0.0,
                    (row.end - max(row.start, cluster["end"])) / pd.Timedelta(days=1),
                )
                cluster["end"] = max(row.end, cluster["end"])
        if cluster is not None:
            events.append(cluster)
    return events


def exposure_by_band(wells, p):
    """Intersect age bands with each well's evidenced observation interval."""
    exposure = [0.0 for _ in p["band_edges_yr"][:-1]]
    intervals = {}
    for row in wells.itertuples():
        start = max(row.first, p["start"])
        end = min(getattr(row, "last", p["end"]), p["end"])
        intervals[row.well] = (start, end, row.first)
        for i, (lo, hi) in enumerate(zip(p["band_edges_yr"], p["band_edges_yr"][1:])):
            left = max(start, row.first + pd.Timedelta(days=lo * p["days_per_year"]))
            right = min(end, row.first + pd.Timedelta(days=hi * p["days_per_year"]))
            exposure[i] += max(
                0.0, (right - left) / pd.Timedelta(days=p["days_per_year"])
            )
    return exposure, intervals


def _summary(values):
    if not values:
        return None
    s = pd.Series(values, dtype=float)
    return {
        "n": len(values),
        "mean": float(s.mean()),
        "p25": float(s.quantile(0.25)),
        "p50": float(s.median()),
        "p75": float(s.quantile(0.75)),
        "min": float(s.min()),
        "max": float(s.max()),
    }


def production_uptime(production, wells, intervals):
    """Observed well-month availability proxy; unknown months stay unknown.

    Quantiles use pandas' linear empirical interpolation; probabilities are
    definitions of quartiles, not calibration coefficients. This proxy does
    not isolate facility-caused downtime from other production constraints.
    """
    df = production.copy().drop_duplicates()
    df["well"] = _ids(df["API_WELL_NUMBER"])
    df = df[df["well"].isin(wells["well"])].copy()
    df["month"] = pd.to_datetime(df["PRODUCTION_DATE"].astype(str), format="%Y%m")
    if df["month"].isna().any():
        raise ValueError("Missing production month")
    df["days"] = pd.to_numeric(df["DAYS_ON_PROD"], errors="raise")
    if (
        df["days"].isna().any()
        or not df["days"].map(math.isfinite).all()
        or (df["days"] < 0).any()
        or (df["days"] > df["month"].dt.days_in_month).any()
    ):
        raise ValueError("Invalid DAYS_ON_PROD")
    # Completion-level rows cannot simply be summed to wellbore uptime.
    if df.duplicated(["well", "month"]).any():
        raise ValueError("Conflicting well-month production rows")
    leases = dict(zip(wells["well"], wells["LEASE_NUMBER"].astype(str)))
    ratios, by_lease = [], defaultdict(list)
    total_on, total_days = 0.0, 0
    omitted = 0
    expected_months = 0
    for start, end, _ in intervals.values():
        if end <= start:
            continue
        months = pd.date_range(start.normalize().replace(day=1), end, freq="MS")
        expected_months += sum(
            month >= start and month + pd.offsets.MonthBegin() <= end
            for month in months
        )
    for row in df.itertuples():
        start, end, _ = intervals[row.well]
        month_end = row.month + pd.offsets.MonthBegin()
        if row.month < start or month_end > end:
            omitted += 1
            continue
        if str(row.LEASE_NUMBER) != leases[row.well]:
            raise ValueError("Production lease disagrees with analog evidence")
        ratio = float(row.days / row.month.days_in_month)
        ratios.append(ratio)
        by_lease[leases[row.well]].append(ratio)
        total_on += float(row.days)
        total_days += row.month.days_in_month
    return {
        "status": "OBSERVED_PROXY" if ratios else "NOT_EVALUATED",
        "facility_availability_suggested": (
            total_on / total_days if total_days else None
        ),
        "n_well_months": len(ratios),
        "distribution": _summary(ratios),
        "expected_well_months": int(expected_months),
        "missing_well_months": int(expected_months - len(ratios)),
        "coverage_complete": bool(expected_months and expected_months == len(ratios)),
        "partial_months_omitted": omitted,
        "per_lease": {k: _summary(v) for k, v in sorted(by_lease.items())},
        "handoff": "Review this proxy before setting input.yml "
        "well_program.facility_availability; the engine ignores uptime.",
    }


def build_calibration(wells, war, production, parameters):
    """Compute events / observed well-years, without invented no-data rates."""
    p = _parameters(parameters)
    analogs = select_analogs(wells, p["dry_tree_codes"])
    exposure, intervals = exposure_by_band(analogs, p)
    events = extract_events(war, analogs, p["event_gap_days"])
    cohort_reports = war[
        _ids(war["API_WELL_NUMBER"]).isin(analogs["well"])
    ].drop_duplicates()
    labels = cohort_reports.get(
        "INTERVENTION_TYPE", pd.Series("", index=cohort_reports.index)
    ).fillna("")
    unlabelled_reports = int(labels.eq("").sum())
    classification_sources = (
        sorted(
            set(cohort_reports.loc[labels.ne(""), "CLASSIFICATION_BASIS"].astype(str))
        )
        if labels.ne("").any()
        else []
    )
    counts = {kind: [0 for _ in exposure] for kind in TYPES}
    durations = defaultdict(list)
    censored = defaultdict(int)
    for event in events:
        start, end, first = intervals[event["well"]]
        if not start <= event["start"] < end:
            continue
        age = (event["start"] - first) / pd.Timedelta(days=p["days_per_year"])
        for i, (lo, hi) in enumerate(zip(p["band_edges_yr"], p["band_edges_yr"][1:])):
            if lo <= age < hi:
                counts[event["kind"]][i] += 1
                if event["end"] <= end and event["duration_days"] > 0:
                    durations[event["kind"]].append(float(event["duration_days"]))
                else:
                    censored[event["kind"]] += 1
                break
    base, diagnostics = {}, {"exposure_years": exposure}
    for kind, resource in TYPES.items():
        n = sum(counts[kind])
        curve = [
            {"age_min_yr": lo, "age_max_yr": hi, "rate_per_well_year": c / e}
            for lo, hi, c, e in zip(
                p["band_edges_yr"], p["band_edges_yr"][1:], counts[kind], exposure
            )
            if e > 0
        ]
        complete = bool(curve and durations[kind])
        low = (
            n < p["min_events"]
            or any(e < p["min_exposure_years"] for e in exposure)
            or censored[kind] > 0
            or kind in ("light_well_intervention", "recompletion")
            or unlabelled_reports > 0
        )
        diagnostics[kind] = {
            "status": (
                ("LOW_CONFIDENCE" if low else "CALIBRATED")
                if complete
                else "NOT_EVALUATED"
            ),
            "event_count": n,
            "events_by_band": counts[kind],
            "censored_durations": censored[kind],
            "duration_distribution": _summary(durations[kind]),
            "unexposed_bands_omitted": sum(e == 0 for e in exposure),
        }
        if complete:
            base[kind] = {
                "duration_days": float(pd.Series(durations[kind]).median()),
                "resource_class": resource,
                "low_confidence": bool(low),
                "age_curve": curve,
            }
    echo = {key: value for key, value in p.items() if key not in ("start", "end")}
    return {
        "meta": {
            "parameters": echo,
            "analog_wells": len(analogs),
            "analog_leases": int(analogs["LEASE_NUMBER"].nunique()),
            "consumer_revision": "84aa1f618eccd06a21b4d79d8c47fd99166c6a8f",
            "basis": "Observed WAR events divided by evidenced well-exposure-years",
            "classification_evidence": classification_sources,
            "unlabelled_reports": unlabelled_reports,
        },
        "base_rates": base,
        "diagnostics": diagnostics,
        "uptime": production_uptime(production, analogs, intervals),
        "caveats": [
            (
                "Demand uses verified dry-tree well analogs only; "
                "subsea is reserved for access multipliers."
            ),
            (
                "WAR availability is limited in time; coverage must be evidenced, "
                "never inferred as complete."
            ),
            (
                "Lower-Tertiary intervention history is sparse; "
                "aggregate analogs do not establish play-specific rates."
            ),
            "Light intervention WAR coverage is incomplete; its rates always carry low confidence.",
            (
                "DAYS_ON_PROD measures production availability, "
                "not independently identified facility uptime."
            ),
            (
                "Unexposed bands and types lacking complete durations are omitted, "
                "not replaced by zero demand."
            ),
            "Durations are covered report-days, not measured continuous resource occupancy.",
            "Raw WAR tokens are undefined; explicit labels require classification evidence.",
            "Suffix-based re-entry and rig-name signals are heuristic and carry low confidence.",
        ],
    }
