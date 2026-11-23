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


@pytest.mark.parametrize("depth", [12, None])
def test_retained_value_without_evidence_does_not_inherit_fallback_evidence(depth):
    """Depth stays 12 or unknown; only the imported operator gets an origin."""
    records = pd.DataFrame({"field_id": ["linked"], "water_depth": [depth]})
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "water_depth": [99],
            "operator": ["synthetic"],
            "value_origins": [{"water_depth": "default", "operator": "reported"}],
            "source": ["synthetic fallback"],
        }
    )
    generator = DatasetGenerator()
    result = generator.create_production_dataset(records, fields)
    assert result.loc[0, "water_depth"] == depth
    assert result.loc[0, "operator"] == "synthetic"
    assert result.loc[0, "value_origins"] == {"operator": "reported"}
    assert "source" not in result
    assert_frame_equal(result, generator.create_production_dataset(result, fields))


def test_existing_evidence_without_its_value_cannot_label_a_fallback():
    """A measured label without an observation cannot establish depth 99."""
    records = pd.DataFrame(
        {
            "field_id": ["linked"],
            "source": ["synthetic measurement"],
            "value_origins": [{"water_depth": "measured"}],
        }
    )
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "water_depth": [99],
            "source": ["synthetic fallback"],
            "value_origins": [{"water_depth": "default"}],
        }
    )
    with pytest.raises(pd.errors.MergeError, match="provenance has no observation"):
        DatasetGenerator().create_production_dataset(records, fields)


def test_imported_origins_extend_existing_evidence_without_mutating_inputs():
    """Retained depth 12 stays measured; the imported operator is reported."""
    records = pd.DataFrame(
        {
            "field_id": ["linked", None],
            "water_depth": [12, None],
            "source": ["synthetic measurement", None],
            "value_origins": [{"water_depth": "measured"}, None],
        }
    )
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "water_depth": [99],
            "operator": ["synthetic"],
            "source": ["synthetic fallback"],
            "value_origins": [{"water_depth": "default", "operator": "reported"}],
        }
    )
    generator = DatasetGenerator()
    result = generator.create_production_dataset(records, fields)
    assert result.loc[0, "water_depth"] == 12
    assert result.loc[0, "source"] == "synthetic measurement"
    assert result.loc[0, "value_origins"] == {
        "water_depth": "measured",
        "operator": "reported",
    }
    assert pd.isna(result.loc[1, "operator"])
    assert result.loc[1, "value_origins"] is None
    assert records.loc[0, "value_origins"] == {"water_depth": "measured"}
    assert fields.loc[0, "value_origins"] == {
        "water_depth": "default",
        "operator": "reported",
    }
    assert_frame_equal(result, generator.create_production_dataset(result, fields))


def test_entirely_imported_values_keep_their_shared_source():
    """With identity only, depth 99 and its default/source evidence join together."""
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "water_depth": [99],
            "source": ["synthetic fallback"],
            "value_origins": [{"water_depth": "default"}],
        }
    )
    result = DatasetGenerator().create_production_dataset(
        pd.DataFrame({"field_id": ["linked"]}), fields
    )
    assert result.loc[0, "water_depth"] == 99
    assert result.loc[0, "value_origins"] == {"water_depth": "default"}
    assert result.loc[0, "source"] == "synthetic fallback"


def test_origins_for_retained_values_do_not_make_imported_metadata_ambiguous():
    """Two discarded depth origins cannot make one imported operator ambiguous."""
    records = pd.DataFrame({"field_id": ["linked"], "water_depth": [12]})
    fields = pd.DataFrame(
        {
            "field_id": ["linked", "linked"],
            "water_depth": [99, 99],
            "operator": ["synthetic", "synthetic"],
            "value_origins": [
                {"water_depth": "measured", "operator": "reported"},
                {"water_depth": "default", "operator": "reported"},
            ],
        }
    )
    result = DatasetGenerator().create_production_dataset(records, fields)
    assert result.loc[0, "water_depth"] == 12
    assert result.loc[0, "operator"] == "synthetic"
    assert result.loc[0, "value_origins"] == {"operator": "reported"}


