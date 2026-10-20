"""Versioned local FX observations for annual disclosure money.

Quote direction is always USD per ONE unit of the reported currency. Only
calendar-year flows are eligible; these are not closing or transaction rates.
No network access, interpolation, inversion or fallback is performed.
"""

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


class FxRate(BaseModel):
    """One annual observation, with its direction fixed by the field name."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    currency: str
    fiscal_year: StrictInt
    usd_per_currency: Decimal = Field(gt=0)  # An exchange ratio must be positive.
    source: str

    @field_validator("currency", "source")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("currency and source must be nonblank")
        return value

    @field_validator("currency")
    @classmethod
    def foreign_currency(cls, value: str) -> str:
        if value == "USD":
            raise ValueError("USD uses the identity ratio, never a table observation")
        return value


class FxTable(BaseModel):
    """Immutable, explicitly versioned observations; duplicate keys are errors."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1)
    rates: tuple[FxRate, ...]

    @model_validator(mode="after")
    def unique_keys(self) -> "FxTable":
        keys = [(row.currency, row.fiscal_year) for row in self.rates]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate currency/fiscal-year FX key")
        return self


# Federal Reserve, Foreign Exchange Rates -- G.5A Annual, 2020 table,
# revised November 1, 2021; EUR and GBP rows, 2019/2020 columns and the
# starred note: "U.S. dollars per currency unit". Opened 2026-10-20.
# https://www.federalreserve.gov/releases/g5a/20210104/
_SOURCE = (
    "Federal Reserve G.5A Annual, 2020 table, revised 2021-11-01; "
    "EUR/GBP rows, 2019/2020 columns, starred quote-direction note; "
    "https://www.federalreserve.gov/releases/g5a/20210104/"
)
BASELINE_FX_TABLE = FxTable(
    version="g5a-2020-revised-2021-11-01-v1",
    rates=(
        FxRate(
            currency="EUR", fiscal_year=2019, usd_per_currency="1.1194", source=_SOURCE
        ),
        FxRate(
            currency="EUR", fiscal_year=2020, usd_per_currency="1.1410", source=_SOURCE
        ),
        FxRate(
            currency="GBP", fiscal_year=2019, usd_per_currency="1.2768", source=_SOURCE
        ),
        FxRate(
            currency="GBP", fiscal_year=2020, usd_per_currency="1.2829", source=_SOURCE
        ),
    ),
)
