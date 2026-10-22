"""Offline failure-state checks for #1337, pack map revision BH-map-1.

An independently enumerated two-source outcome table defines success: both
exports must exist. Zero records means empty_result, not a failed download.
No live HTTP or parquet engine is needed for these control-flow tests.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.collectors.baker_hughes_collector import (
    BakerHughesCollector,
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
