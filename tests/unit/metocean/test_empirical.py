"""Empirical climate statistics use original rows, not a regular time grid."""

from datetime import datetime, timedelta, timezone

import pytest

from worldenergydata.metocean.empirical import percentile, summarize_observations

UTC = timezone.utc


def records(heights, periods, *, times=None, source="ndbc", kind="dominant"):
    result = []
    for index, (height, period) in enumerate(zip(heights, periods)):
        timestamp = times[index] if times else datetime(2020, 1, 1, tzinfo=UTC)
        common = {
            "station_id": "42001",
            "source_id": source,
            "observation_time": timestamp,
            "quality_flag": "not_checked",
            "raw_sha256": "a" * 64,
            "row_number": index,
        }
        result.extend(
            [
                {
                    **common,
                    "variable": "wave_height_m",
                    "value": height,
                    "unit": "m",
                    "period_kind": None,
                },
                {
                    **common,
                    "variable": "wave_period_s",
                    "value": period,
                    "unit": "s",
                    "period_kind": kind,
                },
            ]
        )
    return result


def all_row(data):
    return next(row for row in summarize_observations(data) if row["season"] == "all")


def test_linear_percentile_known_series():
    assert percentile([4, 1, 3, 2], 0.5) == 2.5
    assert percentile([4, 1, 3, 2], 0.95) == pytest.approx(3.85)
    assert percentile([7], 0.99) == 7
    assert percentile([], 0.5) is None
    assert percentile([1, 2], 0) == 1
    assert percentile([1, 2], 1) == 2


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan")])
def test_invalid_fraction_rejected(fraction):
    with pytest.raises(ValueError):
        percentile([1, 2], fraction)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_values_rejected(value):
    with pytest.raises(ValueError):
        percentile([1, value], 0.5)
    with pytest.raises(ValueError):
        summarize_observations(records([value], [8]))


def test_duplicate_timestamps_preserve_distinct_archive_rows():
    row = all_row(records([1, 2, 3, 4], [4, 5, 6, 7]))
    assert row["height_valid_count"] == 4
    assert row["height_p50_m"] == 2.5
    assert row["height_p95_m"] == pytest.approx(3.85)
    assert row["period_p50_s"] == 5.5
    assert row["contributing_years"] == 1


def test_unique_timestamp_comparison_retains_first_valid_paired_row():
    data = records([None, 2, 4], [12, 8, 6])
    table = summarize_observations(data, unique_timestamps=True)
    row = next(row for row in table if row["season"] == "all")
    assert row["height_valid_count"] == 1
    assert row["height_p50_m"] == 2
    assert row["band_period_mode_s"] == 8
    assert all_row(data)["height_valid_count"] == 2


def test_missing_values_counted_and_unpaired_period_not_used():
    row = all_row(records([2, 2, 2, None], [8, None, 6, 10]))
    assert row["height_missing_count"] == 1
    assert row["period_missing_count"] == 1
    assert row["period_valid_count"] == 3
    assert row["band_height_count"] == 3
    assert row["band_paired_count"] == 2
    assert row["band_period_mode_s"] == 6
    assert row["band_period_p10_s"] == pytest.approx(6.2)
    assert row["band_period_p90_s"] == pytest.approx(7.8)


def test_closed_band_includes_both_boundaries():
    # Twenty-one heights give p95=2.0 exactly; band is [1.75, 2.25].
    data = records([1.75] + [2.0] * 19 + [2.25], [6] + [8] * 19 + [10])
    row = all_row(data)
    assert row["height_p95_m"] == 2
    assert row["band_lower_m"] == 1.75
    assert row["band_upper_m"] == 2.25
    assert row["band_paired_count"] == 21


def test_months_and_october_to_march_use_utc_calendar():
    times = [datetime(2019, month, 1, tzinfo=UTC) for month in range(1, 13)]
    table = summarize_observations(records(list(range(1, 13)), [8] * 12, times=times))
    assert len(table) == 14
    season = next(row for row in table if row["season"] == "oct_mar")
    assert season["height_valid_count"] == 6
    assert season["height_p50_m"] == 6.5
    assert (
        next(row for row in table if row["season"] == "month_04")["height_p50_m"] == 4
    )
    offset = timezone(timedelta(hours=2))
    data = records([2], [8], times=[datetime(2020, 4, 1, 1, tzinfo=offset)])
    table = summarize_observations(data)
    assert (
        next(row for row in table if row["season"] == "month_03")["height_valid_count"]
        == 1
    )
    assert (
        next(row for row in table if row["season"] == "oct_mar")["height_valid_count"]
        == 1
    )


def test_naive_time_rejected():
    with pytest.raises(ValueError, match="timezone"):
        summarize_observations(records([2], [8], times=[datetime(2020, 1, 1)]))


@pytest.mark.parametrize(
    "variable,unit", [("wave_height_m", "ft"), ("wave_period_s", "ms")]
)
def test_wrong_units_rejected(variable, unit):
    data = records([2], [8])
    next(row for row in data if row["variable"] == variable)["unit"] = unit
    with pytest.raises(ValueError, match="unit"):
        summarize_observations(data)


def test_missing_period_kind_rejected():
    with pytest.raises(ValueError, match="period_kind"):
        summarize_observations(records([2], [8], kind=None))


def test_sources_and_period_kinds_are_separate():
    data = records([2], [8]) + records([10], [20], source="other", kind="peak")
    rows = [row for row in summarize_observations(data) if row["season"] == "all"]
    assert len(rows) == 2
    assert {
        (row["source_id"], row["period_kind"], row["height_p50_m"]) for row in rows
    } == {("ndbc", "dominant", 2), ("other", "peak", 10)}


def test_pair_requires_same_raw_file_and_row():
    data = records([2], [8])
    data[1]["raw_sha256"] = "b" * 64
    row = all_row(data)
    assert row["band_paired_count"] == 0
    assert row["band_period_mode_s"] is None


def test_duplicate_identity_rejected():
    data = records([2], [8])
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_observations(data + [dict(data[0])])


def test_pair_timestamp_mismatch_rejected():
    data = records([2], [8])
    data[1]["observation_time"] = datetime(2020, 1, 2, tzinfo=UTC)
    with pytest.raises(ValueError, match="timestamp"):
        summarize_observations(data)


def test_height_only_data_and_empty_month_are_explicit():
    data = records([2], [8])[:1]
    table = summarize_observations(data)
    row = next(row for row in table if row["season"] == "all")
    assert row["period_kind"] == "not_available"
    assert row["period_p50_s"] is None
    empty = next(row for row in table if row["season"] == "month_02")
    assert empty["height_valid_count"] == 0
    assert empty["height_p95_m"] is None
    assert summarize_observations([]) == []
