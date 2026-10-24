"""Optional authenticated downloads: operator-supplied tiny selections only.

These tests never load credential files, supply default credentials or print
credentials. Public catalogue checks do not establish authenticated access.
Dataset terms must already have been accepted with the respective publisher.
"""

import json
import os

import pytest

from worldenergydata.metocean.clients.copernicus_clients import CMEMSClient, ERA5Client

pytestmark = [pytest.mark.network, pytest.mark.credentialed]


def _configured(*names):
    return os.environ.get("METOCEAN_CREDENTIAL_TESTS") == "1" and all(
        os.environ.get(name) for name in names
    )


@pytest.mark.skipif(
    not _configured("CDSAPI_KEY", "METOCEAN_CDS_DATASET", "METOCEAN_CDS_REQUEST"),
    reason=(
        "Requires explicit credential-test opt-in, environment "
        "credentials and a tiny CDS selection"
    ),
)
def test_credentialed_cds_download(tmp_path):
    target = tmp_path / "sample.grib"
    ERA5Client().retrieve(
        os.environ["METOCEAN_CDS_DATASET"],
        json.loads(os.environ["METOCEAN_CDS_REQUEST"]),
        str(target),
    )
    assert target.is_file()
    assert target.stat().st_size > 0


@pytest.mark.skipif(
    not _configured(
        "COPERNICUSMARINE_SERVICE_USERNAME",
        "COPERNICUSMARINE_SERVICE_PASSWORD",
        "METOCEAN_MARINE_DATASET",
        "METOCEAN_MARINE_SELECTION",
    ),
    reason=(
        "Requires explicit credential-test opt-in, environment "
        "credentials and a tiny Marine selection"
    ),
)
def test_credentialed_marine_download(tmp_path):
    selection = json.loads(os.environ["METOCEAN_MARINE_SELECTION"])
    selection.update(output_directory=tmp_path, output_filename="sample.nc")
    CMEMSClient().subset(os.environ["METOCEAN_MARINE_DATASET"], **selection)
    target = tmp_path / "sample.nc"
    assert target.is_file()
    assert target.stat().st_size > 0
