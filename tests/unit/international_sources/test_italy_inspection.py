"""Synthetic structural cases; no production values or numeric conversions."""

import csv
import hashlib
import importlib
import io
import json
from pathlib import Path

import pytest

HEADER = (
    "Minerale;Anno;Ub;Titolo;Operatore;Regione;Gennaio;Febbraio;Marzo;Aprile;"
    "Maggio;Giugno;Luglio;Agosto;Settembre;Ottobre;Novembre;Dicembre;Totale"
).split(";")


def row(**changes):
    values = ["GAS", "2024", "T", "EXAMPLE", "EXAMPLE", "EXAMPLE"] + ["0"] * 13
    for key, value in changes.items():
        values[HEADER.index(key)] = value
    return values


def payload(rows=None, header=HEADER, bom=False):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows([row()] if rows is None else rows)
    return stream.getvalue().encode("utf-8-sig" if bom else "utf-8")


def inspect(data, **options):
    module = importlib.import_module(
        "worldenergydata.international_sources.italy_inspection"
    )
    return module.inspect_csv(
        data,
        expected_sha256=options.pop(
            "expected_sha256", hashlib.sha256(data).hexdigest()
        ),
        max_bytes=options.pop("max_bytes", len(data)),
        **options,
    )


@pytest.mark.parametrize("bom", [False, True])
def test_complete_report_retains_concession_status_and_provenance(bom):
    data = payload([row(), row(Anno="2004", Minerale="OLIO")], bom=bom)
    result = inspect(data)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["byte_count"] == len(data)
    assert result["structural_status"] == "VALID"
    assert result["row_count"] == 2
    assert result["year_range"] == [2004, 2024]
    assert result["mineral_categories"] == ["GAS", "OLIO"]
    assert result["granularity"] == "concession"
    assert result["decision"] == "REVIEW_MAPPING"
    assert result["fdas_production"] == "REQUIRES_MAPPING"
    assert result["numeric_interpretation"] == "NOT_EVALUATED"
    assert result["duplicates"] == []
    assert json.loads(json.dumps(result)) == result


def test_literal_tokens_and_quoted_separators_are_preserved():
    result = inspect(
        payload(
            [
                row(
                    Titolo="EXAMPLE;A",
                    Gennaio="",
                    Febbraio="0",
                    Marzo="n.d.",
                    Aprile="1.234,56",
                    Maggio=" ",
                    Totale="UNKNOWN",
                )
            ]
        )
    )
    tokens = result["raw_numeric_rows"][0]
    assert tokens["months"][:5] == ["", "0", "n.d.", "1.234,56", " "]
    assert tokens["total"] == "UNKNOWN"
    assert result["empty_month_counts"] == dict.fromkeys(HEADER[6:18], 0) | {
        "Gennaio": 1
    }


def test_duplicates_keep_all_six_identity_fields_and_source_locations():
    a = row(Titolo="EXAMPLE\nA")
    result = inspect(payload([a, row(Titolo="OTHER"), a, a, row(Operatore="OTHER")]))
    assert result["row_count"] == 5
    assert result["duplicates"] == [{"identity": a[:6], "rows": [2, 5, 7]}]
    assert [(r["row"], r["line_end"]) for r in result["raw_numeric_rows"]] == [
        (2, 3),
        (4, 4),
        (5, 6),
        (7, 8),
        (9, 9),
    ]


@pytest.mark.parametrize(
    "bad_header",
    [
        HEADER[::-1],
        HEADER[:-1],
        HEADER + ["Extra"],
        HEADER[:7] + ["Gennaio"] + HEADER[8:],
    ],
)
def test_header_drift_fails_closed(bad_header):
    with pytest.raises(ValueError, match="row 1: header"):
        inspect(payload(header=bad_header))


@pytest.mark.parametrize("bad_row", [row()[:-1], row() + ["extra"], []])
def test_every_record_has_exact_width(bad_row):
    with pytest.raises(ValueError, match="row 3: width"):
        inspect(payload([row(), bad_row]))


@pytest.mark.parametrize(
    "year", ["", "2024.0", "2,024", "-1", "0000", "２０２４", " 2024"]
)
def test_year_is_an_explicit_calendar_integer(year):
    with pytest.raises(ValueError, match="row 2: year"):
        inspect(payload([row(Anno=year)]))


@pytest.mark.parametrize("field", ["Minerale", "Titolo"])
@pytest.mark.parametrize("token", ["", "  "])
def test_required_identity_is_not_empty(field, token):
    with pytest.raises(ValueError, match="row 2: required"):
        inspect(payload([row(**{field: token})]))


@pytest.mark.parametrize("data", [b"", payload(rows=[])])
def test_empty_input_cannot_claim_structure(data):
    with pytest.raises(ValueError):
        inspect(data)


@pytest.mark.parametrize(
    "data",
    [
        payload() + b'"unterminated',
        payload() + b"\xff",
        payload([row(Titolo="EXAMPLE\x00")]),
    ],
)
def test_invalid_encoding_quoting_and_nulls_are_rejected(data):
    with pytest.raises(ValueError):
        inspect(data)


def test_digest_mismatch_precedes_csv_parsing():
    with pytest.raises(ValueError, match="digest"):
        inspect(b"invalid CSV", expected_sha256="0" * 64)


@pytest.mark.parametrize("digest", ["", "g" * 64, None])
def test_expected_digest_is_required_valid_hex(digest):
    with pytest.raises(ValueError, match="digest"):
        inspect(payload(), expected_sha256=digest)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_cap_is_a_positive_integer(limit):
    with pytest.raises(ValueError, match="max_bytes"):
        inspect(payload(), max_bytes=limit)


def test_cap_is_enforced_before_digest_or_parsing():
    with pytest.raises(ValueError, match="byte cap"):
        inspect(payload(), max_bytes=1, expected_sha256="invalid")


def test_schema_matches_the_retained_dated_assessment():
    assessment = (
        Path(__file__).resolve().parents[3] / "docs/data/eu-tail-source-assessment.json"
    )
    entry = next(
        s
        for s in json.loads(assessment.read_text())["sources"]
        if s["key"] == "italy_unmig"
    )
    assert HEADER == entry["header"]
    assert inspect(payload())["header"] == HEADER
