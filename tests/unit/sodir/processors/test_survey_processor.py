"""Tests for SODIR SurveyProcessor module."""

from worldenergydata.sodir.processors.survey_processor import SurveyProcessor


class TestSurveyProcessorInit:
    def test_defaults(self):
        sp = SurveyProcessor()
        assert sp.processed_count == 0
        assert sp.error_count == 0

    def test_survey_type_mapping(self):
        assert SurveyProcessor.SURVEY_TYPE_MAPPING["2D"] == "2D"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING["3D"] == "3D"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING["4D"] == "4D"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING["2D/3D"] == "2D_3D"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING["SITE SURVEY"] == "SITE_SURVEY"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING["HR"] == "HIGH_RESOLUTION"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING[""] == "UNKNOWN"
        assert SurveyProcessor.SURVEY_TYPE_MAPPING[None] == "UNKNOWN"

    def test_processing_status_mapping(self):
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING["COMPLETED"] == "COMPLETED"
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING["COMPLETE"] == "COMPLETED"
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING["IN PROGRESS"] == "IN_PROGRESS"
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING["PROCESSING"] == "IN_PROGRESS"
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING["PLANNED"] == "PLANNED"
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING["CANCELLED"] == "CANCELLED"
        assert SurveyProcessor.PROCESSING_STATUS_MAPPING[""] == "UNKNOWN"


