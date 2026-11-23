"""Verify caller-supplied source bytes before registering snapshot metadata."""

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest

from .models import SourceSnapshot
from .store import ProductionDatabase


@dataclass(frozen=True, slots=True)
class SnapshotVerification:
    """Byte identity observed at the time of a successful snapshot insertion."""

    snapshot_id: str
    sha256: str
    byte_count: int


def add_verified_snapshot(
    database: ProductionDatabase, snapshot: SourceSnapshot, raw_bytes: bytes
) -> SnapshotVerification:
    """Check the declared SHA-256 and store only the snapshot metadata."""
    if not isinstance(snapshot, SourceSnapshot):
        raise TypeError("snapshot must be SourceSnapshot")
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw_bytes must be immutable bytes")

    content = memoryview(raw_bytes)
    if not content.nbytes:
        raise ValueError("source bytes must not be empty")
    digest = sha256(content).hexdigest()
    if not compare_digest(digest, snapshot.sha256):
        raise ValueError("source bytes do not match the snapshot SHA-256 digest")

    database.add_snapshot(snapshot)
    return SnapshotVerification(snapshot.snapshot_id, digest, content.nbytes)
