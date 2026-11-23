"""Offline input-boundary tests; invented station rows are synthetic."""

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

API = "000000000001"
ROW = "000000000001,10,0,200,N,20,0,E,199,1,2,-90,28\n"
SECOND = '"000000000001"," 11 ",0,100,S,21,0,W,99,,," -90\n",28\n'
RAW = (ROW + SECOND).encode()
METADATA = {
    "api12": API,
    "source_url": "https://example.org/synthetic.csv",
    "retrieved_at": "2026-10-01T12:00:00Z",
    "data_kind": "synthetic",
}


def build_survey_envelope(*args, **kwargs):
    # Import at call time so every contract case records its own red result.
    from worldenergydata.bsee.data.survey_envelope import (
        build_survey_envelope as builder,
    )

    return builder(*args, **kwargs)


def build(raw=RAW, **changes):
    metadata = {**METADATA, "declared_sha256": hashlib.sha256(raw).hexdigest()}
    metadata.update(changes)
    return build_survey_envelope(raw, **metadata)


def changed_cell(index, value):
    row = next(csv.reader(io.StringIO(ROW)))
    row[index] = value
    stream = io.StringIO(newline="")
    csv.writer(stream).writerow(row)
    return stream.getvalue().encode()


def test_complete_envelope_preserves_independently_transcribed_stations():
    envelope = build()
    assert envelope == {
        "schema_version": 1,
        "source_schema": "bsee.dsptsdelimit.v1",
        "api12": API,
        "data_kind": "synthetic",
        "source": {
            "url": METADATA["source_url"],
            "retrieved_at": METADATA["retrieved_at"],
            "sha256": hashlib.sha256(RAW).hexdigest(),
        },
        "units": {
            "depth": "unresolved",
            "angle_degrees": "degree",
            "angle_minutes": "arcminute",
            "geographic_positions_and_differences": "degree",
        },
        "readiness": "not_qualified",
        "stations": [
            {
                "source_row": 1,
                "values": {
                    "API_WELL_NUMBER": API,
                    "INCL_ANG_DEG_VAL": "10",
                    "INCL_ANG_MIN_VAL": "0",
                    "SURVEY_POINT_MD": "200",
                    "WELL_N_S_CODE": "N",
                    "DIR_DEG_VAL": "20",
                    "DIR_MINS_VAL": "0",
                    "WELL_E_W_CODE": "E",
                    "SURVEY_POINT_TVD": "199",
                    "DELTA_X": "1",
                    "DELTA_Y": "2",
                    "SURF_LONGITUDE": "-90",
                    "SURF_LATITUDE": "28",
                },
            },
            {
                "source_row": 2,
                "values": {
                    "API_WELL_NUMBER": API,
                    "INCL_ANG_DEG_VAL": " 11 ",
                    "INCL_ANG_MIN_VAL": "0",
                    "SURVEY_POINT_MD": "100",
                    "WELL_N_S_CODE": "S",
                    "DIR_DEG_VAL": "21",
                    "DIR_MINS_VAL": "0",
                    "WELL_E_W_CODE": "W",
                    "SURVEY_POINT_TVD": "99",
                    "DELTA_X": None,
                    "DELTA_Y": None,
                    "SURF_LONGITUDE": " -90\n",
                    "SURF_LATITUDE": "28",
                },
            },
        ],
    }
    assert json.loads(json.dumps(envelope, allow_nan=False)) == envelope
    assert build() == envelope


def test_inputs_unchanged_and_results_independent():
    before = copy.deepcopy(METADATA)
    raw_before = bytes(RAW)
    result = build_survey_envelope(
        RAW, declared_sha256=hashlib.sha256(RAW).hexdigest(), **METADATA
    )
    result["stations"][0]["values"]["SURVEY_POINT_MD"] = "changed"
    assert METADATA == before
    assert RAW == raw_before
    assert build()["stations"][0]["values"]["SURVEY_POINT_MD"] == "200"


