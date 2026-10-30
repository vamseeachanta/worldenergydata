"""Annual money normalization: independent arithmetic and conservative gating.

Numeric fixtures are synthetic unless explicitly attributed. The supplied 3%
scenario follows the repository's issue-336 plan (2026-04-22), not an observed
inflation series. FX observations: Federal Reserve G.5A annual table (2021
revision), https://www.federalreserve.gov/releases/g5a/20210104/ .
"""

import json
import runpy
from copy import deepcopy
from decimal import Decimal, DefaultContext, Inexact, localcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection.disclosure_normalization import (
    DisclosureMoney,
    NormalizationPolicy,
    NormalizedDisclosureMoney,
    money_values_are_comparable,
    normalize_disclosure_money,
    normalize_disclosure_money_rows,
)
from worldenergydata.cost.data_collection.fx_policy_v1 import (
    BASELINE_FX_TABLE,
    FxRate,
    FxTable,
)


@pytest.fixture
def policy():
    # Required scenario input; issue-336 plan, 2026-04-22, Scope Boundaries.
    return NormalizationPolicy(
        policy_id="example-scenario-v1",
        annual_escalation_rate=Decimal("0.03"),
        escalation_source="Assumed scenario: issue-336 plan, 2026-04-22",
        fx_table=BASELINE_FX_TABLE,
    )


@pytest.fixture
def money():
    # Synthetic monetary input; no real operator or disclosure is represented.
    return DisclosureMoney(
        amount=Decimal(2),
        currency="EUR",
        unit="EUR",
        magnitude_scale="million",
        fiscal_year=2020,
        as_reported_metric_name="Capital expenditure",
        metric_name_normalized="capex",
        scope="operator",
        comparison_basis="consolidated; cash capex; net interest; full year",
        period_basis="calendar_year_flow",
        price_basis="nominal",
        provenance={"locator": {"table": "synthetic example"}},
    )


def changed(money, **values):
    return DisclosureMoney.model_validate({**money.model_dump(), **values})


def test_preserves_as_reported_and_provenance(money, policy):
    """2 million EUR * 1.1410 USD/EUR = 2,282,000 USD in the base year."""
    before = deepcopy(money.model_dump())
    result = normalize_disclosure_money(money, policy)
    assert result.as_reported.model_dump() == before == money.model_dump()
    assert result.normalized_amount == Decimal(2282000)
    assert result.normalized_currency == result.normalized_unit == "USD"
    assert result.normalized_magnitude_scale == "units"
    assert result.normalized_base_year == 2020
    assert result.comparability_status == "comparable"
    assert result.normalization_status == "NORMALIZED"
    assert result.reasons == ()
    assert result.fx_rate == Decimal("1.1410")
    assert "federalreserve.gov" in result.fx_source
    assert result.normalization_method == "fx_then_base_year_adjustment_v1"
    assert result.policy_id == policy.policy_id
    assert result.policy_fingerprint
    assert result.annual_escalation_rate == Decimal("0.03")
    assert result.escalation_source == policy.escalation_source
    result.as_reported.provenance["locator"]["table"] = "changed copy"
    assert money.model_dump() == before


@pytest.mark.parametrize(
    "scale, expected",
    [
        ("units", "2"),
        ("thousand", "2000"),
        ("million", "2000000"),
        ("billion", "2000000000"),
    ],
)
def test_magnitude_scales(money, policy, scale, expected):
    """Hand calculation: 2 USD times 1, 10^3, 10^6 or 10^9.

    Powers of ten: NIST SP 330 (2019), Table 7. Financial scale names
    use the short scale, explicitly defined by this contract.
    """
    result = normalize_disclosure_money(
        changed(money, currency="USD", unit="USD", magnitude_scale=scale), policy
    )
    assert result.normalized_amount == Decimal(expected)
    assert result.fx_rate == Decimal(1)  # USD/USD identity, by definition.


