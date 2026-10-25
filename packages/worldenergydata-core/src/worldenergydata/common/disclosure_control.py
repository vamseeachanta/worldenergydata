"""Conservative disclosure control for a single, one-dimensional count table.

Method reference: Handbook on Statistical Disclosure Control, Chapter 5,
"Frequency tables", section 5.3, "Methods" (post-tabular cell suppression):
https://sdctools.github.io/HandbookSDC/05-frequency-tables.html#sec-Methods_freq
The handbook describes primary suppression of unsafe cells and secondary
(complementary) suppression of additional cells to prevent reconstruction
by subtraction from published marginal totals.

Local policy and scope: repository issue #1703 requires primary suppression
below an explicit caller threshold, with complementary suppression so that
the released total cannot reveal a hidden count. Whole-table withholding is
the local conservative variant, not a selection algorithm from the reference:
it withholds EVERY count and the total if any count falls below that threshold.
Consequently, this table publishes neither a total nor other counts from which
to subtract and reconstruct a suppressed value. Counts below the threshold have reason
``primary``; the other counts and withheld total have reason ``complementary``.
When no count is below the threshold, every count and the exact sum are released.

The caller supplies a positive built-in integer threshold; there is no default
or regulatory recommendation. Counts must be nonnegative built-in integers.
Booleans, floats (including integral or nonfinite floats), numeric strings and
other types are rejected without coercion. The zero boundary follows the
nonnegative-count requirement in #1703. Empty input releases an empty table
and the empty sum, zero, after validating the threshold.

Synthetic caller-policy examples (not recommended thresholds): at threshold 5,
counts [4, 5, 6] with hand sum 4 + 5 + 6 = 15 are all withheld. Counts [5, 6]
are released with the independently hand-summed total 5 + 6 = 11. Threshold 1
withholds [0, 1, 2], including its hand sum 0 + 1 + 2 = 3.

Only releasable counts, suppression reasons and the releasable total appear in
the result; no original hidden values or hidden aggregate are retained in it.
Validation messages do not interpolate inputs. Reasons do reveal which cells
are below the threshold. This policy makes no claim about auxiliary releases,
linked tables, repeated queries, differences between releases, or complete
disclosure protection. Utility-preserving complementary suppression,
multidimensional margins, pseudonymous bands and HSE adoption remain outside
this helper's scope.
"""

from collections.abc import Sequence
from typing import Literal, TypedDict


class ReleasedCell(TypedDict):
    """A published count or a reason for withholding it."""

    count: int | None
    reason: Literal["primary", "complementary"] | None


class CountTableRelease(TypedDict):
    """Plain serializable data containing no withheld count or total."""

    cells: list[ReleasedCell]
    total: int | None
    total_reason: Literal["complementary"] | None


def release_counts(counts: Sequence[int], *, threshold: int) -> CountTableRelease:
    """Apply the explicit caller policy without modifying the input sequence.

    Cell positions correspond to input positions. Lists, tuples and other
    sequences of built-in integers are accepted; text, mappings and unordered
    collections are rejected. Invalid thresholds, shapes or counts raise
    ``ValueError`` with a fixed message that contains no input values.
    """
    if type(threshold) is not int or threshold <= 0:
        raise ValueError("threshold must be a positive built-in integer")
    if not isinstance(counts, Sequence) or isinstance(counts, (str, bytes, bytearray)):
        raise ValueError("counts must be a sequence of nonnegative built-in integers")

    # Snapshot once, then validate every cell before deciding whether to release.
    values = tuple(counts)
    if any(type(count) is not int or count < 0 for count in values):
        raise ValueError("counts must contain only nonnegative built-in integers")

    if any(count < threshold for count in values):
        return {
            "cells": [
                {
                    "count": None,
                    "reason": "primary" if count < threshold else "complementary",
                }
                for count in values
            ],
            "total": None,
            "total_reason": "complementary",
        }

    return {
        "cells": [{"count": count, "reason": None} for count in values],
        "total": sum(values),
        "total_reason": None,
    }
