"""Tests for Canadian UWI (Unique Well Identifier) parser."""

import pytest

from worldenergydata.canada.common.uwi_parser import (
    UWIComponents,
    UWIParseError,
    UWIParser,
    UWISurveySystem,
)


class TestUWISurveySystem:
    """Tests for UWISurveySystem enum."""

    def test_dls_value(self):
        assert UWISurveySystem.DLS.value == "DLS"

    def test_nts_value(self):
        assert UWISurveySystem.NTS.value == "NTS"

    def test_unknown_value(self):
        assert UWISurveySystem.UNKNOWN.value == "UNKNOWN"


class TestUWIParseError:
    """Tests for UWIParseError exception."""

    def test_basic_error(self):
        err = UWIParseError("Invalid format", "BAD-UWI")
        assert err.message == "Invalid format"
        assert err.uwi == "BAD-UWI"
        assert "BAD-UWI" in str(err)

    def test_error_with_detail(self):
        err = UWIParseError("Invalid", "BAD", detail="section out of range")
        assert err.detail == "section out of range"
        assert "section out of range" in str(err)


class TestUWIComponents:
    """Tests for UWIComponents dataclass."""

    def test_to_dict(self):
        comp = UWIComponents(
            survey_system=UWISurveySystem.DLS,
            location_exception="100",
            legal_subdivision="16",
            section="09",
            township="010",
            range="09",
            meridian="W4",
            event_sequence="00",
            raw_uwi="100.16-09-010-09W4.00",
            province="AB",
        )
        d = comp.to_dict()
        assert d["survey_system"] == "DLS"
        assert d["location_exception"] == "100"
        assert d["legal_subdivision"] == "16"
        assert d["section"] == "09"
        assert d["township"] == "010"
        assert d["range"] == "09"
        assert d["meridian"] == "W4"
        assert d["event_sequence"] == "00"
        assert d["province"] == "AB"
        assert d["is_valid"] is True
        assert d["validation_errors"] == []

    def test_default_fields(self):
        comp = UWIComponents(
            survey_system=UWISurveySystem.DLS,
            location_exception="100",
            legal_subdivision="16",
            section="09",
            township="010",
            range="09",
            meridian="W4",
            event_sequence="00",
            raw_uwi="test",
        )
        assert comp.quarter_unit is None
        assert comp.unit is None
        assert comp.block is None
        assert comp.map_area is None
        assert comp.map_sheet is None
        assert comp.is_valid is True
        assert comp.normalized_uwi == ""


class TestUWIParserGetSurveySystem:
    """Tests for UWIParser.get_survey_system."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_empty_string(self):
        assert self.parser.get_survey_system("") == UWISurveySystem.UNKNOWN

    def test_dls_standard(self):
        result = self.parser.get_survey_system("100.16-09-010-09W4.00")
        assert result == UWISurveySystem.DLS

    def test_dls_compact(self):
        result = self.parser.get_survey_system("1001609010009W400")
        assert result == UWISurveySystem.DLS

    def test_nts_format(self):
        result = self.parser.get_survey_system("200.A-001-B-094-A-01.00")
        assert result == UWISurveySystem.NTS

    def test_unknown_format(self):
        result = self.parser.get_survey_system("INVALID")
        assert result == UWISurveySystem.UNKNOWN

    def test_heuristic_dls_w_digit(self):
        # W followed by digit triggers DLS heuristic
        result = self.parser.get_survey_system("some-format-W4-extra")
        assert result == UWISurveySystem.DLS


class TestUWIParserParseDLS:
    """Tests for parsing DLS format UWIs."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_standard_dls(self):
        comp = self.parser.parse("100.16-09-010-09W4.00")
        assert comp.survey_system == UWISurveySystem.DLS
        assert comp.location_exception == "100"
        assert comp.legal_subdivision == "16"
        assert comp.section == "09"
        assert comp.township == "010"
        assert comp.range == "09"
        assert comp.meridian == "W4"
        assert comp.event_sequence == "00"
        assert comp.is_valid is True

    def test_dls_province_inferred(self):
        comp = self.parser.parse("100.16-09-010-09W4.00")
        assert comp.province == "AB"  # W4 = Alberta

    def test_dls_w1_manitoba(self):
        comp = self.parser.parse("100.16-09-010-09W1.00")
        assert comp.province == "MB"

    def test_dls_w2_saskatchewan(self):
        comp = self.parser.parse("100.16-09-010-09W2.00")
        assert comp.province == "SK"

    def test_dls_w5_alberta(self):
        comp = self.parser.parse("100.16-09-010-09W5.00")
        assert comp.province == "AB"

    def test_dls_slash_format(self):
        comp = self.parser.parse("100/16-09-010-09W4/00")
        assert comp.is_valid is True
        assert comp.survey_system == UWISurveySystem.DLS

    def test_dls_normalized_uwi(self):
        comp = self.parser.parse("100.16-09-010-09W4.00")
        assert comp.normalized_uwi == "100.16-09-010-09W4.00"

    def test_dls_invalid_lsd_too_high(self):
        comp = self.parser.parse("100.99-09-010-09W4.00")
        assert comp.is_valid is False
        assert any("Legal subdivision" in e for e in comp.validation_errors)

    def test_dls_invalid_section_too_high(self):
        comp = self.parser.parse("100.16-99-010-09W4.00")
        assert comp.is_valid is False
        assert any("Section" in e for e in comp.validation_errors)


