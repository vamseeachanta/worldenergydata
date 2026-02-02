# ABOUTME: TF-IDF vectorizer wrapper with save/load for safety text classification.
"""
TF-IDF Vectorizer for Safety Analysis

Wraps sklearn's TfidfVectorizer with configuration driven by NLPConfig,
domain-aware stop words, and persistence via joblib.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
    import pandas as pd

from worldenergydata.common import get_logger
from worldenergydata.modules.safety_analysis.config import NLPConfig
from worldenergydata.modules.safety_analysis.exceptions import OptionalDependencyError

try:
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

_logger = get_logger(__name__)


def _require_sklearn() -> None:
    """Raise if scikit-learn is not installed."""
    if not _HAS_SKLEARN:
        raise OptionalDependencyError.missing("scikit-learn", "safety-ml")


class SafetyTfidfVectorizer:
    """Configurable TF-IDF vectorizer for safety observation text.

    Reads settings (analyzer, ngram_range, max_features, etc.) from
    :class:`NLPConfig` and delegates to sklearn's ``TfidfVectorizer``.

    Parameters
    ----------
    config : NLPConfig
        NLP configuration.  Uses ``analyzer``, ``ngram_range``,
        ``max_features``, and ``lowercase`` fields.
    stop_words : set[str] | list[str] | None
        Explicit stop words to pass to sklearn.  When *None* the
        vectorizer uses sklearn's built-in ``"english"`` list.
    """

    def __init__(
        self,
        config: NLPConfig | None = None,
        stop_words: Union[set, list, None] = None,
    ) -> None:
        _require_sklearn()
        self.config = config or NLPConfig()

        # Determine stop words for sklearn
        sw = list(stop_words) if stop_words is not None else "english"

        self._vectorizer = TfidfVectorizer(
            analyzer=self.config.analyzer,
            lowercase=self.config.lowercase,
            max_features=self.config.max_features,
            ngram_range=self.config.ngram_range,
            stop_words=sw,
        )
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Fit / transform
    # ------------------------------------------------------------------

    def fit(self, texts: Union["pd.Series", List[str]]) -> SafetyTfidfVectorizer:
        """Fit the vectorizer on *texts* and return self."""
        self._vectorizer.fit(texts)
        self._is_fitted = True
        _logger.info(
            "TF-IDF fitted with %d features", len(self._vectorizer.vocabulary_)
        )
        return self

    def transform(self, texts: Union["pd.Series", List[str]]):
        """Transform *texts* into a TF-IDF sparse matrix.

        Raises ``RuntimeError`` if :meth:`fit` has not been called.
        """
        if not self._is_fitted:
            raise RuntimeError("Vectorizer must be fitted before calling transform()")
        return self._vectorizer.transform(texts)

    def fit_transform(self, texts: Union["pd.Series", List[str]]):
        """Fit on *texts* and return the transformed sparse matrix."""
        self.fit(texts)
        return self._vectorizer.transform(texts)

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------

    def get_feature_names(self) -> List[str]:
        """Return feature (term) names after fitting."""
        if not self._is_fitted:
            raise RuntimeError("Vectorizer must be fitted first")
        return list(self._vectorizer.get_feature_names_out())

    @property
    def vocabulary_size(self) -> int:
        """Number of features in the fitted vocabulary."""
        if not self._is_fitted:
            return 0
        return len(self._vectorizer.vocabulary_)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Serialize the fitted vectorizer to *path* using joblib."""
        _require_sklearn()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._vectorizer, path)
        _logger.info("Vectorizer saved to %s", path)

    @classmethod
    def load(cls, path: Path, config: NLPConfig | None = None) -> SafetyTfidfVectorizer:
        """Deserialize a vectorizer from *path*.

        Parameters
        ----------
        path : Path
            File previously saved via :meth:`save`.
        config : NLPConfig | None
            Optional config to attach; does *not* override the loaded
            sklearn parameters.
        """
        _require_sklearn()
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Vectorizer file not found: {path}")
        vec = cls.__new__(cls)
        vec.config = config or NLPConfig()
        vec._vectorizer = joblib.load(path)
        vec._is_fitted = True
        _logger.info("Vectorizer loaded from %s", path)
        return vec
