"""Recover exact annual cells from the retained r2.3 tables when ZIPs are offline."""

import argparse
import hashlib
import io
import sys
from pathlib import Path

import pandas as pd
from lease_analysis import ALL, BANDS, DAYS_PER_YEAR, pct
from lease_yearly import observation, with_trends
from source_inputs import EXAMPLE, REPOSITORY, staged_build

# SHA-256 of the LF CSV blobs in the r2.3 baseline at 8dc3da650.
PINS = {
    "issuance": "c27d7cdace58b112d10f2c3c530b5dec4bbf78c6ee96efbb7aad9aace471cc00",
    "exploration": "133c529a8ca79268a8b08e72f26daf62ae880d49fa74878f3236f85723ad01a7",
    "current_status": "ed2728720de646f5316d1d2db093340ce18608631ec6cb89c21a37e28ba164e4",
    "first_production": "27a5a4f692589ad5aae2dc4fb4e91ccadfe6cee45c3c522ca6fa58cfe94b8ada",
}


def retained_table(directory, stem):
    data = (directory / f"{stem}.csv").read_bytes()
    if hashlib.sha256(data).hexdigest() != PINS[stem]:
        raise ValueError(f"{stem}.csv differs from the retained r2.3 baseline")
    return pd.read_csv(io.BytesIO(data), float_precision="round_trip")


def yearly_rows(table):
    return table.loc[
        table.issue_year.ne("All years") & table.depth_band.isin([*BANDS[:4], ALL])
    ]


def restricted_median_days(observed, within, p25, median):
    """Recover an exact prefix median from the full sample's linear quartiles.

    For these 2005 to 2020 effective dates the fifth anniversary is day 1826
    or 1827. Thus the shortest excluded wait is at least the longest possible
    included wait; exchanging ties at the boundary preserves the sorted values.
    """
    if within == 0:
        return None
    if within == observed:
        return median
    if (within - 1) / 2 == (observed - 1) / 4:
        return p25
    if observed == 5 and within == 4:
        # Full-sample ranks 2 and 3 are Q1 and Q2 (one-based ranks).
        return (p25 + median) / 2
    if observed == 3 and within == 1:
        # Q1 = (x1 + x2)/2 and Q2 = x2.
        return 2 * p25 - median
    return None


def retained_series(directory):
    rows = []
    for r in yearly_rows(retained_table(directory, "issuance")).itertuples():
        rows.append(
            observation(
                "effective_leases",
                r.depth_band,
                r.issue_year,
                r.leases,
                r.leases,
                r.leases,
            )
        )
    status = yearly_rows(retained_table(directory, "current_status"))
    for r in status[status.depth_band.eq(ALL)].itertuples():
        rows.append(
            observation(
                f"status_{r.status_code}",
                ALL,
                r.issue_year,
                r.cohort_leases,
                r.leases,
                pct(r.leases, r.cohort_leases),
            )
        )

    production = retained_table(directory, "first_production")
    crude = production[production.event.eq("Crude oil")].set_index(
        ["period", "depth_band"]
    )
    for r in yearly_rows(retained_table(directory, "exploration")).itertuples():
        year, band, n = int(r.issue_year), r.depth_band, r.leases
        observed, within = r.explored_leases, r.explored_within_five_years
        median = r.days_to_spud_median / DAYS_PER_YEAR
        rows.extend(
            [
                observation(
                    "spud_share_observed", band, year, n, observed, pct(observed, n)
                ),
                observation("spud_share_5y", band, year, n, within, pct(within, n)),
                observation("spud_years_observed", band, year, n, observed, median),
            ]
        )
        days = restricted_median_days(
            observed, within, r.days_to_spud_p25, r.days_to_spud_median
        )
        known = within == 0 or days is not None
        rows.append(
            observation(
                "spud_years_5y",
                band,
                year,
                n,
                within,
                days / DAYS_PER_YEAR if days is not None else None,
                "verified" if known else "unavailable",
            )
        )
        # r2.3 retained crude outcomes by period. A single-year row is exact.
        # A zero event count for a whole period also fixes every annual count.
        start = year // 5 * 5
        period = "2020 only" if year == 2020 else f"{start} to {start + 4}"
        pool = crude.loc[(period, band)]
        known = year == 2020 or pool.timed_leases == 0 or n == 0
        events = int(pool.timed_leases) if year == 2020 else (0 if known else None)
        availability = "verified" if known else "unavailable"
        rows.append(
            observation(
                "crude_share_5y",
                band,
                year,
                n,
                events,
                pct(events, n) if known else None,
                availability,
            )
        )
        rows.append(
            observation(
                "crude_years_5y",
                band,
                year,
                n,
                events,
                pool.months_median / 12 if year == 2020 else None,
                availability,
            )
        )
    return with_trends(rows)


def build_retained(destination):
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            "Choose a fresh --output-dir for the retained-table build"
        )
    from lease_charts import write_figures

    data = retained_series(EXAMPLE / "output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with staged_build(destination.parent) as scratch:
        data.to_csv(scratch / "annual_trends.csv", index=False, lineterminator="\n")
        write_figures(scratch, EXAMPLE / "output/exploration.csv")
        scratch.rename(destination)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Fresh directory for CSV, SVG, HTML and manifest",
    )
    args = parser.parse_args()
    # An example can run directly from a checkout without installing the BSEE package.
    sys.path.insert(0, str(REPOSITORY / "packages/worldenergydata-bsee/src"))
    data = build_retained(args.output_dir)
    print(data.groupby(["metric", "availability"]).size().to_string())
