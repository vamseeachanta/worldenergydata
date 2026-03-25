"""Unit tests for the GeologicalEraClassifier module."""

import pytest
from pathlib import Path

import pandas as pd

from tests.test_markers import unit


@unit
class TestGeologicalEraClassifier:
    """Tests for GeologicalEraClassifier class."""

    @pytest.fixture
    def sample_paleowells_df(self):
        """Create sample paleowells data matching Paleowells.csv format."""
        return pd.DataFrame(
            {
                "Record Type": ["P"] * 8,
                "API Well Number": [
                    "608054000300",
                    "608054000300",
                    "608054000301",
                    "608054000301",
                    "608054000302",
                    "608054000303",
                    "608054000304",
                    "608054000305",
                ],
                "Measured Depth": [
                    12660, 14340, 10830, 11500, 9000, 15000, 8000, 7500
                ],
                "True Vertical Depth": [
                    12628, 14067, 10830, 11200, 8800, 14500, 7800, 7300
                ],
                "Definite/Possible": [
                    "DEF", "DEF", "DEF", "POS", "DEF", "DEF", "DEF", "DEF"
                ],
                "Paleo Age": [
                    "Upper Oligocene (Chattian) Discoaster woodringii",
                    "Upper Oligocene (Chattian) Clausicoccus fenestratus",
                    "Lower Eocene (Ypresian) Morozovella quetra",
                    "Eocene",
                    "Miocene Middle Dictyococcites bisectus",
                    "Upper Paleocene (Thanetian) Planulorotalites",
                    "Pliocene Globorotalia margaritae",
                    "Pleistocene upper",
                ],
            }
        )

    @pytest.fixture
    def classifier(self, sample_paleowells_df):
        """Create a classifier with sample data."""
        from worldenergydata.bsee.paleowells.era_classifier import (
            GeologicalEraClassifier,
        )

        return GeologicalEraClassifier(dataframe=sample_paleowells_df)

    def test_init_with_dataframe(self, sample_paleowells_df):
        """Test initialization with DataFrame."""
        from worldenergydata.bsee.paleowells.era_classifier import (
            GeologicalEraClassifier,
        )

        clf = GeologicalEraClassifier(dataframe=sample_paleowells_df)
        assert clf._df is not None
        assert len(clf._df) == 8

    def test_eras_constant(self):
        """Test that ERAS list contains expected geological eras."""
        from worldenergydata.bsee.paleowells.era_classifier import (
            GeologicalEraClassifier,
        )

        assert "Paleocene" in GeologicalEraClassifier.ERAS
        assert "Eocene" in GeologicalEraClassifier.ERAS
        assert "Oligocene" in GeologicalEraClassifier.ERAS
        assert "Miocene" in GeologicalEraClassifier.ERAS
        assert "Pliocene" in GeologicalEraClassifier.ERAS
        assert "Pleistocene" in GeologicalEraClassifier.ERAS

    def test_classify_well_oligocene(self, classifier):
        """Test classifying a well with Oligocene data."""
        result = classifier.classify_well("608054000300")
        assert result == "Oligocene"

    def test_classify_well_eocene(self, classifier):
        """Test classifying a well with Eocene data."""
        result = classifier.classify_well("608054000301")
        assert result == "Eocene"

    def test_classify_well_miocene(self, classifier):
        """Test classifying a well with Miocene data."""
        result = classifier.classify_well("608054000302")
        assert result == "Miocene"

    def test_classify_well_paleocene(self, classifier):
        """Test classifying a well with Paleocene data."""
        result = classifier.classify_well("608054000303")
        assert result == "Paleocene"

    def test_classify_well_pliocene(self, classifier):
        """Test classifying a well with Pliocene data."""
        result = classifier.classify_well("608054000304")
        assert result == "Pliocene"

    def test_classify_well_pleistocene(self, classifier):
        """Test classifying a well with Pleistocene data."""
        result = classifier.classify_well("608054000305")
        assert result == "Pleistocene"

    def test_classify_well_unknown_returns_none(self, classifier):
        """Test classifying an unknown well returns None."""
        result = classifier.classify_well("999999999999")
        assert result is None

    def test_classify_field_dominant_era(self, classifier):
        """Test classifying a field returns the dominant era."""
        # Well 300 = Oligocene (2 records), Well 301 = Eocene (2 records)
        # Both Oligocene and Eocene have 2 wells each in this field
        result = classifier.classify_field(
            ["608054000300", "608054000301"]
        )
        assert result in ("Oligocene", "Eocene")

    def test_classify_field_single_well(self, classifier):
        """Test classifying a field with single well."""
        result = classifier.classify_field(["608054000303"])
        assert result == "Paleocene"

    def test_classify_field_empty_wells(self, classifier):
        """Test classifying a field with no wells returns Unknown."""
        result = classifier.classify_field([])
        assert result == "Unknown"

    def test_classify_field_unknown_wells(self, classifier):
        """Test classifying a field with only unknown wells returns Unknown."""
        result = classifier.classify_field(["999999999999"])
        assert result == "Unknown"

    def test_get_era_summary(self, classifier):
        """Test getting era summary counts."""
        summary = classifier.get_era_summary()
        assert isinstance(summary, dict)
        # Should have counts for eras present in the data
        assert summary.get("Oligocene", 0) > 0
        assert summary.get("Eocene", 0) > 0

    def test_get_well_eras(self, classifier):
        """Test getting era classification for all wells."""
        result = classifier.get_well_eras()
        assert isinstance(result, dict)
        assert result["608054000300"] == "Oligocene"
        assert result["608054000303"] == "Paleocene"

    def test_empty_dataframe(self):
        """Test classifier with empty DataFrame."""
        from worldenergydata.bsee.paleowells.era_classifier import (
            GeologicalEraClassifier,
        )

        empty_df = pd.DataFrame(
            columns=[
                "API Well Number",
                "Paleo Age",
                "Measured Depth",
                "True Vertical Depth",
            ]
        )
        clf = GeologicalEraClassifier(dataframe=empty_df)
        assert clf.classify_well("123") is None
        assert clf.classify_field(["123"]) == "Unknown"
        assert clf.get_era_summary() == {}