@pytest.mark.parametrize(
    "year, amount, expected",
    [
        (2019, "100", "103"),
        (2018, "100", "106.09"),
        (2021, "103", "100"),
        (2022, "106.09", "100"),
        (2020, "0", "0"),
        (2020, "-2", "-2"),
    ],
)
def test_base_year_direction_and_signed_values(money, policy, year, amount, expected):
    """By hand: 100*1.03=103; 103*1.03=106.09; reverse by division.

    NIST HB 135 (2020), section 3.3.3.1, equation 3-13. Zero and negative
    synthetic amounts represent no expenditure and a net reversal.
    """
    row = changed(
        money,
        amount=amount,
        currency="USD",
        unit="USD",
        magnitude_scale="units",
        fiscal_year=year,
    )
    assert normalize_disclosure_money(row, policy).normalized_amount == Decimal(
        expected
    )


@pytest.mark.parametrize(
    "currency, year, expected",
    [
        ("EUR", 2019, "115.2982"),
        ("GBP", 2019, "131.5104"),
        ("EUR", 2020, "114.10"),
        ("GBP", 2020, "128.29"),
    ],
)
def test_published_fx_quote_direction(money, policy, currency, year, expected):
    """G.5A (2021 revision), EUR/GBP rows and starred USD-per-unit note.

    Hand: 100*1.1194*1.03=115.2982; 100*1.2768*1.03=131.5104;
    100*1.1410=114.10; 100*1.2829=128.29. No reciprocal is taken.
    """
    result = normalize_disclosure_money(
        changed(
            money,
            amount="100",
            currency=currency,
            unit=currency,
            fiscal_year=year,
            magnitude_scale="units",
        ),
        policy,
    )
    assert result.normalized_amount == Decimal(expected)


@pytest.mark.parametrize(
    "field, value, reason",
    [
        ("amount", None, "missing_amount"),
        ("currency", None, "missing_currency"),
        ("unit", None, "missing_unit"),
        ("magnitude_scale", None, "missing_scale"),
        ("fiscal_year", None, "missing_fiscal_year"),
        ("as_reported_metric_name", None, "missing_reported_metric"),
        ("metric_name_normalized", None, "missing_normalized_metric"),
        ("scope", None, "missing_scope"),
        ("comparison_basis", None, "missing_comparison_basis"),
        ("comparison_basis", "  ", "missing_comparison_basis"),
        ("period_basis", None, "unsupported_period_basis"),
        ("period_basis", "non_calendar_year_flow", "unsupported_period_basis"),
        ("period_basis", "closing_balance", "unsupported_period_basis"),
        ("price_basis", None, "unsupported_price_basis"),
        ("price_basis", "constant", "unsupported_price_basis"),
        ("unit", "USD", "currency_unit_mismatch"),
        ("unit", "EUR/boe", "currency_unit_mismatch"),
        ("unit", "EUR million", "currency_unit_mismatch"),
        ("magnitude_scale", "mm", "unsupported_scale"),
        ("scope", "unknown", "unsupported_scope"),
    ],
)
def test_missing_or_ambiguous_inputs_are_not_evaluated(
    money, policy, field, value, reason
):
    """Contract cases; no FX, year, scale or economic basis may be inferred."""
    row = changed(money, **{field: value})
    result = normalize_disclosure_money(row, policy)
    assert result.as_reported == row
    assert result.comparability_status == "not_comparable"
    assert result.normalization_status == "NOT_EVALUATED"
    assert reason in result.reasons
    assert result.normalized_amount is None
    assert result.normalized_currency is None
    assert result.normalized_base_year is None
    assert result.comparison_key is None


@pytest.mark.parametrize("currency, year", [("JPY", 2020), ("EUR", 2021)])
def test_no_fx_fallback(money, policy, currency, year):
    """The committed table covers only EUR/GBP in 2019/2020; no interpolation."""
    result = normalize_disclosure_money(
        changed(money, currency=currency, unit=currency, fiscal_year=year), policy
    )
    assert result.normalized_amount is None
    assert result.reasons == ("missing_fx_rate",)


