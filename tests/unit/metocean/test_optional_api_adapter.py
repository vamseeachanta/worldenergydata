"""Offline adapter contracts; synthetic values define inputs, not design limits."""

import importlib.abc
import inspect
import subprocess
import sys

import pandas as pd
import pytest

from worldenergydata.metocean.clients.metocean_api_adapter import MetoceanAPIAdapter


def request(dataset="NORA3"):
    # Arbitrary synthetic coordinates and one-hour window, for call routing only.
    return {
        "dataset": dataset,
        "lon": 5.0,
        "lat": 60.0,
        "start_time": "2020-01-01T00:00",
        "end_time": "2020-01-01T01:00",
        "variables": ["hs"],
    }


def test_reject_other_datasets_before_import(tmp_path):
    with pytest.raises(ValueError, match="NORA3.*NorKyst800"):
        MetoceanAPIAdapter(tmp_path).fetch(**request("ERA5"))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "dataset,product", [("NORA3", "NORA3_wave_sub"), ("NorKyst800", "NORKYST800")]
)
def test_cache_and_routing(tmp_path, monkeypatch, dataset, product):
    calls = []

    def download(payload, directory, destination):
        calls.append(payload)
        assert directory.is_relative_to(tmp_path)
        pd.DataFrame({"value": [1.0, 2.0]}).to_csv(destination, index=False)

    adapter = MetoceanAPIAdapter(tmp_path)
    monkeypatch.setattr(adapter, "_download", download)
    first = adapter.fetch(**request(dataset))
    second = adapter.fetch(**request(dataset))
    assert len(calls) == 1
    assert calls[0]["product"] == product
    assert calls[0]["variable"] == ["hs"]
    pd.testing.assert_frame_equal(first, second)
    # Corruption is rejected, not silently returned or redownloaded.
    next(tmp_path.glob("*/sample.csv")).write_text("value\n999\n")
    with pytest.raises(ValueError, match="digest"):
        adapter.fetch(**request(dataset))


def test_different_requests_use_different_cache_entries(tmp_path, monkeypatch):
    calls = []

    def download(payload, directory, destination):
        calls.append(payload)
        pd.DataFrame({"hs": [1.0]}).to_csv(destination, index=False)

    adapter = MetoceanAPIAdapter(tmp_path)
    monkeypatch.setattr(adapter, "_download", download)
    adapter.fetch(**request())
    adapter.fetch(**(request() | {"variables": ["tp"]}))
    assert len(calls) == 2


def test_missing_extra_has_actionable_error(tmp_path, monkeypatch):
    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, *args):
            if fullname == "metocean_api" or fullname.startswith("metocean_api."):
                raise ModuleNotFoundError("optional backend unavailable")

    monkeypatch.setattr(sys, "meta_path", [Block(), *sys.meta_path])
    for name in tuple(sys.modules):
        if name == "metocean_api" or name.startswith("metocean_api."):
            monkeypatch.delitem(sys.modules, name)
    with pytest.raises(ImportError, match="metocean-api"):
        MetoceanAPIAdapter(tmp_path).fetch(**request())


def test_core_import_with_backends_blocked():
    """A fresh interpreter refuses both libraries, then imports the real core."""
    code = """
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, *args):
        if name.split('.')[0] in {'metocean_api', 'metocean_stats'}:
            raise ModuleNotFoundError('optional backend unavailable')
sys.meta_path.insert(0, Block())
import worldenergydata.metocean
from worldenergydata.metocean.clients.metocean_api_adapter import MetoceanAPIAdapter
assert not any(n.startswith(('metocean_api', 'metocean_stats')) for n in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", code], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_documented_upstream_names_exist():
    """Release API inspection, not a network test; no invented function names."""
    ts = pytest.importorskip("metocean_api.ts")
    assert callable(ts.TimeSeries)
    assert callable(ts.TimeSeries.import_data)
    parameters = inspect.signature(ts.TimeSeries).parameters
    assert {
        "lon",
        "lat",
        "start_time",
        "end_time",
        "product",
        "variable",
        "datafile",
    } <= parameters.keys()
    assert "use_cache" in inspect.signature(ts.TimeSeries.import_data).parameters
    from metocean_api.ts.internal import products

    assert products.find_product("NORA3_wave_sub") is not None
    assert products.find_product("NORKYST800") is not None


def test_child_download_stays_in_cache_directory(tmp_path, monkeypatch):
    """A fake upstream API exercises the actual subprocess protocol offline."""
    upstream = tmp_path / "upstream" / "metocean_api"
    upstream.mkdir(parents=True)
    (upstream / "__init__.py").write_text("")
    (upstream / "ts.py").write_text(
        """
from pathlib import Path
import pandas as pd
class TimeSeries:
    def __init__(self, **request):
        assert request['product'] == 'NORA3_wave_sub'
        assert Path(request['datafile']).parent == Path.cwd()
        self.data = pd.DataFrame({'hs': [1.]})
    def import_data(self, **options):
        assert options == {'save_csv': False, 'save_nc': False, 'use_cache': True}
        Path('upstream-cache-marker').write_text('retained')
"""
    )
    monkeypatch.setenv("PYTHONPATH", str(upstream.parent))
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    adapter = MetoceanAPIAdapter(tmp_path / "cache")
    frame = adapter.fetch(**request())
    assert frame["hs"].tolist() == [1.0]
    assert len(list((tmp_path / "cache").glob("*/upstream-cache-marker"))) == 1
