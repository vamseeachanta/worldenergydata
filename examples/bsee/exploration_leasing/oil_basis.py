"""Read BSEE's monthly lease production detail for lease-to-first-oil timing.

Field basis: worldenergydata docs/knowledge-base/bsee/data-dictionaries/
production/production-fields.md and bsee/data/loaders/production/production_loader.py.
The latter reads binary pickles. Here the original headered CSV inside the
manifest-pinned ZIP supplies the same lease/month fields.
"""

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

MEMBER = "ProductionRawData/mv_productiondata.txt"
OIL = "LEASE_OIL_PROD"
HYDROCARBONS = [OIL, "LEASE_CONDN_PROD", "LEASE_GWG_PROD", "LEASE_OWG_PROD"]


def read_production(zip_path: Path, leases: pd.DataFrame):
    """Return first observed months, row audits, and source coverage metadata.

    The result contains one row per supplied lease. A missing event represents
    no positive reported volume in the supplied file. A first event before the
    effective month stays visible for exclusion from the relevant time sample.
    """
    if leases["lease_id"].duplicated().any() or leases["lease_id"].isna().any():
        raise ValueError("Production linkage requires a unique lease_id per lease")
    columns = ["LEASE_NUMBER", "PROD_YEAR", "PROD_MONTH", *HYDROCARBONS]
    with ZipFile(zip_path) as archive, archive.open(MEMBER) as handle:
        detail = pd.read_csv(handle, usecols=columns, dtype=str, keep_default_na=False)
    detail["lease_id"] = detail.pop("LEASE_NUMBER").str.strip()
    missing_id = detail["lease_id"].eq("")
    year, month = detail.pop("PROD_YEAR"), detail.pop("PROD_MONTH")
    if not (
        year.str.fullmatch(r"[0-9]{4}") & month.str.fullmatch(r"0?[1-9]|1[0-2]")
    ).all():
        raise ValueError("Invalid production date in lease detail")
    detail["month"] = pd.to_datetime(year + "-" + month.str.zfill(2), format="%Y-%m")
    if detail.loc[~missing_id].duplicated(["lease_id", "month"]).any():
        raise ValueError("Unexpected duplicate lease-month in production detail")

    volumes = detail[HYDROCARBONS].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(volumes.to_numpy()).all():
        raise ValueError("Missing or invalid hydrocarbon volume in lease detail")
    coverage = detail["month"].value_counts().sort_index()
    # The four volume series have two different units. Test each independently.
    detail["first_production_month"] = detail["month"].where(volumes.gt(0).any(axis=1))
    detail["first_oil_month"] = detail["month"].where(volumes[OIL].gt(0))
    in_cohort = ~missing_id & detail["lease_id"].isin(leases["lease_id"])
    matched = detail.loc[in_cohort]
    dates = ["first_production_month", "first_oil_month"]
    first = matched.groupby("lease_id")[dates].min()
    linked = leases[["lease_id", "effective_date"]].merge(
        first, how="left", on="lease_id", validate="one_to_one"
    )
    if linked["effective_date"].isna().any():
        raise ValueError("Production linkage requires a known effective date per lease")
    effective_month = linked["effective_date"].dt.to_period("M").dt.to_timestamp()
    audits = [
        {
            "stage": "ProductionRawData monthly detail matched to issuance cohort",
            "read": len(detail),
            "kept": len(matched),
            "drops": {
                "missing_lease_id": int(missing_id.sum()),
                "lease_outside_cohort": int((~missing_id & ~in_cohort).sum()),
            },
        }
    ]
    for event, field in [
        ("crude oil", "first_oil_month"),
        ("any hydrocarbon", "first_production_month"),
    ]:
        positive = matched[field].notna()
        audits.append(
            {
                "stage": f"Matched lease-month rows with positive {event}",
                "read": len(matched),
                "kept": len(matched.loc[positive]),
                "drops": {"no_positive_reported_volume": int((~positive).sum())},
            }
        )
    meta = {
        "first_source_month": coverage.index.min().strftime("%Y-%m"),
        "last_source_month": coverage.index.max().strftime("%Y-%m"),
        "last_source_month_rows": int(coverage.iloc[-1]),
        "source_rows": len(detail),
        "source_months_from_2005": [
            d.strftime("%Y-%m") for d in coverage.index if d.year >= 2005
        ],
        "production_before_effective_month": int(
            (linked["first_production_month"] < effective_month).sum()
        ),
        "oil_before_effective_month": int(
            (linked["first_oil_month"] < effective_month).sum()
        ),
        "cohort_leases_with_source_rows": len(first),
    }
    return linked[["lease_id", *dates]], audits, meta