@pytest.mark.parametrize("origins", [[], "measured", 12])
def test_invalid_supplemental_origins_fail_closed(origins):
    """Non-mapping evidence cannot establish an imported value's origin."""
    fields = pd.DataFrame(
        {"field_id": ["linked"], "water_depth": [99], "value_origins": [origins]}
    )
    with pytest.raises(pd.errors.MergeError, match="origins must be a mapping or null"):
        DatasetGenerator().create_production_dataset(
            pd.DataFrame({"field_id": ["linked"]}), fields
        )


def test_existing_source_without_observations_cannot_describe_imported_values():
    """A source alone provides no retained value to which it can be attributed."""
    records = pd.DataFrame(
        {"field_id": ["linked"], "source": ["synthetic measurement"]}
    )
    fields = pd.DataFrame({"field_id": ["linked"], "water_depth": [99]})
    with pytest.raises(pd.errors.MergeError, match="source has no observation"):
        DatasetGenerator().create_production_dataset(records, fields)


def test_orphan_origin_guard_checks_each_matched_record():
    """The second matched row's origin cannot label an imported fallback."""
    records = pd.DataFrame(
        {
            "field_id": ["first", "second"],
            "operator": ["synthetic", "synthetic"],
            "value_origins": [None, {"water_depth": "measured"}],
        }
    )
    fields = pd.DataFrame({"field_id": ["first", "second"], "water_depth": [99, 99]})
    with pytest.raises(pd.errors.MergeError, match="provenance has no observation"):
        DatasetGenerator().create_production_dataset(records, fields)


@pytest.mark.parametrize("existing_origins", [False, True])
def test_result_origins_are_independent_between_rows_and_inputs(existing_origins):
    """Changing one output's nested evidence cannot change another observation."""
    records = pd.DataFrame(
        {"field_id": ["linked", "linked"], "operator": ["synthetic", "synthetic"]}
    )
    if existing_origins:
        records["value_origins"] = [
            {"operator": {"kind": "reported"}},
            {"operator": {"kind": "reported"}},
        ]
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "water_depth": [99],
            "value_origins": [{"water_depth": {"kind": "default"}}],
        }
    )
    result = DatasetGenerator().create_production_dataset(records, fields)
    result.loc[0, "value_origins"]["water_depth"]["kind"] = "altered"
    assert result.loc[1, "value_origins"]["water_depth"] == {"kind": "default"}
    assert fields.loc[0, "value_origins"] == {"water_depth": {"kind": "default"}}
    if existing_origins:
        result.loc[0, "value_origins"]["operator"]["kind"] = "altered"
        assert result.loc[1, "value_origins"]["operator"] == {"kind": "reported"}
        assert records["value_origins"].tolist() == [
            {"operator": {"kind": "reported"}},
            {"operator": {"kind": "reported"}},
        ]


@pytest.mark.parametrize("observed", [False, True])
def test_wellbore_imports_only_descriptive_field_metadata(observed):
    """The wellbore projection excludes supplemental values and their evidence."""
    records = pd.DataFrame({"field_id": ["linked"]})
    if observed:
        records["water_depth"] = [12]
        records["source"] = ["synthetic measurement"]
        records["value_origins"] = [{"water_depth": "measured"}]
    fields = pd.DataFrame(
        {
            "field_id": ["linked"],
            "field_name": ["synthetic"],
            "operator": ["synthetic"],
            "discovery_year": [None],
            "water_depth": [99],
            "source": ["synthetic fallback"],
            "value_origins": [{"water_depth": "default", "operator": "reported"}],
        }
    )
    result = DatasetGenerator().create_wellbore_dataset(records, fields)
    assert result.loc[0, "field_name"] == "synthetic"
    if observed:
        assert result.loc[0, "water_depth"] == 12
        assert result.loc[0, "source"] == "synthetic measurement"
        assert result.loc[0, "value_origins"] == {"water_depth": "measured"}
    else:
        assert {"water_depth", "source", "value_origins"}.isdisjoint(result.columns)
