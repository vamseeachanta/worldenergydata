"""Parse Colorado ECMC FacilityDetail initial-test source pages (#749)."""

from __future__ import annotations

import re

import pandas as pd
from bs4 import BeautifulSoup

PRESSURE_KINDS = {
    ("initial_test_data", "CASING_PRESS"): "WHP_casing_initial_test",
    ("initial_test_data", "TUBING_PRESS"): "WHP_flowing_tubing_initial_test",
}


def parse_facility_detail_html(
    html: str, source_url: str | None = None
) -> pd.DataFrame:
    """Extract long-form Initial Test Data rows from a COGIS scout page."""
    soup = BeautifulSoup(html, "html.parser")
    page_text = _normalize_space(soup.get_text(" ", strip=True))
    context = _page_context(page_text)
    initial_tables = _find_initial_test_tables(soup)
    if not initial_tables:
        return pd.DataFrame(columns=_columns())

    rows = []
    for initial_table in initial_tables:
        block_context = _present_values(_initial_test_block_context(initial_table))
        fields = {**context, **block_context, **_initial_test_fields(initial_table)}
        for test_type, measure in _initial_test_measures(initial_table):
            rows.append(
                {
                    **fields,
                    "source_url": source_url,
                    "source_section": "initial_test_data",
                    "test_type": test_type,
                    "measure_value": _number(measure),
                    "measure_raw": measure,
                }
            )
    return pd.DataFrame(rows, columns=_columns())


def classify_facility_detail_pressures(frame: pd.DataFrame) -> pd.DataFrame:
    """Classify FacilityDetail measures before any screen use."""
    result = frame.copy()
    result["pressure_role"] = "test_rate_or_property"
    result["pressure_kind"] = pd.NA
    result["exclude_reason"] = pd.NA
    result["underpressured_screen_eligible"] = False

    for (section, test_type), pressure_kind in PRESSURE_KINDS.items():
        use = (result["source_section"] == section) & (result["test_type"] == test_type)
        result.loc[use, "pressure_role"] = "candidate_pressure_observation"
        result.loc[use, "pressure_kind"] = pressure_kind
        result.loc[use, "exclude_reason"] = "source_discovery_not_screen_ready"

    treatment = result["source_section"].eq("formation_treatment")
    result.loc[treatment, "pressure_role"] = "excluded_engineering_pressure"
    result.loc[treatment, "exclude_reason"] = "formation_treatment_pressure"

    integrity = result["source_section"].isin(["mit_form_21", "form_17_bradenhead"])
    result.loc[integrity, "pressure_role"] = "excluded_integrity_pressure"
    result.loc[integrity, "exclude_reason"] = "mechanical_integrity_pressure"
    result["underpressured_screen_eligible"] = result[
        "underpressured_screen_eligible"
    ].astype(object)
    return result


def _page_context(page_text: str) -> dict:
    api_fragment = _first_group(r"API#\s*05[-\s]?(\d{3})[-\s]?(\d{5})", page_text)
    api_fragment = "".join(api_fragment) if isinstance(api_fragment, tuple) else None
    return {
        "api_fragment": api_fragment,
        "api10": f"05{api_fragment}" if api_fragment else pd.NA,
        "api12": f"05{api_fragment}00" if api_fragment else pd.NA,
        "facility_id": _first_group(r"FacilityID:\s*(\d+)", page_text),
        "field": _clean_field(_first_group(r"Field:\s*([A-Z0-9 ()/-]+)", page_text)),
        "formation_code": _first_group(
            r"Formation\s+([A-Z0-9]+)\s+Formation Classification", page_text
        ),
        "formation": _first_group(
            r"Completed Information for Formation\s+([A-Z0-9 ]+?)"
            r"(?:\s+1st Production Date|\s+Formation Name|$)",
            page_text,
        ),
        "wellbore": _first_group(r"Wellbore\s+#(\d+)", page_text),
        "measured_td_ft": _number(
            _first_group(r"Measured TD:\s*([\d,]+)\s*ft", page_text)
        ),
        "vertical_td_ft": _number(
            _first_group(r"Vertical TD:\s*([\d,]+)\s*ft", page_text)
        ),
        "interval_top_ft": _number(
            _first_group(r"Interval Top:\s*([\d,]+)\s*ft", page_text)
        ),
        "interval_bottom_ft": _number(
            _first_group(r"Interval Bottom:\s*([\d,]+)\s*ft", page_text)
        ),
        "first_production_date": _date(
            _first_group(r"1st Production Date:\s*([0-9/]+)", page_text)
        ),
    }


