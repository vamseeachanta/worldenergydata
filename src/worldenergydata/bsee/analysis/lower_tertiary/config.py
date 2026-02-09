"""Load and validate the World Oil Lower Tertiary YAML configuration."""

from __future__ import annotations

from pathlib import Path

import yaml


class LTConfig:
    """Thin accessor over the YAML input file.

    Loads the Lower Tertiary analysis configuration from a YAML file and
    provides typed accessors for field mappings, article metrics,
    architecture ratings, data paths, and output settings.
    """

    def __init__(self, config_path: Path) -> None:
        with open(config_path) as f:
            self._cfg = yaml.safe_load(f)

    # -- Field accessors ---------------------------------------------------

    @property
    def all_fields(self) -> dict[str, dict]:
        """Merge subsea + dry_tree fields into a single dict."""
        merged: dict[str, dict] = {}
        merged.update(self._cfg["fields"]["subsea"])
        merged.update(self._cfg["fields"]["dry_tree"])
        return merged

    @property
    def subsea_fields(self) -> dict[str, dict]:
        return self._cfg["fields"]["subsea"]

    @property
    def dry_tree_fields(self) -> dict[str, dict]:
        return self._cfg["fields"]["dry_tree"]

    def field_blocks(self, name: str) -> tuple[str, list[int]]:
        """Return (area_code, block_list) for a named field.

        Raises:
            KeyError: If the field name is not found in either subsea
                or dry_tree sections.
        """
        all_f = self.all_fields
        if name not in all_f:
            raise KeyError(f"Unknown field: {name}")
        info = all_f[name]
        return (info["area"], info["blocks"])

    # -- Article metrics ---------------------------------------------------

    @property
    def article_metrics(self) -> dict:
        return self._cfg["article_metrics"]

    # -- Architecture ------------------------------------------------------

    @property
    def architecture(self) -> dict:
        return self._cfg["architecture"]

    # -- Data paths --------------------------------------------------------

    @property
    def data_paths(self) -> dict:
        return self._cfg["data"]

    def legacy_csv_paths(self, field: str, base_dir: Path) -> dict[str, Path]:
        """Return resolved paths for a legacy field's CSVs.

        Raises:
            KeyError: If the field name has no legacy data configured.
        """
        legacy = self._cfg["data"]["legacy_fields"]
        if field not in legacy:
            raise KeyError(f"No legacy data for field: {field}")
        return {k: base_dir / v for k, v in legacy[field].items()}

    # -- Output ------------------------------------------------------------

    @property
    def output_config(self) -> dict:
        return self._cfg["output"]

    # -- Metadata ----------------------------------------------------------

    @property
    def metadata(self) -> dict:
        return self._cfg["metadata"]
