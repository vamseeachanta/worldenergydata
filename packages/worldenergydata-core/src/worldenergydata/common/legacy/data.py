from __future__ import annotations

import datetime
import logging
import re
import traceback
from typing import Any

import numpy as np
import urllib3
import xmltodict
from bs4 import BeautifulSoup

headers_default: dict[str, str] = {
    "User-Agent": "Vamsee Achanta support@aceengineer.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}


class ReadDataFromSystemFiles:

    def get_file_list_from_folder(
        self,
        folder_with_file_type: str,
        with_path: bool = True,
        with_extension: bool = True,
    ) -> list[str]:

        import glob
        import os

        file_list: list[str] = []
        for file in glob.glob(folder_with_file_type):
            file_list.append(file)
        if with_path:
            if not with_extension:
                file_list = [os.path.splitext(file)[0] for file in file_list]
        else:
            if with_extension:
                file_list = [os.path.basename(file) for file in file_list]
            else:
                file_list = [
                    os.path.splitext(os.path.basename(file))[0] for file in file_list
                ]

        file_list.sort()
        return file_list

    def get_data_from_json(self, filename: str) -> dict[str, Any] | bool:
        import json
        import os

        if os.path.isfile(filename):
            with open(filename, "r") as fp:
                data: dict[str, Any] = json.load(fp)
        else:
            data = False

        return data

    def get_data_from_yaml(self, filename: str) -> dict[str, Any] | None:
        import os

        import yaml

        if os.path.isfile(filename):
            with open(filename, "r") as fp:
                data: dict[str, Any] = yaml.load(fp, Loader=yaml.Loader)
        else:
            data = None

        return data


class ReadDataFromString:

    def __init__(self) -> None:
        pass

    def get_line_numbers_containing_keyword(
        self, cfg: dict[str, Any] | None
    ) -> list[int]:
        sample_data_1: dict[str, Any] = {
            "data_string": "<XML>, what can I do \n  abc \n <XML>",
            "line": {"key_word": ["<XML>"], "transform": {"scale": 1, "shift": 0}},
        }
        if cfg is None:
            cfg = sample_data_1

        data_string: str = cfg.get("data_string")
        line_list: list[str] = data_string.split("\n")

        line_numbers: list[int] = self.get_row_numbers_containing_keyword(
            line_list, cfg["line"]["key_word"]
        )

        if cfg["line"].__contains__("transform"):
            scale: int = cfg["line"]["transform"]["scale"]
            shift: int = cfg["line"]["transform"]["shift"]
            line_numbers = [line_num * scale + shift for line_num in line_numbers]

        return line_numbers

    def get_row_numbers_containing_keyword(
        self, array: list[str], key_word: str
    ) -> list[int]:
        line_numbers: list[int] = []
        for rownum in range(0, len(array)):
            if key_word in array[rownum]:
                line_numbers.append(rownum + 1)

        return line_numbers

    def get_array_row_containing_any_of_keywords(
        self, array: list[str], key_words: list[str]
    ) -> int | None:
        for rownum in range(0, len(array)):
            if any(keyword in array[rownum] for keyword in key_words):
                return rownum + 1
        return None

    def get_substrings_by_line_number_array(
        self, cfg: dict[str, Any] | None
    ) -> list[str]:
        sample_data_1: dict[str, Any] = {
            "data_string": "<XML>, what can I do \n  abc \n <\\XML>",
            "start_line_number": [1],
            "end_line_number": [3],
        }
        if cfg is None:
            cfg = sample_data_1
        start_line_number: list[int] = cfg.get("start_line_number")
        end_line_number: list[int] = cfg.get("end_line_number")
        start_line_count: int = len(start_line_number)
        end_line_count: int = len(end_line_number)
        sub_string_array: list[str] = []
        if start_line_count == end_line_count:
            for sub_string_index in range(0, start_line_count):
                start_line: int = start_line_number[sub_string_index]
                end_line: int = end_line_number[sub_string_index]
                cfg_temp = cfg.copy()
                cfg_temp.update(
                    {"start_line_number": start_line, "end_line_number": end_line}
                )
                sub_string: str = self.get_sub_string_by_line_numbers(cfg_temp)
                sub_string_array.append(sub_string)
        elif start_line_count > end_line_count:
            raise Exception(
                "End Line array/keyword is missing. Missing count is {}".format(
                    start_line_count - end_line_count
                )
            )
        else:
            raise Exception(
                "End Line array/keyword is missing. Missing count is {}".format(
                    end_line_count - start_line_count
                )
            )

        return sub_string_array

    def get_sub_string_by_line_numbers(self, cfg: dict[str, Any]) -> str:
        data_string: str = cfg.get("data_string")
        line_list: list[str] = data_string.split("\n")
        start_line_number: int = cfg.get("start_line_number")
        end_line_number: int = cfg.get("end_line_number")
        sub_list: list[str] = line_list[start_line_number - 1 : end_line_number]
        sub_string: str = "\n".join(sub_list)
        return sub_string

    def get_xml_dict_from_byte_data(self, byte_data: bytes) -> list[dict[str, Any]]:
        data_string: str = byte_data.decode("UTF-8")
        cfg_temp: dict[str, Any] = {
            "data_string": data_string,
            "line": {"key_word": "<XML>", "transform": {"scale": 1, "shift": 1}},
        }
        line_numbers_start_xml: list[int] = self.get_line_numbers_containing_keyword(
            cfg=cfg_temp
        )
        cfg_temp = {
            "data_string": data_string,
            "line": {"key_word": "</XML>", "transform": {"scale": 1, "shift": -1}},
        }
        line_numbers_end_xml: list[int] = self.get_line_numbers_containing_keyword(
            cfg=cfg_temp
        )
        cfg_temp = {
            "data_string": data_string,
            "start_line_number": line_numbers_start_xml,
            "end_line_number": line_numbers_end_xml,
        }

        data_sub_strings: list[str] = self.get_substrings_by_line_number_array(
            cfg=cfg_temp
        )
        dict_obj_arrays: list[dict[str, Any]] = []
        for sub_string_index in range(0, len(data_sub_strings)):
            sub_string: str = data_sub_strings[sub_string_index]
            dict_obj: dict[str, Any] = xmltodict.parse(sub_string)
            dict_obj_arrays.append(dict_obj)

        return dict_obj_arrays

    def get_all_lines_containing_all_key_words(self, cfg: dict[str, Any]) -> list[str]:
        data_byte: bytes | None = cfg.get("data_byte", None)
        if data_byte is not None:
            data_string: str = data_byte.decode("UTF-8")
        else:
            data_string = cfg.get("data_string", None)

        key_words: list[str] | None = cfg["line"].get("key_words", None)
        line_array_rows: list[str] = data_string.split("\n")
        line_numbers: list[int] = self.get_all_array_row_containing_all_keywords(
            line_array_rows, key_words
        )
        selected_lines: list[str] = [
            line_array_rows[line_number - 1] for line_number in line_numbers
        ]

        return selected_lines

    def get_all_lines_containing_any_key_words(self, cfg: dict[str, Any]) -> list[str]:
        data_byte: bytes | None = cfg.get("data_byte", None)
        if data_byte is not None:
            data_string: str = data_byte.decode("UTF-8")
        else:
            data_string = cfg.get("data_string", None)

        key_words: list[str] | None = cfg["line"].get("key_words", None)
        line_array_rows: list[str] = data_string.split("\n")
        line_numbers: list[int] = self.get_all_array_rows_containing_any_keyword(
            line_array_rows, key_words
        )
        selected_lines: list[str] = [
            line_array_rows[line_number - 1] for line_number in line_numbers
        ]

        return selected_lines

    def get_all_array_rows_containing_any_keyword(
        self, array: list[str], key_words: list[str]
    ) -> list[int]:
        selected_rows: list[int] = []
        for rownum in range(0, len(array)):
            if any(keyword in array[rownum] for keyword in key_words):
                selected_rows.append(rownum + 1)

        return selected_rows

    def get_first_array_row_containing_any_keyword(
        self, array: list[str], key_words: list[str]
    ) -> int | None:
        for rownum in range(0, len(array)):
            if any(keyword in array[rownum] for keyword in key_words):
                return rownum + 1
        return None

    def get_first_array_row_containing_all_keywords(
        self, array: list[str], key_words: list[str]
    ) -> int | None:
        for rownum in range(0, len(array)):
            if all(keyword in array[rownum] for keyword in key_words):
                return rownum + 1
        return None

    def get_all_array_row_containing_all_keywords(
        self, array: list[str], key_words: list[str]
    ) -> list[int]:
        selected_rows: list[int] = []
        for rownum in range(0, len(array)):
            if all(keyword in array[rownum] for keyword in key_words):
                selected_rows.append(rownum + 1)

        return selected_rows

    def get_intermediate_word_based_on_pattern(self, cfg: dict[str, Any]) -> str | None:
        string: str = cfg.get("string", "")
        pattern: str | None = cfg.get("pattern", None)
        substring_raw = re.search(pattern, string)
        substring: str | None = (
            substring_raw.group(1) if substring_raw is not None else None
        )
        return substring


class ReadURLData:

    def __init__(self, cfg: dict[str, Any]) -> None:
        headers: dict[str, str] = cfg.get("headers", headers_default)
        self.http_connection: urllib3.PoolManager = urllib3.PoolManager(
            1, headers=headers
        )

    def get_response_data(self, cfg: dict[str, Any]) -> bytes | None:
        try:
            response = self.http_connection.request("GET", cfg["url"])
            data: bytes = response.data
        except Exception:
            data = None
            logging.info(
                "Failed to parse xml from response (%s)" % traceback.format_exc()
            )

        return data

    def get_xml_data_as_dict(self, cfg: dict[str, Any]) -> dict[str, Any] | None:
        import xmltodict

        response_data: bytes | None = self.get_response_data(cfg)
        try:
            data: dict[str, Any] = xmltodict.parse(response_data)
        except Exception:
            data = None
            logging.info(
                "Failed to parse xml from response (%s)" % traceback.format_exc()
            )

        return data


class AttributeDict(dict):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(AttributeDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class RegEx:

    def __init__(self) -> None:
        default_string: str = "CUSIP No./n/n/n 2543682"
        pattern: str = r"CUSIP No."
        replace_with: str = ""
        self.default_cfg: dict[str, str] = {
            "default_string": default_string,
            "pattern": pattern,
            "replace_with": replace_with,
        }

    def replace_in_string(self, cfg: dict[str, Any] | None = None) -> str | None:
        if cfg is None:
            cfg = self.default_cfg

        data_byte: bytes | None = cfg.get("data_byte", None)
        if data_byte is not None:
            data_string: str = data_byte.decode("UTF-8")
        else:
            data_string = cfg.get("data_string", None)

        pattern: str | list[str] = cfg.get("pattern")
        if not isinstance(pattern, list):
            pattern = [pattern]

        replace_with: str | list[str] = cfg.get("replace_with")
        if not isinstance(replace_with, list):
            replace_with = [replace_with] * len(pattern)

        for item_index in range(0, len(pattern)):
            data_string = re.sub(
                pattern[item_index], replace_with[item_index], data_string
            )

        return data_string

    def get_without_html_tags(self, cfg: dict[str, Any] | None) -> str:
        if cfg is None:
            cfg = self.default_cfg

        data_byte: bytes | None = cfg.get("data_byte", None)
        if data_byte is not None:
            data_string: str = data_byte.decode("UTF-8")
        else:
            data_string = cfg.get("data_string", None)

        features: str = cfg.get("features", "lxml")

        soup = BeautifulSoup(data_string, features=features)
        text_string_without_html: str = soup.get_text()

        return text_string_without_html


def get_initials_from_name(fullname: str) -> str:
    xs: str = fullname
    name_list: list[str] = xs.split()

    initials: str = ""

    for name in name_list:  # go through each name
        initials += name[0].upper()  # append the initial

    return initials


def getClosestIntegerInList(
    list_data: list[int | float], close_value: int | float
) -> tuple[int | float, int]:
    list_data_arr = np.asarray(list_data)
    idx: int = int((np.abs(list_data_arr - close_value)).argmin())
    return list_data_arr[idx], idx


def transform_df_datetime_to_str(
    df: Any, date_format: str = "%Y-%m-%d %H:%M:%S"
) -> Any:

    df = df.copy()
    if len(df) > 0:
        df_columns: list[str] = list(df.columns)
        for column in df_columns:
            if isinstance(df[column].iloc[0], datetime.datetime) or isinstance(
                df[column].iloc[0], datetime.date
            ):
                df[column] = [
                    item.strftime(date_format) if item is not None else item
                    for item in df[column].to_list()
                ]

    return df


def transform_df_None_to_NULL(df: Any) -> Any:
    df = df.copy()

    # default_value = "NULL"
    # df = df.apply(lambda x: x if x is not None else default_value)
    df_columns: list[str] = list(df.columns)
    for column in df_columns:
        for row_num in range(0, len(df)):
            if df[column].iloc[row_num] is None:
                df[column].iloc[row_num] = "NULL"

    return df


class DateTimeUtility:

    def last_day_of_month(self, any_day: datetime.date) -> datetime.date:
        # Standard library imports
        import datetime as dt

        next_month: datetime.date = any_day.replace(day=28) + dt.timedelta(
            days=4
        )  # this will never fail
        return next_month - dt.timedelta(days=next_month.day)
