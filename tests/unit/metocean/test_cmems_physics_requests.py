"""Offline CMEMS physics forwarding contracts; no observations are downloaded.

Publisher references (accessed 2026-10-26):
https://help.marine.copernicus.eu/en/articles/8283072
The Python subset example supplies the dataset ID and every numeric bound and
date below. Only the output directory is replaced with a pytest temporary path.
https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/description
Product metadata identifies uo/vo as eastward/northward velocity, thetao as
potential temperature and so as salinity. Their combined selection is synthetic;
these tests establish forwarding only, not dataset compatibility or readiness.
"""

import socket
import sys
from copy import deepcopy
from types import ModuleType

import pytest

from worldenergydata.metocean.clients.copernicus_clients import CMEMSClient


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail immediately if a test attempts DNS resolution or a connection."""

    def forbidden(*args, **kwargs):
        raise AssertionError("Network transport is forbidden in offline tests")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def test_cmems_physics_selection_is_preserved(monkeypatch, tmp_path):
    calls = []
    sdk_result = object()

    def subset(**kwargs):
        calls.append(deepcopy(kwargs))
        return sdk_result

    toolbox = ModuleType("copernicusmarine")
    toolbox.subset = subset
    monkeypatch.setitem(sys.modules, "copernicusmarine", toolbox)
    client = CMEMSClient()
    selection = {
        "variables": ["uo", "vo", "thetao", "so"],
        "minimum_longitude": 50,
        "maximum_longitude": 90,
        "minimum_latitude": 0,
        "maximum_latitude": 25,
        "start_datetime": "2020-01-01",
        "end_datetime": "2020-01-31",
        "minimum_depth": 0,
        "maximum_depth": 30,
        "output_directory": tmp_path / "physics",
    }

    result = client.subset("cmems_mod_glo_phy_my_0.083deg_P1D-m", **selection)

    assert result is sdk_result
    # Independent literals catch mutation as well as omitted/rewritten selections.
    assert selection == {
        "variables": ["uo", "vo", "thetao", "so"],
        "minimum_longitude": 50,
        "maximum_longitude": 90,
        "minimum_latitude": 0,
        "maximum_latitude": 25,
        "start_datetime": "2020-01-01",
        "end_datetime": "2020-01-31",
        "minimum_depth": 0,
        "maximum_depth": 30,
        "output_directory": tmp_path / "physics",
    }
    assert calls == [
        {
            "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1D-m",
            "variables": ["uo", "vo", "thetao", "so"],
            "minimum_longitude": 50,
            "maximum_longitude": 90,
            "minimum_latitude": 0,
            "maximum_latitude": 25,
            "start_datetime": "2020-01-01",
            "end_datetime": "2020-01-31",
            "minimum_depth": 0,
            "maximum_depth": 30,
            "output_directory": tmp_path / "physics",
        }
    ]


def test_cmems_subset_failure_is_visible(monkeypatch, tmp_path):
    class SubsetFailure(RuntimeError):
        """A distinct SDK failure that the adapter must propagate unchanged."""

    failure = SubsetFailure("Synthetic subset failure")

    def subset(**kwargs):
        raise failure

    toolbox = ModuleType("copernicusmarine")
    toolbox.subset = subset
    monkeypatch.setitem(sys.modules, "copernicusmarine", toolbox)
    client = CMEMSClient()

    with pytest.raises(SubsetFailure) as error:
        client.subset(
            "cmems_mod_glo_phy_my_0.083deg_P1D-m",
            variables=["uo", "vo", "thetao", "so"],
            output_directory=tmp_path / "physics",
        )

    assert type(error.value) is SubsetFailure
    assert error.value is failure