@pytest.mark.parametrize("field", ["annual_escalation_rate", "escalation_source"])
def test_missing_escalation_evidence_is_not_evaluated(money, policy, field):
    values = {**policy.model_dump(), field: None}
    result = normalize_disclosure_money(money, NormalizationPolicy(**values))
    assert result.normalization_status == "NOT_EVALUATED"
    assert result.normalized_amount is None
    assert "missing_escalation_evidence" in result.reasons


def test_reproducible_json_batch_and_decimal_context(money, policy):
    """Same 2*10^6*1.1410 calculation, even with caller precision set to 3."""
    before = normalize_disclosure_money(money, policy)
    with localcontext() as context:
        context.prec = 3  # Deliberately low caller precision, not a tolerance.
        after = normalize_disclosure_money_rows(iter([money, money]), policy)
    assert after == [before, before]
    assert after[0] is not after[1]
    assert (
        NormalizedDisclosureMoney.model_validate_json(before.model_dump_json())
        == before
    )
    assert normalize_disclosure_money_rows([], policy) == []


def test_cross_currency_comparison_requires_same_economic_basis(money, policy):
    """Synthetic equality: 2 million EUR equals 2.282 million USD at 1.1410."""
    eur = normalize_disclosure_money(money, policy)
    usd = normalize_disclosure_money(
        changed(money, amount="2.282", currency="USD", unit="USD"), policy
    )
    assert eur.normalized_amount == usd.normalized_amount
    assert money_values_are_comparable(eur, usd)
    for values in (
        {"comparison_basis": "gross interest"},
        {"scope": "project"},
        {"metric_name_normalized": "opex"},
        {"currency": None},
    ):
        other = normalize_disclosure_money(changed(money, **values), policy)
        assert not money_values_are_comparable(eur, other)
        assert not money_values_are_comparable(other, eur)


def test_changed_policy_changes_comparison_key(money, policy):
    """A different synthetic rate/base year/table must not share a comparison key."""
    first = normalize_disclosure_money(money, policy)
    for values in (
        {"annual_escalation_rate": "0.04"},  # Explicit alternative scenario input.
        {"base_year": 2019},
        {"fx_table": FxTable(version="other", rates=BASELINE_FX_TABLE.rates)},
    ):
        second = normalize_disclosure_money(
            money, NormalizationPolicy(**{**policy.model_dump(), **values})
        )
        assert first.policy_fingerprint != second.policy_fingerprint
        assert not money_values_are_comparable(first, second)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_amounts_rejected(money, value):
    with pytest.raises(ValidationError):
        changed(money, amount=value)


@pytest.mark.parametrize("rate", ["-1", "-2", "NaN", "Infinity"])
def test_invalid_escalation_rate_rejected(policy, rate):
    """1+r must be positive for the real-valued price ratio (HB 135, eq. 3-13)."""
    with pytest.raises(ValidationError):
        NormalizationPolicy(**{**policy.model_dump(), "annual_escalation_rate": rate})


def test_fx_table_rejects_duplicate_keys_and_invalid_rates():
    """Synthetic rate 2 is a dimensional fixture, not a market observation."""
    rate = FxRate(
        currency="EUR",
        fiscal_year=2020,
        usd_per_currency="2",
        source="Synthetic example",
    )
    with pytest.raises(ValidationError, match="duplicate"):
        FxTable(version="test", rates=(rate, rate))
    for bad in ("0", "-1", "NaN", "Infinity"):
        with pytest.raises(ValidationError):
            FxRate(**{**rate.model_dump(), "usd_per_currency": bad})
    with pytest.raises(ValidationError):
        FxRate(**{**rate.model_dump(), "source": " "})
    with pytest.raises(ValidationError, match="USD"):
        FxRate(**{**rate.model_dump(), "currency": "USD"})


