"""Check shared-namespace ownership in built wheels without importing domains.

Sources: PEP 427 (2013), "File contents" and "The .data directory"
https://peps.python.org/pep-0427/; PEP 503 (2015), "Normalized Names"
https://peps.python.org/pep-0503/; ADR 0001, "Risks" (root initializer ownership).

This is an ownership check, not a complete wheel-format or dependency validator.
Only library files under worldenergydata/ are compared. Purelib and platlib
are conservatively treated as a shared destination, as on typical installs.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


def _normalize(name: str) -> str:
    """Apply the PEP 503 normalized-name algorithm verbatim."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _library_path(filename: str) -> str | None:
    """Map wheel library entries to their PEP 427 installed paths."""
    parts = PurePosixPath(filename).parts
    if parts and parts[0].endswith(".data"):
        # PEP 427: .data/{purelib,platlib}/<path> spreads into site-packages.
        if len(parts) < 3 or parts[1] not in {"purelib", "platlib"}:
            return None
        parts = parts[2:]
    if parts and parts[0] == "worldenergydata":
        return "/".join(parts)
    return None


def check_wheels(wheels: Iterable[Path]) -> list[str]:
    """Return deterministic diagnostics for a co-installable wheel selection.

    A member-only selection is valid: PEP 420 contributors need no root wheel.
    When present, the root initializer belongs only to the worldenergydata
    distribution (ADR 0001). All namespace files, including data, belong to a
    single distribution so uninstalling it cannot remove another one's payload.
    """
    paths = sorted(wheels)
    if not paths:
        return ["no wheels selected"]
    errors: list[str] = []
    distributions: dict[str, str] = {}
    owners: dict[str, str] = {}
    directories: dict[str, str] = {}
    for path in paths:
        label = path.name
        try:
            with ZipFile(path) as archive:
                entries = [entry for entry in archive.infolist() if not entry.is_dir()]
                metadata = [
                    entry
                    for entry in entries
                    if len(PurePosixPath(entry.filename).parts) == 2
                    and entry.filename.split("/")[0].endswith(".dist-info")
                    and entry.filename.endswith("/METADATA")
                ]
                # PEP 427: a wheel represents one distribution with METADATA.
                if len(metadata) != 1:
                    errors.append(f"{label}: expected one top-level METADATA record")
                    continue
                identity = BytesParser().parsebytes(archive.read(metadata[0]))
                name = identity.get("Name", "").strip()
                version = identity.get("Version", "").strip()
                if not name or not version:
                    errors.append(f"{label}: incomplete distribution identity")
                    continue
                normalized = _normalize(name)
                if normalized in distributions:
                    errors.append(
                        f"{label}: duplicate distribution with {distributions[normalized]}"
                    )
                distributions[normalized] = label
                for entry in entries:
                    installed = _library_path(entry.filename)
                    if installed is None:
                        continue
                    if (
                        installed == "worldenergydata/__init__.py"
                        and normalized != "worldenergydata"
                    ):
                        errors.append(
                            f"{label}: member owns namespace root {installed}"
                        )
                    if installed in owners:
                        errors.append(
                            f"{label}: overlap at {installed} with {owners[installed]}"
                        )
                    if installed in directories:
                        errors.append(
                            f"{label}: file/directory conflict at {installed} "
                            f"with {directories[installed]}"
                        )
                    for parent in PurePosixPath(installed).parents:
                        if not parent.parts:
                            continue
                        directory = str(parent)
                        if directory in owners:
                            errors.append(
                                f"{label}: file/directory conflict at {directory} "
                                f"with {owners[directory]}"
                            )
                        # Shared directories are valid; retain one diagnostic owner.
                        directories.setdefault(directory, label)
                    owners[installed] = label
        except (OSError, BadZipFile) as exc:
            # Avoid printing archive contents or environment-specific paths.
            errors.append(f"{label}: cannot read wheel ({type(exc).__name__})")
    return sorted(errors)


def main(argv: list[str] | None = None) -> int:
    """Check the supplied artifacts, returning a failing status on collisions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", nargs="+", type=Path, help="wheels to co-install")
    args = parser.parse_args(argv)
    errors = check_wheels(args.wheels)
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print("Wheel namespace ownership: pass")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
