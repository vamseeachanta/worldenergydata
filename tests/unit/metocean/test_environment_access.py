"""Environment-only SDK contracts from CDS setup and Marine subset signatures.

Sources: source_register.json docs_url; the public SDK implementations accept
CDS Client(key=...) and Marine subset(username=..., password=...). Sentinel
strings below are synthetic placeholders, never real credentials.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from worldenergydata.metocean.clients.copernicus_clients import (
    CMEMSClient,
    CredentialsRequired,
    EndpointError,
    ERA5Client,
)


@pytest.mark.parametrize(
    "factory,names",
    [
        (ERA5Client, ["CDSAPI_KEY"]),
        (
            CMEMSClient,
            ["COPERNICUSMARINE_SERVICE_USERNAME", "COPERNICUSMARINE_SERVICE_PASSWORD"],
        ),
    ],
)
def test_missing_environment_does_not_fall_back_to_files(monkeypatch, factory, names):
    for name in names:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(CredentialsRequired, match="environment"):
        factory()


def test_cds_explicit_environment_configuration(monkeypatch):
    calls = []
    monkeypatch.setenv("CDSAPI_KEY", "synthetic-placeholder")
    monkeypatch.setattr(
        "worldenergydata.metocean.clients.copernicus_clients._sdk",
        lambda name: SimpleNamespace(Client=lambda **kwargs: calls.append(kwargs)),
    )
    ERA5Client()
    assert calls[0]["key"] == "synthetic-placeholder"
    assert calls[0]["url"].endswith("/api")
    assert calls[0]["quiet"] is True
    assert calls[0]["debug"] is False


def test_marine_environment_cannot_be_overridden_by_selection(monkeypatch):
    for name in [
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ]:
        monkeypatch.setenv(name, "synthetic-placeholder")
    monkeypatch.setitem(
        sys.modules, "copernicusmarine", SimpleNamespace(subset=lambda **kwargs: kwargs)
    )
    client = CMEMSClient()
    result = client.subset("example-dataset")
    assert result["username"] == result["password"] == "synthetic-placeholder"
    for key in ["username", "password", "credentials_file"]:
        with pytest.raises(ValueError, match="environment"):
            client.subset("example-dataset", **{key: "synthetic-placeholder"})


def test_sdk_errors_do_not_echo_credentials(monkeypatch):
    monkeypatch.setenv("CDSAPI_KEY", "synthetic-placeholder")

    def fail(**kwargs):
        raise RuntimeError("synthetic sensitive detail")

    monkeypatch.setitem(sys.modules, "cdsapi", SimpleNamespace(Client=fail))
    with pytest.raises(EndpointError) as error:
        ERA5Client()
    assert "synthetic sensitive detail" not in str(error.value)
    assert error.value.__suppress_context__
    assert error.value.__context__ is None


def test_optional_extra_declares_current_sdks():
    import tomllib

    root = Path(__file__).resolve().parents[3]
    manifest = tomllib.loads(
        (root / "packages/worldenergydata-metocean/pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    extra = manifest["project"]["optional-dependencies"]["copernicus"]
    # CDSAPI setup (accessed 2026-10-22), Install the CDS API client.
    assert "cdsapi>=0.7.7" in extra
    assert "copernicusmarine" in extra
    assert not any(
        dep.startswith(("cdsapi", "copernicusmarine"))
        for dep in manifest["project"]["dependencies"]
    )


@pytest.mark.parametrize("source", ["era5", "cmems"])
def test_download_errors_are_sanitized(monkeypatch, capsys, source):
    for name in (
        "CDSAPI_KEY",
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ):
        monkeypatch.setenv(name, "synthetic-placeholder")

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic sensitive detail")

    monkeypatch.setitem(
        sys.modules,
        "cdsapi",
        SimpleNamespace(Client=lambda **kwargs: SimpleNamespace(retrieve=fail)),
    )
    monkeypatch.setitem(sys.modules, "copernicusmarine", SimpleNamespace(subset=fail))
    with pytest.raises(EndpointError) as error:
        if source == "era5":
            ERA5Client().retrieve("example-dataset", {}, "unused.grib")
        else:
            CMEMSClient().subset("example-dataset")
    assert "synthetic sensitive detail" not in str(error.value)
    assert error.value.__suppress_context__
    assert error.value.__context__ is None
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("failure", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("action", ["initialize", "retrieve", "subset"])
def test_sdk_cancellation_propagates(monkeypatch, failure, action):
    for name in (
        "CDSAPI_KEY",
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ):
        monkeypatch.setenv(name, "synthetic-placeholder")

    def fail(*args, **kwargs):
        raise failure()

    constructor = (
        fail
        if action == "initialize"
        else lambda **kwargs: SimpleNamespace(retrieve=fail)
    )
    monkeypatch.setitem(sys.modules, "cdsapi", SimpleNamespace(Client=constructor))
    monkeypatch.setitem(sys.modules, "copernicusmarine", SimpleNamespace(subset=fail))
    with pytest.raises(failure):
        if action == "initialize":
            ERA5Client()
        elif action == "retrieve":
            ERA5Client().retrieve("example-dataset", {}, "unused.grib")
        else:
            CMEMSClient().subset("example-dataset")


def test_marine_selection_preserves_sdk_keyword_names(monkeypatch):
    for name in (
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ):
        monkeypatch.setenv(name, "synthetic-placeholder")
    monkeypatch.setitem(
        sys.modules, "copernicusmarine", SimpleNamespace(subset=lambda **kwargs: kwargs)
    )
    selection = {"source": "example", "action": "example", "operation": "example"}
    result = CMEMSClient().subset("example-dataset", **selection)
    assert {key: result[key] for key in selection} == selection


@pytest.mark.parametrize("action", ["initialize", "retrieve", "subset"])
def test_incompatible_sdk_members_are_sanitized(monkeypatch, action):
    for name in (
        "CDSAPI_KEY",
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
    ):
        monkeypatch.setenv(name, "synthetic-placeholder")
    sdk = (
        SimpleNamespace()
        if action == "initialize"
        else SimpleNamespace(Client=lambda **kwargs: object())
    )
    monkeypatch.setitem(sys.modules, "cdsapi", sdk)
    monkeypatch.setitem(sys.modules, "copernicusmarine", SimpleNamespace())
    with pytest.raises(EndpointError) as error:
        if action == "initialize":
            ERA5Client()
        elif action == "retrieve":
            ERA5Client().retrieve("example-dataset", {}, "unused.grib")
        else:
            CMEMSClient().subset("example-dataset")
    assert error.value.__context__ is None
