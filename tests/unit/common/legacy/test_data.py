"""Tests for common.legacy.data module: string parsing, regex, utilities."""

import datetime
from unittest.mock import MagicMock

import numpy as np
import pytest

from worldenergydata.common.legacy.data import (
    AttributeDict,
    DateTimeUtility,
    ReadDataFromString,
    ReadDataFromSystemFiles,
    RegEx,
    get_initials_from_name,
    getClosestIntegerInList,
)

# ---------------------------------------------------------------------------
# get_initials_from_name
# ---------------------------------------------------------------------------


class TestGetInitialsFromName:
    def test_two_names(self):
        assert get_initials_from_name("John Smith") == "JS"

    def test_three_names(self):
        assert get_initials_from_name("John Michael Smith") == "JMS"

    def test_single_name(self):
        assert get_initials_from_name("Alice") == "A"

    def test_lowercase(self):
        assert get_initials_from_name("john smith") == "JS"


# ---------------------------------------------------------------------------
# getClosestIntegerInList
# ---------------------------------------------------------------------------


class TestGetClosestIntegerInList:
    def test_exact_match(self):
        value, idx = getClosestIntegerInList([1, 2, 3, 4, 5], 3)
        assert value == 3
        assert idx == 2

    def test_between_values(self):
        value, idx = getClosestIntegerInList([10, 20, 30], 22)
        assert value == 20
        assert idx == 1

    def test_closest_to_end(self):
        value, idx = getClosestIntegerInList([10, 20, 30], 29)
        assert value == 30
        assert idx == 2

    def test_single_element(self):
        value, idx = getClosestIntegerInList([42], 100)
        assert value == 42
        assert idx == 0

    def test_float_values(self):
        value, idx = getClosestIntegerInList([1.5, 2.5, 3.5], 2.7)
        assert value == pytest.approx(2.5)
        assert idx == 1


# ---------------------------------------------------------------------------
# AttributeDict
# ---------------------------------------------------------------------------


class TestAttributeDict:
    def test_access_as_attribute(self):
        d = AttributeDict({"name": "test", "value": 42})
        assert d.name == "test"
        assert d.value == 42

    def test_access_as_dict(self):
        d = AttributeDict({"key": "val"})
        assert d["key"] == "val"

    def test_set_attribute(self):
        d = AttributeDict()
        d.foo = "bar"
        assert d["foo"] == "bar"

    def test_is_dict_subclass(self):
        d = AttributeDict({"a": 1})
        assert isinstance(d, dict)


# ---------------------------------------------------------------------------
# DateTimeUtility
# ---------------------------------------------------------------------------


class TestDateTimeUtility:
    def test_last_day_of_january(self):
        util = DateTimeUtility()
        result = util.last_day_of_month(datetime.date(2024, 1, 15))
        assert result == datetime.date(2024, 1, 31)

    def test_last_day_of_february_leap(self):
        util = DateTimeUtility()
        result = util.last_day_of_month(datetime.date(2024, 2, 1))
        assert result == datetime.date(2024, 2, 29)

    def test_last_day_of_february_non_leap(self):
        util = DateTimeUtility()
        result = util.last_day_of_month(datetime.date(2023, 2, 10))
        assert result == datetime.date(2023, 2, 28)

    def test_last_day_of_april(self):
        util = DateTimeUtility()
        result = util.last_day_of_month(datetime.date(2024, 4, 5))
        assert result == datetime.date(2024, 4, 30)

    def test_last_day_of_december(self):
        util = DateTimeUtility()
        result = util.last_day_of_month(datetime.date(2024, 12, 1))
        assert result == datetime.date(2024, 12, 31)


# ---------------------------------------------------------------------------
# ReadDataFromString
# ---------------------------------------------------------------------------


