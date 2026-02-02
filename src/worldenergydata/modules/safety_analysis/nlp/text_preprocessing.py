# ABOUTME: Generalized text preprocessor for safety observation NLP.
# Loads stop words from YAML + sklearn English + custom, then cleans text.
"""
Text Preprocessing for Safety Analysis

Provides configurable text cleaning and tokenization for safety
observation descriptions. Combines sklearn English stop words,
domain-specific stop words from YAML, and user-supplied custom words.
"""

from pathlib import Path
from typing import TYPE_CHECKING, List, Set

if TYPE_CHECKING:
    import pandas as pd

import yaml

from worldenergydata.common import get_logger
from worldenergydata.modules.safety_analysis.config import NLPConfig

try:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False
    ENGLISH_STOP_WORDS: Set[str] = set()  # type: ignore[no-redef]

_logger = get_logger(__name__)
_CONFIG_DIR = Path(__file__).parent.parent / "data" / "config"
_DEFAULT_STOP_WORDS_FILE = _CONFIG_DIR / "default_stop_words.yaml"


def _load_stop_words_yaml(path: Path) -> List[str]:
    """Load stop words list from a YAML file.

    Expected format:
        stop_words:
          - word1
          - word2
    """
    if not path.exists():
        _logger.warning("Stop words file not found: %s", path)
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    # Support both 'stop_words' and 'safety_stop_words' keys
    words = data.get("stop_words", data.get("safety_stop_words", []))
    return [str(w).lower() for w in words] if words else []


class TextPreprocessor:
    """Configurable text preprocessor for safety observations.

    Combines three stop-word sources into a single set, then applies
    lowercasing and token-length filtering during preprocessing.

    Parameters
    ----------
    config : NLPConfig
        NLP configuration controlling stop words, casing, and token lengths.
    """

    def __init__(self, config: NLPConfig | None = None) -> None:
        self.config = config or NLPConfig()
        self._stop_words = self._build_stop_words()
        _logger.debug(
            "TextPreprocessor initialised with %d stop words", len(self._stop_words)
        )

    def _build_stop_words(self) -> Set[str]:
        """Merge sklearn, YAML, and custom stop words into one set."""
        words: Set[str] = set()

        # 1. sklearn English stop words (if available)
        if _HAS_SKLEARN:
            words.update(ENGLISH_STOP_WORDS)

        # 2. Domain-specific stop words from YAML
        yaml_path = self.config.stop_words_file or _DEFAULT_STOP_WORDS_FILE
        yaml_words = _load_stop_words_yaml(yaml_path)
        words.update(yaml_words)

        # 3. User-supplied custom stop words
        words.update(w.lower() for w in self.config.custom_stop_words)

        return words

    @property
    def stop_words(self) -> Set[str]:
        """Return the merged stop-word set (read-only copy)."""
        return set(self._stop_words)

    def preprocess(self, text: str) -> str:
        """Clean a single text string.

        Steps: optional lowercasing, token-length filtering, stop-word removal.
        """
        if not text or not text.strip():
            return ""
        if self.config.lowercase:
            text = text.lower()
        tokens = text.split()
        tokens = [
            t
            for t in tokens
            if self.config.min_token_length <= len(t) <= self.config.max_token_length
            and t not in self._stop_words
        ]
        return " ".join(tokens)

    def preprocess_column(self, df: "pd.DataFrame", column: str) -> "pd.Series":
        """Apply preprocessing to every row in a DataFrame column.

        Returns a new Series; the original DataFrame is not mutated.
        """
        series = df[column].fillna("").astype(str)
        return series.apply(self.preprocess)

    def combine_columns(self, df: "pd.DataFrame", columns: List[str]) -> "pd.Series":
        """Concatenate multiple text columns, then preprocess.

        This replaces ENIGMA's ``cols='both'`` pattern where description
        and action columns are merged before TF-IDF fitting.
        """
        combined = df[columns[0]].fillna("").astype(str)
        for col in columns[1:]:
            combined = combined + " " + df[col].fillna("").astype(str)
        return combined.apply(self.preprocess)
