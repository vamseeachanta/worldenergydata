"""Reject ambiguous column mappings and identities before caching a catalog.

Source: issue #1046 requires stable unique component IDs and populated provenance.
Fixtures are synthetic CSV records, not engineering properties or design limits.
"""

import csv
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
)

CSV_NAME = "drilling_riser_components.csv"
HEADER = [
    "COMPONENT_ID",
    "DATA_SOURCE",
    "NOTES",
    "COMPONENT_TYPE",
    "OD_IN",
    "PRESSURE_RATING_PSI",
    "BORE_SIZE_IN",
    "BOP_TYPE",
    "MANUFACTURER",
]


def write_catalog(directory: Path, ids: list[str]) -> None:
    """Write explicit identities with synthetic provenance and no numeric data."""
    with (directory / CSV_NAME).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADER)
        for component_id in ids:
            row = dict.fromkeys(HEADER, "")
            row.update(
                COMPONENT_ID=component_id,
                DATA_SOURCE="Synthetic CSV example",
                NOTES="Identity validation only",
                COMPONENT_TYPE="riser_joint",
            )
            writer.writerow([row[field] for field in HEADER])


@pytest.mark.parametrize("field", HEADER)
def test_duplicate_header_rejected_before_pandas(tmp_path: Path, field: str) -> None:
    """Hand count: adding a label and a cell preserves width but repeats a key."""
    write_catalog(tmp_path, ["A"])
    path = tmp_path / CSV_NAME
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    rows[0].append(field)
    rows[1].append("duplicate cell")
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)

    loader = DrillingRiserLoader(tmp_path)
    with patch("pandas.read_csv") as read_csv:
        with pytest.raises(ValueError, match=rf"header.*line 1.*duplicate.*{field}"):
            loader.load()
        read_csv.assert_not_called()
    assert loader._df is None


@pytest.mark.parametrize("label", ["", " \t"])
def test_blank_header_rejected_before_pandas(tmp_path: Path, label: str) -> None:
    """A trailing unnamed column has matching width but no semantic mapping."""
    write_catalog(tmp_path, ["A"])
    path = tmp_path / CSV_NAME
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    rows[0].append(label)
    rows[1].append("")
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)
    with patch("pandas.read_csv") as read_csv:
        with pytest.raises(ValueError, match="header.*line 1.*blank column"):
            DrillingRiserLoader(tmp_path).load()
        read_csv.assert_not_called()


@pytest.mark.parametrize("component_id", ["", " \t"])
def test_blank_identity_is_not_cached(tmp_path: Path, component_id: str) -> None:
    """An empty or whitespace-only ID has no usable lookup identity (#1046)."""
    write_catalog(tmp_path, [component_id])
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match="COMPONENT_ID must be populated.*CSV line 2"):
        loader.load()
    assert loader._df is None
    write_catalog(tmp_path, ["A"])
    assert loader.get_by_id("A")["COMPONENT_ID"] == "A"


@pytest.mark.parametrize(
    "ids",
    [
        ["1", "01"],
        ["1", "1.0"],
        ["01"],
        ["NA", "NaN", "NULL", "null"],
        ["Å", "A\u030a", "字"],
    ],
)
def test_identity_strings_survive_parsing(tmp_path: Path, ids: list[str]) -> None:
    """Explicit distinct strings stay distinct, including leading zeros and NA."""
    write_catalog(tmp_path, ids)
    loader = DrillingRiserLoader(tmp_path)
    assert loader.load()["COMPONENT_ID"].tolist() == ids
    for component_id in ids:
        assert loader.get_by_id(component_id)["COMPONENT_ID"] == component_id


@pytest.mark.parametrize(
    ("ids", "lines"),
    [
        (["A", " A", "A "], "3, 4"),
        (["\tA"], "2"),
        (["A\t"], "2"),
        (["\u00a0A"], "2"),
        (["A\n"], "2"),
        ([" A "], "2"),
    ],
)
def test_padded_identity_can_be_repaired_and_retried(
    tmp_path: Path, ids: list[str], lines: str
) -> None:
    """Padding is rejected rather than creating a visually ambiguous identity."""
    write_catalog(tmp_path, ids)
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(
        ValueError, match=rf"COMPONENT_ID.*whitespace.*CSV line {lines}$"
    ):
        loader.load()
    assert loader._df is None
    write_catalog(tmp_path, ["A"])
    assert loader.get_by_id("A")["COMPONENT_ID"] == "A"


@pytest.mark.parametrize(
    "component_id",
    ["\u200bA", "A\u200b", "\ufeffA", "A\ufeff", "A\u200dB", "\u202eA", "\u200b"],
)
def test_format_character_identity_can_be_repaired_and_retried(
    tmp_path: Path, component_id: str
) -> None:
    """Invisible or directional formatting must not create an ambiguous ID."""
    write_catalog(tmp_path, ["A", component_id])
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match="COMPONENT_ID.*format character.*CSV line 3$"):
        loader.get_by_id(component_id)
    assert loader._df is None
    write_catalog(tmp_path, ["A", "B"])
    assert loader.get_by_id("B")["COMPONENT_ID"] == "B"


