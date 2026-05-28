"""Unit tests for the SODIR factpages tableview CSV helper.

These tests are network-free: they exercise the snapshot-cache path, the
HTML-error guard, and the URL builder so the demo-critical offline path stays
green regardless of SODIR availability.
"""

import pandas as pd
import pytest

from worldenergydata.sodir import factpages as fp


def test_tableview_url_includes_report_and_csv_format():
    url = fp.tableview_url("field")
    assert "tableview/field" in url
    assert "rs:Format=CSV" in url
    assert url.startswith("https://factpages.sodir.no/public")


def test_fetch_report_reads_snapshot_without_network(tmp_path):
    # A pre-existing snapshot must be read without any network call.
    snap = tmp_path / "fields.csv"
    pd.DataFrame({"fldName": ["TROLL"], "cmpLongName": ["Equinor"]}).to_csv(
        snap, index=False
    )
    df = fp.fetch_report("fields", cache_dir=tmp_path)
    assert list(df["fldName"]) == ["TROLL"]


def test_fetch_report_unknown_key_raises(tmp_path):
    with pytest.raises(KeyError):
        fp.fetch_report("not_a_report", cache_dir=tmp_path)


def test_fetch_report_missing_snapshot_and_no_requests_raises(tmp_path, monkeypatch):
    # Simulate requests unavailable + no snapshot -> must raise, not return junk.
    monkeypatch.setattr(fp, "requests", None)
    with pytest.raises(RuntimeError):
        fp.fetch_report("fields", cache_dir=tmp_path, refresh=True)


def test_parse_csv_rejects_html_error_page():
    with pytest.raises(ValueError):
        fp._parse_csv("<html><head><title>500</title></head></html>")


def test_parse_csv_parses_clean_body():
    df = fp._parse_csv("a,b\n1,2\n3,4\n")
    assert df.shape == (2, 2)
    assert list(df.columns) == ["a", "b"]
