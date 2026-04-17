"""Unit tests for the FieldNameResolver module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tests.test_markers import unit


@unit
class TestFieldNameResolver:
    """Tests for FieldNameResolver class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        from worldenergydata.bsee.data.field_names import FieldNameResolver

        self.resolver = FieldNameResolver.__new__(FieldNameResolver)
        self.resolver._field_names = {}
        self.resolver._loaded = False

    def test_init_with_default_data_dir(self):
        """Test initialization with default data directory."""
        from worldenergydata.bsee.data.field_names import FieldNameResolver

        resolver = FieldNameResolver()
        assert resolver._data_dir is not None

    def test_init_with_custom_data_dir(self, tmp_path):
        """Test initialization with custom data directory."""
        from worldenergydata.bsee.data.field_names import FieldNameResolver

        resolver = FieldNameResolver(data_dir=tmp_path)
        assert resolver._data_dir == tmp_path

    def test_resolve_known_field(self):
        """Test resolving a known field code returns display name."""
        self.resolver._field_names = {"123": "Thunder Horse", "456": "Mars"}
        self.resolver._loaded = True

        assert self.resolver.resolve("123") == "Thunder Horse"
        assert self.resolver.resolve("456") == "Mars"

    def test_resolve_unknown_field_returns_code(self):
        """Test resolving an unknown field code returns the code itself."""
        self.resolver._field_names = {"123": "Thunder Horse"}
        self.resolver._loaded = True

        assert self.resolver.resolve("999") == "999"

    def test_resolve_strips_whitespace(self):
        """Test that resolve strips whitespace from field codes."""
        self.resolver._field_names = {"123": "Thunder Horse"}
        self.resolver._loaded = True

        assert self.resolver.resolve(" 123 ") == "Thunder Horse"

    def test_resolve_batch(self):
        """Test batch resolution of multiple field codes."""
        self.resolver._field_names = {
            "100": "Thunder Horse",
            "200": "Mars",
            "300": "Atlantis",
        }
        self.resolver._loaded = True

        result = self.resolver.resolve_batch(["100", "200", "999"])
        assert result == {
            "100": "Thunder Horse",
            "200": "Mars",
            "999": "999",
        }

    def test_resolve_batch_empty_list(self):
        """Test batch resolution with empty list."""
        self.resolver._loaded = True
        result = self.resolver.resolve_batch([])
        assert result == {}

    def test_load_field_names_from_dataframe(self):
        """Test loading field names from a DataFrame."""
        df = pd.DataFrame(
            {
                "FIELD_NAME_CODE": ["100", "200", "300"],
                "FIELD_NAME": ["Thunder Horse", "Mars", "Atlantis"],
            }
        )
        self.resolver._merge_field_names(df, "FIELD_NAME_CODE", "FIELD_NAME")

        assert self.resolver._field_names["100"] == "Thunder Horse"
        assert self.resolver._field_names["200"] == "Mars"
        assert self.resolver._field_names["300"] == "Atlantis"

    def test_load_field_names_deduplicates(self):
        """Test that duplicate field codes keep first occurrence."""
        df = pd.DataFrame(
            {
                "FIELD_NAME_CODE": ["100", "100"],
                "FIELD_NAME": ["Thunder Horse", "TH Duplicate"],
            }
        )
        self.resolver._merge_field_names(df, "FIELD_NAME_CODE", "FIELD_NAME")
        assert self.resolver._field_names["100"] == "Thunder Horse"

    def test_load_field_names_handles_empty_dataframe(self):
        """Test loading from empty DataFrame doesn't error."""
        df = pd.DataFrame(columns=["FIELD_NAME_CODE", "FIELD_NAME"])
        self.resolver._merge_field_names(df, "FIELD_NAME_CODE", "FIELD_NAME")
        assert self.resolver._field_names == {}

    def test_load_field_names_handles_missing_columns(self):
        """Test loading from DataFrame with wrong columns logs warning."""
        df = pd.DataFrame({"OTHER_COL": ["a", "b"]})
        self.resolver._merge_field_names(df, "FIELD_NAME_CODE", "FIELD_NAME")
        assert self.resolver._field_names == {}

    def test_load_from_pickle_handles_lfs_stub(self, tmp_path):
        """Test that loading an LFS stub file returns empty DataFrame."""
        from worldenergydata.bsee.data.field_names import FieldNameResolver

        lfs_file = tmp_path / "test.bin"
        lfs_file.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:abc123\nsize 1234\n"
        )
        resolver = FieldNameResolver(data_dir=tmp_path)
        result = resolver._load_pickle_safe(lfs_file)
        assert result.empty

    def test_load_from_pickle_handles_missing_file(self, tmp_path):
        """Test that loading a missing file returns empty DataFrame."""
        from worldenergydata.bsee.data.field_names import FieldNameResolver

        resolver = FieldNameResolver(data_dir=tmp_path)
        result = resolver._load_pickle_safe(tmp_path / "nonexistent.bin")
        assert result.empty

    def test_get_all_field_names(self):
        """Test getting all loaded field names."""
        self.resolver._field_names = {
            "100": "Thunder Horse",
            "200": "Mars",
        }
        self.resolver._loaded = True

        result = self.resolver.get_all_field_names()
        assert len(result) == 2
        assert result["100"] == "Thunder Horse"

    def test_get_all_field_names_returns_copy(self):
        """Test that get_all_field_names returns a copy."""
        self.resolver._field_names = {"100": "Thunder Horse"}
        self.resolver._loaded = True

        result = self.resolver.get_all_field_names()
        result["999"] = "New Field"
        assert "999" not in self.resolver._field_names
