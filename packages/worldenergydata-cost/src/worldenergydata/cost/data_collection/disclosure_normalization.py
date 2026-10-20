"""Additive, reproducible monetary comparability for annual disclosures.

FX is applied before price rebasing. An explicit annual escalation assumption
is required; none is borrowed from the sanction-point predictor. Successful
normalization establishes only the caller-declared monetary/economic basis.
It does not authenticate that basis or approve a project benchmark.
"""

from __future__ import annotations

from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    Underflow,
    localcontext,
)
from hashlib import sha256
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from worldenergydata.cost.data_collection.fx_policy_v1 import BASELINE_FX_TABLE, FxTable

# Financial short-scale definitions. Powers match NIST SP 330 (2019),
# Table 7 (kilo, mega, giga): https://doi.org/10.6028/NIST.SP.330-2019 .
# "units" is the multiplicative identity; no SI status is claimed for money.
_SCALES = {
    "units": Decimal("1"),
    "thousand": Decimal("1000"),
    "million": Decimal("1000000"),
    "billion": Decimal("1000000000"),
}
_METHOD = "fx_then_base_year_adjustment_v1"


class DisclosureMoney(BaseModel):
    """As-reported monetary fields plus explicit eligibility metadata.

    Optional fields preserve incomplete evidence for a NOT_EVALUATED result.
    Unit must repeat the currency code; scale is separate, never inferred from
    a currency symbol or a suffix. ``comparison_basis`` is a caller-attested
    description of accounting perimeter, cash/accrual and gross/net interest.
    Provenance can retain the complete source record and its citation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    amount: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    magnitude_scale: str | None = None
    fiscal_year: StrictInt | None = Field(default=None, gt=0)
    as_reported_metric_name: str | None = None
    metric_name_normalized: str | None = None
    scope: str | None = None
    comparison_basis: str | None = None
    period_basis: str | None = None
    price_basis: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class NormalizationPolicy(BaseModel):
    """Versioned, caller-supplied price assumption and a static annual FX table.

    The rate and its evidence are required arguments, but may explicitly be
    None to record a missing assumption. Such a policy never produces a value.
    The full serialized policy is fingerprinted to separate comparison bases.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    policy_id: str = Field(min_length=1)
    # Target year from the repository issue-336 plan (2026-04-22), Scope Boundaries.
    base_year: StrictInt = Field(default=2020, gt=0)
    # Equation 3-13 requires 1+r > 0 for a positive, invertible price ratio.
    annual_escalation_rate: Decimal | None = Field(gt=Decimal("-1"))
    escalation_source: str | None
    fx_table: FxTable = BASELINE_FX_TABLE

    @property
    def fingerprint(self) -> str:
        return sha256(self.model_dump_json().encode("utf-8")).hexdigest()


