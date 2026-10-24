"""Offline adapter contracts; synthetic values define inputs, not design limits."""

import hashlib
import importlib.abc
import inspect
import json
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
        pd.DataFrame({"value": [1.0, 2.0]}).to_csv(
            destination, index=False, encoding="utf-8", lineterminator="\n"
        )

    adapter = MetoceanAPIAdapter(tmp_path)
    monkeypatch.setattr(adapter, "_download", download)
    first = adapter.fetch(**request(dataset))
    second = adapter.fetch(**request(dataset))
    assert len(calls) == 1
    assert calls[0]["product"] == product
    assert calls[0]["variable"] == ["hs"]
    pd.testing.assert_frame_equal(first, second)
    # Corruption is rejected, not silently returned or redownloaded.
    next(tmp_path.glob("*/sample.csv")).write_text(
        "value\n999\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(ValueError, match="digest"):
        adapter.fetch(**request(dataset))


def test_different_requests_use_different_cache_entries(tmp_path, monkeypatch):
    calls = []

    def download(payload, directory, destination):
        calls.append(payload)
        pd.DataFrame({"hs": [1.0]}).to_csv(
            destination, index=False, encoding="utf-8", lineterminator="\n"
        )

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
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
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


def release_download(monkeypatch):
    """Keep real release products, date parsing, combination and flattening.

    Only remote I/O is replaced with synthetic xarray data in the child.
    """
    pytest.importorskip("metocean_api.ts")
    from worldenergydata.metocean.clients import metocean_api_adapter as module

    setup = r"""
import io
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from metocean_api.ts.internal import aux_funcs, products
payload = json.load(sys.stdin)
sys.stdin = io.StringIO(json.dumps(payload))
assert Path(payload['destination']).parent == Path.cwd()
product = products.find_product(payload['request']['product'])
if payload['request']['product'] == 'NORA3_wave_sub':
    times = pd.date_range('2020-01-31T22:00', periods=5, freq='h')
    data = xr.Dataset({'hs': ('time', [0., 1., 2., 3., 4.])},
                      coords={'time': times})
else:
    times = pd.date_range('2020-01-01', periods=2, freq='h')
    data = xr.Dataset({'speed': (('time', 'depth'), [[1., 2., 3.], [4., 5., 6.]]),
                       'lon': 5., 'lat': 60.},
                      coords={'time': times, 'depth': [0., 5., 10.]})
observed_dates = []
def file_date(date):
    observed_dates.append(date.strftime('%Y-%m-%d'))
    return 'synthetic'
type(product)._get_url_info = staticmethod(file_date)
type(product)._get_near_coord = staticmethod(
    lambda *args: ({}, np.float64(5.), np.float64(60.)))
aux_funcs.get_tempfiles = lambda product, lon, lat, dates: [
    (Path.cwd() / f'part-{i}.nc').as_posix() for i in range(len(dates))]
xr.open_dataset = lambda *args, **kwargs: data.copy(deep=True)
xr.open_mfdataset = lambda *args, **kwargs: data.copy(deep=True)
def store_synthetic(self, path, *args, **kwargs):
    Path(path).write_text('synthetic', encoding='utf-8', newline='\n')
xr.Dataset.to_netcdf = store_synthetic
"""
    teardown = r"""
Path('file-dates.json').write_text(json.dumps(observed_dates),
                                  encoding='utf-8', newline='\n')
"""
    monkeypatch.setattr(module, "_DOWNLOAD", setup + module._DOWNLOAD + teardown)


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ("2020-01-31", "2020-02-01", [0.0, 1.0, 2.0]),
        ("2020-01-31T23:00", "2020-02-01T01:00", [1.0, 2.0, 3.0]),
        ("2020-01-31T22:30", "2020-02-01T01:30", [1.0, 2.0, 3.0]),
    ],
)
def test_child_nora3_release_dates_and_exact_time_slice(
    tmp_path, monkeypatch, start, end, expected
):
    release_download(monkeypatch)
    adapter = MetoceanAPIAdapter(tmp_path)
    query = request() | {"start_time": start, "end_time": end}
    frame = adapter.fetch(**query)
    assert frame["hs"].tolist() == expected
    dates = json.loads(
        next(tmp_path.glob("*/file-dates.json")).read_text(encoding="utf-8")
    )
    assert dates == ["2020-01-01", "2020-02-01"]
    monkeypatch.setattr(adapter, "_download", lambda *args: pytest.fail("Cache miss"))
    pd.testing.assert_frame_equal(frame, adapter.fetch(**query))


