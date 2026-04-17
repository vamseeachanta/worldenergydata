"""Tests for canada.common.uwi utility functions."""

from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.canada.common.uwi import (
    get_province_from_uwi,
    normalize_uwi,
    parse_uwi,
    validate_uwi,
)


class TestParseUwi:
    def test_empty_string(self):
        assert parse_uwi("") is None

    def test_none_input(self):
        assert parse_uwi(None) is None

    def test_valid_uwi_returns_dict(self):
        mock_components = MagicMock()
        mock_components.is_valid = True
        mock_components.to_dict.return_value = {
            "province": "AB",
            "raw": "100/06-01-001-01W4/0",
        }
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_components

        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            return_value=mock_parser,
        ):
            result = parse_uwi("100/06-01-001-01W4/0")
            assert result is not None
            assert result["province"] == "AB"

    def test_invalid_uwi_still_returns_dict(self):
        mock_components = MagicMock()
        mock_components.is_valid = False
        mock_components.validation_errors = ["bad range"]
        mock_components.to_dict.return_value = {"province": None}
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_components

        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            return_value=mock_parser,
        ):
            result = parse_uwi("bad-uwi")
            assert result is not None

    def test_exception_returns_none(self):
        """When UWIParser raises, parse_uwi returns None."""
        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            side_effect=Exception("import fail"),
        ):
            result = parse_uwi("some-uwi")
            assert result is None


class TestNormalizeUwi:
    def test_empty_string(self):
        assert normalize_uwi("") == ""

    def test_none_input(self):
        assert normalize_uwi(None) is None

    def test_normalizes_uwi(self):
        mock_parser = MagicMock()
        mock_parser.normalize.return_value = "100/06-01-001-01W4/0"

        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            return_value=mock_parser,
        ):
            result = normalize_uwi("10006010010104")
            assert result == "100/06-01-001-01W4/0"

    def test_exception_returns_original(self):
        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            side_effect=Exception("fail"),
        ):
            result = normalize_uwi("bad-uwi")
            assert result == "bad-uwi"


class TestValidateUwi:
    def test_empty_string(self):
        is_valid, error = validate_uwi("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_none_input(self):
        is_valid, error = validate_uwi(None)
        assert is_valid is False

    def test_valid_uwi(self):
        mock_parser = MagicMock()
        mock_parser.validate.return_value = (True, None)

        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            return_value=mock_parser,
        ):
            is_valid, error = validate_uwi("100/06-01-001-01W4/0")
            assert is_valid is True
            assert error is None

    def test_exception_returns_invalid(self):
        with patch(
            "worldenergydata.canada.common.uwi_parser.UWIParser",
            side_effect=Exception("oops"),
        ):
            is_valid, error = validate_uwi("bad")
            assert is_valid is False
            assert "oops" in error


class TestGetProvinceFromUwi:
    @patch("worldenergydata.canada.common.uwi.parse_uwi")
    def test_returns_province(self, mock_parse):
        mock_parse.return_value = {"province": "AB"}
        assert get_province_from_uwi("some-uwi") == "AB"

    @patch("worldenergydata.canada.common.uwi.parse_uwi")
    def test_returns_none_on_parse_fail(self, mock_parse):
        mock_parse.return_value = None
        assert get_province_from_uwi("bad-uwi") is None

    @patch("worldenergydata.canada.common.uwi.parse_uwi")
    def test_returns_none_when_no_province_key(self, mock_parse):
        mock_parse.return_value = {"other": "data"}
        assert get_province_from_uwi("some-uwi") is None
