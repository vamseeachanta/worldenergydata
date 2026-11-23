"""Offline contracts using synthetic turbine records only."""

import csv
import hashlib
import io

import pytest

from worldenergydata.wind import load_uswtdb_csv

FIELDS = (
    "case_id,faa_ors,faa_asn,usgs_pr_id,eia_id,t_cap,t_hh,t_rd,t_rsa,"
    "t_ttlh,xlong,ylat"
).split(",")


def sample(**changes):
    row = dict.fromkeys(FIELDS, "")
    row.update(
        case_id="0001",
        t_cap="2000",
        t_hh="80.5",
        t_rd="90",
        t_rsa="6361.73",
        t_ttlh="125.5",
        xlong="-100.25",
        ylat="40.5",
    )
    row.update(changes)
    return row


def encode(*rows, fields=FIELDS):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def test_preserves_ids_measurements_units_and_provenance():
    raw = encode(
        sample(
            faa_ors="01-SYNTH", faa_asn="SYNTH-002", usgs_pr_id="0003", eia_id="0004"
        )
    )
    data = load_uswtdb_csv(raw)
    assert data.release == "3.2 (2020-10-14)"
    assert data.source_sha256 == hashlib.sha256(raw).hexdigest()
    (turbine,) = data.turbines
    assert (
        turbine.case_id,
        turbine.faa_ors,
        turbine.faa_asn,
        turbine.usgs_pr_id,
        turbine.eia_id,
    ) == ("0001", "01-SYNTH", "SYNTH-002", "0003", "0004")
    assert (
        turbine.t_cap,
        turbine.t_hh,
        turbine.t_rd,
        turbine.t_rsa,
        turbine.t_ttlh,
        turbine.xlong,
        turbine.ylat,
    ) == (2000, 80.5, 90.0, 6361.73, 125.5, -100.25, 40.5)
    assert type(turbine.t_cap) is int


def test_blank_measurements_are_missing_and_zero_is_reported():
    data = load_uswtdb_csv(
        encode(sample(t_cap="", t_hh="", t_rd="0", t_rsa="0.0", t_ttlh=""))
    )
    (turbine,) = data.turbines
    assert (turbine.t_cap, turbine.t_hh, turbine.t_ttlh) == (None, None, None)
    assert (turbine.t_rd, turbine.t_rsa) == (0.0, 0.0)
    assert (turbine.faa_ors, turbine.faa_asn, turbine.usgs_pr_id, turbine.eia_id) == (
        None,
        None,
        None,
        None,
    )
    assert load_uswtdb_csv(encode(sample(t_cap="0"))).turbines[0].t_cap == 0


@pytest.mark.parametrize("field", FIELDS)
def test_missing_supported_header_is_rejected(field):
    fields = [name for name in FIELDS if name != field]
    row = sample()
    del row[field]
    with pytest.raises(ValueError, match="header"):
        load_uswtdb_csv(encode(row, fields=fields))


@pytest.mark.parametrize("field", ["case_id", "usgs_pr_id", "eia_id"])
@pytest.mark.parametrize("value", ["1.5", "-1", "1_000", " 1"])
def test_invalid_integer_identifiers_are_rejected(field, value):
    with pytest.raises(ValueError, match=rf"line 2.*{field}"):
        load_uswtdb_csv(encode(sample(**{field: value})))


@pytest.mark.parametrize("field", ["case_id", "xlong", "ylat"])
def test_required_values_cannot_be_blank(field):
    with pytest.raises(ValueError, match=rf"line 2.*{field}"):
        load_uswtdb_csv(encode(sample(**{field: ""})))


@pytest.mark.parametrize(
    "field", ["t_cap", "t_hh", "t_rd", "t_rsa", "t_ttlh", "xlong", "ylat"]
)
@pytest.mark.parametrize(
    "value", ["bad", "NaN", "inf", "-inf", "1e999", "1,000", "1_000", " ", "9" * 400]
)
def test_invalid_numeric_values_are_rejected(field, value):
    with pytest.raises(ValueError, match=rf"line 2.*{field}"):
        load_uswtdb_csv(encode(sample(**{field: value})))


@pytest.mark.parametrize(
    "field,value",
    [
        ("t_cap", "1.5"),
        ("t_cap", "-1"),
        ("t_hh", "-9999"),
        ("t_rd", "-1"),
        ("t_rsa", "-1"),
        ("t_ttlh", "-1"),
        ("xlong", "181"),
        ("ylat", "-91"),
    ],
)
def test_invalid_ranges_and_capacity_type_are_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        load_uswtdb_csv(encode(sample(**{field: value})))


def test_duplicate_ids_do_not_silently_replace_records():
    with pytest.raises(ValueError, match="line 3.*duplicate case_id"):
        load_uswtdb_csv(encode(sample(), sample()))


def test_source_order_bom_and_unmapped_columns():
    rows = [sample(case_id="0002"), sample(case_id="0001")]
    for row in rows:
        row["t_state"] = "ZZ"
    raw = b"\xef\xbb\xbf" + encode(*rows, fields=FIELDS + ["t_state"])
    data = load_uswtdb_csv(raw)
    assert [r.case_id for r in data.turbines] == ["0002", "0001"]
    assert data.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert not hasattr(data.turbines[0], "t_state")


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        encode(),
        encode(sample()) + b"\n",
        encode(sample()) + b'"unterminated',
        encode(sample()).replace(b"2000,", b"2000,extra,"),
        encode(sample()).replace(b",40.5", b""),
        encode(sample()).replace(b"40.5", b"\xff"),
        encode(sample(), fields=FIELDS + ["case_id"]),
    ],
)
def test_empty_or_malformed_csv_is_rejected(raw):
    with pytest.raises(ValueError):
        load_uswtdb_csv(raw)