def test_public_exports():
    from worldenergydata.cost import data_collection

    assert data_collection.normalize_disclosure_money is normalize_disclosure_money
    assert data_collection.DisclosureMoney is DisclosureMoney


@pytest.mark.parametrize("amount", ["1e1000000", "1e-1000030"])
def test_decimal_range_failure_is_not_a_comparable_value(money, policy, amount):
    """Synthetic exponent stress beyond Python's default decimal context range.

    Decimal Library Reference, Python 3.10: default Emin/Emax and precision.
    Overflow and loss of a nonzero amount to underflow must never become a
    plausible normalized value. These are not financial acceptance limits.
    """
    result = normalize_disclosure_money(
        changed(
            money, amount=amount, currency="USD", unit="USD", magnitude_scale="units"
        ),
        policy,
    )
    assert result.normalized_amount is None
    assert result.normalization_status == "NOT_EVALUATED"
    assert result.reasons == ("decimal_calculation_failed",)


@pytest.mark.parametrize("year", [0, -1, True, 2020.5])
def test_years_are_positive_integers(money, policy, year):
    """The contract uses positive calendar-year labels, never coercion."""
    with pytest.raises(ValidationError):
        changed(money, fiscal_year=year)
    with pytest.raises(ValidationError):
        NormalizationPolicy(**{**policy.model_dump(), "base_year": year})


def test_result_schema_rejects_inconsistent_status(money, policy):
    result = normalize_disclosure_money(money, policy).model_dump()
    with pytest.raises(ValidationError):
        NormalizedDisclosureMoney(**{**result, "normalized_amount": None})
    with pytest.raises(ValidationError):
        NormalizedDisclosureMoney(**{**result, "normalization_status": "NOT_EVALUATED"})


def test_worked_example(capsys):
    """Hand: 2*10^6*1.1410=2,282,000; 2.282*10^6=2,282,000 USD.

    FX source: Federal Reserve G.5A (2021 revision), EUR/2020 starred row.
    """
    root = Path(__file__).resolve().parents[3]
    runpy.run_path(
        str(root / "examples/cost/normalize_annual_disclosures.py"), run_name="__main__"
    )
    result = json.loads(capsys.readouterr().out)
    assert [Decimal(value) for value in result["normalized_usd"]] == [
        Decimal(2282000),
        Decimal(2282000),
    ]
    assert result["comparable"] is True


@pytest.mark.parametrize(
    "field, value",
    [
        ("normalized_base_year", 2021),
        ("policy_fingerprint", "different-policy"),
        ("comparison_basis", "gross interest"),
        ("metric_name_normalized", "opex"),
        ("scope", "project"),
        ("normalization_method", "different-method"),
    ],
)
def test_serialized_comparison_key_must_match_metadata(money, policy, field, value):
    """Each independent basis change must invalidate the old serialized key."""
    original = normalize_disclosure_money(money, policy)
    payload = json.loads(original.model_dump_json())
    if field in {"comparison_basis", "metric_name_normalized", "scope"}:
        payload["as_reported"][field] = value
    else:
        payload[field] = value
    with pytest.raises(ValidationError, match="comparison key"):
        NormalizedDisclosureMoney.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "field, value",
    [
        ("normalized_base_year", 2021),
        ("policy_fingerprint", "different-policy"),
        ("comparison_basis", "gross interest"),
    ],
)
def test_comparison_gate_rechecks_metadata(money, policy, field, value):
    """Unvalidated copies cannot reuse a stale key to pass the comparison gate."""
    original = normalize_disclosure_money(money, policy)
    if field == "comparison_basis":
        copied = original.model_copy(
            update={"as_reported": changed(money, comparison_basis=value)}
        )
    else:
        copied = original.model_copy(update={field: value})
    assert not money_values_are_comparable(original, copied)
    assert not money_values_are_comparable(copied, original)


