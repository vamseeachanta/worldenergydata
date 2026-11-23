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
from worldenergydata.texas_rrc.production_atlas.atlas import is_usable_production_frame
from worldenergydata.texas_rrc.production_atlas.sources import (
    _read_pdq_member,
    _read_pdq_member_chunks,
    _read_pdq_text,
    iter_production_input_chunks,
    load_production_inputs,
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


@pytest.mark.parametrize("chunked", [False, True])
@pytest.mark.parametrize("normalized", [False, True], ids=["canonical", "normalized"])
def test_atlas_preserves_condensate_without_field_name(chunked, normalized):
    frame = pd.DataFrame(
        {"district": ["7B"], "production_month": ["202301"], "condensate_bbl": ["10"]}
    )
    assert is_usable_production_frame(frame)
    if normalized:
        frame = normalize_production_frame(
            frame.rename(columns={"condensate_bbl": "condensate"})
        )
        frame = frame.drop(columns="field_name")

    atlas = (
        build_production_atlas_from_chunks([frame])
        if chunked
        else build_production_atlas(frame)
    )
    statewide = atlas.loc[atlas["aggregation_level"] == "statewide"].iloc[0]
    assert statewide["cumulative_condensate_bbl"] == 10
    assert statewide["cumulative_boe"] == 10
    assert statewide["still_producing"]
    assert pd.isna(statewide["cumulative_water_bbl"])


@pytest.mark.parametrize("chunked", [False, True])
@pytest.mark.parametrize(
    "district,month,boe,report_filed",
    [("7b", "202301", 10, "Y"), ("7b", 202301, 10, "Y"), ("7B", "2023-01", 90, "N")],
)
def test_atlas_normalizes_raw_numeric_metrics(
    chunked, district, month, boe, report_filed
):
    frame = pd.DataFrame(
        [
            {
                "district": district,
                "production_month": month,
                "oil_bbl": 0,
                "gas_mcf": 0,
                "condensate_bbl": 10,
                "water_bbl": 0,
                "well_count": 0,
                "boe": boe,
                "report_filed": report_filed,
            }
        ]
    )
    atlas = (
        build_production_atlas_from_chunks([frame])
        if chunked
        else build_production_atlas(frame)
    )
    row = atlas.loc[atlas["aggregation_level"] == "district"].iloc[0]
    assert row["district"] == "7B"
    assert row["first_production_month"] == "2023-01"
    assert row["cumulative_condensate_bbl"] == 10
    assert row["cumulative_boe"] == 10
    assert bool(row["still_producing"]) == (report_filed == "Y")


@pytest.mark.parametrize("reader", ["text", "bulk", "chunked"])
def test_single_column_header_preserves_district(reader):
    frames = read_frames("district\n7B\n", reader)
    assert frames[0].to_dict("list") == {"district": ["7B"]}


@pytest.mark.parametrize("reader", ["text", "bulk", "chunked"])
def test_single_column_header_rejects_numeric_district_id(reader):
    with pytest.raises(ValueError, match="numeric district IDs"):
        read_frames("DISTRICT_NO\n08\n", reader)


def test_condensate_aliases_across_snapshots_preserve_each_row():
    frame = pd.DataFrame(
        [
            {"condensate_bbl": "10"},
            {"OG_COND_PROD": "4"},
            {"OG_COND_PROD": "0", "condensate_bbl": "8"},
        ]
    )
    result = normalize_production_frame(frame, sort_rows=False)
    assert result["condensate_bbl"].tolist() == [10, 4, 0]


def test_normalized_production_retains_filing_and_availability_on_second_pass():
    raw = pd.DataFrame(
        {
            "production_month": ["202301", "202302"],
            "condensate": [10, 0],
            "report_filed": ["Y", "N"],
            "water_bbl": ["", "0"],
        }
    )
    normalized = normalize_production_frame(raw)
    pd.testing.assert_frame_equal(normalize_production_frame(normalized), normalized)


def test_condensate_totals_match_across_separate_snapshots(monkeypatch):
    snapshots = [
        ("OG_COND_PROD", "4"),
        ("LEASE_COND_PROD_VOL", "7"),
        ("condensate_bbl", "10"),
        ("LEASE_COND_PROD_VOL,condensate_bbl", "0,8"),
    ]
    archives = []
    for month, (header, values) in enumerate(snapshots, start=1):
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr(
                "production.csv",
                f"district,production_month,{header}\n7B,2023{month:02},{values}\n",
            )
        archives.append(buffer)
    monkeypatch.setattr(
        "worldenergydata.texas_rrc.production_atlas.sources._pdq_zip_paths",
        lambda root: archives,
    )
    production = load_production_inputs(".").production
    assert production["condensate_bbl"].tolist() == [4, 7, 10, 0]
    bulk = build_production_atlas(production)
    chunks = iter_production_input_chunks(".", chunksize=1).chunks
    chunked = build_production_atlas_from_chunks(chunks)
    for atlas in (bulk, chunked):
        row = atlas.loc[atlas["aggregation_level"] == "statewide"].iloc[0]
        assert row["cumulative_condensate_bbl"] == 21
        assert row["cumulative_boe"] == 21
