"""Outward-rounded interval arithmetic, including open and unbounded endpoints.

Source: Boost Numeric Interval documentation (2006), Interval Arithmetic and
Operations and functions; inclusion property and directed rounding.
https://www.boost.org/doc/libs/latest/libs/numeric/interval/doc/interval.htm
Accounting equations: repository cost synthesis plan (2026), Pseudocode.
Precision is a computational policy, not an empirical cost coefficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext

ZERO = Decimal(0)
ONE = Decimal(1)
PRECISION = 50  # Computational policy: 50 significant digits; round outwards.


def _op(left: Decimal, right: Decimal, operation: str, upper: bool) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.rounding = ROUND_CEILING if upper else ROUND_FLOOR
        if operation == "add":
            return left + right
        if operation == "mul":
            # A zero endpoint times an unbounded endpoint contributes zero.
            return ZERO if left == 0 or right == 0 else left * right
        return left / right


@dataclass(frozen=True)
class Interval:
    low: Decimal
    high: Decimal
    low_open: bool = False
    high_open: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.low, Decimal) or not isinstance(self.high, Decimal):
            raise TypeError("interval bounds must be Decimal")
        if self.low.is_nan() or self.high.is_nan() or self.low > self.high:
            raise ValueError("invalid interval bounds")
        if self.low == Decimal("Infinity") or self.high == Decimal("-Infinity"):
            raise ValueError("empty infinite interval")
        if (not self.low.is_finite() and not self.low_open) or (
            not self.high.is_finite() and not self.high_open
        ):
            raise ValueError("infinite endpoints must be open")
        if self.low == self.high and (self.low_open or self.high_open):
            raise ValueError("empty open interval")

    @classmethod
    def point(cls, value: Decimal) -> Interval:
        return cls(value, value)

    def __add__(self, other: Interval) -> Interval:
        return Interval(
            _op(self.low, other.low, "add", False),
            _op(self.high, other.high, "add", True),
            self.low_open or other.low_open,
            self.high_open or other.high_open,
        )

    def __sub__(self, other: Interval) -> Interval:
        return self + Interval(
            other.high.copy_negate(),
            other.low.copy_negate(),
            other.high_open,
            other.low_open,
        )

    def multiply(self, other: Interval) -> Interval:
        corners = []
        for left, lo in ((self.low, self.low_open), (self.high, self.high_open)):
            for right, ro in (
                (other.low, other.low_open),
                (other.high, other.high_open),
            ):
                corners.append(
                    (
                        _op(left, right, "mul", False),
                        _op(left, right, "mul", True),
                        lo or ro,
                    )
                )
        low = min(c[0] for c in corners)
        high = max(c[1] for c in corners)
        low_open = all(c[2] for c in corners if c[0] == low)
        high_open = all(c[2] for c in corners if c[1] == high)
        # Zero is attained whenever either operand contains zero.
        zero_attained = any(
            (v.low < 0 < v.high)
            or (v.low == 0 and not v.low_open)
            or (v.high == 0 and not v.high_open)
            for v in (self, other)
        )
        if low == 0 and zero_attained:
            low_open = False
        if high == 0 and zero_attained:
            high_open = False
        return Interval(low, high, low_open, high_open)

    def divide(self, denominator: Interval) -> Interval | None:
        """Unavailable for a denominator whose lower bound is nonpositive."""
        if denominator.low <= 0:
            return None
        reciprocal = Interval(
            _op(ONE, denominator.high, "div", False),
            _op(ONE, denominator.low, "div", True),
            denominator.high_open,
            denominator.low_open,
        )
        return self.multiply(reciprocal)
