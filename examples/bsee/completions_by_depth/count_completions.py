"""Count Gulf of America well completions from BSEE public raw data.

Part 3 of 7 in the series "Life of a Gulf of America well". A completion leaves two
public records, and both are counted here:

- the approval: an approved permit to modify whose type is COMP (Completion),
  excluding plug-backs, new-hole work and Change Zone. The interventions
  example (``../interventions_by_depth``, part 5) sets this group aside as "initial
  completion excluded". The rule is imported from that example, so one
  definition serves both articles;
- the report: an End of Operations Report whose operation code is C
  (COMPLETION), with its completion intervals and perforated intervals.

The archives are read directly from the zip files with the standard library;
nothing is extracted and no narrative text is exported. Reading, removal of
repeated rows, the Gulf filter, the water-depth join and the tallies are
written here independently of C6, and the run compares the result with C6's
own code on the same archives. A run stops when an archive does not match the
size and SHA-256 in ``series_basis.json``, when a conservation check fails or
when the count differs from C6's.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import platform
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[2] / "packages/worldenergydata-bsee/src"))
from comp_yearly import write_annual_trends  # noqa: E402

from worldenergydata.bsee.half_decade import PERIODS, summarize  # noqa: E402
from worldenergydata.bsee.yearly_trend import with_trend  # noqa: E402

sys.path.insert(0, str(ROOT.parent / "interventions_by_depth"))
import count_interventions as ci  # noqa: E402  shared rule and bands (C6)

BANDS = ci.BANDS
SHARED_GROUP = ci.GROUPS[7]  # "initial completion excluded" in C6
KINDS = ["initial completion", "other completion work"]
BOREHOLE, APM, EOR = "BoreholeRawData.zip", "eWellAPMRawData.zip", "eWellEORRawData.zip"
# Completion status codes of mv_eor_compstatcodes, grouped by the fluid the
# code names. The grouping is this example's; the labels are the regulator's.
FLUID_OF_STATUS = {
    "POW": "oil",  # PRODUCING OIL WELL
    "GLO": "oil",  # GAS LIFT OIL
    "OSI": "oil",  # OIL SHUT IN
    "GIO": "oil",  # OIL WELL TURNAROUND
    "PGW": "gas",  # PRODUCING GAS WELL
    "GSI": "gas",  # GAS SHUT IN
    "WIW": "injection or source",  # WATER INJECTION WELL
    "GIW": "injection or source",  # GAS INJECTION WELL
    "LIW": "injection or source",  # LIQUID INJECTION WELL
    "WSW": "injection or source",  # WATER SOURCE WELL
    "WDW": "injection or source",  # SALT WATER DISPOSAL
    "IDS": "injection or source",  # A DISPOSAL OR FIELD SERVICE WELL
    "STI": "injection or source",  # STEAM INJECTION
}
FLUIDS = ["oil", "gas", "oil and gas", "injection or source", "other", "not reported"]
FLAGS = ["YES", "NO", "not stated"]
INTERVAL_BINS = ["0", "1", "2", "3 or more"]
WELL_TYPES = ["development", "exploration", "other or not stated"]
ALL = "all water depths"
TOLERANCE = 0  # every count comparison is exact

csv.field_size_limit(10**9)


class BasisError(RuntimeError):
    """An archive is missing or does not match the recorded series basis."""


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def verify_basis(data_dir, basis):
    """Names of the archives whose size and SHA-256 match the basis record."""
    verified = []
    for record in basis["files"]:
        path = Path(data_dir) / record["name"]
        if not path.is_file():
            raise BasisError(f"archive not found: {record['name']}")
        data = path.read_bytes()
        if (
            len(data) != record["bytes"]
            or hashlib.sha256(data).hexdigest() != record["sha256"]
        ):
            raise BasisError(f"archive digest mismatch: {record['name']}")
        verified.append(record["name"])
    return verified


def read_member(data_dir, archive, member, encoding="cp1252"):
    """Rows of one zipped table as dictionaries of stripped text."""
    with zipfile.ZipFile(Path(data_dir) / archive) as z:
        names = [n for n in z.namelist() if Path(n).name == member + ".txt"]
        if len(names) != 1:
            raise ValueError(f"expected one member: {member}")
        with z.open(names[0]) as raw:
            text = io.TextIOWrapper(raw, encoding=encoding, newline="")
            return [
                {k: (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(text)
            ]


def parse_date(text):
    """Calendar date of a source date or timestamp; None when unreadable."""
    for pattern in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return dt.datetime.strptime(text.strip(), pattern).date()
        except (ValueError, AttributeError):
            continue
    return None


def norm_api(text):
    """A 10 or 12 digit API well number, or an empty string."""
    value = (text or "").strip()
    return value if value.isdigit() and len(value) in (10, 12) else ""


def band_of(depth_ft):
    """Water-depth band of C6: the same edges and the same labels."""
    return ci.band_from_feet(depth_ft)


def window(first_date, file_date):
    """First full year, last full year and the part year, if any.

    The first full year is the first year whose January is in the feed; the
    last full year is the year before the file date unless that date is
    31 December.
    """
    first_full = first_date.year if first_date.month == 1 else first_date.year + 1
    last_full = file_date.year - int((file_date.month, file_date.day) != (12, 31))
    return first_full, last_full, file_date.year if last_full < file_date.year else None


def quantile(values, q):
    """Linear interpolation between closest ranks, positions 0 to n - 1."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("no values")
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


