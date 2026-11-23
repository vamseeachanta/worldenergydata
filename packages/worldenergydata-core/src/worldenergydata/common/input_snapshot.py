"""Frozen input bytes and closing integrity checks for deterministic builds."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from re import fullmatch
from types import MappingProxyType

_HASH_CHUNK_SIZE = 1024 * 1024


class InputIntegrityError(ValueError):
    """An input-integrity failure with a reason code and affected identity.

    Codes: unreadable (entry read), unknown-identity (pin outside the input set),
    pin-mismatch (wrong or malformed pin), changed (closing digest differs),
    unavailable (closing read). Identity names the first reported input when
    multiple inputs fail.
    """

    def __init__(self, message: str, *, reason: str, identity: str) -> None:
        """Retain the legacy message and identify the integrity failure."""
        super().__init__(message)
        self.reason = reason
        self.identity = identity


@dataclass(frozen=True)
class FrozenInputs:
    """Read-only input bytes and their pre-render SHA-256 fingerprints."""

    bytes: Mapping[str, bytes]
    sha256: Mapping[str, str]
    size: Mapping[str, int]
    algorithm: str = "sha256"


def _read_inputs(paths: Mapping[str, Path]) -> dict[str, bytes]:
    """Capture each entry buffer or identify the unavailable input."""
    contents = {}
    for identity, path in paths.items():
        try:
            contents[identity] = path.read_bytes()
        except OSError as error:
            raise InputIntegrityError(
                f"input unavailable: {identity}", reason="unreadable", identity=identity
            ) from error
    return contents


def _hash_inputs(contents: Mapping[str, bytes]) -> dict[str, str]:
    return {identity: sha256(raw).hexdigest() for identity, raw in contents.items()}


def _hash_paths(paths: Mapping[str, Path]) -> dict[str, str]:
    """Hash captured paths with at most one bounded read buffer."""
    hashes = {}
    for identity, path in paths.items():
        digest = sha256()
        try:
            with path.open("rb") as stream:
                while chunk := stream.read(_HASH_CHUNK_SIZE):
                    digest.update(chunk)
                    del chunk
        except OSError as error:
            raise InputIntegrityError(
                f"input unavailable: {identity}",
                reason="unavailable",
                identity=identity,
            ) from error
        hashes[identity] = digest.hexdigest()
    return hashes


def _check_pin_identities(paths: Mapping[str, Path], pins: Mapping[str, str]) -> None:
    """Reject pins outside the captured input set before any input read."""
    unknown = pins.keys() - paths.keys()
    if unknown:
        raise InputIntegrityError(
            f"unknown fingerprint identities: {sorted(unknown)}",
            reason="unknown-identity",
            identity=sorted(unknown)[0],
        )


@contextmanager
def freeze_inputs(
    inputs: Mapping[str, Path],
    *,
    expected_sha256: Mapping[str, str] | None = None,
) -> Iterator[FrozenInputs]:
    """Capture inputs, validate external pins, and rehash after rendering.

    All semantic reads shall use the yielded bytes. Render every output inside
    the context; publish only after successful exit. This guard validates input
    integrity, not staged output integrity, atomic publication or producer ancestry.
    Caller enumeration defines the complete input set; later additions are excluded.
    Inputs remain in memory for the block: peak is about total input size plus a
    1 MiB chunk. Present candidates are text sources and one workbook; entry
    capture does not stream large binary inputs.
    Closing revalidation runs only when the body finishes normally. A file changed
    and restored to identical bytes is not detected; rendering uses frozen bytes.
    InputIntegrityError(ValueError) carries documented reason and identity attributes.
    Pins must be 64 hex characters without whitespace/prefix; case is ignored.
    Returned digests are lower-case; malformed pins raise pin-mismatch.
    """
    paths = {identity: Path(path).absolute() for identity, path in inputs.items()}
    pins = dict(expected_sha256 or {})
    _check_pin_identities(paths, pins)
    contents = _read_inputs(paths)
    hashes = _hash_inputs(contents)
    for identity, expected in pins.items():
        if (
            fullmatch(r"[0-9a-fA-F]{64}", expected) is None
            or hashes[identity] != expected.lower()
        ):
            raise InputIntegrityError(
                f"fingerprint mismatch: {identity}",
                reason="pin-mismatch",
                identity=identity,
            )
    yield FrozenInputs(
        MappingProxyType(contents),
        MappingProxyType(hashes),
        MappingProxyType({identity: len(raw) for identity, raw in contents.items()}),
    )
    live_hashes = _hash_paths(paths)
    changed = [
        identity for identity in paths if live_hashes[identity] != hashes[identity]
    ]
    if changed:
        raise InputIntegrityError(
            f"input changed during build: {changed}",
            reason="changed",
            identity=changed[0],
        )
