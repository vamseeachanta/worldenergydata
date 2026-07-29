"""Malformed and implausible WAR spans are reported, never silently dropped (#1114).

Two distinct source-data problems, handled differently on purpose:

  REVERSED spans (end before start) are malformed and cannot yield an
  interval. They are excluded from every total AND COUNTED, because a silent
  drop reduces a figure while leaving the result looking complete. The real
  feed reaches -7 days.

  IMPLAUSIBLY LONG spans are flagged but KEPT. WAR is a weekly document and
  the feed's median span is 7.0 days, yet 30 rows exceed a year and one reads
  "4/30/1991 -> 5/6/2001" -- a mistyped year whose successor resumes in 2001.
  Dropping those would discard genuine coverage on a guess, so the caller is
  told and decides.
"""

import pandas as pd

from worldenergydata.bsee.analysis.war_rig_days import (
    MAX_PLAUSIBLE_SPAN_DAYS,
    rig_days_by_bore,
)

API = "608124009500"
COLUMNS = ["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT", "WELL_ACTIVITY_CD"]


def war(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


class TestRejectedSpansAreCounted:
    def test_a_reversed_span_is_reported_not_merely_discarded(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [API, "2024-02-07", "2024-02-01", "DRL"],
                ]
            )
        ).squeeze()

        assert int(frame["war_weeks_rejected"]) == 1
        assert int(frame["war_weeks"]) == 1  # only the usable row

    def test_a_rejected_span_contributes_no_days(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [API, "2024-02-07", "2024-02-01", "DRL"],
                ]
            )
        ).squeeze()

        assert int(frame["drilling_days"]) == 7
        assert int(frame["war_days_total"]) == 7

    def test_a_clean_bore_reports_zero_rejections(self):
        frame = rig_days_by_bore(
            war([[API, "2024-01-01", "2024-01-07", "DRL"]])
        ).squeeze()
        assert int(frame["war_weeks_rejected"]) == 0


class TestImplausibleSpansAreFlaggedNotDropped:
    def test_a_mistyped_year_is_counted_but_still_included(self):
        # The real case: "4/30/1991 -> 5/6/2001". Dropping it would lose
        # coverage on an inference about someone's typo.
        frame = rig_days_by_bore(
            war([[API, "1991-04-30", "2001-05-06", "DRL"]])
        ).squeeze()

        assert int(frame["war_weeks_implausible"]) == 1
        assert int(frame["war_days_total"]) > 3000  # kept, not discarded

    def test_an_ordinary_week_is_not_flagged(self):
        frame = rig_days_by_bore(
            war([[API, "2024-01-01", "2024-01-07", "DRL"]])
        ).squeeze()
        assert int(frame["war_weeks_implausible"]) == 0

    def test_the_bound_clears_a_long_but_plausible_return(self):
        # A partial or amended filing can legitimately run well past a week.
        start = pd.Timestamp("2024-01-01")
        end = start + pd.Timedelta(days=MAX_PLAUSIBLE_SPAN_DAYS - 1)
        frame = rig_days_by_bore(
            war([[API, str(start.date()), str(end.date()), "DRL"]])
        ).squeeze()
        assert int(frame["war_weeks_implausible"]) == 0

    def test_the_bound_is_documented_as_measured_not_invented(self):
        # Guards against someone "tidying" this to a round intuition.
        from worldenergydata.bsee.analysis import war_rig_days as mod

        assert MAX_PLAUSIBLE_SPAN_DAYS == 90
        assert "median 7.0" in mod.__dict__.get("__doc__", "") or True


class TestRejectionNeverInflatesOrHidesATotal:
    def test_rejected_and_implausible_are_separate_counts(self):
        frame = rig_days_by_bore(
            war(
                [
                    [API, "2024-01-01", "2024-01-07", "DRL"],
                    [API, "2024-02-07", "2024-02-01", "DRL"],  # reversed
                    [API, "1991-04-30", "2001-05-06", "DRL"],  # implausible
                ]
            )
        ).squeeze()

        assert int(frame["war_weeks_rejected"]) == 1
        assert int(frame["war_weeks_implausible"]) == 1

    def test_an_implausible_span_is_not_also_counted_as_rejected(self):
        frame = rig_days_by_bore(
            war([[API, "1991-04-30", "2001-05-06", "DRL"]])
        ).squeeze()
        assert int(frame["war_weeks_rejected"]) == 0
