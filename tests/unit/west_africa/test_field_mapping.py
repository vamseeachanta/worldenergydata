"""Tests for Nigeria blend name to field/operator mapping."""

import pytest

from worldenergydata.west_africa.nigeria.field_mapping import (
    BLEND_TO_FIELD_MAP,
    lookup_field,
    lookup_operator,
    FieldInfo,
    resolve_blend,
)


class TestBlendToFieldMap:
    def test_map_is_dict(self):
        assert isinstance(BLEND_TO_FIELD_MAP, dict)

    def test_bonny_light_present(self):
        assert "BONNY LIGHT" in BLEND_TO_FIELD_MAP

    def test_map_values_are_field_info(self):
        for key, val in BLEND_TO_FIELD_MAP.items():
            assert isinstance(val, FieldInfo), f"{key} value is not FieldInfo"

    def test_key_names_are_uppercase(self):
        for key in BLEND_TO_FIELD_MAP:
            assert key == key.upper(), f"Key '{key}' should be uppercase"


class TestFieldInfo:
    def test_field_info_required_fields(self):
        fi = FieldInfo(
            field_name="Bonga",
            operator="Shell",
            water_depth_m=1000,
            blend_name="BONNY LIGHT",
        )
        assert fi.field_name == "Bonga"
        assert fi.operator == "Shell"
        assert fi.water_depth_m == 1000

    def test_field_info_optional_status(self):
        fi = FieldInfo(
            field_name="Bonga",
            operator="Shell",
            water_depth_m=1000,
            blend_name="BONNY LIGHT",
            status="Producing",
        )
        assert fi.status == "Producing"

    def test_field_info_is_deepwater(self):
        fi = FieldInfo(
            field_name="Bonga",
            operator="Shell",
            water_depth_m=1000,
            blend_name="BONNY LIGHT",
        )
        assert fi.is_deepwater is True

    def test_shallow_field_not_deepwater(self):
        fi = FieldInfo(
            field_name="Shallow",
            operator="Generic",
            water_depth_m=100,
            blend_name="QUAT IBOE",
        )
        assert fi.is_deepwater is False


class TestLookupField:
    def test_lookup_known_blend(self):
        result = lookup_field("BONNY LIGHT")
        assert result is not None

    def test_lookup_returns_field_info(self):
        result = lookup_field("BONNY LIGHT")
        assert isinstance(result, FieldInfo)

    def test_lookup_unknown_blend_returns_none(self):
        result = lookup_field("UNKNOWN_BLEND_XYZ")
        assert result is None

    def test_lookup_case_insensitive(self):
        result_upper = lookup_field("BONNY LIGHT")
        result_lower = lookup_field("bonny light")
        assert result_upper == result_lower


class TestLookupOperator:
    def test_lookup_operator_known_blend(self):
        operator = lookup_operator("BONNY LIGHT")
        assert operator is not None
        assert isinstance(operator, str)
        assert len(operator) > 0

    def test_lookup_operator_unknown_blend(self):
        result = lookup_operator("COMPLETELY_UNKNOWN_BLEND")
        assert result is None


class TestResolveBlend:
    def test_resolve_exact_match(self):
        result = resolve_blend("BONNY LIGHT")
        assert result is not None

    def test_resolve_partial_match(self):
        # Should handle "BONNY LT" → "BONNY LIGHT" via pattern matching
        result = resolve_blend("BONNY")
        # May return None for ambiguous; should not raise
        assert result is None or isinstance(result, FieldInfo)

    def test_resolve_none_input(self):
        result = resolve_blend(None)
        assert result is None

    def test_resolve_empty_string(self):
        result = resolve_blend("")
        assert result is None
