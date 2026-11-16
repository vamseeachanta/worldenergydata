"""Archive identity checks using only the synthetic master defined below."""

import io
import urllib.request
import zipfile
from typing import Any

import pytest

from tests.unit.bsee.fieldreserves_helpers import archive
from worldenergydata.bsee import fieldreserves_loader as loader

# Synthetic archive member and retrieval label; no external dataset is used.
MASTER_MEMBER = "mastproddelimit.txt"
RETRIEVED_UTC = "2000-01-01T00:00:00Z"


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("live network forbidden")

    monkeypatch.setattr(urllib.request, "urlopen", denied)


@pytest.fixture
def master_payload() -> bytes:
    """Define three literal CSV rows, each with ten production-master fields.

    The first two fields are numeric-looking identifiers with leading zeros.
    A field spans two leases, and a lease spans two fields. Production values
    and dates are arbitrary synthetic inputs; no physical conversion is tested.
    """
    return (
        b'"00001","00003","10","0","10","20","0","20","30","JAN-2000"\n'
        b'"00001","00004","10","0","10","20","0","20","30","JAN-2000"\n'
        b'"00002","00003","10","0","10","20","0","20","30","JAN-2000"\n'
    )


def test_duplicate_master_member_is_rejected(master_payload: bytes) -> None:
    output = io.BytesIO(archive(MASTER_MEMBER, master_payload))
    with zipfile.ZipFile(output, "a") as duplicate:
        with pytest.warns(UserWarning, match="Duplicate name: 'mastproddelimit[.]txt'"):
            duplicate.writestr(MASTER_MEMBER, master_payload)

    with pytest.raises(ValueError, match="Expected exactly one member"):
        loader.load_master(output.getvalue(), retrieved_utc=RETRIEVED_UTC)


@pytest.mark.parametrize(
    ("column", "identifier"),
    [
        ("FIELD_NAME_CODE", b'"00001"'),
        ("LEASE_NUMBER", b'"00003"'),
    ],
)
@pytest.mark.parametrize("blank", [b"", b" ", b"\t"], ids=["empty", "space", "tab"])
def test_blank_canonical_identifiers_are_rejected(
    master_payload: bytes, column: str, identifier: bytes, blank: bytes
) -> None:
    # Replace only the first matching identifier from master_payload's CSV rows.
    raw = master_payload.replace(identifier, b'"' + blank + b'"', 1)
    with pytest.raises(ValueError, match=f"^Missing identifier: {column}$"):
        loader.load_master(archive(MASTER_MEMBER, raw), retrieved_utc=RETRIEVED_UTC)


def test_valid_master_retains_identifier_bytes(master_payload: bytes) -> None:
    df = loader.load_master(
        archive(MASTER_MEMBER, master_payload), retrieved_utc=RETRIEVED_UTC
    )
    # Expected pairs are the first two CSV fields of master_payload, in row order.
    assert list(
        df[["FIELD_NAME_CODE", "LEASE_NUMBER"]].itertuples(index=False, name=None)
    ) == [
        ("00001", "00003"),
        ("00001", "00004"),
        ("00002", "00003"),
    ]