class Bores:
    """Water depth and region of a bore, with the well as the fallback.

    A value is used only where it is unique: the bore's own value first, then
    the single value shared by every bore of the same ten-digit well.
    """

    def __init__(self, rows):
        depth12, depth10, region12, region10 = {}, {}, {}, {}
        for row in rows:
            api = norm_api(row.get("API_WELL_NUMBER"))
            if not api:
                continue
            region12.setdefault(api, set()).add(row.get("REGION_CODE", ""))
            region10.setdefault(api[:10], set()).add(row.get("REGION_CODE", ""))
            try:
                depth = float(row.get("WATER_DEPTH", ""))
            except (TypeError, ValueError):
                continue
            if math.isfinite(depth) and depth >= 0:
                depth12.setdefault(api, set()).add(depth)
                depth10.setdefault(api[:10], set()).add(depth)
        self._depth12, self._depth10 = self._unique(depth12), self._unique(depth10)
        self._region12 = self._unique(region12)
        self._region10 = self._unique(region10)

    @staticmethod
    def _unique(groups):
        return {k: next(iter(v)) for k, v in groups.items() if len(v) == 1}

    def depth(self, api):
        exact = self._depth12.get(api)
        return exact if exact is not None else self._depth10.get(api[:10])

    def region(self, api, lease=""):
        """Borehole region; a G lease number only where no bore matches."""
        region = self._region12.get(api)
        if region is None:
            region = self._region10.get(api[:10])
        if region is None and lease.startswith("G"):
            region = "G"
        return "unknown" if region is None else region


def unique_rows(rows, key, identity):
    """One row per key; a repeat must agree on every identity column."""
    kept = {}
    for row in rows:
        k = row[key]
        if not k:
            raise ValueError(f"missing {key}")
        if k in kept:
            if any(kept[k][c] != row[c] for c in identity):
                raise ValueError(f"conflicting rows for {key} {k}")
            continue
        kept[k] = row
    return kept


def grouped(rows, key, value):
    out = {}
    for row in rows:
        out.setdefault(row[key], set()).add(row[value])
    return out


# ---------------------------------------------------------------------------
# The two records of a completion
# ---------------------------------------------------------------------------
def completion_kind(code, subcodes, narrative=""):
    """Kind of completion approval, or None when C6 does not exclude it.

    The test is C6's own classification, so the approvals counted here are
    exactly the group C6 sets aside. Inside that group, an approval that
    carries the regulator's sub-operation INITCOMP (Initial Completion) is an
    initial completion; the rest is other completion work without a change
    of zone (perforation changes, other completion).
    """
    if ci.classify_operation(code, subcodes, narrative) != SHARED_GROUP:
        return None
    return KINDS[0] if "INITCOMP" in subcodes else KINDS[1]


def completion_approvals(apm_rows, subop_rows, narrative_rows, bore_rows):
    """One record per approved completion permit of the shared definition."""
    bores = Bores(bore_rows)
    subcodes = grouped(subop_rows, "SN_APM_FK", "APM_SUBOP_CD")
    narratives = {
        sn: "\n\n".join(sorted(texts))
        for sn, texts in grouped(narrative_rows, "SN_APM", "APM_OP_DESC").items()
    }
    permits = unique_rows(
        apm_rows, "SN_APM", ["API_WELL_NUMBER", "ACC_STATUS_DATE", "APM_OP_CD"]
    )
    out = []
    for sn, row in permits.items():
        api = norm_api(row["API_WELL_NUMBER"])
        lease = row.get("SURF_LEASE_NUM", row.get("SURF_LEASE_NUMBER", ""))
        if bores.region(api, lease) != "G":
            continue
        subs = subcodes.get(sn, set())
        kind = completion_kind(row["APM_OP_CD"], subs, narratives.get(sn, ""))
        if kind is None:
            continue
        date = parse_date(row["ACC_STATUS_DATE"])
        out.append(
            dict(
                sn=sn,
                api12=api,
                api10=api[:10],
                date=date,
                year=date.year if date else None,
                band=band_of(bores.depth(api)),
                kind=kind,
                frac="FRAC" in subs,
            )
        )
    return sorted(out, key=_order)


def completion_reports(eor_rows, bore_rows):
    """One record per End of Operations Report with operation code C."""
    bores = Bores(bore_rows)
    identity = ["API_WELL_NUMBER", "EOR_OPERATION_CD", "BOREHOLE_STAT_DT"]
    out = []
    for sn, row in unique_rows(eor_rows, "SN_EOR", identity).items():
        api = norm_api(row["API_WELL_NUMBER"])
        lease = row.get("SURF_LEASE_NUMBER", row.get("SURF_LEASE_NUM", ""))
        if row["EOR_OPERATION_CD"] != "C" or bores.region(api, lease) != "G":
            continue
        date = parse_date(row["BOREHOLE_STAT_DT"])
        out.append(
            dict(
                sn=sn,
                api12=api,
                api10=api[:10],
                date=date,
                year=date.year if date else None,
                band=band_of(bores.depth(api)),
                status=row.get("BOREHOLE_STAT_CD", ""),
                subsea=row.get("SUBSEA_COMPLETION_FLAG", ""),
            )
        )
    return sorted(out, key=_order)


def _order(event):
    return (event["date"] or dt.date.max, event["sn"])


def first_per_bore(events):
    """The earliest record of each bore (API12); ties go to the lower key."""
    first = {}
    for event in sorted(events, key=_order):
        first.setdefault(event["api12"], event)
    return list(first.values())


def year_band_table(events, years, kinds=None):
    """Complete year by band (by kind) grid of counts; zeros are kept."""
    counts = {}
    for e in events:
        key = (e["year"], e["band"]) + ((e["kind"],) if kinds else ())
        counts[key] = counts.get(key, 0) + 1
    rows = []
    for year in years:
        for band in BANDS:
            for kind in kinds or [None]:
                key = (year, band) + ((kind,) if kinds else ())
                row = dict(year=year, band=band, count=counts.get(key, 0))
                if kinds:
                    row["kind"] = kind
                rows.append(row)
    return rows