def test_format_character_identity_reports_all_physical_lines(tmp_path: Path) -> None:
    """Bad IDs start on lines 2 and 5 after a quoted newline and an empty line."""
    write_catalog(tmp_path, ["A\u200b", "B\ufeff"])
    path = tmp_path / CSV_NAME
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    rows[1][HEADER.index("NOTES")] = "first\nsecond"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerows(rows[:2])
        stream.write("\n")
        writer.writerow(rows[2])

    with pytest.raises(
        ValueError, match="COMPONENT_ID.*format character.*CSV line 2, 5$"
    ):
        DrillingRiserLoader(tmp_path).load()


@pytest.mark.parametrize("field", ["DATA_SOURCE", "NOTES"])
@pytest.mark.parametrize("blank", ["", " \t"])
def test_blank_provenance_reports_physical_line(
    tmp_path: Path, field: str, blank: str
) -> None:
    """The bad record starts at line 5 after a quoted newline and an empty line."""
    write_catalog(tmp_path, ["A", "B"])
    path = tmp_path / CSV_NAME
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    rows[1][HEADER.index("NOTES")] = "first\nsecond"
    rows[2][HEADER.index(field)] = blank
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerows(rows[:2])
        stream.write("\n")
        writer.writerow(rows[2])

    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match=rf"{field} must be populated.*CSV line 5"):
        loader.load()
    assert loader._df is None
    write_catalog(tmp_path, ["A", "B"])
    assert loader.load()["COMPONENT_ID"].tolist() == ["A", "B"]


@pytest.mark.parametrize("field", ["DATA_SOURCE", "NOTES"])
def test_blank_provenance_reports_all_lines(tmp_path: Path, field: str) -> None:
    """Only records on lines 2 and 4 lack the required provenance field."""
    write_catalog(tmp_path, ["A", "B", "C"])
    path = tmp_path / CSV_NAME
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    for index in (1, 3):
        rows[index][HEADER.index(field)] = ""
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)

    with pytest.raises(ValueError, match=rf"{field} must be populated.*CSV line 2, 4$"):
        DrillingRiserLoader(tmp_path).load()


def test_delimiter_only_record_reports_physical_line(tmp_path: Path) -> None:
    """An explicit nine-cell empty record retains the provenance error priority."""
    write_catalog(tmp_path, ["A"])
    with (tmp_path / CSV_NAME).open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows([HEADER, [""] * len(HEADER)])
    with pytest.raises(ValueError, match="DATA_SOURCE must be populated.*CSV line 2"):
        DrillingRiserLoader(tmp_path).load()


@pytest.mark.parametrize("field", ["DATA_SOURCE", "NOTES"])
def test_blank_provenance_precedes_padded_identity(tmp_path: Path, field: str) -> None:
    """Missing provenance keeps priority when the same record has a padded ID."""
    write_catalog(tmp_path, [" A"])
    path = tmp_path / CSV_NAME
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    rows[1][HEADER.index(field)] = ""
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)
    with pytest.raises(ValueError, match=rf"{field} must be populated.*CSV line 2$"):
        DrillingRiserLoader(tmp_path).load()


@pytest.mark.parametrize("component_id", ["01", "NA"])
def test_duplicate_identity_reports_literal_string(
    tmp_path: Path, component_id: str
) -> None:
    """Two identical strings remain duplicates without numeric or NA coercion."""
    write_catalog(tmp_path, [component_id, component_id])
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match="Duplicate COMPONENT_ID") as error:
        loader.load()
    assert repr(component_id) in str(error.value)
    assert loader._df is None


@pytest.mark.parametrize(
    ("component_id", "reason"),
    [
        ("", "must be populated"),
        (" \t", "must be populated"),
        (" B", "whitespace"),
        ("B\u200b", "format character"),
        ("\ufeffB", "format character"),
    ],
)
def test_invalid_identity_reports_physical_line(
    tmp_path: Path, component_id: str, reason: str
) -> None:
    """The bad record starts at line 5 after a quoted newline and an empty line."""
    write_catalog(tmp_path, ["A", component_id])
    path = tmp_path / CSV_NAME
    content = path.read_text()
    content = content.replace("Identity validation only", '"first\nsecond"', 1)
    first_record_end = content.index('second"') + len('second"')
    line_end = content.index("\n", first_record_end)
    path.write_text(content[:line_end] + "\n" + content[line_end:])

    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match=rf"COMPONENT_ID.*{reason}.*CSV line 5$"):
        loader.load()
    assert loader._df is None


def test_duplicate_identity_can_be_repaired_and_retried(tmp_path: Path) -> None:
    """Hand calculation: [A, A] has two rows but one distinct ID; [A, B] has two.

    Both records have provenance and matching widths. An ID lookup must not
    silently select the first of the conflicting records. After correction,
    the same loader must read the new file rather than retain an invalid cache.
    """
    write_catalog(tmp_path, ["A", "A"])
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match="Duplicate COMPONENT_ID.*A"):
        loader.get_by_id("A")
    assert loader._df is None
    write_catalog(tmp_path, ["A", "B"])
    frame = loader.load()
    assert frame["COMPONENT_ID"].tolist() == ["A", "B"]
    assert loader.load() is frame


def test_distinct_ids_and_quoted_provenance_round_trip(tmp_path: Path) -> None:
    """A file BOM and quoted provenance format characters preserve distinct IDs."""
    write_catalog(tmp_path, ["A", "B"])
    path = tmp_path / CSV_NAME
    frame = pd.read_csv(path)
    frame["DATA_SOURCE"] = "Synthetic, public example"
    frame["NOTES"] = "first line\nsecond line\u200b"
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    pd.testing.assert_frame_equal(DrillingRiserLoader(tmp_path).load(), frame)
