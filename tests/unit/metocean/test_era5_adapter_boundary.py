"""Offline ERA5 Mapping and SDK failure contracts; no live ingestion evidence.

Dataset, selection and target follow the CDSAPI setup example already cited in
test_copernicus_clients.py: https://cds.climate.copernicus.eu/en/how-to-api
(accessed 2026-10-26). These are publisher request fields, not physical constants.
The adapter makes one SDK retrieve call for each caller invocation.
"""

import builtins
import io
import os
import socket
import sys
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
from types import MappingProxyType, ModuleType

import pytest

from worldenergydata.metocean.clients import copernicus_clients as clients


@pytest.fixture
def publisher_request():
    """Use the publisher example independently of the adapter implementation."""
    return {
        "product_type": ["reanalysis"],
        "variable": ["geopotential"],
        "year": ["2024"],
        "month": ["03"],
        "day": ["01"],
        "time": ["13:00"],
        "pressure_level": ["1000"],
        "data_format": "grib",
    }


@pytest.fixture
def cds_sandbox(monkeypatch):
    """Resolve only the injected SDK and forbid socket and credential-file I/O."""

    @contextmanager
    def sandbox(client_type):
        fake_sdk = ModuleType("cdsapi")
        fake_sdk.Client = client_type
        imports = []

        def import_fake_sdk(name):
            assert name == "cdsapi"
            assert sys.modules[name] is fake_sdk
            imports.append(name)
            return import_module(name)

        def blocked_io(*args, **kwargs):
            raise AssertionError("Offline adapter attempted socket or file access")

        with monkeypatch.context() as patch:
            patch.setitem(sys.modules, "cdsapi", fake_sdk)
            patch.setattr(clients, "import_module", import_fake_sdk)
            patch.setattr(socket, "socket", blocked_io)
            patch.setattr(socket, "create_connection", blocked_io)
            patch.setattr(socket, "getaddrinfo", blocked_io)
            patch.setattr(builtins, "open", blocked_io)
            patch.setattr(io, "open", blocked_io)
            patch.setattr(os, "open", blocked_io)
            try:
                yield
            finally:
                assert imports == ["cdsapi"]

    return sandbox


def test_era5_readonly_mapping_forwarding(cds_sandbox, publisher_request):
    expected = deepcopy(publisher_request)
    request = MappingProxyType(publisher_request)
    dataset = "reanalysis-era5-pressure-levels"
    target = "download.grib"
    sentinel_result = object()
    constructors = []
    calls = []

    class CDS:
        def __init__(self, **kwargs):
            constructors.append(kwargs)

        def retrieve(self, dataset, request, target):
            calls.append((dataset, request, target))
            return sentinel_result

    with cds_sandbox(CDS):
        result = clients.ERA5Client().retrieve(dataset, request, target)

    assert constructors == [{"url": "https://cds.climate.copernicus.eu/api"}]
    assert calls == [(dataset, expected, target)]
    [(forwarded_dataset, forwarded_request, forwarded_target)] = calls
    assert forwarded_dataset == dataset
    assert type(forwarded_request) is dict
    assert forwarded_request is not request
    assert forwarded_request is not publisher_request
    assert forwarded_target is target
    assert result is sentinel_result
    assert dict(request) == expected
    assert publisher_request == expected

    # Only a separate top-level dict is promised; no nested SDK mutation occurs.
    forwarded_request.pop("variable")
    assert dict(request) == expected
    assert publisher_request == expected


def test_era5_sdk_failure_is_propagated(cds_sandbox, publisher_request):
    expected = deepcopy(publisher_request)
    request = MappingProxyType(publisher_request)
    dataset = "reanalysis-era5-pressure-levels"
    target = "download.grib"
    sentinel_error = RuntimeError("sentinel SDK failure")
    constructors = []
    calls = []

    class CDS:
        def __init__(self, **kwargs):
            constructors.append(kwargs)

        def retrieve(self, dataset, request, target):
            calls.append((dataset, request, target))
            raise sentinel_error

    with pytest.raises(RuntimeError) as error:
        with cds_sandbox(CDS):
            clients.ERA5Client().retrieve(dataset, request, target)

    assert error.value is sentinel_error
    assert constructors == [{"url": "https://cds.climate.copernicus.eu/api"}]
    assert calls == [(dataset, expected, target)]
    [(_, forwarded_request, forwarded_target)] = calls
    assert type(forwarded_request) is dict
    assert forwarded_request is not request
    assert forwarded_request is not publisher_request
    assert forwarded_target is target
    assert dict(request) == expected
    assert publisher_request == expected
