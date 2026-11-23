"""Load user-supplied licensed metocean tables that are not distributed."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import yaml

LICENSED_DATA_ENV = "METOCEAN_LICENSED_DATA_DIR"


def _repository_root() -> Path:
    """Locate the owning checkout independently of the current directory."""
    for root in Path(__file__).resolve().parents:
        if (root / "config/repo_structure.yml").is_file() and (
            root / "data/modules/metocean/schema.yaml"
        ).is_file():
            return root
    raise ValueError(
        "Repository boundary cannot be established; use the metocean source checkout."
    )


def load_licensed_table(
    name: str, *, copy_path: str | Path | None = None
) -> list[dict[str, str]]:
    """Read an external licensed CSV after checking its documented columns.

    An explicit file takes precedence over METOCEAN_LICENSED_DATA_DIR.
    Returned cells remain strings; schema types and units describe their basis.
    Repository-local files, including resolved symlinks, are refused.
    """
    root = _repository_root()
    schema = yaml.safe_load((root / "data/modules/metocean/schema.yaml").read_text())
    entries = {
        entry["name"]: entry
        for entry in schema["datasets"]
        if entry.get("distributed") is False
    }
    if name not in entries:
        raise ValueError(
            "Unknown licensed table; select a name in the metocean schema."
        )
    entry = entries[name]
    missing = (
        f"{entry['citation']} Expected file: {name}. The values are licensed and "
        "are not distributed with the repository. Supply copy_path or set "
        f"{LICENSED_DATA_ENV} to an external directory containing the expected file."
    )
    directory = os.environ.get(LICENSED_DATA_ENV)
    if copy_path is None and not directory:
        raise FileNotFoundError(missing)
    supplied = Path(copy_path) if copy_path is not None else Path(directory) / name
    supplied = supplied.expanduser().resolve()
    if supplied.is_relative_to(root):
        raise ValueError("A licensed copy must be outside the repository.")
    if not supplied.is_file():
        raise FileNotFoundError(missing)
    columns = [column["name"] for column in entry["columns"]]
    with supplied.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != columns:
            raise ValueError(
                "Licensed table column names must match the metocean schema."
            )
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("Licensed table row width must match the metocean schema.")
    return rows
