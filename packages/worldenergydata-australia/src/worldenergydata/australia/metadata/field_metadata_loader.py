"""Australia per-field metadata loader (DataVic / NOPTA, #721a).

Reads the committed CC-BY Gippsland field-metadata fixture (per-field water depth
+ spud date; NO production volumes) into field-metadata dicts for the screening
chain. Both DataVic Open Data and NOPTA are CC-BY-4.0, so a small metadata fixture
is committed with attribution provenance in ``_metadata.json``.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Dict, List

import pandas as pd

_DATA_ROOT = files("worldenergydata.australia").joinpath("data")
DEFAULT_FIXTURE_CSV = _DATA_ROOT.joinpath("gippsland_fields_sample.csv")
DEFAULT_METADATA_JSON = _DATA_ROOT.joinpath("_metadata.json")


class AustraliaFieldMetadataLoader:
    """Loads Australia field metadata (CC-BY) for concept screening."""

    def __init__(
        self, *, path=DEFAULT_FIXTURE_CSV, metadata_path=DEFAULT_METADATA_JSON
    ):
        self._path = path
        self._metadata_path = metadata_path

    def load_all(self) -> pd.DataFrame:
        return pd.read_csv(self._path)

    def available_fields(self) -> List[str]:
        return sorted(self.load_all()["field_name"].astype(str).unique().tolist())

    def field_meta(self, field_name: str) -> Dict[str, Any]:
        frame = self.load_all()
        mask = frame["field_name"].astype(str).str.lower() == field_name.lower()
        rows = frame[mask]
        if rows.empty:
            raise KeyError(f"unknown Australia field {field_name!r}")
        return rows.iloc[0].to_dict()

    def metadata(self) -> Dict[str, Any]:
        with self._metadata_path.open(encoding="utf-8") as fh:
            return json.load(fh)
