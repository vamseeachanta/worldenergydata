"""BSEE Field Name Resolver.

Resolves BSEE field codes to human-readable display names by loading
field-to-name mappings from binary data files (deepqual, platstruc, lab).
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Default data directory relative to project root
_DEFAULT_DATA_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data"
    / "modules"
    / "bsee"
    / "bin"
)


class FieldNameResolver:
    """Resolves BSEE field name codes to display names.

    Loads mappings from pickled DataFrames stored in the BSEE binary data
    directory. Handles LFS stubs and missing files gracefully.
    """

    # Sources to load, in priority order (first wins for duplicate codes).
    # The deep-water-leases table carries the authoritative field nickname
    # (``FLD_NICK_NAME``, e.g. "Mars-Ursa"); the platform-structures table
    # only has *structure* names ("A (Mars)"), so it is intentionally not
    # used as a field-name source (it would mislabel fields).
    _SOURCES = [
        {
            "subdir": "deepqual",
            "file": "mv_deep_water_field_leases.bin",
            "code_col": "FIELD_NAME_CODE",
            "name_col": "FLD_NICK_NAME",
        },
    ]

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._field_names: Dict[str, str] = {}
        self._loaded = False

    def _load_pickle_safe(self, file_path: Path) -> pd.DataFrame:
        """Load a pickle file, returning empty DataFrame for LFS stubs or errors."""
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return pd.DataFrame()

        try:
            # Check for LFS pointer (text file starting with "version https://git-lfs")
            with open(file_path, "rb") as f:
                header = f.read(40)
            if b"version https://git-lfs" in header:
                logger.warning("LFS stub detected (not materialized): %s", file_path)
                return pd.DataFrame()

            with open(file_path, "rb") as f:
                obj = pickle.load(f)  # nosec B301

            if isinstance(obj, pd.DataFrame):
                return obj

            logger.warning("File does not contain a DataFrame: %s", file_path)
            return pd.DataFrame()

        except Exception as e:
            logger.error("Error loading %s: %s", file_path, e)
            return pd.DataFrame()

    def _merge_field_names(
        self, df: pd.DataFrame, code_col: str, name_col: str
    ) -> None:
        """Merge field name mappings from a DataFrame into the internal dict."""
        if df.empty:
            return

        if code_col not in df.columns or name_col not in df.columns:
            logger.warning(
                "Expected columns %s, %s not found in DataFrame with columns: %s",
                code_col,
                name_col,
                list(df.columns),
            )
            return

        for _, row in df.drop_duplicates(subset=[code_col]).iterrows():
            code = str(row[code_col]).strip()
            name = str(row[name_col]).strip()
            if code and name and code not in self._field_names:
                self._field_names[code] = name

    def _ensure_loaded(self) -> None:
        """Load field names from all sources if not already loaded."""
        if self._loaded:
            return

        for source in self._SOURCES:
            file_path = self._data_dir / source["subdir"] / source["file"]
            df = self._load_pickle_safe(file_path)
            if not df.empty:
                self._merge_field_names(df, source["code_col"], source["name_col"])
                logger.info(
                    "Loaded %d field names from %s",
                    len(self._field_names),
                    file_path.name,
                )

        self._loaded = True
        logger.info("Total field names loaded: %d", len(self._field_names))

    def resolve(self, field_code: str) -> str:
        """Resolve a field code to its display name.

        Returns the code itself if no mapping is found.
        """
        self._ensure_loaded()
        code = str(field_code).strip()
        return self._field_names.get(code, code)

    def resolve_batch(self, field_codes: List[str]) -> Dict[str, str]:
        """Resolve multiple field codes at once."""
        self._ensure_loaded()
        return {code: self.resolve(code) for code in field_codes}

    def get_all_field_names(self) -> Dict[str, str]:
        """Return a copy of all loaded field name mappings."""
        self._ensure_loaded()
        return dict(self._field_names)
