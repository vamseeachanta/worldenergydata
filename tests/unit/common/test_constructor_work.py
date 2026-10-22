"""Bound constructor work with operation counts rather than elapsed time."""

import subprocess
import sys
from importlib import import_module


def test_api_settings_does_not_import_pandas():
    """Independent work budget: API settings need no dataframe operations.

    Therefore zero pandas import requests are permitted. A fresh interpreter
    excludes an already-loaded pandas module from hiding eager imports.
    """
    code = """
import builtins
import sys
original = builtins.__import__
requests = []
def counted(name, *args, **kwargs):
    if name.split(".")[0] == "pandas":
        requests.append(name)
    return original(name, *args, **kwargs)
builtins.__import__ = counted
from worldenergydata.common.config import APISettings
APISettings(_env_file=None)
assert requests == [], requests
assert "pandas" not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )


def test_type_exports_remain_available():
    """Every public type name from the original export list remains resolvable.

    Lazy access must retain identity with the actual types module, including
    pandas' concrete types in the dataframe alias; no substitute type is used.
    """
    common = import_module("worldenergydata.common")
    types = import_module("worldenergydata.common.types")

    names = (
        "CacheProtocol",
        "DataFrameLike",
        "DataSourceProtocol",
        "JSONDict",
        "JSONList",
        "PathLike",
        "ValidatorProtocol",
    )
    for name in names:
        assert getattr(common, name) is getattr(types, name)
        assert name in dir(common)
        assert name in common.__all__


def test_validator_import_does_not_load_plotly():
    """Zero Plotly import requests: construction does not generate a report."""
    code = """
import builtins
import sys
original = builtins.__import__
requests = []
def counted(name, *args, **kwargs):
    if name.split(".")[0] == "plotly":
        requests.append(name)
    return original(name, *args, **kwargs)
builtins.__import__ = counted
from validators.data_validator import DataValidator
DataValidator()
assert requests == [], requests
assert "plotly" not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )


def test_no_config_constructor_does_not_open_files(monkeypatch):
    """An absent config requires zero file opens and zero config-loader calls."""
    from pathlib import Path
    from unittest.mock import Mock

    from validators.data_validator import DataValidator

    opened = Mock(side_effect=AssertionError("unexpected file open"))
    loaded = Mock(side_effect=AssertionError("unexpected config load"))
    monkeypatch.setattr("builtins.open", opened)
    monkeypatch.setattr(Path, "open", opened)
    monkeypatch.setattr(DataValidator, "_load_config", loaded)
    assert DataValidator().config == {}
    opened.assert_not_called()
    loaded.assert_not_called()
