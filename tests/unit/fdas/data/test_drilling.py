"""Tests for FDAS drilling & completion timeline module."""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.fdas.data.drilling import (
    CompletionActivityClassifier,
    DrillingDataError,
    DrillingTimelineExtractor,
    calculate_drilling_days,
)

# ---------------------------------------------------------------------------
# DrillingDataError
# ---------------------------------------------------------------------------


class TestDrillingDataError:
    def test_is_exception(self):
        err = DrillingDataError("test")
        assert isinstance(err, Exception)

    def test_message(self):
        err = DrillingDataError("missing column")
        assert str(err) == "missing column"


# ---------------------------------------------------------------------------
# CompletionActivityClassifier
# ---------------------------------------------------------------------------


class TestClassifierInit:
    def test_default_keywords(self):
        c = CompletionActivityClassifier()
        assert c.completion_kw is CompletionActivityClassifier.COMPLETION_KEYWORDS
        assert c.testing_kw is CompletionActivityClassifier.TESTING_KEYWORDS
        assert c.drilling_kw is CompletionActivityClassifier.DRILLING_KEYWORDS

    def test_custom_keywords(self):
        custom = {"completion": {"my_kw"}, "testing": {"test_kw"}}
        c = CompletionActivityClassifier(custom_keywords=custom)
        assert c.completion_kw == {"my_kw"}
        assert c.testing_kw == {"test_kw"}
        # drilling falls back to default
        assert c.drilling_kw is CompletionActivityClassifier.DRILLING_KEYWORDS


