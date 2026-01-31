# ABOUTME: Classifies OGOR production records as well-test, commercial, or non-producing
# ABOUTME: Uses PRODUCT_CODE, WELL_STAT_CD, and first_oil dates with priority ordering
from __future__ import annotations

import pandas as pd


class ProductionClass:
    WELL_TEST = "well_test"
    COMMERCIAL = "commercial"
    NON_PRODUCING = "non_producing"


def _clean_code_column(series: pd.Series) -> pd.Series:
    """Strip whitespace, quotes, and uppercase a code column."""
    return series.astype(str).str.strip().str.replace('"', "", regex=False).str.upper()


def classify_production(
    df: pd.DataFrame,
    first_oil_map: dict[str, pd.Timestamp] | None = None,
    development_col: str = "development",
) -> pd.DataFrame:
    """Add a ``production_class`` column to *df* using priority rules.

    Classification priority:
      1. PRODUCT_CODE='T'  => well_test
      2. WELL_STAT_CD='1' (Exploratory) + oil > 0  => well_test
      3. date < first_oil for the development  => well_test
      4. oil > 0  => commercial
      5. oil == 0  => non_producing

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: oil_bbl, PRODUCT_CODE, WELL_STAT_CD, date.
        Optionally *development_col* for per-development first_oil lookup.
    first_oil_map : dict, optional
        Mapping of development name -> first_oil Timestamp.
    development_col : str
        Column name holding the development identifier.
    """
    result = df.copy()

    # Clean code columns
    result["_pc"] = _clean_code_column(result["PRODUCT_CODE"])
    result["_ws"] = _clean_code_column(result["WELL_STAT_CD"])

    # Default: classify by oil volume (rules 4 & 5)
    result["production_class"] = result["oil_bbl"].apply(
        lambda v: ProductionClass.COMMERCIAL if v > 0 else ProductionClass.NON_PRODUCING
    )

    # Rule 3: date < first_oil => well_test (only where oil > 0)
    if first_oil_map and development_col in result.columns:
        for dev_name, first_oil_ts in first_oil_map.items():
            mask = (
                (result[development_col] == dev_name)
                & (result["date"] < first_oil_ts)
                & (result["oil_bbl"] > 0)
            )
            result.loc[mask, "production_class"] = ProductionClass.WELL_TEST

    # Rule 2: WELL_STAT_CD='1' + oil > 0 => well_test (overrides rule 3/4)
    mask_exploratory = (result["_ws"] == "1") & (result["oil_bbl"] > 0)
    result.loc[mask_exploratory, "production_class"] = ProductionClass.WELL_TEST

    # Rule 2b: WELL_STAT_CD='1' + oil == 0 => non_producing
    mask_exploratory_zero = (result["_ws"] == "1") & (result["oil_bbl"] == 0)
    result.loc[mask_exploratory_zero, "production_class"] = (
        ProductionClass.NON_PRODUCING
    )

    # Rule 1: PRODUCT_CODE='T' => well_test (highest priority)
    mask_t = result["_pc"] == "T"
    result.loc[mask_t, "production_class"] = ProductionClass.WELL_TEST

    # Drop working columns
    result.drop(columns=["_pc", "_ws"], inplace=True)

    return result


def summarize_classification(
    df: pd.DataFrame,
    development_col: str = "development",
) -> dict[str, dict]:
    """Summarize classified production per development.

    Returns a dict keyed by development name with:
      - commercial_oil_bbl, well_test_oil_bbl
      - commercial_count, well_test_count, non_producing_count
    """
    summary: dict[str, dict] = {}
    for dev_name, group in df.groupby(development_col):
        commercial = group[group["production_class"] == ProductionClass.COMMERCIAL]
        well_test = group[group["production_class"] == ProductionClass.WELL_TEST]
        non_producing = group[
            group["production_class"] == ProductionClass.NON_PRODUCING
        ]
        summary[dev_name] = {
            "commercial_oil_bbl": float(commercial["oil_bbl"].sum()),
            "well_test_oil_bbl": float(well_test["oil_bbl"].sum()),
            "commercial_count": len(commercial),
            "well_test_count": len(well_test),
            "non_producing_count": len(non_producing),
        }
    return summary
