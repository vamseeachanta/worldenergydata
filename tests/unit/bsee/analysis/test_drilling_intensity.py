"""Offline tests using synthetic bores; no values represent measured wells."""

import socket
import urllib.request

import pytest

from worldenergydata.bsee.analysis.drilling_intensity import (
    COLUMN_SCHEMA,
    REFERENCE_BAND,
    bore_intensity,
    intensity_rollups,
)


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network access is forbidden in synthetic tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(urllib.request, "urlopen", denied)


def synthetic_bore(**changes):
    row = dict(
        bore_id="synthetic-1",
        field="synthetic-field",
        block="synthetic-block",
        drilling_days=40.0,
        completion_days=900.0,
        basis="synthetic-rule-a",
        MAX_BH_TOTAL_MD=20000.0,
        MAX_WELL_BORE_TVD=10000.0,
    )
    row.update(changes)
    return row


@pytest.mark.parametrize("denominator,expected", [("md", 20.0), ("tvd", 40.0)])
def test_formula_and_explicit_alias(denominator, expected):
    result = bore_intensity(synthetic_bore(), denominator=denominator)
    assert result["days_per_10k_md"] == 20.0
    assert result["days_per_10k_tvd"] == 40.0
    assert result["days_per_10k_ft"] == expected
    assert result["days_per_10k_ft_denominator"] == denominator
    assert result["basis"] == "synthetic-rule-a"
    assert result["intensity_status"] == "computed"


def test_denominator_cannot_be_implicit_or_unknown():
    with pytest.raises(TypeError):
        bore_intensity(synthetic_bore())
    with pytest.raises(ValueError, match="denominator"):
        bore_intensity(synthetic_bore(), denominator="unknown")


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -1, True])
def test_missing_or_invalid_days_are_null(value):
    result = bore_intensity(synthetic_bore(drilling_days=value), denominator="md")
    assert result["days_per_10k_ft"] is None
    assert result["intensity_status"] == "no_valid_pairs"


@pytest.mark.parametrize("value", [None, 0, -1, float("nan"), float("inf"), True])
def test_invalid_depth_is_null_only_for_affected_denominator(value):
    result = bore_intensity(synthetic_bore(MAX_BH_TOTAL_MD=value), denominator="md")
    assert result["days_per_10k_md"] is None
    assert result["days_per_10k_tvd"] == 40.0
    assert result["excluded_bores_md"] == 1
    assert result["excluded_bores_tvd"] == 0


def test_true_measured_zero_days_remains_zero():
    assert (
        bore_intensity(synthetic_bore(drilling_days=0), denominator="md")[
            "days_per_10k_ft"
        ]
        == 0
    )


def test_completion_days_never_enter_numerator():
    a = bore_intensity(synthetic_bore(completion_days=0), denominator="md")
    b = bore_intensity(synthetic_bore(completion_days=100000), denominator="md")
    assert a == b


@pytest.mark.parametrize(
    "basis,status",
    [
        (None, "missing_basis"),
        ("", "missing_basis"),
        ("unavailable", "missing_basis"),
        ("mixed", "mixed_basis"),
    ],
)
def test_unusable_basis_refuses_computation(basis, status):
    result = bore_intensity(synthetic_bore(basis=basis), denominator="md")
    assert result["days_per_10k_ft"] is None
    assert result["intensity_status"] == status


@pytest.mark.parametrize("group_by", ["field", "block"])
def test_rollup_is_ratio_of_totals_not_mean_of_ratios(group_by):
    rows = [
        synthetic_bore(drilling_days=10, MAX_BH_TOTAL_MD=10000),
        synthetic_bore(bore_id="synthetic-2", drilling_days=90, MAX_BH_TOTAL_MD=30000),
    ]
    result = intensity_rollups(rows, group_by=group_by, denominator="md")[0]
    assert result["days_per_10k_ft"] == 25
    assert result["days_per_10k_ft"] != (10 + 30) / 2
    assert result["total_drilling_days_md"] == 100
    assert result["total_depth_ft_md"] == 40000
    assert result["excluded_bores_md"] == 0