class TestClassifyActivity:
    def test_completion_perforate(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Perforated 15,000-15,500ft") == "completion"

    def test_completion_frac(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Frac stage 5 complete") == "completion"

    def test_completion_casing(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Running 9-5/8 casing to 12000ft") == "completion"

    def test_completion_xmas_tree(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Installed xmas tree") == "completion"

    def test_testing_dst(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Running DST tools") == "testing"

    def test_testing_flow_test(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Conducting flow test") == "testing"

    def test_testing_pressure_test(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Pressure test on BOP") == "testing"

    def test_drilling_spud(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Spudded well at 0800hrs") == "drilling"

    def test_drilling_td(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Reached TD at 25,000ft") == "drilling"

    def test_unknown_remark(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity("Waiting on weather") == "unknown"

    def test_nan_remark(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity(float("nan")) == "unknown"

    def test_none_remark(self):
        c = CompletionActivityClassifier()
        assert c.classify_activity(None) == "unknown"

    def test_completion_takes_priority_over_testing(self):
        c = CompletionActivityClassifier()
        # "cement" is completion, even if "test" is also present
        assert c.classify_activity("Cement test") == "completion"


class TestExtractMudWeight:
    def test_valid_ppg(self):
        c = CompletionActivityClassifier()
        assert c.extract_mud_weight("Drilling with 12.5 ppg mud") == 12.5

    def test_integer_ppg(self):
        c = CompletionActivityClassifier()
        assert c.extract_mud_weight("Using 14 ppg") == 14.0

    def test_no_ppg(self):
        c = CompletionActivityClassifier()
        assert c.extract_mud_weight("Drilling ahead at 500ft/day") is None

    def test_nan(self):
        c = CompletionActivityClassifier()
        assert c.extract_mud_weight(float("nan")) is None

    def test_none(self):
        c = CompletionActivityClassifier()
        assert c.extract_mud_weight(None) is None


# ---------------------------------------------------------------------------
# DrillingTimelineExtractor
# ---------------------------------------------------------------------------


def _make_activity_df(**overrides):
    defaults = {
        "API_WELL_NUMBER": ["608054011700"],
        "SPUD_DATE": [datetime(2020, 1, 1)],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


class TestDrillingTimelineExtractorInit:
    def test_valid_init(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        assert extractor.remarks_df is None

    def test_missing_columns_raises(self):
        df = pd.DataFrame({"OTHER": ["A"]})
        with pytest.raises(DrillingDataError, match="Missing required columns"):
            DrillingTimelineExtractor(df)

    def test_with_remarks(self):
        df = _make_activity_df()
        remarks = pd.DataFrame({"REMARK": ["test"]})
        extractor = DrillingTimelineExtractor(df, remarks_df=remarks)
        assert extractor.remarks_df is not None


class TestCalculateDrillingDays:
    def test_with_td_date(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        days, ranges = extractor.calculate_drilling_days(
            datetime(2020, 1, 1), datetime(2020, 3, 15)
        )
        assert days == 74.0
        assert len(ranges) == 1

    def test_without_td_date_estimates_60(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        days, ranges = extractor.calculate_drilling_days(datetime(2020, 1, 1))
        assert days == 60.0


class TestAllocateDaysToMonths:
    def test_single_month(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        result = extractor.allocate_days_to_months(
            datetime(2020, 1, 5), datetime(2020, 1, 20)
        )
        assert result == {"2020-01": 15}

    def test_cross_month(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        result = extractor.allocate_days_to_months(
            datetime(2020, 1, 15), datetime(2020, 3, 10)
        )
        assert "2020-01" in result
        assert "2020-02" in result
        assert "2020-03" in result
        assert result["2020-01"] == 17  # Jan 15-31 = 17 days
        assert result["2020-02"] == 29  # Feb has 29 days in 2020
        assert result["2020-03"] == 9  # Mar 1-9 (end_date Mar 10 exclusive)

    def test_cross_year(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        result = extractor.allocate_days_to_months(
            datetime(2020, 12, 15), datetime(2021, 1, 10)
        )
        assert "2020-12" in result
        assert "2021-01" in result

    def test_same_day_returns_empty(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        result = extractor.allocate_days_to_months(
            datetime(2020, 1, 1), datetime(2020, 1, 1)
        )
        assert result == {}


class TestExtractWellTimeline:
    def test_basic_timeline(self):
        df = _make_activity_df(
            API_WELL_NUMBER=["WELL-001"],
            SPUD_DATE=[datetime(2020, 1, 1)],
            TD_DATE=[datetime(2020, 3, 1)],
            COMPLETION_DATE=[datetime(2020, 4, 1)],
        )
        extractor = DrillingTimelineExtractor(df)
        timeline = extractor.extract_well_timeline("WELL-001")
        assert timeline["drilling_days"] == 60.0
        assert timeline["completion_days"] == 31
        assert "drilling_monthly" in timeline
        assert "completion_monthly" in timeline

    def test_missing_well_raises(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        with pytest.raises(DrillingDataError, match="No data found"):
            extractor.extract_well_timeline("NONEXISTENT")

    def test_no_td_date_uses_default(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        timeline = extractor.extract_well_timeline("608054011700")
        assert timeline["drilling_days"] == 60.0
        assert timeline["completion_days"] == 30  # default estimate


class TestClassifyActivitiesFromRemarks:
    def test_no_remarks_raises(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        with pytest.raises(DrillingDataError, match="Remarks data not provided"):
            extractor.classify_activities_from_remarks()

    def test_with_remarks(self):
        df = _make_activity_df()
        remarks = pd.DataFrame(
            {"REMARK": ["Perforated zone", "Drilling ahead", "Waiting"]}
        )
        extractor = DrillingTimelineExtractor(df, remarks_df=remarks)
        result = extractor.classify_activities_from_remarks()
        assert "ACTIVITY_TYPE" in result.columns
        assert "MUD_WEIGHT_PPG" in result.columns
        assert result["ACTIVITY_TYPE"].iloc[0] == "completion"
        assert result["ACTIVITY_TYPE"].iloc[1] == "drilling"
        assert result["ACTIVITY_TYPE"].iloc[2] == "unknown"


class TestConvenienceCalculateDrillingDays:
    def test_simple(self):
        result = calculate_drilling_days(datetime(2020, 1, 1), datetime(2020, 3, 15))
        assert result == 74


class TestExtractAllWellsTimeline:
    def test_single_well(self):
        df = _make_activity_df()
        extractor = DrillingTimelineExtractor(df)
        result = extractor.extract_all_wells_timeline()
        assert len(result) == 1
        assert "drilling_days" in result.columns

    def test_multiple_wells(self):
        df = _make_activity_df(
            API_WELL_NUMBER=["W1", "W2"],
            SPUD_DATE=[datetime(2020, 1, 1), datetime(2020, 6, 1)],
        )
        extractor = DrillingTimelineExtractor(df)
        result = extractor.extract_all_wells_timeline()
        assert len(result) == 2
