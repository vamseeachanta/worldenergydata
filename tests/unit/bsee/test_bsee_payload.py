"""Tests for BSEE payload classification and archive extraction.

Encodes the live-verified BSEE raw-data archive shape from issue #267
(2026-06-10): a leading directory entry, quoted-CSV ``.txt`` members
with CRLF line endings, and HTTP-200 HTML bodies for stale URLs.
"""

import io
import zipfile

import pytest

from worldenergydata.bsee.data.refresh.payload import (
    DatasetFailure,
    FailureClass,
    PayloadKind,
    classify_payload,
    extract_primary_table,
    list_data_members,
    select_primary_member,
)

# Mimics live PlatStrucRawData member content (quoted CSV, CRLF, .txt).
BSEE_TXT_CONTENT = (
    '"AREA_CODE","BLOCK_NUMBER","STRUCTURE_NAME"\r\n'
    '"MP","   20","3"\r\n'
    '"MI","  686","C-CMP"\r\n'
)


def _bsee_style_zip(members: dict, dir_name: str = "PlatStrucRawData") -> bytes:
    """Build a zip shaped like a live BSEE archive (leading dir entry)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{dir_name}/", "")
        for name, content in members.items():
            zf.writestr(f"{dir_name}/{name}", content)
    return buf.getvalue()


class TestClassifyPayload:
    def test_zip_magic_is_zip(self):
        data = _bsee_style_zip({"mv_x.txt": BSEE_TXT_CONTENT})
        assert classify_payload(data) is PayloadKind.ZIP

    def test_html_error_page_detected(self):
        # BSEE serves HTTP 200 + HTML for stale URLs (issue #267).
        html = b"\r\n<!DOCTYPE html>\r\n<html><head>..."
        assert classify_payload(html) is PayloadKind.HTML

    def test_html_lowercase_tag_detected(self):
        assert classify_payload(b"  <html lang='en'>") is PayloadKind.HTML

    def test_none_and_empty_are_empty(self):
        assert classify_payload(None) is PayloadKind.EMPTY
        assert classify_payload(b"") is PayloadKind.EMPTY

    def test_garbage_is_unknown(self):
        assert classify_payload(b"\x00\x01\x02 not anything") is PayloadKind.UNKNOWN


class TestListDataMembers:
    def test_skips_directory_entry_and_keeps_txt(self):
        data = _bsee_style_zip({"mv_a.txt": "x", "readme.pdf": "y", "mv_b.csv": "z"})
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [m.filename for m in list_data_members(zf)]
        assert "PlatStrucRawData/" not in names
        assert "PlatStrucRawData/readme.pdf" not in names
        assert set(names) == {
            "PlatStrucRawData/mv_a.txt",
            "PlatStrucRawData/mv_b.csv",
        }


class TestSelectPrimaryMember:
    def _members(self, data):
        zf = zipfile.ZipFile(io.BytesIO(data))
        return list_data_members(zf)

    def test_pattern_match_wins_over_size(self):
        data = _bsee_style_zip(
            {
                "mv_platstruc_platformincs.txt": "h\n" + "x\n" * 5000,
                "mv_platstruc_structures.txt": BSEE_TXT_CONTENT,
            }
        )
        chosen = select_primary_member(
            self._members(data), ["mv_platstruc_structures.txt"]
        )
        assert chosen.filename.endswith("mv_platstruc_structures.txt")

    def test_falls_back_to_largest_member(self):
        data = _bsee_style_zip(
            {"mv_small.txt": "a,b\n1,2\n", "mv_big.txt": "a,b\n" + "1,2\n" * 1000}
        )
        chosen = select_primary_member(self._members(data), ["no_match_*.txt"])
        assert chosen.filename.endswith("mv_big.txt")

    def test_empty_members_returns_none(self):
        assert select_primary_member([], ["x"]) is None


class TestExtractPrimaryTable:
    def test_extracts_bsee_style_txt_member(self):
        data = _bsee_style_zip({"mv_platstruc_structures.txt": BSEE_TXT_CONTENT})
        df, member = extract_primary_table(data, ["mv_platstruc_structures.txt"])
        assert member == "PlatStrucRawData/mv_platstruc_structures.txt"
        assert list(df.columns) == ["AREA_CODE", "BLOCK_NUMBER", "STRUCTURE_NAME"]
        assert len(df) == 2

    def test_legacy_csv_member_still_supported(self):
        data = _bsee_style_zip({"data.csv": "col_a,col_b\n1,hello\n"})
        df, member = extract_primary_table(data)
        assert len(df) == 1

    def test_latin1_fallback_for_non_utf8_operator_names(self):
        content = b'"NAME"\r\n"Petr\xf3leo"\r\n'  # latin-1 accented byte
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("X/mv_ops.txt", content)
        df, _ = extract_primary_table(buf.getvalue())
        assert df.iloc[0, 0] == "Petróleo"

    def test_no_data_members_raises_lookup_error(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("X/", "")
            zf.writestr("X/readme.pdf", "no tables here")
        with pytest.raises(LookupError):
            extract_primary_table(buf.getvalue())

    def test_non_zip_bytes_raise_bad_zip_file(self):
        with pytest.raises(zipfile.BadZipFile):
            extract_primary_table(b"<html>error page</html>")


class TestDatasetFailure:
    def test_summary_includes_class(self):
        f = DatasetFailure("platform", "boom", FailureClass.DETERMINISTIC)
        assert f.summary() == "platform: boom (deterministic)"
