"""Appendix B schema tests using invented identifiers, not source data.

Source: BOEM, Field Definitions for FIELDLEASEAPENLEASE, undated,
https://www.data.boem.gov/Main/HtmlPage.aspx?page=appendixB
(accessed 2026-10-19). Its five columns are LEASE, FIELD, AREA, BLOCK,
and AR/BLK. Expected strings below are direct transcriptions of the
synthetic input; no numerical calculation or engineering limit applies.
"""

import hashlib
import io
import zipfile

import pytest

from tests.unit.bsee.fieldreserves_helpers import archive
from worldenergydata.bsee import fieldreserves_loader as loader

STAMP = "2026-10-19T00:00:00Z"


def test_appendix_preserves_identifiers_rows_and_citations() -> None:
    body = (
        b'" G00001 "," ZZ001 "," ZZ "," 001 "," ZZ 001 "\n'
        b'"G00001","ZZ002","ZZ","002","ZZ 002"\n'
    )
    zipped = archive("appendbdelimit.txt", body)
    df = loader.load_appendix(zipped, retrieved_utc=STAMP)
    assert df.LEASE_NUMBER.tolist() == ["G00001", "G00001"]
    assert df.FIELD_NAME_CODE.tolist() == ["ZZ001", "ZZ002"]
    assert df.AREA_CODE.tolist() == ["ZZ", "ZZ"]
    assert df.BLOCK_NUMBER.tolist() == ["001", "002"]
    assert df.AREA_BLOCK.tolist() == ["ZZ 001", "ZZ 002"]
    assert all(str(dtype) == "string" for dtype in df.dtypes)
    assert df.SOURCE_URL.str.endswith("/appendbdelimit.zip").all()
    assert df.SOURCE_MEMBER.eq("appendbdelimit.txt").all()
    assert df.SOURCE_SHA256.eq(hashlib.sha256(zipped).hexdigest()).all()
    assert df.RETRIEVED_UTC.eq(STAMP).all()


@pytest.mark.parametrize(
    "body, message",
    [
        (b'"G00001","ZZ001","ZZ","001"\n', "Appendix B columns"),
        (b'"G00001","ZZ001","ZZ","001","ZZ 001","extra"\n', "Appendix B columns"),
        (
            b'"G00001","ZZ001","ZZ","001","ZZ 001"\n"G00002","ZZ002"\n',
            "Missing identifier",
        ),
        (b'"G00001"," ","ZZ","001","ZZ 001"\n', "Missing identifier"),
        (b"", "no Appendix B rows"),
        (b" \n\t\n", "no Appendix B rows"),
    ],
)
def test_appendix_rejects_incomplete_or_changed_schema(
    body: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        loader.load_appendix(archive("appendbdelimit.txt", body), retrieved_utc=STAMP)


@pytest.mark.parametrize(
    "body",
    [
        b"LEASE,FIELD,AREA,BLOCK,AR/BLK\n",
        b"LEASE,FIELD,AREA,BLOCK,AR/BLK\nG00001,ZZ001,ZZ,001,ZZ 001\n",
        b'" LEASE "," FIELD "," AREA "," BLOCK "," AR/BLK "\r\n'
        b'"G00001","ZZ001","ZZ","001","ZZ 001"\r\n',
        b"G00001,ZZ001,ZZ,001,ZZ 001\nLEASE,FIELD,AREA,BLOCK,AR/BLK\n",
    ],
)
def test_appendix_rejects_alias_header_as_data(body: bytes) -> None:
    with pytest.raises(ValueError, match="Appendix B header row"):
        loader.load_appendix(archive("appendbdelimit.txt", body), retrieved_utc=STAMP)


def test_appendix_rejects_renamed_member() -> None:
    with pytest.raises(ValueError, match="member"):
        loader.load_appendix(archive("renamed.txt", b""), retrieved_utc=STAMP)


def test_appendix_preserves_na_like_identifier() -> None:
    df = loader.load_appendix(
        archive("appendbdelimit.txt", b'"G00001","NA","ZZ","001","ZZ 001"\n'),
        retrieved_utc=STAMP,
    )
    assert df.FIELD_NAME_CODE.tolist() == ["NA"]


@pytest.mark.parametrize("column", loader.APPENDIX_COLUMNS)
def test_appendix_requires_each_identifier(column: str) -> None:
    values = dict(
        zip(loader.APPENDIX_COLUMNS, ["G00001", "ZZ001", "ZZ", "001", "ZZ 001"])
    )
    values[column] = " "
    raw = (",".join(f'"{value}"' for value in values.values()) + "\n").encode()
    with pytest.raises(ValueError, match=f"Missing identifier: {column}"):
        loader.load_appendix(archive("appendbdelimit.txt", raw), retrieved_utc=STAMP)


def test_appendix_rejects_duplicate_archive_members() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zipped:
        zipped.writestr("appendbdelimit.txt", b"synthetic")
        with pytest.warns(UserWarning, match="Duplicate name"):
            zipped.writestr("appendbdelimit.txt", b"different synthetic")
    with pytest.raises(ValueError, match="exactly one member"):
        loader.load_appendix(output.getvalue(), retrieved_utc=STAMP)