def conservation(events, table, years):
    """Checks that a wrong tally would break; every comparison is exact."""
    years = list(years)
    counted = len(events)
    in_window = sum(1 for e in events if e["year"] in years)
    total = sum(r["count"] for r in table)
    kinds = sorted({r["kind"] for r in table if "kind" in r}) or [None]
    cells = {(r["year"], r["band"], r.get("kind")) for r in table}
    checks = {
        "each_counted_once": len({e["sn"] for e in events}) == counted,
        "table_total_equals_events_in_window": total == in_window,
        "band_counts_sum_to_total": sum(
            sum(r["count"] for r in table if r["band"] == b) for b in BANDS
        )
        == in_window,
        "year_counts_sum_to_total": sum(
            sum(r["count"] for r in table if r["year"] == y) for y in years
        )
        == in_window,
        "grid_complete_without_repeats": len(table)
        == len(cells)
        == len(years) * len(BANDS) * len(kinds),
        "no_negative_count": all(r["count"] >= 0 for r in table),
    }
    return dict(
        counted=counted,
        in_window=in_window,
        outside_window=counted - in_window,
        checks=checks,
        ok=all(checks.values()),
    )


def bore_attributes(reports, interval_rows, perf_rows):
    """What the completion reports of each bore record.

    fluid: from the status codes of the bore's completion intervals;
    intervals: distinct interval labels reported; dual: a label beginning
    with D is present; subsea: YES where any report says YES, else NO where
    any says NO; perforations: perforated intervals per completion interval.
    """
    report_bore = {r["sn"]: r["api12"] for r in reports}
    perf_count = {}
    for row in perf_rows:
        key = row["SN_EOR_WELL_COMP_FK"]
        perf_count[key] = perf_count.get(key, 0) + 1
    attrs = {
        api: dict(flags=set(), status=set(), labels=set(), perforations=[])
        for api in report_bore.values()
    }
    for r in reports:
        attrs[r["api12"]]["flags"].add(r["subsea"])
    for row in unique_rows(
        interval_rows, "SN_EOR_WELL_COMP", ["SN_EOR_FK", "INTERVAL"]
    ).values():
        api = report_bore.get(row["SN_EOR_FK"])
        if api is None:
            continue
        attrs[api]["status"].add(row["COMP_STATUS_CD"])
        attrs[api]["labels"].add(row["INTERVAL"])
        attrs[api]["perforations"].append(perf_count.get(row["SN_EOR_WELL_COMP"], 0))
    out = {}
    for api, a in attrs.items():
        fluids = {FLUID_OF_STATUS.get(s, "other") for s in a["status"]}
        if {"oil", "gas"} <= fluids:
            fluid = "oil and gas"
        elif not fluids:
            fluid = "not reported"
        else:
            fluid = next(f for f in FLUIDS if f in fluids)
        out[api] = dict(
            fluid=fluid,
            intervals=len(a["labels"]),
            dual=any(label.startswith("D") for label in a["labels"]),
            subsea=(
                "YES"
                if "YES" in a["flags"]
                else "NO" if "NO" in a["flags"] else "not stated"
            ),
            perforations=a["perforations"],
        )
    return out