class TestReadDataFromString:
    def setup_method(self):
        self.reader = ReadDataFromString()

    def test_get_row_numbers_containing_keyword(self):
        array = ["abc", "def", "abc def", "ghi"]
        result = self.reader.get_row_numbers_containing_keyword(array, "abc")
        assert result == [1, 3]

    def test_get_row_numbers_no_match(self):
        array = ["abc", "def"]
        result = self.reader.get_row_numbers_containing_keyword(array, "xyz")
        assert result == []

    def test_get_array_row_containing_any_of_keywords_found(self):
        array = ["first line", "second line", "target here"]
        result = self.reader.get_array_row_containing_any_of_keywords(
            array, ["target", "missing"]
        )
        assert result == 3

    def test_get_array_row_containing_any_of_keywords_not_found(self):
        array = ["first", "second"]
        result = self.reader.get_array_row_containing_any_of_keywords(
            array, ["missing"]
        )
        assert result is None

    def test_get_sub_string_by_line_numbers(self):
        cfg = {
            "data_string": "line1\nline2\nline3\nline4\nline5",
            "start_line_number": 2,
            "end_line_number": 4,
        }
        result = self.reader.get_sub_string_by_line_numbers(cfg)
        assert result == "line2\nline3\nline4"

    def test_get_substrings_by_line_number_array(self):
        cfg = {
            "data_string": "line1\nline2\nline3\nline4\nline5",
            "start_line_number": [1, 4],
            "end_line_number": [2, 5],
        }
        result = self.reader.get_substrings_by_line_number_array(cfg)
        assert len(result) == 2
        assert result[0] == "line1\nline2"
        assert result[1] == "line4\nline5"

    def test_get_substrings_mismatched_arrays_raises(self):
        cfg = {
            "data_string": "line1\nline2",
            "start_line_number": [1, 2],
            "end_line_number": [2],
        }
        with pytest.raises(Exception, match="Missing count"):
            self.reader.get_substrings_by_line_number_array(cfg)

    def test_get_line_numbers_containing_keyword(self):
        cfg = {
            "data_string": "ABC\nhello\nABC again",
            "line": {"key_word": "ABC", "transform": {"scale": 1, "shift": 0}},
        }
        result = self.reader.get_line_numbers_containing_keyword(cfg)
        assert result == [1, 3]

    def test_get_line_numbers_with_transform(self):
        cfg = {
            "data_string": "ABC\nhello\nABC again",
            "line": {"key_word": "ABC", "transform": {"scale": 2, "shift": 1}},
        }
        result = self.reader.get_line_numbers_containing_keyword(cfg)
        assert result == [3, 7]  # 1*2+1=3, 3*2+1=7

    def test_get_all_array_rows_containing_any_keyword(self):
        array = ["cat dog", "fish", "cat bird", "mouse"]
        result = self.reader.get_all_array_rows_containing_any_keyword(
            array, ["cat", "mouse"]
        )
        assert result == [1, 3, 4]

    def test_get_first_array_row_containing_any_keyword(self):
        array = ["abc", "def", "ghi abc"]
        result = self.reader.get_first_array_row_containing_any_keyword(array, ["abc"])
        assert result == 1

    def test_get_first_array_row_containing_any_keyword_none(self):
        array = ["abc", "def"]
        result = self.reader.get_first_array_row_containing_any_keyword(array, ["xyz"])
        assert result is None

    def test_get_first_array_row_containing_all_keywords(self):
        array = ["abc", "abc def", "def"]
        result = self.reader.get_first_array_row_containing_all_keywords(
            array, ["abc", "def"]
        )
        assert result == 2

    def test_get_first_array_row_containing_all_keywords_none(self):
        array = ["abc", "def"]
        result = self.reader.get_first_array_row_containing_all_keywords(
            array, ["abc", "def"]
        )
        assert result is None

    def test_get_all_array_row_containing_all_keywords(self):
        array = ["abc def", "abc", "abc def ghi", "def"]
        result = self.reader.get_all_array_row_containing_all_keywords(
            array, ["abc", "def"]
        )
        assert result == [1, 3]

    def test_get_all_lines_containing_any_key_words_string(self):
        cfg = {
            "data_string": "cat dog\nfish\ncat bird",
            "line": {"key_words": ["cat"]},
        }
        result = self.reader.get_all_lines_containing_any_key_words(cfg)
        assert len(result) == 2
        assert "cat dog" in result

    def test_get_all_lines_containing_any_key_words_bytes(self):
        cfg = {
            "data_byte": b"cat dog\nfish\ncat bird",
            "line": {"key_words": ["cat"]},
        }
        result = self.reader.get_all_lines_containing_any_key_words(cfg)
        assert len(result) == 2

    def test_get_all_lines_containing_all_key_words(self):
        cfg = {
            "data_string": "cat dog\nfish\ncat bird",
            "line": {"key_words": ["cat", "dog"]},
        }
        result = self.reader.get_all_lines_containing_all_key_words(cfg)
        assert len(result) == 1
        assert result[0] == "cat dog"

    def test_get_all_lines_containing_all_key_words_bytes(self):
        cfg = {
            "data_byte": b"cat dog\nfish\ncat bird",
            "line": {"key_words": ["cat", "dog"]},
        }
        result = self.reader.get_all_lines_containing_all_key_words(cfg)
        assert len(result) == 1

    def test_get_intermediate_word_based_on_pattern(self):
        cfg = {
            "string": "Hello World 123 End",
            "pattern": r"World (\d+) End",
        }
        result = self.reader.get_intermediate_word_based_on_pattern(cfg)
        assert result == "123"

    def test_get_intermediate_word_no_match(self):
        cfg = {"string": "Hello World", "pattern": r"(\d+)"}
        result = self.reader.get_intermediate_word_based_on_pattern(cfg)
        assert result is None