@pytest.mark.parametrize("depth", [[5.0], [0.0, 10.0], None])
def test_child_current_release_selects_requested_depths(tmp_path, monkeypatch, depth):
    release_download(monkeypatch)
    query = request("NorKyst800") | {"variables": ["speed"], "depth": depth}
    frame = MetoceanAPIAdapter(tmp_path).fetch(**query)
    # Synthetic matrix columns are [1, 4], [2, 5], [3, 6] at 0, 5, 10 m.
    values = {0.0: [1.0, 4.0], 5.0: [2.0, 5.0], 10.0: [3.0, 6.0]}
    expected = {f"speed_{d}m": values[d] for d in (depth or [0.0, 5.0, 10.0])}
    assert frame.filter(like="speed_").to_dict("list") == expected


def test_child_current_release_rejects_unavailable_depth(tmp_path, monkeypatch):
    release_download(monkeypatch)
    query = request("NorKyst800") | {"variables": ["speed"], "depth": [7.0]}
    with pytest.raises(RuntimeError, match="retrieval failed"):
        MetoceanAPIAdapter(tmp_path).fetch(**query)
    assert list(tmp_path.glob("*/manifest.json")) == []


def test_depth_request_does_not_reuse_legacy_cache(tmp_path, monkeypatch):
    query = request("NorKyst800") | {"variables": ["speed"], "depth": [5.0]}
    legacy = {
        "product": "NORKYST800",
        "lon": 5.0,
        "lat": 60.0,
        "start_time": "2020-01-01T00:00:00",
        "end_time": "2020-01-01T01:00:00",
        "variable": ["speed"],
        "depth": [5.0],
    }
    key = hashlib.sha256(json.dumps(legacy, sort_keys=True).encode()).hexdigest()
    directory = tmp_path / key
    directory.mkdir()
    sample = directory / "sample.csv"
    sample.write_text("speed_0.0m\n1\n", encoding="utf-8", newline="\n")
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "request": legacy,
                "sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
        newline="\n",
    )

    def download(payload, directory, destination):
        pd.DataFrame({"speed_5.0m": [2.0]}).to_csv(
            destination, index=False, encoding="utf-8", lineterminator="\n"
        )

    adapter = MetoceanAPIAdapter(tmp_path)
    monkeypatch.setattr(adapter, "_download", download)
    assert adapter.fetch(**query).columns.tolist() == ["speed_5.0m"]
    assert sample.read_text(encoding="utf-8") == "speed_0.0m\n1\n"


@pytest.mark.parametrize(
    "depth", [[], [float("nan")], [float("inf")], [-1.0], ["5"], [True]]
)
def test_invalid_depth_is_rejected_before_download(tmp_path, monkeypatch, depth):
    def download(*args):
        pytest.fail("Invalid depth reached download")

    monkeypatch.setattr(MetoceanAPIAdapter, "_download", download)
    with pytest.raises(ValueError, match="depth"):
        MetoceanAPIAdapter(tmp_path).fetch(**(request("NorKyst800") | {"depth": depth}))
    assert list(tmp_path.iterdir()) == []


def test_wave_depth_is_rejected_before_download(tmp_path, monkeypatch):
    def download(*args):
        pytest.fail("Inapplicable depth reached download")

    monkeypatch.setattr(MetoceanAPIAdapter, "_download", download)
    with pytest.raises(ValueError, match="depth.*NorKyst800"):
        MetoceanAPIAdapter(tmp_path).fetch(**(request() | {"depth": [5.0]}))
    assert list(tmp_path.iterdir()) == []