class TestUWIParserParseNTS:
    """Tests for parsing NTS format UWIs."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_standard_nts(self):
        comp = self.parser.parse("200.A-001-B-094-A-01.00")
        assert comp.survey_system == UWISurveySystem.NTS
        assert comp.location_exception == "200"
        assert comp.quarter_unit == "A"
        assert comp.block == "B"
        assert comp.event_sequence == "00"
        assert comp.is_valid is True

    def test_nts_default_province_bc(self):
        comp = self.parser.parse("200.A-001-B-094-A-01.00")
        assert comp.province == "BC"


class TestUWIParserValidate:
    """Tests for UWIParser.validate."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_valid_dls(self):
        is_valid, err = self.parser.validate("100.16-09-010-09W4.00")
        assert is_valid is True
        assert err is None

    def test_empty(self):
        is_valid, err = self.parser.validate("")
        assert is_valid is False
        assert "empty" in err.lower()

    def test_none(self):
        is_valid, err = self.parser.validate(None)
        assert is_valid is False

    def test_unknown_format(self):
        is_valid, err = self.parser.validate("INVALID")
        assert is_valid is False
        assert "survey system" in err.lower()


class TestUWIParserFormat:
    """Tests for UWIParser.format."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_format_dls(self):
        comp = UWIComponents(
            survey_system=UWISurveySystem.DLS,
            location_exception="100",
            legal_subdivision="16",
            section="09",
            township="010",
            range="09",
            meridian="W4",
            event_sequence="00",
            raw_uwi="test",
        )
        result = self.parser.format(comp)
        assert result == "100.16-09-010-09W4.00"

    def test_format_unknown_returns_raw(self):
        comp = UWIComponents(
            survey_system=UWISurveySystem.UNKNOWN,
            location_exception="",
            legal_subdivision="",
            section="",
            township="",
            range="",
            meridian="",
            event_sequence="",
            raw_uwi="ORIGINAL",
        )
        result = self.parser.format(comp)
        assert result == "ORIGINAL"


class TestUWIParserNormalize:
    """Tests for UWIParser.normalize."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_normalize_slash_to_standard(self):
        result = self.parser.normalize("100/16-09-010-09W4/00")
        assert result == "100.16-09-010-09W4.00"

    def test_normalize_invalid_returns_original(self):
        result = self.parser.normalize("INVALID")
        assert result == "INVALID"


class TestUWIParserStrictMode:
    """Tests for UWIParser strict mode."""

    def setup_method(self):
        self.parser = UWIParser(strict=True)

    def test_strict_empty_raises(self):
        with pytest.raises(UWIParseError):
            self.parser.parse("")

    def test_strict_invalid_format_raises(self):
        with pytest.raises(UWIParseError):
            self.parser.parse("INVALID")

    def test_strict_valid_no_exception(self):
        comp = self.parser.parse("100.16-09-010-09W4.00")
        assert comp.is_valid is True

    def test_strict_invalid_lsd_raises(self):
        with pytest.raises(UWIParseError):
            self.parser.parse("100.99-09-010-09W4.00")


class TestUWIParserBatch:
    """Tests for UWIParser batch operations."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_batch_parse(self):
        uwis = ["100.16-09-010-09W4.00", "100.01-01-001-01W1.00"]
        results = self.parser.batch_parse(uwis)
        assert len(results) == 2
        assert all(r.is_valid for r in results)

    def test_batch_parse_with_invalid(self):
        uwis = ["100.16-09-010-09W4.00", "INVALID"]
        results = self.parser.batch_parse(uwis)
        assert len(results) == 2
        assert results[0].is_valid is True
        assert results[1].is_valid is False

    def test_batch_validate(self):
        uwis = ["100.16-09-010-09W4.00", "INVALID"]
        results = self.parser.batch_validate(uwis)
        assert len(results) == 2
        assert results[0][1] is True  # (uwi, is_valid, error)
        assert results[1][1] is False

    def test_batch_validate_empty(self):
        results = self.parser.batch_validate([])
        assert results == []


class TestUWIParserCleanUWI:
    """Tests for UWIParser._clean_uwi."""

    def setup_method(self):
        self.parser = UWIParser()

    def test_strip_whitespace(self):
        result = self.parser._clean_uwi("  100.16-09-010-09W4.00  ")
        assert result == "100.16-09-010-09W4.00"

    def test_remove_spaces(self):
        result = self.parser._clean_uwi("100.16 - 09 - 010 - 09W4.00")
        assert " " not in result

    def test_backslash_to_forward(self):
        result = self.parser._clean_uwi("100\\16-09-010-09W4\\00")
        assert "\\" not in result