# ---------------------------------------------------------------------------
# ReadDataFromSystemFiles
# ---------------------------------------------------------------------------


class TestReadDataFromSystemFiles:
    def test_get_file_list_from_folder_empty(self, tmp_path):
        reader = ReadDataFromSystemFiles()
        result = reader.get_file_list_from_folder(str(tmp_path / "*.nonexistent"))
        assert result == []

    def test_get_file_list_with_extension(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        reader = ReadDataFromSystemFiles()
        result = reader.get_file_list_from_folder(
            str(tmp_path / "*.txt"), with_path=True, with_extension=True
        )
        assert len(result) == 2
        assert result[0].endswith(".txt")

    def test_get_file_list_without_extension(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        reader = ReadDataFromSystemFiles()
        result = reader.get_file_list_from_folder(
            str(tmp_path / "*.txt"), with_path=True, with_extension=False
        )
        assert not result[0].endswith(".txt")

    def test_get_file_list_without_path_with_ext(self, tmp_path):
        (tmp_path / "test.txt").write_text("data")
        reader = ReadDataFromSystemFiles()
        result = reader.get_file_list_from_folder(
            str(tmp_path / "*.txt"), with_path=False, with_extension=True
        )
        assert result[0] == "test.txt"

    def test_get_file_list_without_path_without_ext(self, tmp_path):
        (tmp_path / "test.txt").write_text("data")
        reader = ReadDataFromSystemFiles()
        result = reader.get_file_list_from_folder(
            str(tmp_path / "*.txt"), with_path=False, with_extension=False
        )
        assert result[0] == "test"

    def test_get_data_from_json(self, tmp_path):
        import json

        f = tmp_path / "test.json"
        f.write_text(json.dumps({"key": "value"}))
        reader = ReadDataFromSystemFiles()
        result = reader.get_data_from_json(str(f))
        assert result["key"] == "value"

    def test_get_data_from_json_missing(self, tmp_path):
        reader = ReadDataFromSystemFiles()
        result = reader.get_data_from_json(str(tmp_path / "missing.json"))
        assert result is False

    def test_get_data_from_yaml(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("key: value\n")
        reader = ReadDataFromSystemFiles()
        result = reader.get_data_from_yaml(str(f))
        assert result["key"] == "value"

    def test_get_data_from_yaml_missing(self, tmp_path):
        reader = ReadDataFromSystemFiles()
        result = reader.get_data_from_yaml(str(tmp_path / "missing.yaml"))
        assert result is None


# ---------------------------------------------------------------------------
# RegEx
# ---------------------------------------------------------------------------


class TestRegEx:
    def test_replace_in_string_custom(self):
        regex = RegEx()
        cfg = {
            "data_string": "Hello World",
            "pattern": "World",
            "replace_with": "Python",
        }
        result = regex.replace_in_string(cfg)
        assert result == "Hello Python"

    def test_replace_in_string_bytes(self):
        regex = RegEx()
        cfg = {
            "data_byte": b"Hello World",
            "pattern": "World",
            "replace_with": "Python",
        }
        result = regex.replace_in_string(cfg)
        assert result == "Hello Python"

    def test_replace_in_string_multiple_patterns(self):
        regex = RegEx()
        cfg = {
            "data_string": "Hello World Foo",
            "pattern": ["World", "Foo"],
            "replace_with": ["Bar", "Baz"],
        }
        result = regex.replace_in_string(cfg)
        assert result == "Hello Bar Baz"

    def test_replace_in_string_single_pattern_list(self):
        regex = RegEx()
        cfg = {
            "data_string": "abc abc",
            "pattern": ["abc"],
            "replace_with": "xyz",
        }
        result = regex.replace_in_string(cfg)
        assert result == "xyz xyz"

    def test_get_without_html_tags_string(self):
        regex = RegEx()
        cfg = {"data_string": "<p>Hello <b>World</b></p>", "features": "html.parser"}
        result = regex.get_without_html_tags(cfg)
        assert "Hello" in result
        assert "World" in result
        assert "<p>" not in result

    def test_get_without_html_tags_bytes(self):
        regex = RegEx()
        cfg = {"data_byte": b"<p>Test</p>", "features": "html.parser"}
        result = regex.get_without_html_tags(cfg)
        assert "Test" in result
        assert "<p>" not in result
