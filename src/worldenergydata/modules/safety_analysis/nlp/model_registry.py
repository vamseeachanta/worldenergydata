# ABOUTME: File-based model registry for persisting trained classifiers and metadata.
"""
Model Registry for Safety Analysis

File-based model persistence that stores trained classifiers alongside
JSON metadata (metrics, params, feature type) for lightweight,
self-contained model management.

Directory layout::

    registry_dir/
      {model_name}/
        metadata.json
        model.joblib
        vectorizer.joblib  (optional)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from worldenergydata.common import get_logger
from worldenergydata.modules.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyClassificationError,
)

try:
    import joblib

    _HAS_JOBLIB = True
except ImportError:
    _HAS_JOBLIB = False

_logger = get_logger(__name__)


def _require_joblib() -> None:
    if not _HAS_JOBLIB:
        raise OptionalDependencyError.missing("joblib", "safety-ml")


class ModelEntry(BaseModel):
    """Metadata for a persisted model."""

    model_name: str = Field(..., description="Unique model identifier")
    classifier_type: str = Field(..., description="Classifier algorithm name")
    feature_type: str = Field(default="tfidf", description="Feature extraction method")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of creation",
    )
    metrics: Dict[str, float] = Field(
        default_factory=dict, description="Evaluation metrics"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Model hyperparameters"
    )
    model_path: Path = Field(..., description="Path to serialised model file")
    vectorizer_path: Optional[Path] = Field(
        default=None, description="Path to serialised vectorizer"
    )


class ModelRegistry:
    """File-based registry for trained classification models.

    Parameters
    ----------
    registry_dir : Path
        Root directory under which model sub-directories are created.
    """

    _METADATA_FILE = "metadata.json"
    _MODEL_FILE = "model.joblib"
    _VECTORIZER_FILE = "vectorizer.joblib"

    def __init__(self, registry_dir: Path) -> None:
        _require_joblib()
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        _logger.debug("ModelRegistry rooted at %s", self.registry_dir)

    def _model_dir(self, model_name: str) -> Path:
        return self.registry_dir / model_name

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save_model(
        self,
        model: Any,
        entry: ModelEntry,
        vectorizer: Any | None = None,
    ) -> ModelEntry:
        """Persist a trained model (and optional vectorizer) to disk.

        The *entry* is updated with concrete file paths and written as
        JSON metadata alongside the joblib artefacts.

        Returns the updated :class:`ModelEntry`.
        """
        model_dir = self._model_dir(entry.model_name)
        model_dir.mkdir(parents=True, exist_ok=True)

        # Serialize model
        model_path = model_dir / self._MODEL_FILE
        joblib.dump(model, model_path)
        entry.model_path = model_path

        # Optionally serialize vectorizer
        if vectorizer is not None:
            vec_path = model_dir / self._VECTORIZER_FILE
            joblib.dump(vectorizer, vec_path)
            entry.vectorizer_path = vec_path

        # Write metadata
        meta_path = model_dir / self._METADATA_FILE
        meta_path.write_text(entry.model_dump_json(indent=2), encoding="utf-8")

        _logger.info("Model '%s' saved to %s", entry.model_name, model_dir)
        return entry

    def load_model(self, model_name: str) -> Tuple[Any, ModelEntry]:
        """Load a model and its metadata by name.

        Returns ``(model_object, entry)``.
        """
        entry = self.get_entry(model_name)
        model = joblib.load(entry.model_path)
        _logger.info("Model '%s' loaded from %s", model_name, entry.model_path)
        return model, entry

    def get_entry(self, model_name: str) -> ModelEntry:
        """Load metadata only (no model deserialisation)."""
        meta_path = self._model_dir(model_name) / self._METADATA_FILE
        if not meta_path.exists():
            raise SafetyClassificationError.model_not_found(model_name)
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        return ModelEntry(**raw)

    # ------------------------------------------------------------------
    # Listing / querying
    # ------------------------------------------------------------------

    def list_models(self) -> List[ModelEntry]:
        """Return metadata for every registered model."""
        entries: List[ModelEntry] = []
        if not self.registry_dir.exists():
            return entries
        for child in sorted(self.registry_dir.iterdir()):
            meta = child / self._METADATA_FILE
            if child.is_dir() and meta.exists():
                raw = json.loads(meta.read_text(encoding="utf-8"))
                entries.append(ModelEntry(**raw))
        return entries

    def get_best_model(self, metric: str = "f1_weighted") -> Tuple[Any, ModelEntry]:
        """Load the model with the highest value for *metric*.

        Raises :class:`SafetyClassificationError` if no models are
        registered or none have the requested metric.
        """
        entries = self.list_models()
        if not entries:
            raise SafetyClassificationError(
                message="No models registered",
                code="NO_MODELS",
            )
        scored = [(e, e.metrics.get(metric, -1.0)) for e in entries]
        best_entry = max(scored, key=lambda t: t[1])[0]
        if best_entry.metrics.get(metric) is None:
            raise SafetyClassificationError(
                message=f"No model has metric '{metric}'",
                code="METRIC_NOT_FOUND",
            )
        return self.load_model(best_entry.model_name)

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete_model(self, model_name: str) -> None:
        """Remove all files for *model_name* from the registry."""
        model_dir = self._model_dir(model_name)
        if not model_dir.exists():
            raise SafetyClassificationError.model_not_found(model_name)
        import shutil

        shutil.rmtree(model_dir)
        _logger.info("Model '%s' deleted from registry", model_name)
