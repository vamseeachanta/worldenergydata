"""Missing links are not identities (issue 1164).

Synthetic software cases only; no engineering constants or measured inputs.
Null cases follow pandas.isna, API reference, pandas 3.0 (2026):
https://pandas.pydata.org/docs/reference/api/pandas.isna.html
Expected links are enumerated by hand in each case, independently of the reducer.
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from worldenergydata.brazil_anp.field_concept import (
    _matching_platforms,
    _matching_wells,
    build_brazil_field_meta,
)

MISSING = [None, float("nan"), pd.NA, pd.NaT, "", " \t"]


@pytest.mark.parametrize("missing", MISSING)
def test_missing_requested_name_cannot_select_a_field(missing):
    """No requested identity means no field, even if source identity is absent."""
    with pytest.raises(ValueError, match="field_name must be a non-blank string"):
        build_brazil_field_meta(
            fields_df=pd.DataFrame({"CAMPO": [missing]}),
            platforms_df=pd.DataFrame(),
            wells_df=pd.DataFrame(),
            field_name=missing,
        )


@pytest.mark.parametrize(
    "matcher,column",
    [
        (_matching_platforms, "[CAMPOS]"),
        (_matching_wells, "Campo"),
        (_matching_wells, "CAMPO"),
    ],
)
@pytest.mark.parametrize("missing", MISSING)
def test_missing_requested_link_matches_no_rows(matcher, column, missing):
    """An absent name cannot match an absent row link or an empty list token."""
    rows = pd.DataFrame({column: [missing, ";", "SYNTHETIC"]})
    before = rows.copy(deep=True)
    assert matcher(rows, missing).empty
    assert_frame_equal(rows, before)


@pytest.mark.parametrize("name", ["SYNTHETIC", "nan", "none", "nat"])
def test_missing_source_links_cannot_contaminate_valid_metadata(name):
    """Only the explicitly named row contributes: depth 12 and one well.

    Hand calculation: eligible platform depths = [12]; mean = 12 / 1 = 12 m.
    Eligible well identities = {test-well}; unique count = 1. The synthetic
    magnitudes only distinguish rows; they are not published engineering data.
    Literal text 'nan', 'none', and 'nat' remains a valid name, not a null marker.
    """
    fields = pd.DataFrame({"CAMPO": MISSING + [name]})
    platforms = pd.DataFrame(
        {
            "[CAMPOS]": MISSING + [f"; {name};"],
            "[LÂMINA D'ÁGUA (m)]": ["99"] * len(MISSING) + ["12"],
        }
    )
    wells = pd.DataFrame(
        {
            "Campo": MISSING + [name],
            "POCO": ["unlinked"] * len(MISSING) + ["test-well"],
        }
    )
    originals = [frame.copy(deep=True) for frame in (fields, platforms, wells)]
    kwargs = dict(
        fields_df=fields, platforms_df=platforms, wells_df=wells, field_name=name
    )
    result = build_brazil_field_meta(**kwargs)
    assert result["field_name"] == name
    assert result["water_depth_m"] == 12
    assert result["well_count"] == 1
    assert build_brazil_field_meta(**kwargs) == result
    for frame, original in zip((fields, platforms, wells), originals):
        assert_frame_equal(frame, original)


def test_valid_name_normalization_is_preserved():
    """One case/accent-insensitive link gives one unique synthetic well."""
    result = build_brazil_field_meta(
        fields_df=pd.DataFrame({"CAMPO": ["ÁREA TESTE"]}),
        platforms_df=pd.DataFrame(),
        wells_df=pd.DataFrame({"Campo": [" area teste "], "POCO": ["test-well"]}),
        field_name=" área teste ",
    )
    assert result["well_count"] == 1