def test_rollup_excludes_invalid_pairs_from_both_totals():
    rows = [
        synthetic_bore(),
        synthetic_bore(drilling_days=None),
        synthetic_bore(MAX_BH_TOTAL_MD=0),
    ]
    result = intensity_rollups(rows, group_by="field", denominator="md")[0]
    assert result["days_per_10k_md"] == 20
    assert result["days_per_10k_tvd"] == 40
    assert result["total_drilling_days_md"] == 40
    assert result["total_depth_ft_md"] == 20000
    assert result["included_bores_md"] == 1
    assert result["excluded_bores_md"] == 2
    assert result["excluded_bores_tvd"] == 1
    assert result["intensity_status"] == "computed_partial"


@pytest.fixture
def synthetic_rollup_bores():
    """All inputs are synthetic; issue #1080 supplies the 10,000 ft scale.

    Chosen days/MD/TVD are (10, 10000, 5000), (30, 30000, missing),
    and (missing, 20000, 10000). Completion days remain the synthetic
    helper's 900 per bore and must not enter either drilling numerator.
    Independent hand calculation: MD days = 10 + 30 = 40, depth =
    10000 + 30000 = 40000, ratio = 40 / 40000 * 10000 = 10.0,
    included/excluded = 2/1. TVD days = 10, depth = 5000, ratio =
    10 / 5000 * 10000 = 20.0, included/excluded = 1/2. For either grouping
    key the group contains 3 bores; missing days contribute to neither total.
    """
    return [
        synthetic_bore(
            bore_id="synthetic-a",
            drilling_days=10,
            MAX_BH_TOTAL_MD=10000,
            MAX_WELL_BORE_TVD=5000,
        ),
        synthetic_bore(
            bore_id="synthetic-b",
            drilling_days=30,
            MAX_BH_TOTAL_MD=30000,
            MAX_WELL_BORE_TVD=None,
        ),
        synthetic_bore(bore_id="synthetic-c", drilling_days=None),
    ]


@pytest.mark.parametrize(
    "iterable_factory",
    [list, tuple, lambda rows: (row for row in rows)],
    ids=["list", "tuple", "generator"],
)
@pytest.mark.parametrize("group_by", ["field", "block"])
@pytest.mark.parametrize("denominator,expected_alias", [("md", 10.0), ("tvd", 20.0)])
@pytest.mark.parametrize("reverse", [False, True], ids=["original", "reversed"])
def test_rollups_accept_one_shot_iterables(
    synthetic_rollup_bores,
    iterable_factory,
    group_by,
    denominator,
    expected_alias,
    reverse,
):
    """Each variant uses the fixture's independent synthetic hand calculation."""
    rows = reversed(synthetic_rollup_bores) if reverse else synthetic_rollup_bores
    result = intensity_rollups(
        iterable_factory(rows), group_by=group_by, denominator=denominator
    )
    assert result == [
        {
            group_by: f"synthetic-{group_by}",
            "basis": "synthetic-rule-a",
            "bore_count": 3,
            "days_per_10k_ft_denominator": denominator,
            "days_per_10k_ft": expected_alias,
            "days_per_10k_md": 10.0,
            "days_per_10k_tvd": 20.0,
            "total_drilling_days_md": 40.0,
            "total_depth_ft_md": 40000.0,
            "included_bores_md": 2,
            "excluded_bores_md": 1,
            "total_drilling_days_tvd": 10.0,
            "total_depth_ft_tvd": 5000.0,
            "included_bores_tvd": 1,
            "excluded_bores_tvd": 2,
            "intensity_status": "computed_partial",
            "intensity_status_md": "computed_partial",
            "intensity_status_tvd": "computed_partial",
        }
    ]