class NormalizedDisclosureMoney(BaseModel):
    """Separate normalized fields; raw money is a deep snapshot.

    Amounts are base-year USD in individual units. Decimal values serialize as
    strings in JSON, avoiding binary-float rounding. No presentation rounding
    is performed. The comparison key is opaque and includes the entire policy.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    as_reported: DisclosureMoney
    normalization_status: Literal["NORMALIZED", "NOT_EVALUATED"]
    comparability_status: Literal["comparable", "not_comparable"]
    reasons: tuple[str, ...] = ()
    normalized_amount: Decimal | None = None
    normalized_currency: Literal["USD"] | None = None
    normalized_unit: Literal["USD"] | None = None
    normalized_magnitude_scale: Literal["units"] | None = None
    normalized_base_year: int | None = None
    normalization_method: str = _METHOD
    policy_id: str
    policy_fingerprint: str
    fx_table_version: str
    fx_rate: Decimal | None = None
    fx_source: str | None = None
    annual_escalation_rate: Decimal | None
    escalation_source: str | None
    comparison_key: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def consistent_status(self) -> "NormalizedDisclosureMoney":
        values = (
            self.normalized_amount,
            self.normalized_currency,
            self.normalized_unit,
            self.normalized_magnitude_scale,
            self.normalized_base_year,
            self.fx_rate,
            self.fx_source,
            self.comparison_key,
        )
        if self.normalization_status == "NORMALIZED":
            if (
                self.comparability_status != "comparable"
                or self.reasons
                or any(value is None for value in values)
            ):
                raise ValueError(
                    "normalized results require complete comparable fields"
                )
        elif (
            self.comparability_status != "not_comparable"
            or not self.reasons
            or any(value is not None for value in values)
        ):
            raise ValueError(
                "NOT_EVALUATED results require reasons and no normalized fields"
            )
        return self


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


def normalize_disclosure_money(
    record: DisclosureMoney,
    policy: NormalizationPolicy,
) -> NormalizedDisclosureMoney:
    """Normalize one row or preserve it with explicit reasons for ineligibility.

    C_base = amount * magnitude * USD_per_currency * (1+r)^(base_year-year).
    FX direction: Federal Reserve G.5A (2021 revision), starred currency note.
    Price adjustment: NIST HB 135 (2020), section 3.3.3.1, equation 3-13,
    https://doi.org/10.6028/NIST.HB.135-2020 . This is price escalation,
    not investment discounting or purchasing-power-parity conversion.
    """
    metadata = dict(
        as_reported=record.model_copy(deep=True),
        policy_id=policy.policy_id,
        policy_fingerprint=policy.fingerprint,
        fx_table_version=policy.fx_table.version,
        annual_escalation_rate=policy.annual_escalation_rate,
        escalation_source=policy.escalation_source,
    )
    reasons: list[str] = []
    if record.amount is None:
        reasons.append("missing_amount")
    for field, reason in (
        ("currency", "missing_currency"),
        ("unit", "missing_unit"),
        ("magnitude_scale", "missing_scale"),
        ("as_reported_metric_name", "missing_reported_metric"),
        ("metric_name_normalized", "missing_normalized_metric"),
        ("scope", "missing_scope"),
        ("comparison_basis", "missing_comparison_basis"),
    ):
        if _blank(getattr(record, field)):
            reasons.append(reason)
    if record.fiscal_year is None:
        reasons.append("missing_fiscal_year")
    if record.currency and record.unit and record.unit != record.currency:
        reasons.append("currency_unit_mismatch")
    if record.magnitude_scale and record.magnitude_scale not in _SCALES:
        reasons.append("unsupported_scale")
    if record.scope and record.scope not in {
        "operator",
        "project",
        "corporate",
        "segment",
    }:
        reasons.append("unsupported_scope")
    if record.period_basis != "calendar_year_flow":
        reasons.append("unsupported_period_basis")
    if record.price_basis != "nominal":
        reasons.append("unsupported_price_basis")
    if policy.annual_escalation_rate is None or _blank(policy.escalation_source):
        reasons.append("missing_escalation_evidence")

    def unevaluated() -> NormalizedDisclosureMoney:
        return NormalizedDisclosureMoney(
            **metadata,
            normalization_status="NOT_EVALUATED",
            comparability_status="not_comparable",
            reasons=tuple(reasons),
        )

    if reasons:
        return unevaluated()

    if record.currency == "USD":
        fx_rate = Decimal("1")  # USD/USD identity, by definition, in every year.
        fx_source = "USD/USD identity; no exchange conversion"
    else:
        observation = next(
            (
                rate
                for rate in policy.fx_table.rates
                if (rate.currency, rate.fiscal_year)
                == (record.currency, record.fiscal_year)
            ),
            None,
        )
        if observation is None:
            reasons.append("missing_fx_rate")
            return unevaluated()
        fx_rate, fx_source = observation.usd_per_currency, observation.source

    try:
        # Python decimal.Context default precision/rounding (Library Reference,
        # decimal, Python 3.10): 28 significant digits, ROUND_HALF_EVEN.
        # https://docs.python.org/3.10/library/decimal.html#decimal.Context
        # Use a
        # fresh context so caller precision, rounding and traps cannot alter it.
        context = Context(prec=28, rounding=ROUND_HALF_EVEN)
        context.traps[Underflow] = True  # Do not silently lose a nonzero amount.
        with localcontext(context):
            nominal_usd = record.amount * _SCALES[record.magnitude_scale] * fx_rate
            normalized = nominal_usd * (
                (Decimal("1") + policy.annual_escalation_rate)
                ** (policy.base_year - record.fiscal_year)
            )
    except DecimalException:
        reasons.append("decimal_calculation_failed")
        return unevaluated()

    key = (
        record.metric_name_normalized,
        record.scope,
        record.comparison_basis,
        "USD",
        str(policy.base_year),
        _METHOD,
        policy.fingerprint,
    )
    return NormalizedDisclosureMoney(
        **metadata,
        normalization_status="NORMALIZED",
        comparability_status="comparable",
        normalized_amount=normalized,
        normalized_currency="USD",
        normalized_unit="USD",
        normalized_magnitude_scale="units",
        normalized_base_year=policy.base_year,
        fx_rate=fx_rate,
        fx_source=fx_source,
        comparison_key=key,
    )


def normalize_disclosure_money_rows(
    records: Iterable[DisclosureMoney],
    policy: NormalizationPolicy,
) -> list[NormalizedDisclosureMoney]:
    """Derived batch view, preserving input order and one output per input."""
    return [normalize_disclosure_money(record, policy) for record in records]


def money_values_are_comparable(
    left: NormalizedDisclosureMoney,
    right: NormalizedDisclosureMoney,
) -> bool:
    """Require successful normalization and an identical declared economic basis."""
    return (
        left.comparability_status == right.comparability_status == "comparable"
        and left.comparison_key is not None
        and left.comparison_key == right.comparison_key
    )
