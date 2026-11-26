"""Resolve the four BSEE snapshots and verify the exact bytes used for parsing."""

import argparse
import hashlib
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

EXAMPLE = Path(__file__).resolve().parent
REPOSITORY = EXAMPLE.parents[2]
BORE = "BoreholeRawData.zip"
TAPE = "lsetapefixed.zip"
PRODUCTION = "ProductionRawData.zip"
OWNERS = "LeaseOwnerRawData.zip"
ARCHIVES = (BORE, TAPE, PRODUCTION, OWNERS)


@contextmanager
def staged_build(parent):
    """Stage this public dataset beside its destination for same-volume publication."""
    parent = parent.resolve(strict=True)
    scratch = parent / f".derive-{uuid4().hex}"
    # Windows builds inherit the destination parent's ACL, as the published
    # directory will. POSIX staging remains private to the build account.
    scratch.mkdir(mode=0o777 if os.name == "nt" else 0o700)
    try:
        yield scratch
    finally:
        if scratch.exists() and scratch.resolve() == scratch:
            shutil.rmtree(scratch)


def input_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=os.environ.get("BSEE_EXP_DATA_DIR") or None,
        required=not os.environ.get("BSEE_EXP_DATA_DIR"),
        help="Directory containing the pinned ZIP files (default: BSEE_EXP_DATA_DIR)",
    )
    return parser


def verified_inputs(data_dir, scratch, names=ARCHIVES):
    """Copy and verify each required archive before any member is read."""
    manifest = json.loads((EXAMPLE / "source_pins.json").read_text(encoding="utf-8"))
    entries = manifest["sources"]
    pins = {entry["name"]: entry for entry in entries}
    if len(entries) != len(ARCHIVES) or set(pins) != set(ARCHIVES):
        raise ValueError("Expected one pin for each of the four BSEE archives")
    scratch.mkdir()
    for name in names:
        pin = pins[name]
        path = scratch / name
        sha256 = hashlib.sha256()
        with (data_dir / name).open("rb") as original, path.open("wb") as target:
            while chunk := original.read(1024 * 1024):
                target.write(chunk)
                sha256.update(chunk)
        digest = sha256.hexdigest()
        size = path.stat().st_size
        if digest != pin["sha256"] or size != pin["bytes"]:
            raise ValueError(
                f"{name}: expected SHA-256 {pin['sha256']}, got {digest}; "
                f"expected {pin['bytes']} bytes, got {size}"
            )
    return pins
