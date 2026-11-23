"""Snapshot byte verification using invented metadata and fixed SHA-256 vectors."""

from dataclasses import asdict, replace
from pathlib import Path

import pytest

from worldenergydata.production import database as catalog

ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
def snapshot():
    return catalog.SourceSnapshot(
        snapshot_id="sample",
        source_id="eia-api-v2",
        version="example",
        locator="https://example.invalid/source",
        retrieved_at="2026-01-01T00:00:00Z",
        sha256=ABC_SHA256,
        data_kind="synthetic",
    )


@pytest.mark.parametrize("data_kind", ["reported", "synthetic"])
def test_receipt_and_reopened_metadata(tmp_path, snapshot, data_kind):
    path = tmp_path / "snapshot.sqlite"
    snapshot = replace(snapshot, data_kind=data_kind)
    with catalog.ProductionDatabase(path) as db:
        receipt = catalog.add_verified_snapshot(db, snapshot, b"abc")
    assert asdict(receipt) == {
        "snapshot_id": snapshot.snapshot_id,
        "sha256": ABC_SHA256,
        "byte_count": 3,
    }
    with catalog.ProductionDatabase(path) as reopened:
        assert reopened.source_snapshot(snapshot.snapshot_id) == {
            **asdict(snapshot),
            "loaded": 0,
        }


@pytest.mark.parametrize(
    ("content", "digest", "error", "message"),
    [
        (b"abd", ABC_SHA256, ValueError, "digest"),
        (b"", EMPTY_SHA256, ValueError, "empty"),
        (bytearray(b"abc"), ABC_SHA256, TypeError, "bytes"),
        (memoryview(b"abc"), ABC_SHA256, TypeError, "bytes"),
        ("abc", ABC_SHA256, TypeError, "bytes"),
        (Path("source.csv"), ABC_SHA256, TypeError, "bytes"),
    ],
)
def test_invalid_evidence_leaves_snapshot_id_available(
    snapshot, content, digest, error, message
):
    with catalog.ProductionDatabase(":memory:") as db:
        with pytest.raises(error, match=message):
            catalog.add_verified_snapshot(db, replace(snapshot, sha256=digest), content)
        with pytest.raises(ValueError, match="unknown snapshot"):
            db.source_snapshot(snapshot.snapshot_id)
        catalog.add_verified_snapshot(db, snapshot, b"abc")


def test_legacy_snapshot_cannot_be_replaced_by_verified_insert(snapshot):
    with catalog.ProductionDatabase(":memory:") as db:
        db.add_snapshot(snapshot)
        with pytest.raises(ValueError, match="duplicate snapshot"):
            catalog.add_verified_snapshot(db, replace(snapshot, version="new"), b"abc")
        assert db.source_snapshot(snapshot.snapshot_id)["version"] == snapshot.version


def test_byte_count_comes_from_the_hashed_buffer(snapshot):
    class MiscountedBytes(bytes):
        def __len__(self):
            return 1

    with catalog.ProductionDatabase(":memory:") as db:
        receipt = catalog.add_verified_snapshot(db, snapshot, MiscountedBytes(b"abc"))
        assert receipt.byte_count == 3


def test_verified_insert_during_ingest_rolls_back_partial_batch(snapshot):
    with catalog.ProductionDatabase(":memory:") as db:
        db.add_snapshot(snapshot)
        db.add_asset("field", "Example field", "field")
        db.map_field(snapshot.source_id, "external", "field")
        nested = replace(snapshot, snapshot_id="nested")

        def records():
            yield {
                "year": 2026,
                "month": 1,
                "region": "example",
                "field_name": "external",
                "source": "synthetic",
                **dict.fromkeys(catalog.CANONICAL_UNITS),
            }
            catalog.add_verified_snapshot(db, nested, b"abc")

        with pytest.raises(RuntimeError, match="reentrant"):
            db.ingest(snapshot.snapshot_id, records(), units=catalog.CANONICAL_UNITS)
        assert db.production(snapshot.snapshot_id, "field") == []
        assert db.source_snapshot(snapshot.snapshot_id)["loaded"] == 0
        with pytest.raises(ValueError, match="unknown snapshot"):
            db.source_snapshot(nested.snapshot_id)


def test_invalid_snapshot_metadata_raises_type_error():
    with catalog.ProductionDatabase(":memory:") as db:
        with pytest.raises(TypeError, match="SourceSnapshot"):
            catalog.add_verified_snapshot(db, None, b"abc")
