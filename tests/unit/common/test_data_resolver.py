"""Tests for data_resolver module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from worldenergydata.common.data_resolver import (
    DataNotFoundError,
    _clear_cache,
    get_data_root,
    get_module_data,
)


@pytest.fixture(autouse=True)
def clear_resolver_cache():
    _clear_cache()
    yield
    _clear_cache()


def test_get_data_root_from_env_var(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    with patch.dict(os.environ, {"WED_DATA_ROOT": str(data_dir)}):
        assert get_data_root() == data_dir


def test_get_data_root_from_symlink(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    actual_data = tmp_path / "actual_data"
    actual_data.mkdir()
    data_link = project / "data"
    data_link.symlink_to(actual_data)

    monkeypatch.delenv("WED_DATA_ROOT", raising=False)
    with patch(
        "worldenergydata.common.data_resolver._get_project_root", return_value=project
    ):
        result = get_data_root()
        assert result == actual_data


def test_get_data_root_fallback(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    data_dir = project / "data"
    data_dir.mkdir()

    monkeypatch.delenv("WED_DATA_ROOT", raising=False)
    with patch(
        "worldenergydata.common.data_resolver._get_project_root", return_value=project
    ):
        assert get_data_root() == data_dir


def test_get_data_root_raises_when_missing(tmp_path, monkeypatch):
    project = tmp_path / "empty_project"
    project.mkdir()

    monkeypatch.delenv("WED_DATA_ROOT", raising=False)
    with patch(
        "worldenergydata.common.data_resolver._get_project_root", return_value=project
    ):
        with pytest.raises(DataNotFoundError, match="No data directory found"):
            get_data_root()


def test_get_module_data(tmp_path):
    data_dir = tmp_path / "data" / "modules" / "bsee"
    data_dir.mkdir(parents=True)

    with patch.dict(os.environ, {"WED_DATA_ROOT": str(tmp_path / "data")}):
        result = get_module_data("bsee")
        assert result == data_dir


def test_get_module_data_missing_module(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with patch.dict(os.environ, {"WED_DATA_ROOT": str(data_dir)}):
        with pytest.raises(
            DataNotFoundError, match="Module data not found: nonexistent"
        ):
            get_module_data("nonexistent")
