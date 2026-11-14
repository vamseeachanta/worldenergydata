"""Synthetic caller-policy examples for the method in repository issue #1703.

Thresholds here are caller choices, not recommended or regulatory values.
Boundary example: threshold 5, counts 4, 5, 6; hand sum 4 + 5 + 6 = 15.
Release examples: 5 + 6 = 11, 9 + 10 = 19, 1 + 2 = 3, 5 + 6 + 9 = 20.
Zero example: threshold 1, counts 0, 1, 2; hand sum 0 + 1 + 2 = 3.
Empty input has the empty hand sum 0. Invalid fixtures exercise the integer
and nonnegative requirements, rather than suggesting additional policy values.
"""

import copy
import json
import pickle
from decimal import Decimal
from fractions import Fraction
from itertools import permutations

import pytest

from worldenergydata.common.disclosure_control import release_counts


def test_small_cell_withholds_values_and_total(capsys, caplog):
    counts = [4, 5, 6]

    result = release_counts(counts, threshold=5)

    assert result == {
        "cells": [
            {"count": None, "reason": "primary"},
            {"count": None, "reason": "complementary"},
            {"count": None, "reason": "complementary"},
        ],
        "total": None,
        "total_reason": "complementary",
    }

    # Walk the entire structure, including keys and any unexpected metadata.
    def leaves(value):
        if isinstance(value, dict):
            for key, item in value.items():
                yield from leaves(key)
                yield from leaves(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from leaves(item)
        else:
            yield value

    assert all(type(value) is not int for value in leaves(result))
    for encoded in (json.dumps(result), repr(result), str(result)):
        for hidden in (*counts, 15):  # Independent hand sum above.
            assert str(hidden) not in encoded
    assert json.loads(json.dumps(result)) == result
    assert pickle.loads(pickle.dumps(result)) == result
    assert capsys.readouterr() == ("", "")
    assert not caplog.records


@pytest.mark.parametrize(
    "threshold, counts, hand_total",
    [(5, [5, 6], 11), (9, [9, 10], 19), (1, [1, 2], 3)],
)
def test_threshold_boundary_and_hand_total(threshold, counts, hand_total):
    assert release_counts(counts, threshold=threshold) == {
        "cells": [{"count": count, "reason": None} for count in counts],
        "total": hand_total,
        "total_reason": None,
    }


def test_threshold_minus_one_withholds_entire_table():
    result = release_counts([4, 5, 6], threshold=5)

    assert [cell["count"] for cell in result["cells"]] == [None, None, None]
    assert result["cells"][0]["reason"] == "primary"
    assert result["total"] is None


def test_zero_is_primary_and_withholds_total():
    assert release_counts([0, 1, 2], threshold=1) == {
        "cells": [
            {"count": None, "reason": "primary"},
            {"count": None, "reason": "complementary"},
            {"count": None, "reason": "complementary"},
        ],
        "total": None,
        "total_reason": "complementary",
    }


def test_all_primary_cells_and_single_cell_withhold_total():
    for counts in ([0, 4], [4], [0]):
        assert release_counts(counts, threshold=5) == {
            "cells": [{"count": None, "reason": "primary"} for _ in counts],
            "total": None,
            "total_reason": "complementary",
        }


def test_single_cell_at_threshold_is_released():
    # Single-cell hand sum: 5 = 5, for the caller's threshold 5.
    assert release_counts([5], threshold=5) == {
        "cells": [{"count": 5, "reason": None}],
        "total": 5,
        "total_reason": None,
    }


def test_empty_input_releases_empty_hand_sum():
    assert release_counts([], threshold=5) == {
        "cells": [],
        "total": 0,
        "total_reason": None,
    }


@pytest.mark.parametrize(
    "invalid",
    [
        True,
        False,
        -1,
        1.5,
        5.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        "5",
        None,
        Decimal("5"),
        Fraction(5),
        complex(5),
        [5],
        {"count": 5},
    ],
)
def test_invalid_counts_are_rejected(invalid):
    # A small cell must not hide invalid data later in the input.
    for prefix in ([5], [0]):
        with pytest.raises(ValueError, match="^counts must contain only"):
            release_counts([*prefix, invalid], threshold=5)


@pytest.mark.parametrize(
    "threshold",
    [
        True,
        False,
        0,
        -1,
        1.5,
        5.0,
        float("nan"),
        float("inf"),
        -float("inf"),
        "5",
        None,
        Decimal("5"),
        Fraction(5),
        [],
    ],
)
def test_invalid_thresholds_are_rejected_even_for_empty_input(threshold):
    for counts in ([], [5, 6]):
        with pytest.raises(ValueError, match="^threshold must be a positive"):
            release_counts(counts, threshold=threshold)


def test_threshold_has_no_default():
    with pytest.raises(TypeError):
        release_counts([5, 6])


@pytest.mark.parametrize("counts", [None, 5, "56", b"56", {5, 6}, {"a": 5}])
def test_invalid_table_shapes_are_rejected(counts):
    with pytest.raises(ValueError, match="^counts must be a sequence"):
        release_counts(counts, threshold=5)


def test_invalid_input_diagnostics_do_not_echo_values(capsys, caplog):
    # Sentinel is deliberately invalid and must never appear in diagnostics.
    sentinel = "unpublishable-count"
    with pytest.raises(ValueError) as count_error:
        release_counts([sentinel], threshold=5)
    with pytest.raises(ValueError) as threshold_error:
        release_counts([5], threshold=sentinel)

    assert sentinel not in str(count_error.value)
    assert sentinel not in repr(count_error.value)
    assert sentinel not in str(threshold_error.value)
    assert sentinel not in repr(threshold_error.value)
    assert capsys.readouterr() == ("", "")
    assert not caplog.records


@pytest.mark.parametrize(
    "counts, expected_cells, hand_total, total_reason",
    [
        (
            [4, 5, 6],
            [
                {"count": None, "reason": "primary"},
                {"count": None, "reason": "complementary"},
                {"count": None, "reason": "complementary"},
            ],
            None,
            "complementary",
        ),
        (
            [5, 6, 9],
            [
                {"count": 5, "reason": None},
                {"count": 6, "reason": None},
                {"count": 9, "reason": None},
            ],
            20,
            None,
        ),
    ],
)
def test_order_invariance(counts, expected_cells, hand_total, total_reason):
    for order in permutations(range(len(counts))):
        result = release_counts([counts[index] for index in order], threshold=5)
        assert result == {
            "cells": [expected_cells[index] for index in order],
            "total": hand_total,
            "total_reason": total_reason,
        }


@pytest.mark.parametrize("counts", [[4, 5, 6], [5, 6, 9], [], (5, 6)])
def test_input_is_unchanged_and_output_is_detached(counts):
    original = copy.deepcopy(counts)
    result = release_counts(counts, threshold=5)
    assert counts == original

    result["cells"].clear()
    assert counts == original


def test_sum_keeps_large_integer_precision():
    # Synthetic exact-arithmetic example: 10**100 + 5 = 10**100 + 5 by hand.
    large = 10**100
    assert release_counts([large, 5], threshold=5)["total"] == large + 5
