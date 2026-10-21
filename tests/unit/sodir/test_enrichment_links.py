"""Offline field-link contracts for issue 1164.

All identifiers and magnitudes are synthetic software inputs. Expected joins
are enumerated by hand, not calculated by the implementation. pandas documents
that null keys match by default (DataFrame.merge API reference, 2026, Warning):
https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html
"""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from worldenergydata.sodir.datasets import DatasetGenerator


@pytest.fixture(params=["wellbore", "production"])
def enrich(request):
    generator = DatasetGenerator()
    return getattr(generator, f"create_{request.param}_dataset")


@pytest.mark.parametrize("missing", [None, float("nan"), pd.NA, pd.NaT, "", " \t"])
def test_absent_field_keys_never_enrich(enrich, missing):
    """Only 'linked' joins; the absent left key has no eligible right row.

    Hand calculation: two input rows, two output rows; exactly one field name.
    Distinct missing source rows must neither enrich nor multiply the input.
    """
    records = pd.DataFrame({"field_id": [missing, "linked"]})
    fields = pd.DataFrame(
        {
            "field_id": [missing, missing, "linked"],
            "field_name": ["unlinked-a", "unlinked-b", "synthetic"],
            "operator": ["unlinked", "unlinked", "synthetic"],
            "discovery_year": [None, None, None],
        }
    )
    before_records, before_fields = records.copy(deep=True), fields.copy(deep=True)
    result = enrich(records, fields)
    assert len(result) == 2
    assert pd.isna(result.loc[0, "field_name"])
    assert result.loc[1, "field_name"] == "synthetic"
    assert_frame_equal(records, before_records)
    assert_frame_equal(fields, before_fields)


@pytest.mark.parametrize("key", [0, 7, "nan", "None", "NaT", "synthetic"])
def test_valid_keys_keep_exact_matching(enrich, key):
    """One explicit key selects one row; textual null spellings remain names."""
    records = pd.DataFrame({"field_id": [key]})
    fields = pd.DataFrame(
        {
            "field_id": [key, key],
            "field_name": ["synthetic", "synthetic"],
            "operator": ["synthetic", "synthetic"],
            "discovery_year": [None, None],
        }
    )
    result = enrich(records, fields)
    assert result["field_name"].tolist() == ["synthetic"]


def test_conflicting_field_identity_fails_instead_of_multiplying(enrich):
    """A single observation cannot select two different metadata records."""
    fields = pd.DataFrame(
        {
            "field_id": ["linked", "linked"],
            "field_name": ["first", "second"],
            "operator": ["synthetic", "synthetic"],
            "discovery_year": [None, None],
        }
    )
    with pytest.raises(pd.errors.MergeError, match="not a many-to-one merge"):
        enrich(pd.DataFrame({"field_id": ["linked"]}), fields)


def test_repeated_enrichment_preserves_observation_and_provenance(enrich):
    """Hand calculation: retained depth = 12 m, not the field fallback 99 m.

    The source and measured-origin evidence belong to that observation. Running
    twice must not rename, replace or duplicate them. No physical limit is used.
    """
    records = pd.DataFrame(
        {
            "field_id": ["linked"],
            "water_depth": [12],
            "source": ["synthetic measurement"],
            "value_origins": [{"water_depth": "measured"}],
        }
    )
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "field_name": ["synthetic"],
            "operator": ["synthetic"],
            "discovery_year": [None],
            "water_depth": [99],
            "source": ["synthetic fallback"],
            "value_origins": [{"water_depth": "default"}],
        }
    )
    first = enrich(records, fields)
    second = enrich(first, fields)
    assert first.loc[0, "water_depth"] == 12
    assert first.loc[0, "source"] == "synthetic measurement"
    assert first.loc[0, "value_origins"] == {"water_depth": "measured"}
    assert_frame_equal(first, second)


def test_existing_unknown_observation_is_not_silently_reclassified(enrich):
    """A missing observation and its origin remain paired; only new columns join."""
    records = pd.DataFrame({"field_id": ["linked"], "operator": [None]})
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "field_name": ["synthetic"],
            "operator": ["synthetic fallback"],
            "discovery_year": [None],
        }
    )
    result = enrich(records, fields)
    assert result.loc[0, "operator"] is None
    assert result.loc[0, "field_name"] == "synthetic"


@pytest.mark.parametrize("keys", [[], [None, " \t"]])
def test_no_eligible_source_identity_keeps_all_input_rows(enrich, keys):
    """No eligible right rows means one unchanged left identity, no field name."""
    records = pd.DataFrame({"field_id": [7]})
    fields = pd.DataFrame(
        {
            "field_id": keys,
            "field_name": ["unlinked"] * len(keys),
            "operator": ["unlinked"] * len(keys),
            "discovery_year": [None] * len(keys),
        }
    )
    result = enrich(records, fields)
    assert result["field_id"].tolist() == [7]
    assert result["field_name"].isna().all()


@pytest.mark.parametrize("conflicting", [False, True])
def test_supplemental_structured_origins_are_compared_without_coercion(conflicting):
    """Equal origin dicts describe one field; different origins are ambiguous.

    Hand calculation: duplicate equal rows collapse to one, with depth 12 m;
    measured versus default evidence cannot be chosen by source row order.
    """
    records = pd.DataFrame({"field_id": ["linked"]})
    fields = pd.DataFrame(
        {
            "field_id": ["linked", "linked"],
            "water_depth": [12, 12],
            "value_origins": [
                {"water_depth": "measured"},
                {"water_depth": "default" if conflicting else "measured"},
            ],
        }
    )
    generator = DatasetGenerator()
    if conflicting:
        with pytest.raises(pd.errors.MergeError, match="not a many-to-one merge"):
            generator.create_production_dataset(records, fields)
    else:
        result = generator.create_production_dataset(records, fields)
        assert result["water_depth"].tolist() == [12]
        assert result["value_origins"].tolist() == [{"water_depth": "measured"}]
        assert_frame_equal(result, generator.create_production_dataset(result, fields))
