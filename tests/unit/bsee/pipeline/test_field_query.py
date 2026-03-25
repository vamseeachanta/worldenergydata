"""Unit tests for the BSEE pipeline field query interface.

Tests the FieldContext dataclass, resolve_field() function,
build_lease_field_map() helper, and FieldQueryError exception.
All tests use synthetic data -- no real binary files required.
"""

from __future__ import annotations

import logging
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Lightweight stubs for FieldNameResolver and GeologicalEraClassifier
# ---------------------------------------------------------------------------

class StubFieldNameResolver:
    """Minimal stub replicating FieldNameResolver's public interface."""

    def __init__(self, field_names: Dict[str, str]):
        self._field_names = dict(field_names)

    def resolve(self, field_code: str) -> str:
        code = str(field_code).strip()
        return self._field_names.get(code, code)

    def get_all_field_names(self) -> Dict[str, str]:
        return dict(self._field_names)


class StubEraClassifier:
    """Minimal stub replicating GeologicalEraClassifier's public interface."""

    ERAS = [
        "Paleocene",
        "Eocene",
        "Oligocene",
        "Miocene",
        "Pliocene",
        "Pleistocene",
    ]

    def __init__(self, well_eras: Optional[Dict[str, str]] = None):
        self._well_eras = well_eras or {}

    def classify_well(self, api_well_number: str) -> Optional[str]:
        return self._well_eras.get(str(api_well_number).strip())

    def classify_field(self, field_wells: List[str]) -> str:
        from collections import Counter

        if not field_wells:
            return "Unknown"
        counter: Counter = Counter()
        for api in field_wells:
            era = self.classify_well(api)
            if era:
                counter[era] += 1
        if not counter:
            return "Unknown"
        return counter.most_common(1)[0][0]

    def get_well_eras(self) -> Dict[str, str]:
        return dict(self._well_eras)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def field_resolver():
    """FieldNameResolver with a handful of known fields."""
    return StubFieldNameResolver(
        {
            "001": "BUCKSKIN",
            "002": "THUNDER HORSE",
            "003": "MARS",
            "004": "ATLANTIS",
        }
    )


@pytest.fixture()
def era_classifier():
    """GeologicalEraClassifier with a few well -> era mappings."""
    return StubEraClassifier(
        {
            "6081140012": "Miocene",
            "6081140013": "Miocene",
            "6081140020": "Eocene",
            "6081140025": "Eocene",
            "6081140030": "Oligocene",
        }
    )


@pytest.fixture()
def empty_era_classifier():
    """GeologicalEraClassifier with no data."""
    return StubEraClassifier()


