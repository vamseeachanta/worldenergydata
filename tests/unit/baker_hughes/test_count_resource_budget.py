"""Synthetic representation-budget regressions; no source qualification (#1859)."""

from decimal import Inexact, Rounded, localcontext

import pandas as pd
import pytest

from tests.unit.baker_hughes.test_numeric_contract import load_counts, write_workbook
from worldenergydata.baker_hughes import loader


def allocation_sentinel(*args, **kwargs):
    raise AssertionError("Count reached integer allocation before resource rejection")


@pytest.mark.parametrize("kind", ["pivot", "summary"])
@pytest.mark.parametrize("token", ["1e999999999999", "1e4096"])
def test_rejects_expanded_count_before_integer_allocation(
    tmp_path, monkeypatch, kind, token
):
    """A missing guard must fail immediately without allocating the integer."""
    path = write_workbook(tmp_path, kind, [token])
    monkeypatch.setattr(loader, "int", allocation_sentinel, raising=False)
    with pytest.raises(ValueError, match=r"rig_count row 0:.*resource.*rejected"):
        load_counts(path, kind)


@pytest.mark.parametrize("kind", ["pivot", "summary"])
@pytest.mark.parametrize(
    "token,expected",
    [
        pytest.param("1e4095", 10**4095, id="expanded-digit-boundary"),
        pytest.param("9" * 4096, 10**4096 - 1, id="token-and-digit-boundary"),
        pytest.param("  " + "0" * 4095 + "1\t", 1, id="stripped-token-boundary"),
        pytest.param("1." + "0" * 4094, 1, id="long-whole-mantissa"),
        pytest.param("0e999999999999", 0, id="zero-extreme-exponent"),
        pytest.param("-0e999999999999", 0, id="signed-zero-extreme-exponent"),
        pytest.param("3e2", 300, id="ordinary-scientific"),
        pytest.param("9007199254740993", 9007199254740993, id="exact-large-control"),
    ],
)
def test_public_loaders_preserve_counts_within_budgets(tmp_path, kind, token, expected):
    """Decimal place value supplies independent expected values at each bound."""
    result = load_counts(write_workbook(tmp_path, kind, [token]), kind)
    assert result.rig_count.tolist() == [expected]
    assert isinstance(result.rig_count.tolist()[0], int)
    assert (
        result.attrs["numeric_validation"]["rig_count"] == "nonnegative_integer_reject"
    )


@pytest.mark.parametrize("kind", ["pivot", "summary"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_unsigned_storage_boundary_keeps_exact_values(tmp_path, kind, offset):
    """2**64 - 1 fits uint64; larger counts require Python integer storage."""
    expected = 2**64 + offset
    result = load_counts(write_workbook(tmp_path, kind, ["2", str(expected)]), kind)
    assert result.rig_count.tolist() == [2, expected]
    if offset < 0:
        assert pd.api.types.is_numeric_dtype(result.rig_count)
    else:
        assert result.rig_count.dtype == object
        assert all(isinstance(value, int) for value in result.rig_count)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("0" * 4096 + "1", id="leading-zero-token"),
        pytest.param("1." + "0" * 4095, id="long-mantissa"),
        pytest.param("0" * 4097, id="overlong-zero"),
    ],
)
def test_overlong_token_is_rejected_before_decimal_parsing(monkeypatch, token):
    values = pd.Series([token], index=[17], name="rig_count")
    monkeypatch.setattr(loader, "_decimal_number", allocation_sentinel)
    with pytest.raises(ValueError, match=r"rig_count row 17:.*resource.*rejected"):
        loader._validated_counts(values)


def test_count_token_limit_does_not_change_depth_parsing():
    """The count-only token budget must not restrict the shared decimal parser."""
    assert loader._decimal_number("0" * 4096 + "1") == 1


@pytest.mark.parametrize("kind", ["pivot", "summary"])
def test_public_loaders_reject_overlong_count_token(tmp_path, kind):
    path = write_workbook(tmp_path, kind, ["0" * 4096 + "1"])
    with pytest.raises(ValueError, match=r"rig_count row 0:.*resource.*rejected"):
        load_counts(path, kind)


@pytest.mark.parametrize("token", ["1.5", "1e-999999999999", "-1", "NaN", "", None])
def test_existing_invalid_count_diagnostics_are_retained(token):
    with pytest.raises(
        ValueError, match=r"rig_count row 7:.*nonnegative integer.*rejected"
    ):
        loader._validated_counts(pd.Series([token], index=[7]))


def test_budget_boundaries_preserve_decimal_context_and_series_identity():
    values = pd.Series(["1e4095", "-0e999999999999"], index=[5, 9], name="rig_count")
    with localcontext() as context:
        context.prec = 2
        context.Emax, context.Emin = 0, 0
        context.traps[Inexact] = context.traps[Rounded] = True
        context.flags[Rounded] = True
        original = context.copy()
        result = loader._validated_counts(values)
        with pytest.raises(ValueError, match=r"rig_count row 3:.*resource.*rejected"):
            loader._validated_counts(pd.Series(["1e4096"], index=[3]))
        assert context.prec == original.prec
        assert context.rounding == original.rounding
        assert context.Emax == original.Emax
        assert context.Emin == original.Emin
        assert context.traps == original.traps
        assert context.flags == original.flags
    assert result.tolist() == [10**4095, 0]
    assert result.index.equals(values.index)
    assert result.name == values.name