@pytest.mark.parametrize(
    "currency",
    ["$", "€", "£", "US$", "eur", " EUR", "EUR ", "EUR million", "EUR/boe", "UЅD"],
)
def test_ambiguous_currency_unit_pair_is_not_evaluated(money, policy, currency):
    """Matching symbols or aliases do not establish an explicit currency code."""
    row = changed(money, currency=currency, unit=currency)
    result = normalize_disclosure_money(row, policy)
    assert result.as_reported == row
    assert result.normalization_status == "NOT_EVALUATED"
    assert result.normalized_amount is None
    assert result.comparison_key is None
    assert "unsupported_currency" in result.reasons
    assert "unsupported_unit" in result.reasons


@pytest.mark.parametrize(
    "currency",
    ["$", "€", "£", "US$", "eur", " EUR", "EUR ", "EUR million", "EUR/boe", "UЅD"],
)
def test_custom_fx_table_cannot_authorize_ambiguous_currency(policy, currency):
    """Reject ambiguous codes at policy input, even for matching raw unit pairs."""
    payload = json.loads(policy.model_dump_json())
    payload["fx_table"]["rates"] = [
        {
            "currency": currency,
            "fiscal_year": 2020,
            "usd_per_currency": "2",
            "source": "Synthetic example",
        }
    ]
    with pytest.raises(ValidationError, match="currency code"):
        NormalizationPolicy.model_validate_json(json.dumps(payload))


def test_custom_fx_table_accepts_explicit_currency_code(money, policy):
    """Synthetic 2 CAD * 2 USD/CAD = 4 USD; the rate is not an observation."""
    table = FxTable(
        version="synthetic-cad-v1",
        rates=(
            FxRate(
                currency="CAD",
                fiscal_year=2020,
                usd_per_currency="2",
                source="Synthetic example",
            ),
        ),
    )
    custom = NormalizationPolicy(**{**policy.model_dump(), "fx_table": table})
    row = changed(money, currency="CAD", unit="CAD", magnitude_scale="units")
    result = normalize_disclosure_money(row, custom)
    assert result.normalization_status == "NORMALIZED"
    assert result.normalized_amount == Decimal(4)


@pytest.mark.parametrize("target", ["default", "current"])
@pytest.mark.parametrize("setting", ["traps", "exponent_bounds"])
def test_rebasing_ignores_mutable_decimal_contexts(
    money, policy, monkeypatch, target, setting
):
    """103 / 1.03 = 100 despite traps for inexact division or narrow bounds."""
    row = changed(
        money,
        amount="103",
        currency="USD",
        unit="USD",
        magnitude_scale="units",
        fiscal_year=2021,
    )
    expected = normalize_disclosure_money(row, policy)
    assert expected.normalization_status == "NORMALIZED"
    assert expected.normalized_amount == Decimal(100)
    with localcontext() as current:
        context = DefaultContext if target == "default" else current
        if setting == "traps":
            monkeypatch.setitem(context.traps, Inexact, True)
        else:
            monkeypatch.setattr(context, "Emin", -1)
            monkeypatch.setattr(context, "Emax", 1)
        actual = normalize_disclosure_money(row, policy)
    assert actual.model_dump_json() == expected.model_dump_json()


@pytest.mark.parametrize("target", ["default", "current"])
@pytest.mark.parametrize("amount", ["1e1000000", "1e-1000030"])
def test_decimal_range_failures_ignore_disabled_external_traps(
    money, policy, monkeypatch, target, amount
):
    """Out-of-range amounts still refuse evaluation when external traps are off."""
    row = changed(
        money, amount=amount, currency="USD", unit="USD", magnitude_scale="units"
    )
    with localcontext() as current:
        context = DefaultContext if target == "default" else current
        for signal in context.traps:
            monkeypatch.setitem(context.traps, signal, False)
        result = normalize_disclosure_money(row, policy)
    assert result.normalization_status == "NOT_EVALUATED"
    assert result.normalized_amount is None
    assert result.reasons == ("decimal_calculation_failed",)