@pytest.fixture()
def lease_field_map():
    """DataFrame mapping leases to fields."""
    return pd.DataFrame(
        {
            "LEASE_NUMBER": ["G12345", "G12346", "G12347", "G99999"],
            "FIELD_NAME_CODE": ["001", "001", "002", "003"],
            "AREA_CODE": ["GC", "GC", "MC", "MC"],
        }
    )


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from worldenergydata.bsee.pipeline.field_query import (
    FieldContext,
    FieldQueryError,
    build_lease_field_map,
    resolve_field,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFieldContext:
    """Tests for the FieldContext dataclass."""

    def test_field_context_fields(self, field_resolver, era_classifier):
        """All FieldContext fields are populated correctly."""
        ctx = FieldContext(
            field_code="001",
            field_name="BUCKSKIN",
            leases=("G12345", "G12346"),
            area_code="GC",
            geological_era="Miocene",
            well_count=5,
            query_type="field_code",
        )
        assert ctx.field_code == "001"
        assert ctx.field_name == "BUCKSKIN"
        assert ctx.leases == ("G12345", "G12346")
        assert ctx.area_code == "GC"
        assert ctx.geological_era == "Miocene"
        assert ctx.well_count == 5
        assert ctx.query_type == "field_code"

    def test_field_context_frozen(self):
        """FieldContext is immutable (frozen dataclass)."""
        ctx = FieldContext(
            field_code="001",
            field_name="BUCKSKIN",
            leases=("G12345",),
            area_code="GC",
            geological_era="Miocene",
            well_count=1,
            query_type="field_code",
        )
        with pytest.raises(FrozenInstanceError):
            ctx.field_code = "999"

    def test_field_context_repr(self):
        """FieldContext has a reasonable repr string."""
        ctx = FieldContext(
            field_code="001",
            field_name="BUCKSKIN",
            leases=("G12345",),
            area_code="GC",
            geological_era="Miocene",
            well_count=1,
            query_type="field_code",
        )
        r = repr(ctx)
        assert "FieldContext" in r
        assert "001" in r
        assert "BUCKSKIN" in r


class TestFieldQueryError:
    """Tests for FieldQueryError."""

    def test_field_query_error_is_value_error(self):
        """FieldQueryError inherits from ValueError."""
        assert issubclass(FieldQueryError, ValueError)
        err = FieldQueryError("bad query")
        assert isinstance(err, ValueError)
        assert str(err) == "bad query"


class TestResolveFieldByLeaseNumber:
    """Tests for resolving a field via lease number lookup."""

    def test_resolve_field_by_lease_number(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """A lease number present in the lease_field_map resolves to its field."""
        ctx = resolve_field(
            query="G12345",
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            lease_field_map=lease_field_map,
        )
        assert ctx.field_code == "001"
        assert ctx.field_name == "BUCKSKIN"
        assert ctx.query_type == "lease"
        assert "G12345" in ctx.leases

    def test_resolve_field_no_lease_map_falls_through(
        self, field_resolver, era_classifier
    ):
        """With lease_field_map=None, lease resolution is skipped entirely."""
        # "G12345" won't match a field code or name, so should raise
        with pytest.raises(FieldQueryError):
            resolve_field(
                query="G12345",
                field_resolver=field_resolver,
                era_classifier=era_classifier,
                lease_field_map=None,
            )

    def test_resolve_field_lease_not_in_map(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """A lease number absent from the map falls through to code/name search."""
        # "G00001" not in map, not a field code, not a name -> error
        with pytest.raises(FieldQueryError):
            resolve_field(
                query="G00001",
                field_resolver=field_resolver,
                era_classifier=era_classifier,
                lease_field_map=lease_field_map,
            )


class TestResolveFieldByFieldCode:
    """Tests for resolving by BSEE field code."""

    def test_resolve_field_by_field_code(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """A known field code resolves directly."""
        ctx = resolve_field(
            query="002",
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            lease_field_map=lease_field_map,
        )
        assert ctx.field_code == "002"
        assert ctx.field_name == "THUNDER HORSE"
        assert ctx.query_type == "field_code"


class TestResolveFieldByFieldName:
    """Tests for resolving by field display name."""

    def test_resolve_field_by_field_name(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """Exact field name match (upper case) resolves."""
        ctx = resolve_field(
            query="MARS",
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            lease_field_map=lease_field_map,
        )
        assert ctx.field_code == "003"
        assert ctx.field_name == "MARS"
        assert ctx.query_type == "field_name"

    def test_resolve_field_by_field_name_case_insensitive(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """Field name match is case-insensitive."""
        ctx = resolve_field(
            query="buckskin",
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            lease_field_map=lease_field_map,
        )
        assert ctx.field_code == "001"
        assert ctx.field_name == "BUCKSKIN"
        assert ctx.query_type == "field_name"


class TestResolveFieldByEra:
    """Tests for resolving by geological era."""

    def test_resolve_field_by_era(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """A geological era name returns an aggregate FieldContext."""
        ctx = resolve_field(
            query="Miocene",
            field_resolver=field_resolver,
            era_classifier=era_classifier,
            lease_field_map=lease_field_map,
        )
        assert ctx.field_code == "Miocene"
        assert ctx.field_name == "All Miocene fields"
        assert ctx.geological_era == "Miocene"
        assert ctx.query_type == "era"

    def test_resolve_field_by_era_empty_classifier(
        self, field_resolver, empty_era_classifier, lease_field_map
    ):
        """Era query with empty classifier returns FieldContext with empty leases."""
        ctx = resolve_field(
            query="Eocene",
            field_resolver=field_resolver,
            era_classifier=empty_era_classifier,
            lease_field_map=lease_field_map,
        )
        assert ctx.field_code == "Eocene"
        assert ctx.field_name == "All Eocene fields"
        assert ctx.geological_era == "Eocene"
        assert ctx.leases == ()
        assert ctx.well_count == 0
        assert ctx.query_type == "era"


class TestResolveFieldUnknown:
    """Tests for unresolvable queries."""

    def test_resolve_field_unknown_query_raises(
        self, field_resolver, era_classifier, lease_field_map
    ):
        """An unrecognisable query raises FieldQueryError."""
        with pytest.raises(FieldQueryError, match="Cannot resolve query"):
            resolve_field(
                query="NONEXISTENT_GIBBERISH",
                field_resolver=field_resolver,
                era_classifier=era_classifier,
                lease_field_map=lease_field_map,
            )


class TestBuildLeaseFieldMap:
    """Tests for the build_lease_field_map helper."""

    def test_build_lease_field_map_missing_file(self, tmp_path):
        """Missing data file returns an empty DataFrame."""
        df = build_lease_field_map(tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_build_lease_field_map_lfs_stub(self, tmp_path):
        """LFS stub file returns an empty DataFrame (with warning)."""
        deepqual = tmp_path / "deepqual"
        deepqual.mkdir()
        lfs_file = deepqual / "mv_deep_water_field_leases.bin"
        lfs_file.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:abc123\nsize 1234\n"
        )
        df = build_lease_field_map(tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert df.empty
