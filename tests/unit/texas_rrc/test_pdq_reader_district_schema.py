"""Synthetic PDQ reader regressions for names, IDs, and retained columns."""

from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import pytest

from worldenergydata.texas_rrc.processors.production_processor import (
    ProductionProcessor,
)
from worldenergydata.texas_rrc.production_atlas import (
    build_production_atlas,
    build_production_atlas_from_chunks,
    normalize_production_frame,
)
from worldenergydata.texas_rrc.production_atlas.sources import (
    _read_pdq_member,
    _read_pdq_member_chunks,
    _read_pdq_text,
)


def read_frames(text, reader):
    if reader == "text":
        return [_read_pdq_text(text)]
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("OG_LEASE_CYCLE_DATA_TABLE.dsv", text)
    buffer.seek(0)
    with ZipFile(buffer) as archive:
        name = archive.namelist()[0]
        if reader == "bulk":
            return [_read_pdq_member(archive, name)]
        return list(_read_pdq_member_chunks(archive, name, chunksize=1))


@pytest.mark.parametrize("separator", ["|", "}"])
@pytest.mark.parametrize("reader", ["text", "bulk", "chunked"])
def test_canonical_columns_survive_delimited_read(separator, reader):
    text = "\n".join(
        separator.join(row)
        for row in [
            ["district", "production_month", "oil_production", "extra"],
            ["6E", "202301", "10", "retained"],
            ["7B", "202302", "20", "also retained"],
        ]
    )
    frames = read_frames(text, reader)
    raw = pd.concat(frames, ignore_index=True)
    assert raw.columns.tolist() == [
        "district",
        "production_month",
        "oil_production",
        "extra",
    ]
    assert raw["extra"].tolist() == ["retained", "also retained"]
    result = normalize_production_frame(raw, sort_rows=False)
    assert result["district"].tolist() == ["6E", "7B"]
    assert result["production_month"].tolist() == ["2023-01", "2023-02"]
    assert result["oil_bbl"].tolist() == [10, 20]
    if reader == "chunked":
        assert [len(frame) for frame in frames] == [1, 1]
    atlas = (
        build_production_atlas_from_chunks(frames)
        if reader == "chunked"
        else build_production_atlas(raw)
    )
    statewide = atlas[atlas["aggregation_level"] == "statewide"].iloc[0]
    assert statewide["cumulative_oil_bbl"] == 30
    assert statewide["first_production_month"] == "2023-01"
    assert statewide["last_production_month"] == "2023-02"


@pytest.mark.parametrize("separator", ["|", "}", ","])
@pytest.mark.parametrize("reader", ["text", "bulk", "chunked"])
@pytest.mark.parametrize(
    "column", ['"DISTRICT_NO"', "DISTRICT NO", "OG DIST NO", "DIST-NO"]
)
def test_id_only_header_is_rejected_before_reading_rows(separator, reader, column):
    text = separator.join([column, "OG_CYCLE", "OG_OIL_PROD"])
    text += "\n" + separator.join(["08", "202301", "10"]) + "\n"
    with pytest.raises(ValueError, match="numeric district IDs"):
        read_frames(text, reader)


@pytest.mark.parametrize("separator", ["|", "}", ","])
@pytest.mark.parametrize("reader", ["text", "bulk", "chunked"])
@pytest.mark.parametrize("column", ['"DISTRICT_NO"', "DISTRICT NO"])
def test_official_shaped_mixed_schema_uses_names(separator, reader, column):
    text = separator.join(
        [column, "DISTRICT_NAME", "CYCLE_YEAR_MONTH", "LEASE_OIL_PROD_VOL"]
    )
    text += "\n" + separator.join(["08", "7B", "202301", "10"]) + "\n"
    frames = read_frames(text, reader)
    result = normalize_production_frame(pd.concat(frames, ignore_index=True))
    assert result["district"].tolist() == ["7B"]
    assert result["district_no"].tolist() == ["08"]
    assert result["production_month"].tolist() == ["2023-01"]
    assert result["oil_bbl"].tolist() == [10]
    atlas = (
        build_production_atlas_from_chunks(frames)
        if reader == "chunked"
        else build_production_atlas(pd.concat(frames, ignore_index=True))
    )
    districts = atlas[atlas["aggregation_level"] == "district"]
    assert districts["district"].tolist() == ["7B"]
    assert districts["cumulative_oil_bbl"].tolist() == [10]


@pytest.mark.parametrize("as_frame", [False, True])
@pytest.mark.parametrize(
    "id_column,name_column",
    [
        ("DISTRICT_NO", "DISTRICT_NAME"),
        ("OG_DIST_NO", "district"),
        ("district_no", "district"),
        (" DISTRICT NO ", " DISTRICT NAME "),
    ],
)
def test_processor_keeps_mixed_schema_ids_separate(as_frame, id_column, name_column):
    records = [{id_column: "08", name_column: "7b", "oil_production": "10"}]
    data = pd.DataFrame(records) if as_frame else records
    processed = ProductionProcessor().process(data, validate=False)
    result = processed.to_dict("records") if as_frame else processed
    assert result[0]["district"] == "7B"
    assert result[0]["district_no"] == "08"
    assert result[0]["oil_production"] == 10


@pytest.mark.parametrize("name", ["", None, "invalid"])
def test_missing_or_invalid_names_never_fall_back_to_numeric_id(name):
    frame = pd.DataFrame(
        {"DISTRICT_NO": ["08"], "DISTRICT_NAME": [name], "OIL_BBL": [10]}
    )
    result = normalize_production_frame(frame)
    assert result["district"].tolist() == [""]
    assert result["district_no"].tolist() == ["08"]
    assert result["oil_bbl"].tolist() == [10]
