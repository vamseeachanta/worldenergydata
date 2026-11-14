"""Private output staging paired with frozen-input revalidation.

Implements the snapshot/staging contract in issue #1048. SHA-256 is specified
by RFC 6234 (2011), section 6. No publication or implicit network access occurs.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from types import MappingProxyType

from worldenergydata.common.input_snapshot import FrozenInputs, freeze_inputs


class OutputIntegrityError(ValueError):
    """A staged output is undeclared, duplicated, missing, unsafe or changed."""

    def __init__(self, message: str, *, identity: str) -> None:
        super().__init__(message)
        self.identity = identity


@dataclass(frozen=True)
class ArtifactSnapshot:
    """Validated, immutable bytes for publication without reopening stage files."""

    inputs: FrozenInputs
    bytes: Mapping[str, bytes]
    sha256: Mapping[str, str]
    size: Mapping[str, int]
    algorithm: str = "sha256"


class StagedOutputs:
    """Write each declared identity once, sealing its digest at write time.

    Identities are opaque keys, never filesystem paths. Returned paths permit
    format-specific validation, but later changes are rejected. Renderers shall
    write only here, using frozen input bytes. This is a cooperative integrity
    guard, not a sandbox for hostile rendering code.
    """

    def __init__(self, directory: Path, identities: tuple[str, ...]) -> None:
        self._directory = directory
        self._identities = identities
        self._paths: dict[str, Path] = {}
        self._hashes: dict[str, str] = {}

    @property
    def sha256(self) -> Mapping[str, str]:
        """Sealed hashes so far; a manifest shall not include its own hash."""
        return MappingProxyType(dict(self._hashes))

    def write(self, identity: str, data: bytes) -> Path:
        """Stage immutable bytes and record the digest of that exact buffer."""
        if identity not in self._identities:
            raise OutputIntegrityError("undeclared output", identity=identity)
        if identity in self._paths:
            raise OutputIntegrityError("duplicate output", identity=identity)
        if not isinstance(data, bytes):
            raise TypeError("staged output data must be bytes")
        with NamedTemporaryFile(dir=self._directory, delete=False) as stream:
            stream.write(data)
            path = Path(stream.name)
        self._paths[identity] = path
        self._hashes[identity] = sha256(data).hexdigest()
        return path

    def _validated_bytes(self) -> dict[str, bytes]:
        """Validate and retain the same buffers that will be published."""
        contents = {}
        for identity in self._identities:
            if identity not in self._paths:
                raise OutputIntegrityError("missing output", identity=identity)
            path = self._paths[identity]
            try:
                if path.is_symlink() or not path.is_file():
                    raise OutputIntegrityError(
                        "staged output is not a regular file", identity=identity
                    )
                raw = path.read_bytes()
            except OSError as error:
                raise OutputIntegrityError(
                    "staged output unavailable", identity=identity
                ) from error
            if sha256(raw).hexdigest() != self._hashes[identity]:
                raise OutputIntegrityError("staged output changed", identity=identity)
            contents[identity] = raw
        return contents


def build_artifacts(
    inputs: Mapping[str, Path],
    output_ids: Iterable[str],
    render: Callable[[FrozenInputs, StagedOutputs], None],
    *,
    expected_sha256: Mapping[str, str] | None = None,
    staging_parent: Path | None = None,
) -> ArtifactSnapshot:
    """Render privately, revalidate inputs, then validate every staged output.

    The complete input and output sets are captured before rendering. External
    binary pins are checked before the renderer can extract frozen bytes.
    Input revalidation occurs on successful renderer exit; output validation
    follows it. No result is returned on failure. Canonical paths are never
    supplied to this helper: callers publish only returned bytes, after all
    checks pass, and own transactional publication and rollback.

    Input and output bytes are held in memory. Equal endpoint hashes do not
    detect a change restored to identical bytes. Producer ancestry and Git blob
    validation remain the caller's responsibility. Staging uses the configured
    temporary directory unless staging_parent is supplied.
    """
    if isinstance(output_ids, str):
        raise TypeError("output identities must be an iterable of strings")
    identities = tuple(output_ids)
    if any(not isinstance(identity, str) or not identity for identity in identities):
        raise ValueError("output identities must be nonempty strings")
    if len(set(identities)) != len(identities):
        raise ValueError("output identities must be unique")
    with TemporaryDirectory(prefix="artifact-", dir=staging_parent) as directory:
        stage = StagedOutputs(Path(directory), identities)
        with freeze_inputs(inputs, expected_sha256=expected_sha256) as frozen:
            render(frozen, stage)
        contents = stage._validated_bytes()
        return ArtifactSnapshot(
            inputs=frozen,
            bytes=MappingProxyType(contents),
            sha256=stage.sha256,
            size=MappingProxyType(
                {identity: len(raw) for identity, raw in contents.items()}
            ),
        )
