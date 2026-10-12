"""Frozen input bytes and closing integrity checks for deterministic builds."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType


@dataclass(frozen=True)
class FrozenInputs:
    """Read-only input bytes and their pre-render SHA-256 fingerprints."""

    bytes: Mapping[str, bytes]
    sha256: Mapping[str, str]


def _read_inputs(paths: Mapping[str, Path]) -> dict[str, bytes]:
    contents = {}
    for identity, path in paths.items():
        try:
            contents[identity] = path.read_bytes()
        except OSError as error:
            raise ValueError(f"input unavailable: {identity}") from error
    return contents


def _hash_inputs(contents: Mapping[str, bytes]) -> dict[str, str]:
    return {identity: sha256(raw).hexdigest() for identity, raw in contents.items()}


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
    """
    paths = {identity: Path(path).absolute() for identity, path in inputs.items()}
    pins = dict(expected_sha256 or {})
    unknown = pins.keys() - paths.keys()
    if unknown:
        raise ValueError(f"unknown fingerprint identities: {sorted(unknown)}")
    contents = _read_inputs(paths)
    hashes = _hash_inputs(contents)
    for identity, expected in pins.items():
        if hashes[identity] != expected:
            raise ValueError(f"fingerprint mismatch: {identity}")
    yield FrozenInputs(MappingProxyType(contents), MappingProxyType(hashes))
    live_hashes = _hash_inputs(_read_inputs(paths))
    changed = [identity for identity in paths if live_hashes[identity] != hashes[identity]]
    if changed:
        raise ValueError(f"input changed during build: {changed}")