def _find_initial_test_tables(soup: BeautifulSoup) -> list:
    tables = []
    seen = set()
    markers = soup.find_all(string=lambda text: text and "Initial Test Data" in text)
    for marker in markers:
        table = marker.find_parent("table")
        if table is not None and id(table) not in seen:
            tables.append(table)
            seen.add(id(table))
    return tables


def _initial_test_block_context(table) -> dict:
    container = table.find_parent("div", class_="accordion2") or table
    block_text = _normalize_space(container.get_text(" ", strip=True))
    return {
        "formation_code": _first_group(
            r"Formation\s+([A-Z0-9]+)\s+Formation Classification", block_text
        ),
        "formation": _first_group(
            r"Completed Information for Formation\s+([A-Z0-9 ]+?)"
            r"(?:\s+1st Production Date|\s+Formation Name|$)",
            block_text,
        ),
        "interval_top_ft": _number(
            _first_group(r"Interval Top:\s*([\d,]+)\s*ft", block_text)
        ),
        "interval_bottom_ft": _number(
            _first_group(r"Interval Bottom:\s*([\d,]+)\s*ft", block_text)
        ),
        "first_production_date": _date(
            _first_group(r"1st Production Date:\s*([0-9/]+)", block_text)
        ),
    }


def _initial_test_fields(table) -> dict:
    fields = {
        "test_date": pd.NaT,
        "test_method": pd.NA,
        "hours_tested": pd.NA,
        "gas_type": pd.NA,
        "gas_disposal": pd.NA,
    }
    for row in table.find_all("tr"):
        cells = _cells(row)
        for label, value in _label_values(cells).items():
            if label == "Test Date":
                fields["test_date"] = _date(value)
            elif label == "Test Method":
                fields["test_method"] = value
            elif label == "Hours Tested":
                fields["hours_tested"] = _number(value)
            elif label == "Gas Type":
                fields["gas_type"] = value
            elif label == "Gas Disposal":
                fields["gas_disposal"] = value
    return fields


def _initial_test_measures(table) -> list[tuple[str, str]]:
    rows = []
    in_measures = False
    for row in table.find_all("tr"):
        cells = _cells(row)
        joined = " ".join(cells)
        if "Perforation Data" in joined:
            break
        if len(cells) >= 2 and cells[0] == "Test Type" and cells[1] == "Measure":
            in_measures = True
            continue
        if in_measures and len(cells) >= 2 and _looks_like_measure(cells[0]):
            rows.append((cells[0], cells[1]))
    return rows


def _label_values(cells: list[str]) -> dict[str, str]:
    values = {}
    index = 0
    while index < len(cells) - 1:
        label = cells[index].rstrip(":")
        if cells[index].endswith(":"):
            values[label] = cells[index + 1]
            index += 2
        else:
            index += 1
    return values


def _cells(row) -> list[str]:
    cells = row.find_all(["td", "th"], recursive=False)
    if not cells:
        cells = row.find_all(["td", "th"])
    return [_normalize_space(cell.get_text(" ", strip=True)) for cell in cells]


def _first_group(pattern: str, text: str):
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return pd.NA
    if len(match.groups()) > 1:
        return tuple(group.strip() for group in match.groups())
    return match.group(1).strip()


def _clean_field(value):
    if pd.isna(value):
        return pd.NA
    return str(value).split("-", 1)[0].strip()


def _present_values(values: dict) -> dict:
    return {key: value for key, value in values.items() if not pd.isna(value)}


def _number(value):
    if pd.isna(value):
        return pd.NA
    match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?", str(value))
    if not match:
        return pd.NA
    number = float(match.group(0).replace(",", ""))
    return int(number) if number.is_integer() else number


def _date(value):
    if pd.isna(value):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce")


def _looks_like_measure(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9_]+", value.strip()))


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _columns() -> list[str]:
    return [
        "api_fragment",
        "api10",
        "api12",
        "facility_id",
        "field",
        "formation_code",
        "formation",
        "wellbore",
        "measured_td_ft",
        "vertical_td_ft",
        "interval_top_ft",
        "interval_bottom_ft",
        "first_production_date",
        "test_date",
        "test_method",
        "hours_tested",
        "gas_type",
        "gas_disposal",
        "source_url",
        "source_section",
        "test_type",
        "measure_value",
        "measure_raw",
    ]
