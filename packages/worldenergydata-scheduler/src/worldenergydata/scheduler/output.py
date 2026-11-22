"""Shared scheduler output paths and timestamped copies (issue #271)."""

import os
import shutil
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def validate_output_dir(value: object) -> None:
    """Reject ambiguous destinations instead of writing into the working directory."""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("output_dir must be a non-empty path")


def resolve_output_dir(job_name: str, config: dict) -> Path:
    """Resolve configured paths, data-root overrides, or the module convention.

    The convention and environment override follow the repository plan for
    issue #271. WED_DATA_ROOT remains supported as the existing data-root name.
    Explicit absolute paths win. Relative paths beginning with ``data`` are
    relocated below the data-root override; other paths use the repository root.
    """
    source = (
        "eia" if job_name == "eia_us_refresh" else job_name.removesuffix("_refresh")
    )
    value = config.get("output_dir", Path("data") / "modules" / source)
    validate_output_dir(value)
    path = Path(value)
    repo_root = Path(config.get("_scheduler_repo_root", Path.cwd()))
    if path.is_absolute():
        return path
    data_root = os.environ.get("WORLDENERGYDATA_DATA_DIR") or os.environ.get(
        "WED_DATA_ROOT"
    )
    if data_root and path.parts and path.parts[0] == "data":
        path = Path(data_root) / Path(*path.parts[1:])
    return (repo_root / path).resolve()


def current_output_files(output_dir: Path) -> Iterator[Path]:
    """Iterate live payloads without descending into historical snapshots."""
    for directory, subdirs, filenames in os.walk(output_dir, followlinks=False):
        if Path(directory) == output_dir:
            subdirs[:] = [name for name in subdirs if name != "runs"]
        for name in filenames:
            path = Path(directory) / name
            if not path.is_symlink():
                yield path


def snapshot_outputs(output_dir: Path) -> Path:
    """Copy the current payload to a unique UTC-named run directory.

    Stable filenames remain available to incremental ingestors and consumers.
    Prior runs and scheduler health manifests are excluded from the copy.
    Symlinks are rejected so snapshots cannot silently capture external data.
    A manifest is added by the scheduler only after this copy succeeds.
    """
    runs = output_dir / "runs"
    if runs.is_symlink():
        raise ValueError("Snapshot runs directory must not be a symlink")
    runs.mkdir(parents=True, exist_ok=True)
    # UTC calendar fields and microseconds identify the execution, not a
    # scientific coefficient or an acceptance threshold (issue #271).
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")
    snapshot = runs / f"{timestamp}-{uuid4().hex}Z"
    snapshot.mkdir()
    for entry in output_dir.iterdir():
        if entry.name in {"runs", "manifest.json"}:
            continue
        if entry.is_symlink():
            raise ValueError("Snapshot payload must not contain symlinks")
        if entry.is_dir():
            # copytree's default dereferences links; reject nested links first.
            if any(path.is_symlink() for path in entry.rglob("*")):
                raise ValueError("Snapshot payload must not contain symlinks")
            shutil.copytree(entry, snapshot / entry.name, copy_function=shutil.copy2)
        elif entry.is_file():
            shutil.copy2(entry, snapshot / entry.name)
    return snapshot