@pytest.mark.parametrize("group_by", ["field", "block"])
@pytest.mark.parametrize("denominator", ["md", "tvd"])
@pytest.mark.parametrize("missing_days", [False, True])
def test_rollup_refuses_mixed_basis_even_on_an_excluded_member(
    missing_days, group_by, denominator
):
    rows = [
        synthetic_bore(),
        synthetic_bore(
            basis="synthetic-rule-b", drilling_days=None if missing_days else 40
        ),
    ]
    result = intensity_rollups(rows, group_by=group_by, denominator=denominator)[0]
    assert result["basis"] == "mixed"
    assert result["intensity_status"] == "mixed_basis"
    assert result["intensity_status_md"] == "mixed_basis"
    assert result["intensity_status_tvd"] == "mixed_basis"
    for key in (
        "days_per_10k_md",
        "days_per_10k_tvd",
        "days_per_10k_ft",
        "total_drilling_days_md",
        "total_depth_ft_md",
        "total_drilling_days_tvd",
        "total_depth_ft_tvd",
    ):
        assert result[key] is None


def test_no_pairs_and_empty_groups_do_not_emit_zero():
    result = intensity_rollups(
        [synthetic_bore(drilling_days=None)], group_by="field", denominator="md"
    )[0]
    assert result["days_per_10k_ft"] is None
    assert result["total_drilling_days_md"] is None
    assert result["intensity_status"] == "no_valid_pairs"
    assert intensity_rollups([], group_by="field", denominator="md") == []


def test_groups_are_separate_and_input_is_not_mutated():
    rows = [synthetic_bore(), synthetic_bore(field="synthetic-other")]
    before = [dict(row) for row in rows]
    assert len(intensity_rollups(iter(rows), group_by="field", denominator="tvd")) == 2
    assert rows == before


def test_reference_is_issue_attributed_and_schema_declares_depth():
    assert REFERENCE_BAND["lower"] == 20
    assert REFERENCE_BAND["upper"] == 23
    assert "SPE-87117" in REFERENCE_BAND["citation"]
    assert REFERENCE_BAND["source_url"].endswith("/issues/1080")
    assert "MAX_BH_TOTAL_MD" in COLUMN_SCHEMA["days_per_10k_md"]
    assert "MAX_WELL_BORE_TVD" in COLUMN_SCHEMA["days_per_10k_tvd"]
    assert "Days/10K" in COLUMN_SCHEMA["days_per_10k_ft"]


@pytest.mark.parametrize("basis", [[], {}, 4, " "])
def test_malformed_basis_is_refused_without_an_exception(basis):
    result = bore_intensity(synthetic_bore(basis=basis), denominator="md")
    assert result["days_per_10k_ft"] is None
    assert result["intensity_status"] == "missing_basis"


def test_overflow_emits_null_with_status():
    result = bore_intensity(
        synthetic_bore(drilling_days=1e308, MAX_BH_TOTAL_MD=1), denominator="md"
    )
    assert result["days_per_10k_ft"] is None
    assert result["intensity_status"] == "nonfinite_result"


def test_missing_basis_member_refuses_rollup():
    result = intensity_rollups(
        [synthetic_bore(), synthetic_bore(basis=None)],
        group_by="field",
        denominator="md",
    )[0]
    assert result["days_per_10k_ft"] is None
    assert result["intensity_status"] == "missing_basis"


@pytest.mark.parametrize("group_by,label", [("field", None), ("block", " ")])
def test_missing_group_is_rejected(group_by, label):
    with pytest.raises(ValueError, match="label"):
        intensity_rollups(
            [synthetic_bore(**{group_by: label})], group_by=group_by, denominator="md"
        )


def test_unhashable_basis_member_refuses_rollup():
    result = intensity_rollups(
        [synthetic_bore(), synthetic_bore(basis=[])], group_by="field", denominator="md"
    )[0]
    assert result["days_per_10k_ft"] is None
    assert result["intensity_status"] == "missing_basis"
