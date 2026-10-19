"""Date metadata regressions for the API12 summary before survey processing.

Schema sources: the retained ``data/modules/bsee/current/wells/well_data.csv``
header (uppercase names), and ``WellAPI12.prepare_well_paths`` (display aliases).
Dates below are synthetic calendar examples, not published well measurements.
No geometry equation, engineering coefficient or acceptance limit is introduced.
"""

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.well_api12 import WellAPI12


@pytest.mark.parametrize(
    "td_column, spud_column",
    [
        ("TOTAL_DEPTH_DATE", "WELL_SPUD_DATE"),
        ("Total Depth Date", "Spud Date"),
    ],
)
def test_borehole_summary_orders_parsed_dates(td_column, spud_column):
    """Hand check: October follows September; March follows February.

    Lexicographic maxima of the unpadded strings select September and
    February instead. The ISO entry also represents October, so mixed input
    formats must be parsed individually before selecting the latest date.
    """
    source = pd.DataFrame(
        {
            td_column: ["9/30/2023", "10/01/2023", "2023-10-02"],
            spud_column: ["2/28/2023", "3/01/2023", None],
        },
        index=[7, 3, 9],  # Synthetic labels exercise index independence.
    )
    before = source.copy(deep=True)

    result = WellAPI12().get_well_borehole_data({"api12_BoreholeRawData": source}, None)

    assert result["TOTAL_DEPTH_DATE"].item() == pd.Timestamp("2023-10-02")
    assert result["WELL_SPUD_DATE"].item() == pd.Timestamp("2023-03-01")
    pd.testing.assert_frame_equal(source, before)


@pytest.mark.parametrize(
    "dates",
    [
        {},
        {"TOTAL_DEPTH_DATE": "not a date", "WELL_SPUD_DATE": None},
        {"Total Depth Date": "", "Spud Date": "not a date"},
    ],
)
def test_missing_or_unusable_borehole_dates_remain_unknown(dates):
    """No valid calendar value implies NaT, never a fabricated date."""
    source = pd.DataFrame([{"unrelated_metadata": "present", **dates}])
    before = source.copy(deep=True)

    result = WellAPI12().get_well_borehole_data({"api12_BoreholeRawData": source}, None)

    assert pd.isna(result["TOTAL_DEPTH_DATE"].item())
    assert pd.isna(result["WELL_SPUD_DATE"].item())
    pd.testing.assert_frame_equal(source, before)


@pytest.mark.parametrize("column", ["TOTAL_DEPTH_DATE", "WELL_SPUD_DATE"])
def test_missing_one_date_does_not_discard_the_other(column):
    """One supplied date is retained verbatim; the absent date is unknown."""
    result = WellAPI12().get_well_borehole_data(
        {"api12_BoreholeRawData": pd.DataFrame([{column: "2023-03-01"}])},
        None,
    )

    for name in ("TOTAL_DEPTH_DATE", "WELL_SPUD_DATE"):
        if name == column:
            assert result[name].item() == pd.Timestamp("2023-03-01")
        else:
            assert pd.isna(result[name].item())


def test_invalid_rows_do_not_hide_valid_dates():
    """Hand check: the only valid date is March first, despite bad rows."""
    source = pd.DataFrame(
        {
            column: [None, "not a date", "2023-03-01", ""]
            for column in ("TOTAL_DEPTH_DATE", "WELL_SPUD_DATE")
        }
    )

    result = WellAPI12().get_well_borehole_data({"api12_BoreholeRawData": source}, None)

    for column in ("TOTAL_DEPTH_DATE", "WELL_SPUD_DATE"):
        assert result[column].item() == pd.Timestamp("2023-03-01")


@pytest.mark.parametrize("raw_date", ["2023-03-01", None])
def test_raw_borehole_columns_keep_precedence(raw_date):
    """Source columns stay authoritative even if an alias has a later date."""
    result = WellAPI12().get_well_borehole_data(
        {
            "api12_BoreholeRawData": pd.DataFrame(
                [
                    {
                        "TOTAL_DEPTH_DATE": raw_date,
                        "Total Depth Date": "2023-10-02",
                        "WELL_SPUD_DATE": raw_date,
                        "Spud Date": "2023-10-02",
                    }
                ]
            )
        },
        None,
    )

    for column in ("TOTAL_DEPTH_DATE", "WELL_SPUD_DATE"):
        if raw_date is None:
            assert pd.isna(result[column].item())
        else:
            assert result[column].item() == pd.Timestamp("2023-03-01")


def test_empty_borehole_table_retains_unknown_dates():
    """An empty table supplies neither milestone; retain the existing contract."""
    result = WellAPI12().get_well_borehole_data(
        {"api12_BoreholeRawData": pd.DataFrame()}, None
    )

    assert pd.isna(result["TOTAL_DEPTH_DATE"].item())
    assert pd.isna(result["WELL_SPUD_DATE"].item())


@pytest.mark.parametrize(
    "dates",
    [{}, {"Total Depth Date": "2023-10-02", "Spud Date": "2023-03-01"}],
)
def test_api12_analysis_reaches_survey_preparation_without_raw_dates(
    monkeypatch, dates
):
    """The real summary and survey setup must run for absent or legacy dates.

    Rig analysis and the external binary loader are isolated: neither defines
    this date contract. Expected dates are the supplied calendar literals, or
    NaT where absent; no output of the method supplies the expectation.
    """
    api = WellAPI12()
    cfg = {}
    source = pd.DataFrame([{"unrelated_metadata": "present", **dates}])
    before = source.copy(deep=True)
    monkeypatch.setattr(
        api, "get_sidetracklabel_and_rig_rigdays", lambda cfg, data, summary: summary
    )
    monkeypatch.setattr(
        api, "get_directional_surveys_by_api10", lambda cfg: pd.DataFrame()
    )

    returned_cfg, summary = api.get_api12_analysis(
        cfg, {"api12_BoreholeRawData": source, "merged_api12_df": source}
    )

    assert returned_cfg is cfg
    assert api.output_data_well_path == {}
    for display, raw in (
        ("Total Depth Date", "TOTAL_DEPTH_DATE"),
        ("Spud Date", "WELL_SPUD_DATE"),
    ):
        if display in dates:
            assert summary[raw].item() == pd.Timestamp(dates[display])
            assert api.output_data_api12_df[display].item() == pd.Timestamp(
                dates[display]
            )
        else:
            assert pd.isna(summary[raw].item())
            assert pd.isna(api.output_data_api12_df[display].item())
    pd.testing.assert_frame_equal(source, before)
