"""Offline failure-state checks for #1337, pack map revision BH-map-1.

An independently enumerated two-source outcome table defines success: both
exports must exist. Zero records means empty_result, not a failed download.
No live HTTP or parquet engine is needed for these control-flow tests.
"""

import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.collectors.baker_hughes_collector import (
    BakerHughesCollector,
    DownloadError,
)


def caller():
    path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "vessel_fleet"
        / "enrich_from_government.py"
    )
    spec = importlib.util.spec_from_file_location("government_export_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "method", ["download_na_rig_count", "download_international_rig_count"]
)
def test_collector_surfaces_failure(monkeypatch, method):
    collector = BakerHughesCollector()

    def fail(*args):
        raise OSError("synthetic failure")

    monkeypatch.setattr(collector, "get_bytes", fail)
    with pytest.raises(RuntimeError, match="download failed"):
        getattr(collector, method)()


@pytest.mark.parametrize(
    "method", ["download_na_rig_count", "download_international_rig_count"]
)
@pytest.mark.parametrize("empty", [False, True])
def test_collector_parses_fake_download(monkeypatch, method, empty):
    collector = BakerHughesCollector()
    monkeypatch.setattr(collector, "get_bytes", lambda *a: b"synthetic workbook")
    frame = pd.DataFrame() if empty else pd.DataFrame({"Count": [2]})
    monkeypatch.setattr(pd, "read_excel", lambda *a, **kw: frame.copy())
    pd.testing.assert_frame_equal(getattr(collector, method)(), frame)


@pytest.mark.parametrize(
    "method", ["download_na_rig_count", "download_international_rig_count"]
)
def test_collector_parse_failure(monkeypatch, method):
    collector = BakerHughesCollector()
    monkeypatch.setattr(collector, "get_bytes", lambda *a: b"invalid")

    def fail(*args):
        raise ValueError("synthetic invalid workbook")

    monkeypatch.setattr(pd, "read_excel", fail)
    with pytest.raises(RuntimeError, match="download failed"):
        getattr(collector, method)()


def workbook_bytes(malformed):
    """Keep real-reader workbook fixtures in memory; no source downloads."""
    content = io.BytesIO()
    if malformed:
        with ZipFile(content, "w") as archive:
            archive.writestr("xl/workbook.xml", "<workbook/>")
    else:
        pd.DataFrame({"Count": [2]}).to_excel(content, index=False, engine="openpyxl")
    return content.getvalue()


@pytest.mark.parametrize(
    "method", ["download_na_rig_count", "download_international_rig_count"]
)
def test_collector_missing_workbook_member(monkeypatch, method):
    """Missing XLSX members must raise the documented download error."""
    collector = BakerHughesCollector()
    content = workbook_bytes(malformed=True)
    monkeypatch.setattr(collector, "get_bytes", lambda *args: content)

    with pytest.raises(DownloadError, match="workbook download failed"):
        getattr(collector, method)()


@pytest.mark.parametrize(
    "malformed, expected",
    [
        ((True, False), {"na": "download_failed", "international": "exported"}),
        ((False, True), {"na": "exported", "international": "download_failed"}),
        ((True, True), {"na": "download_failed", "international": "download_failed"}),
        ((False, False), {"na": "exported", "international": "exported"}),
    ],
)
def test_export_real_workbooks(monkeypatch, tmp_path, malformed, expected):
    """Real readers must attempt both sources even when an XLSX member is absent."""
    module = caller()
    collector = BakerHughesCollector()
    payloads = iter(workbook_bytes(broken) for broken in malformed)
    attempts = []
    saved = []

    def get_bytes(*args):
        attempts.append(None)
        return next(payloads)

    def save(records, filename):
        assert records == [{"Count": 2}]
        path = tmp_path / filename
        path.write_bytes(b"synthetic exported bytes")
        saved.append(filename)
        return path

    monkeypatch.setattr(collector, "get_bytes", get_bytes)
    result = module.export_baker_hughes(collector, SimpleNamespace(save=save))

    assert result == expected
    assert len(attempts) == 2
    assert set(saved) == {
        f"{source}_rig_count.parquet"
        for source, status in expected.items()
        if status == "exported"
    }


@pytest.mark.parametrize(
    "state", ["download_failed", "empty_result", "missing_export", "exported"]
)
def test_export_states(tmp_path, state):
    module = caller()

    def download():
        if state == "download_failed":
            raise RuntimeError("synthetic failure")
        return (
            pd.DataFrame() if state == "empty_result" else pd.DataFrame({"Count": [2]})
        )

    def save(records, filename):
        path = tmp_path / filename
        if state == "exported":
            path.write_bytes(b"synthetic exported bytes")
        return path

    collector = SimpleNamespace(
        download_na_rig_count=download, download_international_rig_count=download
    )
    result = module.export_baker_hughes(collector, SimpleNamespace(save=save))
    assert result == {"na": state, "international": state}


def test_export_write_exception(tmp_path):
    module = caller()

    def save(*args, **kwargs):
        raise OSError("synthetic write failure")

    download = lambda: pd.DataFrame({"Count": [2]})
    result = module.export_baker_hughes(
        SimpleNamespace(
            download_na_rig_count=download, download_international_rig_count=download
        ),
        SimpleNamespace(save=save),
    )
    assert result == {"na": "missing_export", "international": "missing_export"}


@pytest.mark.parametrize(
    "failures", [(True, True), (True, False), (False, True), (False, False)]
)
def test_main_exit_status(monkeypatch, tmp_path, failures):
    """Success needs both files: fail/fail, fail/pass, pass/fail => nonzero."""
    module = caller()

    def download(fail):
        if fail:
            raise RuntimeError("synthetic download failure")
        return pd.DataFrame({"Count": [2]})

    monkeypatch.setattr(
        module,
        "BOEMCollector",
        lambda: SimpleNamespace(download_platform_structures=lambda: pd.DataFrame()),
    )
    monkeypatch.setattr(
        module,
        "BakerHughesCollector",
        lambda: SimpleNamespace(
            download_na_rig_count=lambda: download(failures[0]),
            download_international_rig_count=lambda: download(failures[1]),
        ),
    )

    def save(records, filename):
        path = tmp_path / filename
        path.write_bytes(b"synthetic exported bytes")
        return path

    monkeypatch.setattr(module, "ParquetStore", lambda **kw: SimpleNamespace(save=save))
    assert module.main() == (1 if any(failures) else 0)