class TestNormalizeSurveyType:
    def test_exact_match(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("3D") == "3D"
        assert sp.normalize_survey_type("2D") == "2D"
        assert sp.normalize_survey_type("4D") == "4D"

    def test_case_insensitive(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("3d") == "3D"
        assert sp.normalize_survey_type("2d") == "2D"

    def test_none(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type(None) == "UNKNOWN"

    def test_empty(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("") == "UNKNOWN"

    def test_time_lapse_variation(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("Time Lapse 4D") == "4D"

    def test_3d_variation(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("3D Wide Azimuth") == "3D"

    def test_2d_variation(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("Regional 2D Line") == "2D"

    def test_site_survey_variation(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("Site survey") == "SITE_SURVEY"

    def test_high_resolution_variation(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("High Resolution survey") == "HIGH_RESOLUTION"

    def test_unknown_type(self):
        sp = SurveyProcessor()
        assert sp.normalize_survey_type("magnetic") == "UNKNOWN"


class TestNormalizeProcessingStatus:
    def test_exact_match(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("COMPLETED") == "COMPLETED"
        assert sp.normalize_processing_status("PLANNED") == "PLANNED"

    def test_case_insensitive(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("completed") == "COMPLETED"
        assert sp.normalize_processing_status("Planned") == "PLANNED"

    def test_none(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status(None) == "UNKNOWN"

    def test_empty(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("") == "UNKNOWN"

    def test_variation_completing(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("Completing phase 2") == "COMPLETED"

    def test_variation_in_progress(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("In Progress") == "IN_PROGRESS"

    def test_variation_processing(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("Processing data") == "IN_PROGRESS"

    def test_variation_cancelled(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("Cancelled by operator") == "CANCELLED"

    def test_unknown_status(self):
        sp = SurveyProcessor()
        assert sp.normalize_processing_status("deferred") == "UNKNOWN"


class TestParseDate:
    def test_iso_format(self):
        sp = SurveyProcessor()
        assert sp._parse_date("2024-06-15") == "2024-06-15"

    def test_dmy_slash(self):
        sp = SurveyProcessor()
        assert sp._parse_date("15/06/2024") == "2024-06-15"

    def test_dmy_dot(self):
        sp = SurveyProcessor()
        assert sp._parse_date("15.06.2024") == "2024-06-15"

    def test_compact(self):
        sp = SurveyProcessor()
        assert sp._parse_date("20240615") == "2024-06-15"

    def test_none(self):
        sp = SurveyProcessor()
        assert sp._parse_date(None) is None

    def test_empty(self):
        sp = SurveyProcessor()
        assert sp._parse_date("") is None

    def test_unparseable_returns_string(self):
        sp = SurveyProcessor()
        assert sp._parse_date("June 2024") == "June 2024"


class TestSafeFloat:
    def test_valid(self):
        sp = SurveyProcessor()
        assert sp._safe_float("123.45") == 123.45

    def test_int(self):
        sp = SurveyProcessor()
        assert sp._safe_float(42) == 42.0

    def test_none(self):
        sp = SurveyProcessor()
        assert sp._safe_float(None) is None

    def test_invalid_string(self):
        sp = SurveyProcessor()
        assert sp._safe_float("abc") is None


class TestSafeInt:
    def test_valid(self):
        sp = SurveyProcessor()
        assert sp._safe_int("42") == 42

    def test_float_input(self):
        sp = SurveyProcessor()
        assert sp._safe_int(3.7) == 3

    def test_none(self):
        sp = SurveyProcessor()
        assert sp._safe_int(None) is None

    def test_invalid_string(self):
        sp = SurveyProcessor()
        assert sp._safe_int("abc") is None


class TestParseBoolean:
    def test_true_values(self):
        sp = SurveyProcessor()
        assert sp._parse_boolean(True) is True
        assert sp._parse_boolean("TRUE") is True
        assert sp._parse_boolean("Yes") is True
        assert sp._parse_boolean("Y") is True
        assert sp._parse_boolean("1") is True

    def test_false_values(self):
        sp = SurveyProcessor()
        assert sp._parse_boolean(False) is False
        assert sp._parse_boolean("FALSE") is False
        assert sp._parse_boolean("No") is False
        assert sp._parse_boolean("N") is False
        assert sp._parse_boolean("0") is False

    def test_none(self):
        sp = SurveyProcessor()
        assert sp._parse_boolean(None) is None

    def test_ambiguous(self):
        sp = SurveyProcessor()
        assert sp._parse_boolean("maybe") is None


class TestParseBlocks:
    def test_comma_separated(self):
        sp = SurveyProcessor()
        result = sp._parse_blocks("35/11, 35/12, 35/13")
        assert result == ["35/11", "35/12", "35/13"]

    def test_semicolon_separated(self):
        sp = SurveyProcessor()
        result = sp._parse_blocks("35/11; 35/12")
        assert result == ["35/11", "35/12"]

    def test_space_separated_with_slash(self):
        sp = SurveyProcessor()
        result = sp._parse_blocks("35/11 35/12")
        assert result == ["35/11", "35/12"]

    def test_single_block(self):
        sp = SurveyProcessor()
        result = sp._parse_blocks("35/11")
        assert result == ["35/11"]

    def test_none(self):
        sp = SurveyProcessor()
        assert sp._parse_blocks(None) == []

    def test_empty(self):
        sp = SurveyProcessor()
        assert sp._parse_blocks("") == []


class TestCalculateDuration:
    def test_basic(self):
        sp = SurveyProcessor()
        assert sp._calculate_duration("2024-01-01", "2024-01-31") == 30

    def test_same_day(self):
        sp = SurveyProcessor()
        assert sp._calculate_duration("2024-06-15", "2024-06-15") == 0

    def test_invalid_dates(self):
        sp = SurveyProcessor()
        assert sp._calculate_duration("invalid", "invalid") == 0


class TestAssessSurveyQuality:
    def test_4d(self):
        sp = SurveyProcessor()
        assert sp._assess_survey_quality({"survey_type": "4D"}) == "VERY_HIGH"

    def test_3d_high_streamer(self):
        sp = SurveyProcessor()
        result = sp._assess_survey_quality({"survey_type": "3D", "streamer_count": 12})
        assert result == "VERY_HIGH"

    def test_3d_medium_streamer(self):
        sp = SurveyProcessor()
        result = sp._assess_survey_quality({"survey_type": "3D", "streamer_count": 8})
        assert result == "HIGH"

    def test_3d_no_streamer(self):
        sp = SurveyProcessor()
        result = sp._assess_survey_quality({"survey_type": "3D"})
        assert result == "HIGH"

    def test_high_resolution(self):
        sp = SurveyProcessor()
        result = sp._assess_survey_quality({"survey_type": "HIGH_RESOLUTION"})
        assert result == "HIGH"

    def test_2d(self):
        sp = SurveyProcessor()
        assert sp._assess_survey_quality({"survey_type": "2D"}) == "STANDARD"

    def test_site_survey(self):
        sp = SurveyProcessor()
        result = sp._assess_survey_quality({"survey_type": "SITE_SURVEY"})
        assert result == "SPECIALIZED"

    def test_unknown(self):
        sp = SurveyProcessor()
        assert sp._assess_survey_quality({"survey_type": "OTHER"}) == "UNKNOWN"


class TestProcess:
    def test_minimal_record(self):
        sp = SurveyProcessor()
        result = sp.process({"srvName": "Test Survey"})
        assert result is not None
        assert result["survey_name"] == "Test Survey"
        assert result["source"] == "SODIR"
        assert sp.processed_count == 1

    def test_full_record(self):
        sp = SurveyProcessor()
        data = {
            "srvName": "North Sea 3D",
            "srvNpdidSurvey": 12345,
            "srvType": "3D",
            "srvSubType": "Wide Azimuth",
            "srvAcquisitionStartDate": "2024-01-15",
            "srvAcquisitionEndDate": "2024-06-30",
            "srvAcquisitionYear": 2024,
            "srvCompanyName": "Equinor",
            "srvContractorName": "PGS",
            "srvVesselName": "Ramform Titan",
            "srvAreaKm2": "2500.0",
            "srvLineKm": "15000.0",
            "srvStreamerCount": "10",
            "srvRecordLength": "8000",
            "srvSampleRate": "2.0",
            "srvProcessingStatus": "COMPLETED",
            "srvMainArea": "North Sea",
            "srvBlockCoverage": "35/11, 35/12",
            "srvDataAvailable": "Yes",
        }
        result = sp.process(data)
        assert result is not None
        assert result["survey_name"] == "North Sea 3D"
        assert result["survey_type"] == "3D"
        assert result["area_km2"] == 2500.0
        assert result["line_km"] == 15000.0
        assert result["streamer_count"] == 10
        assert result["processing_status"] == "COMPLETED"
        assert result["block_coverage"] == ["35/11", "35/12"]
        assert result["data_available"] is True
        assert result["acquisition_duration_days"] is not None
        assert result["line_density_km_per_km2"] == 6.0

    def test_processed_count_increments(self):
        sp = SurveyProcessor()
        sp.process({"srvName": "Survey1"})
        sp.process({"srvName": "Survey2"})
        assert sp.processed_count == 2

    def test_no_duration_when_missing_dates(self):
        sp = SurveyProcessor()
        result = sp.process({"srvName": "Test"})
        assert result["acquisition_duration_days"] is None

    def test_no_line_density_when_area_zero(self):
        sp = SurveyProcessor()
        result = sp.process(
            {
                "srvName": "Test",
                "srvLineKm": "100",
                "srvAreaKm2": "0",
            }
        )
        assert result["line_density_km_per_km2"] is None


class TestProcessBatch:
    def test_empty(self):
        sp = SurveyProcessor()
        result = sp.process_batch([])
        assert result == []

    def test_multiple(self):
        sp = SurveyProcessor()
        surveys = [
            {"srvName": "Survey1", "srvType": "3D"},
            {"srvName": "Survey2", "srvType": "2D"},
        ]
        result = sp.process_batch(surveys)
        assert len(result) == 2
        assert result[0]["survey_name"] == "Survey1"
        assert result[1]["survey_name"] == "Survey2"


class TestValidate:
    def test_valid(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test"})
        assert is_valid is True
        assert errors == []

    def test_missing_name(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({})
        assert is_valid is False
        assert any("srvName" in e for e in errors)

    def test_negative_area(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvAreaKm2": -100})
        assert is_valid is False
        assert any("Negative" in e for e in errors)

    def test_huge_area(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvAreaKm2": 200000})
        assert is_valid is False
        assert any("large" in e.lower() for e in errors)

    def test_invalid_area_string(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvAreaKm2": "abc"})
        assert is_valid is False
        assert any("Invalid area" in e for e in errors)

    def test_end_before_start(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate(
            {
                "srvName": "Test",
                "srvAcquisitionStartDate": "2024-06-01",
                "srvAcquisitionEndDate": "2024-01-01",
            }
        )
        assert is_valid is False
        assert any("before start" in e for e in errors)

    def test_invalid_year_too_old(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvAcquisitionYear": 1900})
        assert is_valid is False
        assert any("year" in e.lower() for e in errors)

    def test_invalid_streamer_count(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvStreamerCount": 100})
        assert is_valid is False
        assert any("streamer" in e.lower() for e in errors)

    def test_invalid_streamer_count_string(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvStreamerCount": "many"})
        assert is_valid is False

    def test_valid_area(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvAreaKm2": 5000})
        assert is_valid is True

    def test_null_area_ok(self):
        sp = SurveyProcessor()
        is_valid, errors = sp.validate({"srvName": "Test", "srvAreaKm2": None})
        assert is_valid is True


class TestGetStatistics:
    def test_initial(self):
        sp = SurveyProcessor()
        stats = sp.get_statistics()
        assert stats["processed"] == 0
        assert stats["errors"] == 0
        assert stats["success_rate"] == 0.0

    def test_after_processing(self):
        sp = SurveyProcessor()
        sp.process({"srvName": "Test1"})
        sp.process({"srvName": "Test2"})
        stats = sp.get_statistics()
        assert stats["processed"] == 2
        assert stats["errors"] == 0
        assert stats["success_rate"] == 1.0