def match_summary(first_approved, first_reported):
    """Bores seen in both records and the days from approval to report."""
    approved = {e["api12"]: e for e in first_approved}
    reported = {e["api12"]: e for e in first_reported}
    both = sorted(set(approved) & set(reported))
    lags = sorted(
        (reported[a]["date"] - approved[a]["date"]).days
        for a in both
        if approved[a]["date"] and reported[a]["date"]
    )
    return dict(
        bores_with_initial_completion_approval=len(approved),
        of_which_with_completion_report=len(both),
        bores_with_completion_report=len(reported),
        of_which_with_initial_completion_approval=len(both),
        lag_days=lags,
        lag_median_days=quantile(lags, 0.5) if lags else None,
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def write_csv(rows, out, name, columns):
    with open(out / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(data, out, name):
    (out / f"{name}.json").write_text(
        json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def write_yearly_table(out, stem, rows, partial_year, *, is_count=False):
    result = with_trend(rows, is_count=is_count, partial_year=partial_year)
    columns = ["year", "band", "group", "value", "moving_average", "partial_year"]
    columns.extend(k for k in result[0] if k not in columns)
    write_csv(result, out, stem, columns)


def write_trend_tables(
    out, years, approvals, subcodes, classified, stock, partial_year=None
):
    """Write yearly permit counts and rates, plus the historical pooled tables."""
    # The C6 workover group also contains ordinary workovers. Only its COMP
    # permits have a Change Zone flag and pass the new hole and plugback screen.
    zone = classified[
        classified.APM_OP_CD.eq("COMP") & classified.group.eq(ci.GROUPS[0])
    ]
    work = [
        dict(year=row.year, band=row.band, kind="Recompletion")
        for row in zone.itertuples()
        if row.year in years
    ]
    flags = {"PERF": "Modify Perforations", "REPERF": "Reperforation"}
    for row in approvals:
        if row["year"] in years and row["kind"] == KINDS[1]:
            for code, label in flags.items():
                if code in subcodes.get(row["sn"], ()):
                    work.append(dict(year=row["year"], band=row["band"], kind=label))

    # Zero rows preserve the panels if a kind of permit has no observations.
    def count_grid(events, kinds):
        if any(e["year"] in years and e["band"] not in BANDS[:-1] for e in events):
            raise ValueError("a counted approval lacks a recognized depth band")
        rows = year_band_table(events, years, kinds)
        return [
            dict(year=r["year"], band=r["band"], group=r["kind"], count=r["count"])
            for r in rows
            if r["band"] != "no depth"
        ]

    permits = count_grid(approvals, KINDS)
    annual = {}
    for row in permits:
        row["group"] = row["group"].capitalize()
        key = (row["year"], row["band"])
        annual[key] = annual.get(key, 0) + row["count"]
    inventory = stock.set_index(["year", "band"], verify_integrity=True).standing_wells
    rates = [
        dict(year=y, band=b, count=count, exposure=int(inventory.loc[y, b]))
        for (y, b), count in annual.items()
    ]
    activity = count_grid(work, ["Recompletion", *flags.values()])
    for stem, counts in [
        ("01_approvals_by_period", permits),
        ("02_recompletion_by_period", activity),
    ]:
        write_yearly_table(
            out,
            stem,
            [dict(r, value=r["count"]) for r in counts],
            partial_year,
            is_count=True,
        )
    write_yearly_table(
        out,
        "03_approvals_per_well",
        [
            dict(
                year=r["year"],
                band=r["band"],
                completion_approvals=r["count"],
                january_well_years=r["exposure"],
                value=r["count"] / r["exposure"] if r["exposure"] else None,
            )
            for r in rates
        ],
        partial_year,
    )

    permit_rows = summarize(permits, mode="per_year")
    write_csv(
        permit_rows, out, "appendix_01_approvals_by_period", permit_rows[0].keys()
    )

    work_rows = summarize(activity, mode="per_year")
    group_totals, band_totals = {}, {}
    for row in work_rows:
        group = row["group"]
        group_totals[group] = group_totals.get(group, 0) + row["count"]
        key = group, row["band"]
        band_totals[key] = band_totals.get(key, 0) + row["count"]
    for row in work_rows:
        total = group_totals[row["group"]]
        row["cell_share_of_group_percent"] = percent(row["count"], total)
        row["band_share_of_group_percent"] = percent(
            band_totals[row["group"], row["band"]], total
        )
    write_csv(work_rows, out, "appendix_02_recompletion_by_period", work_rows[0].keys())

    rate_rows = summarize(rates, mode="per_well")
    for row in rate_rows:
        row["completion_approvals"] = row.pop("count")
        row["january_well_years"] = row.pop("exposure")
        row["approvals_per_january_well_year"] = row.pop("value")
    write_csv(rate_rows, out, "appendix_03_approvals_per_well", rate_rows[0].keys())


def tally(events, key):
    out = {}
    for e in events:
        out[e[key]] = out.get(e[key], 0) + 1
    return out


def spread(values):
    if not values:
        return dict(n=0, p25_days="", median_days="", p75_days="")
    return dict(
        n=len(values),
        p25_days=round(quantile(values, 0.25), 1),
        median_days=round(quantile(values, 0.5), 1),
        p75_days=round(quantile(values, 0.75), 1),
    )


def percent(part, whole):
    return round(100 * part / whole, 1) if whole else ""


def drilled_observations(
    inventory, types, initial, file_date, *, include_unknown_depth=False
):
    """Group distinct drilled wells by first spud and any initial permit by cutoff."""
    approved = {a["api10"] for a in initial if a["date"] and a["date"] <= file_date}
    groups = {"exploration": "Exploratory wells", "development": "Development wells"}
    observations = {group: [] for group in groups.values()}
    for well in inventory.itertuples():
        group = groups.get(types.get(well.api10))
        if group is None or ci.pd.isna(well.spud):
            continue
        if well.band == "no depth" and not include_unknown_depth:
            continue
        if well.spud.date() <= file_date:
            observations[group].append(
                dict(
                    year=well.spud.year,
                    band=well.band,
                    count=int(well.api10 in approved),
                    exposure=1,
                )
            )

    return observations


def drilled_spud_exclusions(inventory, types, first_year, file_date):
    """Count dated wells otherwise eligible for the depth-band drilling cohorts."""
    eligible = inventory.api10.map(types).isin(["exploration", "development"])
    spuds = inventory.loc[eligible & inventory.band.ne("no depth"), "spud"]
    return {
        "before_first_year": int((spuds.dt.year < first_year).sum()),
        "after_file_date": int(
            (spuds.dt.normalize() > ci.pd.Timestamp(file_date)).sum()
        ),
    }


def drilled_year_rows(observations, years):
    result = []
    for group, wells in observations.items():
        drilled, approved = Counter(), Counter()
        for well in wells:
            key = well["year"], well["band"]
            drilled[key] += well["exposure"]
            approved[key] += well["count"]
        for year in years:
            for band in BANDS[:-1]:
                key = year, band
                n, done = drilled[key], approved[key]
                result.append(
                    dict(
                        group=group,
                        year=year,
                        band=band,
                        wells_first_drilled=n,
                        with_initial_completion_approval=done,
                        value=100 * done / n if n else None,
                    )
                )
    return result


def drilled_period_table(inventory, types, initial, file_date):
    """Return the historical period table for the supplied drilling cohort."""
    return _drilled_period_rows(
        drilled_observations(inventory, types, initial, file_date), file_date
    )


def _drilled_period_rows(observations, file_date):
    observed = f"Initial completion approvals observed through {file_date:%d %B %Y}."
    recent = observed + " These recently drilled wells had little time for approval."
    result = []
    for group, rows in observations.items():
        for cell in summarize(rows, mode="per_well"):
            drilled, with_approval = cell["exposure"], cell["count"]
            result.append(
                dict(
                    group=group,
                    period=cell["period"],
                    band=cell["band"],
                    wells_first_drilled=drilled,
                    with_initial_completion_approval=with_approval,
                    share_percent=percent(with_approval, drilled),
                    follow_up=recent if cell["period"] == PERIODS[-1] else observed,
                )
            )
    return result


def suboperation_table(approvals, subcodes, names):
    """Approvals carrying each sub-operation, split by kind of approval.

    One approval can carry several sub-operations, so the rows do not sum to
    the number of approvals. Each row does split exactly between the two
    kinds, and the last share is of the other completion work only.
    """
    carried = {}
    for a in approvals:
        for code in subcodes.get(a["sn"], set()) or {"(none)"}:
            row = carried.setdefault(code, {k: 0 for k in KINDS})
            row[a["kind"]] += 1
    others = sum(1 for a in approvals if a["kind"] == KINDS[1])
    rows = [
        dict(
            suboperation=code,
            description=names.get(code, "no sub-operation row"),
            approvals=sum(by_kind.values()),
            share_percent=percent(sum(by_kind.values()), len(approvals)),
            on_initial_completion=by_kind[KINDS[0]],
            on_other_completion_work=by_kind[KINDS[1]],
            share_of_other_percent=percent(by_kind[KINDS[1]], others),
        )
        for code, by_kind in carried.items()
    ]
    return sorted(rows, key=lambda r: (-r["approvals"], r["suboperation"]))


def c6_cross_check(data_dir, years, mine_approvals, mine_reports):
    """Compare the tallies with C6's own code on the same archives."""
    bore = ci.read_table(data_dir, BOREHOLE, "mv_boreholes_all")
    _, apm, _, _ = ci.classified_permits(data_dir, bore)
    c6 = apm[apm.group.eq(SHARED_GROUP) & apm.year.isin(years)]
    theirs_a = {
        (int(y), b): int(n) for (y, b), n in c6.groupby(["year", "band"]).size().items()
    }
    # The same steps C6's run() applies to the End of Operations Reports.
    eor = ci.read_table(
        data_dir,
        EOR,
        "mv_eor_mainquery",
        [
            "SN_EOR",
            "API_WELL_NUMBER",
            "EOR_OPERATION_CD",
            "BOREHOLE_STAT_DT",
            "SURF_LEASE_NUMBER",
        ],
    ).drop_duplicates()
    if eor.SN_EOR.duplicated().any():
        raise ValueError("conflicting EOR keys")
    eor = ci.gulf_only(eor, bore)
    eor = ci.attach_depth(eor[eor.region.eq("G")], bore)
    eor["year"] = ci.dates(eor.BOREHOLE_STAT_DT).dt.year
    c = eor[eor.EOR_OPERATION_CD.eq("C") & eor.year.isin(years)]
    theirs_r = {
        (int(y), b): int(n) for (y, b), n in c.groupby(["year", "band"]).size().items()
    }

    def side(mine, theirs):
        cells = [(y, b) for y in years for b in BANDS]
        return dict(
            this_article=sum(mine.values()),
            c6_code=sum(theirs.values()),
            cells_compared=len(cells),
            cells_different=sum(
                abs(mine.get(k, 0) - theirs.get(k, 0)) > TOLERANCE for k in cells
            )
            + sum(k not in cells for k in theirs),
        )

    return (
        dict(
            comparator="count_interventions.classified_permits and the End of "
            "Operations Report steps of count_interventions.run, unmodified",
            tolerance=TOLERANCE,
            approvals=side(mine_approvals, theirs_a),
            reports=side(mine_reports, theirs_r),
        ),
        bore,
        apm[["APM_OP_CD", "year", "band", "group"]],
    )


def hand_counts(permits, subcodes, bores, approvals, reports):
    """The same slices that were counted by hand from the extracted text."""

    def bands(events):
        t = tally(events, "band")
        return {b: t.get(b, 0) for b in BANDS}

    listed = [
        (sn, row)
        for sn, row in permits.items()
        if row["APM_OP_CD"] == "COMP"
        and bores.region(norm_api(row["API_WELL_NUMBER"]), row["SURF_LEASE_NUM"]) == "G"
        and (parse_date(row["ACC_STATUS_DATE"]) or dt.date.min).timetuple()[:2]
        == (2025, 3)
    ]
    march = [
        a for a in approvals if a["date"] and (a["year"], a["date"].month) == (2025, 3)
    ]
    initial = [a for a in march if a["kind"] == KINDS[0]]
    q1 = [
        r for r in reports if r["date"] and r["year"] == 2025 and r["date"].month <= 3
    ]
    return dict(
        approvals_2025_03=dict(
            comp_permits_listed=len(listed),
            with_change_zone=sum("ZONE" in subcodes.get(sn, set()) for sn, _ in listed),
            completion_approvals=len(march),
            by_band=bands(march),
            initial_completion=len(initial),
            initial_by_band=bands(initial),
            bores_with_initial_completion=len({a["api12"] for a in initial}),
        ),
        reports_2025_q1=dict(
            completion_reports=len(q1),
            by_band=bands(q1),
            bores=len({r["api12"] for r in q1}),
        ),
    )


def write_hand_count_csv(out, samples):
    gulf_rule = (
        " Select region G by bore, then by well if unique. If neither resolves "
        "the region, use a surface lease beginning with G."
    )
    region_fields = "mv_boreholes_all.txt (API_WELL_NUMBER, REGION_CODE)"
    rows = [
        dict(
            sample="completion_approvals",
            period="2025-03",
            selection=(
                "Distinct Gulf permits approved in the month with APM_OP_CD = COMP. "
                "Exclude ZONE, PLUGBACK and explicit new hole work." + gulf_rule
            ),
            source_files=f"{APM}, {BOREHOLE}",
            source_fields=(
                "mv_apm_main.txt (SN_APM, API_WELL_NUMBER, SURF_LEASE_NUM, "
                "ACC_STATUS_DATE, APM_OP_CD), mv_apm_suboperations.txt "
                "(SN_APM_FK, APM_SUBOP_CD), mv_apm_main_prop.txt (SN_APM, APM_OP_DESC), "
                + region_fields
            ),
            count=samples["approvals_2025_03"]["completion_approvals"],
        ),
        dict(
            sample="completion_reports",
            period="2025-Q1",
            selection=(
                "Distinct Gulf End of Operations Reports with EOR_OPERATION_CD = C "
                "and borehole status date in the quarter. Include every status code."
                + gulf_rule
            ),
            source_files=f"{EOR}, {BOREHOLE}",
            source_fields=(
                "mv_eor_mainquery.txt (SN_EOR, API_WELL_NUMBER, SURF_LEASE_NUMBER, "
                "BOREHOLE_STAT_DT, EOR_OPERATION_CD), " + region_fields
            ),
            count=samples["reports_2025_q1"]["completion_reports"],
        ),
    ]
    write_csv(
        rows,
        out,
        "hand_counts",
        ["sample", "period", "selection", "source_files", "source_fields", "count"],
    )


def run_record():
    def git(*args):
        try:
            return subprocess.run(
                ["git", "-C", str(ROOT), *args],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    return dict(
        code_commit=git("rev-parse", "HEAD"),
        code_uncommitted_changes=bool(
            git("status", "--porcelain", "--", "*.py", "../interventions_by_depth/*.py")
        ),
        # Folder arguments are recorded by their last component only, so the
        # record carries no machine path.
        command="uv run python -I "
        + " ".join(a if a.startswith("--") else Path(a).name for a in sys.argv),
        python=platform.python_version(),
        pandas=ci.pd.__version__,
        timestamp_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def run(data_dir, out):
    data_dir, out = Path(data_dir), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    basis = json.loads((ROOT / "series_basis.json").read_text(encoding="utf-8"))
    verify_basis(data_dir, basis)
    file_date = dt.date.fromisoformat(basis["file_date"])

    bore_rows = read_member(data_dir, BOREHOLE, "mv_boreholes_all")
    apm_rows = read_member(data_dir, APM, "mv_apm_main")
    subop_rows = read_member(data_dir, APM, "mv_apm_suboperations")
    # Latin-1 keeps every source byte of the narratives, as in C6. They are
    # read for the new-hole screen only and are never written out.
    narrative_rows = read_member(data_dir, APM, "mv_apm_main_prop", encoding="latin1")
    eor_rows = read_member(data_dir, EOR, "mv_eor_mainquery")
    interval_rows = read_member(data_dir, EOR, "mv_eor_completions")
    perf_rows = read_member(data_dir, EOR, "mv_eor_perf_intervals")
    subop_names = {
        r["VALUE"]: r["DESCRIP"]
        for r in read_member(data_dir, APM, "mv_apm_suboperation_codes")
    }
    bores = Bores(bore_rows)
    permits = unique_rows(
        apm_rows, "SN_APM", ["API_WELL_NUMBER", "ACC_STATUS_DATE", "APM_OP_CD"]
    )
    subcodes = grouped(subop_rows, "SN_APM_FK", "APM_SUBOP_CD")

    approvals = completion_approvals(apm_rows, subop_rows, narrative_rows, bore_rows)
    reports = completion_reports(eor_rows, bore_rows)
    first_date = min(
        d for d in (parse_date(r["ACC_STATUS_DATE"]) for r in permits.values()) if d
    )
    first_year, last_full_year, part_year = window(first_date, file_date)
    years = list(range(first_year, (part_year or last_full_year) + 1))
    in_years = set(years)

    def partial(rows):
        for r in rows:
            r["partial_year"] = r["year"] == part_year
        return rows

    # 1. Completion approvals, the group C6 sets aside.
    a_table = year_band_table(approvals, years, kinds=KINDS)
    a_checks = conservation(approvals, a_table, years)
    write_csv(
        partial([dict(r, approvals=r["count"]) for r in a_table]),
        out,
        "completion_approvals_by_year_band",
        ["year", "band", "kind", "approvals", "partial_year"],
    )
    in_window = [a for a in approvals if a["year"] in in_years]
    write_csv(
        suboperation_table(in_window, subcodes, subop_names),
        out,
        "completion_approval_suboperations",
        [
            "suboperation",
            "description",
            "approvals",
            "share_percent",
            "on_initial_completion",
            "on_other_completion_work",
            "share_of_other_percent",
        ],
    )

    # 2. Completion reports, counted as C6 counts them.
    r_table = year_band_table(reports, years)
    r_checks = conservation(reports, r_table, years)
    write_csv(
        partial([dict(r, reports=r["count"]) for r in r_table]),
        out,
        "completion_reports_by_year_band",
        ["year", "band", "reports", "partial_year"],
    )

    # 3. Bores first completed, by each record. The first record is taken
    # over every year in the file, then the window is applied.
    initial = [a for a in approvals if a["kind"] == KINDS[0]]
    first_a_all = first_per_bore(initial)
    first_r_all = first_per_bore(reports)
    first_a = [e for e in first_a_all if e["year"] in in_years]
    first_r = [e for e in first_r_all if e["year"] in in_years]
    b_rows = []
    for basis_name, events in [("approval", first_a), ("report", first_r)]:
        for r in year_band_table(events, years):
            b_rows.append(dict(r, basis=basis_name, bores=r["count"]))
    write_csv(
        partial(b_rows),
        out,
        "bores_first_completed_by_year_band",
        ["year", "band", "basis", "bores", "partial_year"],
    )
    b_checks = {
        "bores_by_approval_counted_once": len({e["api12"] for e in first_a})
        == len(first_a)
        == sum(r["bores"] for r in b_rows if r["basis"] == "approval"),
        "bores_by_report_counted_once": len({e["api12"] for e in first_r})
        == len(first_r)
        == sum(r["bores"] for r in b_rows if r["basis"] == "report"),
    }

    # 4. The two records against each other.
    match = match_summary(first_a, first_r_all)
    match_back = match_summary(first_a_all, first_r)
    lags = match["lag_days"]
    per_bore = tally(
        [a for a in initial if a["api12"] in {e["api12"] for e in first_a}], "api12"
    )
    write_csv(
        [
            dict(metric=k, value=v)
            for k, v in [
                (
                    "bores first approved in the window",
                    match["bores_with_initial_completion_approval"],
                ),
                (
                    "of which with a completion report in the file",
                    match["of_which_with_completion_report"],
                ),
                (
                    "bores first reported in the window",
                    match_back["bores_with_completion_report"],
                ),
                (
                    "of which with an initial completion approval in the file",
                    match_back["of_which_with_initial_completion_approval"],
                ),
                ("days from first approval to status date, p25", quantile(lags, 0.25)),
                (
                    "days from first approval to status date, median",
                    quantile(lags, 0.5),
                ),
                ("days from first approval to status date, p75", quantile(lags, 0.75)),
                (
                    "matched bores with a status date before the approval",
                    sum(v < 0 for v in lags),
                ),
                (
                    "initial completion approvals per bore, mean",
                    round(sum(per_bore.values()) / len(per_bore), 2),
                ),
                (
                    "initial completion approvals per bore, median",
                    quantile(list(per_bore.values()), 0.5),
                ),
                (
                    "bores with one initial completion approval",
                    sum(v == 1 for v in per_bore.values()),
                ),
            ]
        ],
        out,
        "approval_report_match",
        ["metric", "value"],
    )

    # 5. What the reports of the bores first reported in the window record.
    cohort = {e["api12"]: e for e in first_r}
    cohort_reports = [r for r in reports if r["api12"] in cohort]
    attrs = bore_attributes(cohort_reports, interval_rows, perf_rows)
    attr_rows, perf_table = [], []

    def bin_of(n):
        return INTERVAL_BINS[min(n, 3)]

    features = [
        ("fluid", FLUIDS, lambda a: a["fluid"]),
        ("subsea completion flag", FLAGS, lambda a: a["subsea"]),
        (
            "completion intervals reported",
            INTERVAL_BINS,
            lambda a: bin_of(a["intervals"]),
        ),
        (
            "interval label beginning with D",
            ["yes", "no"],
            lambda a: "yes" if a["dual"] else "no",
        ),
    ]
    for band in BANDS + [ALL]:
        members = [api for api, e in cohort.items() if band in (e["band"], ALL)]
        for attribute, values, pick in features:
            t = {}
            for api in members:
                t[pick(attrs[api])] = t.get(pick(attrs[api]), 0) + 1
            for value in values:
                attr_rows.append(
                    dict(
                        band=band,
                        attribute=attribute,
                        value=value,
                        bores=t.get(value, 0),
                        share_percent=percent(t.get(value, 0), len(members)),
                    )
                )
        perfs = [n for api in members for n in attrs[api]["perforations"]]
        for value in INTERVAL_BINS:
            n = sum(bin_of(p) == value for p in perfs)
            perf_table.append(
                dict(
                    band=band,
                    perforated_intervals=value,
                    completion_intervals=n,
                    share_percent=percent(n, len(perfs)),
                )
            )
    # The by-band rows carry the cohort once; the all-depth rows repeat it and
    # are written to their own file so that each file sums to the cohort.
    write_csv(
        [r for r in attr_rows if r["band"] != ALL],
        out,
        "bore_attributes_by_band",
        ["band", "attribute", "value", "bores", "share_percent"],
    )
    write_csv(
        [r for r in attr_rows if r["band"] == ALL],
        out,
        "bore_attributes_all_depths",
        ["attribute", "value", "bores", "share_percent"],
    )
    write_csv(
        perf_table,
        out,
        "perforated_intervals_by_band",
        ["band", "perforated_intervals", "completion_intervals", "share_percent"],
    )
    fluid_rows = []
    for year in years:
        members = [api for api, e in cohort.items() if e["year"] == year]
        t = tally([attrs[api] for api in members], "fluid")
        for fluid in FLUIDS:
            fluid_rows.append(dict(year=year, fluid=fluid, bores=t.get(fluid, 0)))
    write_csv(
        partial(fluid_rows),
        out,
        "fluid_by_year",
        ["year", "fluid", "bores", "partial_year"],
    )
    b_checks["attributes_sum_to_cohort"] = all(
        sum(
            r["bores"] for r in attr_rows if r["band"] != ALL and r["attribute"] == f[0]
        )
        == len(cohort)
        for f in features
    )
    b_checks["fluid_by_year_sums_to_cohort"] = sum(
        r["bores"] for r in fluid_rows
    ) == len(cohort)

    # 6. Hydraulic fracturing sub-operation on initial completion approvals.
    frac_bores = {a["api12"] for a in initial if a["frac"]}
    frac_first_year = min(
        (
            parse_date(permits[sn]["ACC_STATUS_DATE"]).year
            for sn, codes in subcodes.items()
            if "FRAC" in codes and sn in permits
        ),
        default=None,
    )
    frac_rows = [
        dict(
            year=year,
            bores_first_approved=sum(e["year"] == year for e in first_a),
            with_fracturing_suboperation=sum(
                e["year"] == year and e["api12"] in frac_bores for e in first_a
            ),
        )
        for year in years
    ]
    for r in frac_rows:
        r["share_percent"] = percent(
            r["with_fracturing_suboperation"], r["bores_first_approved"]
        )
    write_csv(
        partial(frac_rows),
        out,
        "fracturing_by_year",
        [
            "year",
            "bores_first_approved",
            "with_fracturing_suboperation",
            "share_percent",
            "partial_year",
        ],
    )
    frac_from = (frac_first_year or first_year) + 1  # first full year with the code
    frac_band = []
    for band in BANDS + [ALL]:
        members = [
            e for e in first_a if e["year"] >= frac_from and band in (e["band"], ALL)
        ]
        n = sum(e["api12"] in frac_bores for e in members)
        frac_band.append(
            dict(
                band=band,
                first_year=frac_from,
                bores_first_approved=len(members),
                with_fracturing_suboperation=n,
                share_percent=percent(n, len(members)),
            )
        )
    write_csv(
        frac_band,
        out,
        "fracturing_by_band",
        [
            "band",
            "first_year",
            "bores_first_approved",
            "with_fracturing_suboperation",
            "share_percent",
        ],
    )

    # 7. The C6 comparison, and the wells of C6's life-cycle cohort.
    mine_a, mine_r = {}, {}
    for r in a_table:
        mine_a[(r["year"], r["band"])] = (
            mine_a.get((r["year"], r["band"]), 0) + r["count"]
        )
    for r in r_table:
        mine_r[(r["year"], r["band"])] = r["count"]
    cross, bore_frame, classified = c6_cross_check(data_dir, years, mine_a, mine_r)
    stock = ci.standing_wells(bore_frame, years, at="start")
    write_trend_tables(out, years, in_window, subcodes, classified, stock, part_year)

    import well_life_cycle as wl  # C6's well and well-type rules

    inventory = ci.well_inventory(bore_frame)
    types = wl.well_types(bore_frame)
    observations = drilled_observations(inventory, types, initial, file_date)
    write_yearly_table(
        out,
        "04_drilled_to_completed",
        drilled_year_rows(observations, years),
        part_year,
    )
    by_period = _drilled_period_rows(observations, file_date)
    write_csv(by_period, out, "appendix_04_drilled_to_completed", by_period[0].keys())

    approved_wells = {a["api10"] for a in initial}
    drilled = []
    cohort_wells = {}
    for well in inventory.itertuples():
        if ci.pd.isna(well.spud) or not first_year <= well.spud.year <= last_full_year:
            continue
        kind = types.get(well.api10)
        kind = kind if isinstance(kind, str) else WELL_TYPES[2]
        cohort_wells.setdefault(kind, []).append(
            (well.band, well.api10 in approved_wells)
        )
    for kind in WELL_TYPES:
        for band in BANDS + [ALL]:
            members = [
                done for b, done in cohort_wells.get(kind, []) if band in (b, ALL)
            ]
            drilled.append(
                dict(
                    well_type=kind,
                    band=band,
                    wells_first_drilled=len(members),
                    with_initial_completion_approval=sum(members),
                    share_percent=percent(sum(members), len(members)),
                )
            )
    write_csv(
        drilled,
        out,
        "drilled_to_completed",
        [
            "well_type",
            "band",
            "wells_first_drilled",
            "with_initial_completion_approval",
            "share_percent",
        ],
    )

    # 8. Days from total depth to the first approval and to the status date.
    total_depth = {
        norm_api(r["API_WELL_NUMBER"]): parse_date(r["TOTAL_DEPTH_DATE"])
        for r in bore_rows
    }
    reported = {e["api12"]: e for e in first_r_all}
    timing = []
    for band in BANDS + [ALL]:
        members = [e for e in first_a if band in (e["band"], ALL)]
        to_approval, to_status, approval_to_status = [], [], []
        for e in members:
            td = total_depth.get(e["api12"])
            rep = reported.get(e["api12"])
            if td:
                to_approval.append((e["date"] - td).days)
            if td and rep:
                to_status.append((rep["date"] - td).days)
            if rep:
                approval_to_status.append((rep["date"] - e["date"]).days)
        for measure, values in [
            ("total depth date to first initial completion approval", to_approval),
            ("total depth date to completion status date", to_status),
            (
                "first initial completion approval to completion status date",
                approval_to_status,
            ),
        ]:
            timing.append(dict(band=band, measure=measure, **spread(values)))
    write_csv(
        timing,
        out,
        "timing_by_band",
        ["band", "measure", "n", "p25_days", "median_days", "p75_days"],
    )

    report_dates = {}
    for r in reports:
        report_dates.setdefault(r["api12"], []).append(r["date"])
    repeat_bores = {
        api: set(dates) for api, dates in report_dates.items() if len(dates) > 1
    }
    by_band = tally(in_window, "band")
    by_year = tally(in_window, "year")
    status = tally([r for r in reports if r["year"] in in_years], "status")
    write_csv(
        [
            dict(
                report_status_code=code,
                reports=count,
                all_reports_in_window=r_checks["in_window"],
                first_year=first_year,
                snapshot_date=str(file_date),
            )
            for code, count in sorted(status.items())
        ],
        out,
        "report_status_counts",
        [
            "report_status_code",
            "reports",
            "all_reports_in_window",
            "first_year",
            "snapshot_date",
        ],
    )
    summary = dict(
        file_date=str(file_date),
        first_full_year=first_year,
        last_full_year=last_full_year,
        partial_year=part_year,
        apm_rows=len(apm_rows),
        unique_permits=len(permits),
        completion_approvals=len(in_window),
        completion_approvals_outside_window=a_checks["outside_window"],
        completion_approvals_by_band={b: by_band.get(b, 0) for b in BANDS},
        completion_approvals_by_year={str(y): by_year.get(y, 0) for y in years},
        initial_completion_approvals=sum(a["kind"] == KINDS[0] for a in in_window),
        other_completion_work_approvals=sum(a["kind"] == KINDS[1] for a in in_window),
        bores_first_completed_by_approval=len(first_a),
        wells_first_completed_by_approval=len({e["api10"] for e in first_a}),
        bores_first_completed_by_report=len(first_r),
        wells_first_completed_by_report=len({e["api10"] for e in first_r}),
        completion_reports_all_years=len(reports),
        bores_with_more_than_one_completion_report=len(repeat_bores),
        of_which_every_report_has_the_same_status_date=sum(
            len(dates) == 1 for dates in repeat_bores.values()
        ),
        completion_reports_in_window=r_checks["in_window"],
        completion_reports_in_window_by_status=dict(sorted(status.items())),
        completion_intervals_read=sum(len(a["perforations"]) for a in attrs.values()),
        fracturing_code_first_year=frac_first_year,
        drilled_wells_excluded_by_spud_date=drilled_spud_exclusions(
            inventory, types, first_year, file_date
        ),
    )
    write_json(summary, out, "summary")
    checks = {f"approvals_{k}": v for k, v in a_checks["checks"].items()}
    checks.update({f"reports_{k}": v for k, v in r_checks["checks"].items()})
    checks.update(b_checks)
    samples = hand_counts(permits, subcodes, bores, approvals, reports)
    write_hand_count_csv(out, samples)
    verification = dict(
        basis=dict(files=basis["files"]),
        conservation=dict(ok=all(checks.values()), checks=checks),
        c6_cross_check=cross,
        hand_counts=samples,
        run=run_record(),
    )
    write_json(verification, out, "verification")
    if not verification["conservation"]["ok"]:
        raise RuntimeError("a conservation check failed; see verification.json")
    for side in ("approvals", "reports"):
        if (
            cross[side]["cells_different"]
            or cross[side]["this_article"] != cross[side]["c6_code"]
        ):
            raise RuntimeError(f"{side} differ from C6's code; see verification.json")
    all_drilled = drilled_observations(
        inventory, types, initial, file_date, include_unknown_depth=True
    )
    write_annual_trends(out, all_drilled)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    print(json.dumps(run(args.data_dir, args.out), indent=2))
