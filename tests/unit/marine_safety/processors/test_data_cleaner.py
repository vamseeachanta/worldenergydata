"""Tests for data cleaner."""

from datetime import date, datetime
from decimal import Decimal

from worldenergydata.marine_safety.processors.data_cleaner import DataCleaner


class TestCleanText:
    def test_normal_text(self):
        dc = DataCleaner()
        assert dc.clean_text("Hello World") == "Hello World"

    def test_strips_whitespace(self):
        dc = DataCleaner()
        assert dc.clean_text("  hello  ") == "hello"

    def test_collapses_spaces(self):
        dc = DataCleaner()
        assert dc.clean_text("hello   world") == "hello world"

    def test_none_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_text(None) is None

    def test_empty_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_text("") is None

    def test_whitespace_only_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_text("   ") is None

    def test_non_string_converted(self):
        dc = DataCleaner()
        assert dc.clean_text(123) == "123"


class TestCleanDate:
    def test_iso_format(self):
        dc = DataCleaner()
        result = dc.clean_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_us_format(self):
        dc = DataCleaner()
        result = dc.clean_date("01/15/2024")
        assert result == date(2024, 1, 15)

    def test_date_object(self):
        dc = DataCleaner()
        d = date(2024, 1, 15)
        assert dc.clean_date(d) == d

    def test_datetime_object(self):
        dc = DataCleaner()
        dt = datetime(2024, 1, 15, 10, 30)
        assert dc.clean_date(dt) == date(2024, 1, 15)

    def test_none_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_date(None) is None

    def test_empty_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_date("") is None

    def test_invalid_format_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_date("not a date") is None

    def test_month_name_format(self):
        dc = DataCleaner()
        result = dc.clean_date("January 15, 2024")
        assert result == date(2024, 1, 15)


class TestCleanDatetime:
    def test_standard_format(self):
        dc = DataCleaner()
        result = dc.clean_datetime("2024-01-15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_short_format(self):
        dc = DataCleaner()
        result = dc.clean_datetime("2024-01-15 10:30")
        assert result == datetime(2024, 1, 15, 10, 30)

    def test_datetime_object(self):
        dc = DataCleaner()
        dt = datetime(2024, 1, 15, 10, 30)
        assert dc.clean_datetime(dt) == dt

    def test_none_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_datetime(None) is None

    def test_invalid_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_datetime("not a time") is None


class TestCleanInteger:
    def test_valid_int(self):
        dc = DataCleaner()
        assert dc.clean_integer(42) == 42

    def test_string_int(self):
        dc = DataCleaner()
        assert dc.clean_integer("42") == 42

    def test_float_string(self):
        dc = DataCleaner()
        assert dc.clean_integer("10.0") == 10

    def test_with_commas(self):
        dc = DataCleaner()
        assert dc.clean_integer("1,000") == 1000

    def test_none_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_integer(None) is None

    def test_empty_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_integer("") is None

    def test_min_value_clamp(self):
        dc = DataCleaner()
        assert dc.clean_integer(-5, min_value=0) == 0

    def test_max_value_clamp(self):
        dc = DataCleaner()
        assert dc.clean_integer(200, max_value=100) == 100

    def test_invalid_string(self):
        dc = DataCleaner()
        assert dc.clean_integer("abc") is None


class TestCleanDecimal:
    def test_valid_decimal(self):
        dc = DataCleaner()
        result = dc.clean_decimal("123.456")
        assert result == Decimal("123.46")  # 2 decimal places

    def test_with_currency_symbol(self):
        dc = DataCleaner()
        result = dc.clean_decimal("$1,000.50")
        assert result == Decimal("1000.50")

    def test_none_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_decimal(None) is None

    def test_empty_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_decimal("") is None

    def test_min_value(self):
        dc = DataCleaner()
        result = dc.clean_decimal("-5", min_value=0)
        assert result == 0

    def test_integer_value(self):
        dc = DataCleaner()
        result = dc.clean_decimal(100)
        assert result == Decimal("100.00")

    def test_invalid_returns_none(self):
        dc = DataCleaner()
        assert dc.clean_decimal("abc") is None


class TestCleanLatitude:
    def test_valid(self):
        dc = DataCleaner()
        result = dc.clean_latitude("45.5")
        assert result is not None
        assert float(result) == 45.5

    def test_too_high_clamped(self):
        dc = DataCleaner()
        result = dc.clean_latitude("95")
        assert result == Decimal("90")

    def test_too_low_clamped(self):
        dc = DataCleaner()
        result = dc.clean_latitude("-95")
        assert result == Decimal("-90")

    def test_none(self):
        dc = DataCleaner()
        assert dc.clean_latitude(None) is None


class TestCleanLongitude:
    def test_valid(self):
        dc = DataCleaner()
        result = dc.clean_longitude("-73.5")
        assert result is not None
        assert float(result) == -73.5

    def test_too_high_clamped(self):
        dc = DataCleaner()
        result = dc.clean_longitude("200")
        assert result == Decimal("180")

    def test_none(self):
        dc = DataCleaner()
        assert dc.clean_longitude(None) is None


class TestProcess:
    def test_full_record(self):
        dc = DataCleaner()
        data = {
            "title": "  Test Incident  ",
            "incident_date": "2024-01-15",
            "fatalities": "2",
            "latitude": "45.5",
            "longitude": "-73.5",
            "other_field": "preserved",
        }
        result = dc.process(data)
        assert result["title"] == "Test Incident"
        assert result["incident_date"] == date(2024, 1, 15)
        assert result["fatalities"] == 2
        assert result["other_field"] == "preserved"

    def test_none_data(self):
        dc = DataCleaner()
        result = dc.process(None)
        assert result is None
        assert dc.stats["errors"] == 1

    def test_empty_record(self):
        dc = DataCleaner()
        result = dc.process({})
        assert result == {}

    def test_stats_updated(self):
        dc = DataCleaner()
        dc.process({"title": "test"})
        assert dc.stats["processed"] == 1


class TestBatchProcess:
    def test_batch(self):
        dc = DataCleaner()
        results = dc.batch_process(
            [
                {"title": "First"},
                {"title": "Second"},
            ]
        )
        assert len(results) == 2
        assert results[0]["title"] == "First"

    def test_batch_empty(self):
        dc = DataCleaner()
        assert dc.batch_process([]) == []

    def test_batch_resets_stats(self):
        dc = DataCleaner()
        dc.stats["processed"] = 99
        dc.batch_process([{"title": "x"}])
        assert dc.stats["processed"] == 1


class TestInit:
    def test_defaults(self):
        dc = DataCleaner()
        assert dc.trim_strings is True
        assert dc.normalize_case is True
        assert dc.remove_duplicates is True

    def test_custom_config(self):
        dc = DataCleaner(config={"trim_strings": False})
        assert dc.trim_strings is False
