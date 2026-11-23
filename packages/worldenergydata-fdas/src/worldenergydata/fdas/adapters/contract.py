"""
FDAS production-input contract (F2, #715).

Bridges the repo's existing per-country production adapters
(``worldenergydata.production.unified`` — ``AbstractProductionAdapter`` with its
``STANDARD_COLUMNS`` output, 8 country implementations) into the column schema
the FDAS cashflow engine actually consumes. This is a **pure leaf**: pandas
only, no ``field_development`` import — the FieldConcept side lives in a separate
normalizer so this module stays free of member→root coupling.

Canonical FDAS production schema (what ``CashflowEngine.generate_monthly_cashflow``
reads): ``YEAR_MONTH`` + ``MONTHLY_OIL_BBL`` (+ water/gas + a dev grouping). This
resolves the pre-existing column split — ``fdas.data.production`` and the cashflow
engine use ``MONTHLY_OIL_BBL``/``_WATER_BBL``/``_GAS_MCF``, whereas the legacy
``fdas.adapters.bsee_adapter`` emitted ``MONTHLY_*_VOLUME`` (live-but-incompatible
public API; reconciliation tracked as a follow-on). The contract pins ``_BBL``/
``_MCF``.

Author: WorldEnergyData Team
Issue:  https://github.com/vamseeachanta/worldenergydata/issues/715
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# The unified per-country adapter output contract
# (worldenergydata.production.unified.query.STANDARD_COLUMNS). Duplicated here as
# a required-input constant so this leaf does not import the production member.
UNIFIED_REQUIRED_COLUMNS = (
    "region",
    "field_name",
    "year",
    "month",
    "oil_bbl",
    "gas_mcf",
    "water_bbl",
)

# Canonical FDAS monthly-production columns (what the cashflow engine reads).
FDAS_PRODUCTION_COLUMNS = (
    "YEAR_MONTH",  # "YYYY-MM"
    "DEV_NAME",  # development / field grouping key
    "MONTHLY_OIL_BBL",
    "MONTHLY_WATER_BBL",
    "MONTHLY_GAS_MCF",
)

_UNIFIED_TO_FDAS = {
    "oil_bbl": "MONTHLY_OIL_BBL",
    "water_bbl": "MONTHLY_WATER_BBL",
    "gas_mcf": "MONTHLY_GAS_MCF",
}


class FdasContractError(ValueError):
    """Raised when a unified frame cannot be normalized to the FDAS schema."""


def _empty_fdas_production() -> pd.DataFrame:
    """A correctly-typed empty FDAS production frame."""
    return pd.DataFrame(
        {
            "YEAR_MONTH": pd.Series(dtype="object"),
            "DEV_NAME": pd.Series(dtype="object"),
            "MONTHLY_OIL_BBL": pd.Series(dtype="float64"),
            "MONTHLY_WATER_BBL": pd.Series(dtype="float64"),
            "MONTHLY_GAS_MCF": pd.Series(dtype="float64"),
        }
    )


def to_fdas_production(
    unified_df: pd.DataFrame, *, dev_name_col: str = "field_name"
) -> pd.DataFrame:
    """Normalize a unified ``STANDARD_COLUMNS`` frame to FDAS monthly production.

    Args:
        unified_df: output of any ``AbstractProductionAdapter.fetch`` — must
            carry ``UNIFIED_REQUIRED_COLUMNS`` (year, month, oil/gas/water_bbl,
            field_name, region).
        dev_name_col: which unified column becomes ``DEV_NAME`` (default
            ``field_name``; a caller with a canonical field crosswalk may pass a
            resolved column instead).

    Returns:
        A DataFrame with exactly ``FDAS_PRODUCTION_COLUMNS``. ``YEAR_MONTH`` is a
        zero-padded ``"YYYY-MM"`` string built from ``year`` + ``month``.

    Raises:
        FdasContractError: required columns are missing (fail-closed — never
            silently emit a partial schema).
    """
    if unified_df is None or len(unified_df) == 0:
        return _empty_fdas_production()

    missing = [c for c in UNIFIED_REQUIRED_COLUMNS if c not in unified_df.columns]
    if dev_name_col not in unified_df.columns:
        missing.append(dev_name_col)
    if missing:
        raise FdasContractError(
            f"unified frame missing required column(s) {sorted(set(missing))}; "
            f"expected {list(UNIFIED_REQUIRED_COLUMNS)} (+ dev_name_col "
            f"{dev_name_col!r})"
        )

    year = pd.to_numeric(unified_df["year"], errors="coerce").astype("Int64")
    month = pd.to_numeric(unified_df["month"], errors="coerce").astype("Int64")
    if year.isna().any() or month.isna().any():
        raise FdasContractError("year/month contain non-numeric or null values")
    if not month.between(1, 12).all():
        raise FdasContractError("month values must be in 1..12")

    out = pd.DataFrame(
        {
            "YEAR_MONTH": [f"{y:04d}-{m:02d}" for y, m in zip(year, month)],
            "DEV_NAME": unified_df[dev_name_col].astype("object").values,
        }
    )
    for src, dst in _UNIFIED_TO_FDAS.items():
        out[dst] = (
            pd.to_numeric(unified_df[src], errors="coerce").astype("float64").values
        )
    # column order + membership pinned to the contract
    return out[list(FDAS_PRODUCTION_COLUMNS)]


@dataclass(frozen=True)
class FdasInputs:
    """The FDAS-ready bundle a country produces.

    v1 carries production only. The FieldConcept (from the separate
    ``field_concept_normalizer``) and any wells/drilling-timeline inputs are
    attached by the chain orchestration, keeping this contract a pure leaf. The
    wells/drilling source is an explicit follow-on (STANDARD_COLUMNS cannot carry
    per-well spud/API — see #715 plan R3).
    """

    production: pd.DataFrame
    region: str
    metadata: dict = field(default_factory=dict)