@pytest.mark.parametrize(
    "raw",
    [b"", b"\n", ROW.rsplit(",", 1)[0].encode(), (ROW.rstrip() + ",extra\n").encode()],
)
def test_empty_or_wrong_width_fails(raw):
    with pytest.raises(ValueError, match="record|fields"):
        build(raw)


def test_error_identifies_csv_record_after_quoted_newline():
    with pytest.raises(ValueError, match="record 3"):
        build(RAW + b"short,row\n")


@pytest.mark.parametrize(
    "raw",
    [
        RAW.replace(b"000000000001", b"000000000002", 1),
        changed_cell(0, ""),
        b'"unterminated',
    ],
)
def test_mixed_or_missing_identifier_and_malformed_csv_fail(raw):
    with pytest.raises(ValueError):
        build(raw)


@pytest.mark.parametrize("index", [1, 2, 3, 5, 6, 8])
@pytest.mark.parametrize("value", ["", "NaN", "inf", "-Infinity", "1e999", "1,000"])
def test_missing_nonfinite_or_grouped_critical_numbers_fail(index, value):
    with pytest.raises(ValueError, match="record 1.*finite"):
        build(changed_cell(index, value))


@pytest.mark.parametrize("index", [9, 10, 11, 12])
def test_optional_numbers_are_null_when_empty_but_finite_when_present(index):
    assert (
        list(build(changed_cell(index, " "))["stations"][0]["values"].values())[index]
        is None
    )
    with pytest.raises(ValueError, match="finite"):
        build(changed_cell(index, "NaN"))


@pytest.mark.parametrize("index,value", [(4, "X"), (7, ""), (7, "NE")])
def test_unknown_quadrants_fail(index, value):
    with pytest.raises(ValueError, match="direction"):
        build(changed_cell(index, value))


@pytest.mark.parametrize("digest", ["0" * 64, "invalid", "", "a" * 63])
def test_bad_digest_fails_before_decode(digest):
    with pytest.raises(ValueError, match="SHA-256"):
        build(b"\xff", declared_sha256=digest)


def test_tampered_bytes_fail_and_uppercase_pin_is_accepted():
    pin = hashlib.sha256(RAW).hexdigest()
    with pytest.raises(ValueError, match="SHA-256"):
        build(RAW + b" ", declared_sha256=pin)
    assert build(declared_sha256=pin.upper()) == build()


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-10-01",
        "2026-10-01T12:00:00",
        "2026-02-30T12:00:00Z",
        "invalid",
        "2026-10-01T12:00:00+24:00",
        "2026-10-01T12:00:00+00:60",
    ],
)
def test_inconsistent_timestamps_fail(timestamp):
    with pytest.raises(ValueError, match="retrieved_at"):
        build(retrieved_at=timestamp)


@pytest.mark.parametrize(
    "changes",
    [
        {"api12": 1},
        {"api12": "1"},
        {"source_url": ""},
        {"source_url": "file:source"},
        {"data_kind": "unknown"},
    ],
)
def test_invalid_metadata_fails(changes):
    with pytest.raises(ValueError):
        build(**changes)


def test_mutable_bytes_and_invalid_utf8_are_rejected():
    with pytest.raises(TypeError, match="bytes"):
        build(bytearray(RAW))
    with pytest.raises(ValueError, match="UTF-8"):
        build(b"\xff")


def test_retained_public_fixture_is_read_only_and_unqualified():
    root = Path(__file__).resolve().parents[4]
    folder = root / "data/modules/bsee/directional_survey_validation"
    source_bytes = (folder / "source.json").read_bytes()
    source = json.loads(source_bytes)
    raw = (folder / "stations.csv").read_bytes()
    result = build_survey_envelope(
        raw,
        api12=source["api12"],
        source_url=source["url"],
        retrieved_at=source["retrieved_at"],
        declared_sha256=source["data_sha256"],
        data_kind="source",
    )
    assert len(result["stations"]) == source["record_count"]
    assert result["readiness"] == "not_qualified"
    assert result["units"]["depth"] == "unresolved"
    assert (folder / "stations.csv").read_bytes() == raw
    assert (folder / "source.json").read_bytes() == source_bytes
