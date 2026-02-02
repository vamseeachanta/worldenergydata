# ABOUTME: BERT-based text embedding and classification pipeline using HuggingFace transformers.
"""
BERT Classification Pipeline for Safety Analysis.

Uses pretrained transformer models to generate text embeddings,
then applies sklearn classifiers for classification.  All torch/transformers
imports are gated behind try/except so the module is importable without
heavy dependencies.

Install with::

    pip install worldenergydata[safety-bert]   # torch, transformers
    pip install worldenergydata[safety-ml]     # scikit-learn
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from worldenergydata.common import get_logger
from worldenergydata.modules.safety_analysis.config import AnalysisConfig
from worldenergydata.modules.safety_analysis.constants import (
    ClassifierType,
    FeatureType,
)
from worldenergydata.modules.safety_analysis.core.models import ClassificationResult
from worldenergydata.modules.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyClassificationError,
)
from worldenergydata.modules.safety_analysis.nlp.model_registry import (
    ModelEntry,
    ModelRegistry,
)

try:
    import torch
    from transformers import AutoModel, AutoTokenizer

    _HAS_BERT = True
except ImportError:
    _HAS_BERT = False

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

_logger = get_logger(__name__)


def _require_bert() -> None:
    """Raise if torch/transformers are not installed."""
    if not _HAS_BERT:
        raise OptionalDependencyError.missing("torch/transformers", "safety-bert")


def _require_sklearn() -> None:
    """Raise if scikit-learn is not installed."""
    if not _HAS_SKLEARN:
        raise OptionalDependencyError.missing("scikit-learn", "safety-ml")


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


class BertConfig(BaseModel):
    """Configuration for BERT embedding extraction."""

    model_name: str = Field(
        default="bert-base-uncased",
        description="HuggingFace model identifier",
    )
    max_length: int = Field(
        default=512,
        description="Maximum token sequence length",
    )
    batch_size: int = Field(
        default=32,
        description="Number of texts per forward pass",
    )
    device: str = Field(
        default="cpu",
        description="Compute device: 'cpu' or 'cuda'",
    )
    pooling_strategy: str = Field(
        default="cls",
        description="Pooling strategy: 'cls' (CLS token) or 'mean' (mean pooling)",
    )


# ------------------------------------------------------------------
# Embedder
# ------------------------------------------------------------------


class BertEmbedder:
    """Extracts dense text embeddings using a pretrained transformer model.

    Parameters
    ----------
    config : BertConfig, optional
        Embedding configuration.  Defaults to ``BertConfig()``.
    """

    def __init__(self, config: Optional[BertConfig] = None) -> None:
        _require_bert()
        self.config = config or BertConfig()
        self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self._model = AutoModel.from_pretrained(self.config.model_name)
        self._model.eval()
        if self.config.device == "cuda" and torch.cuda.is_available():
            self._model = self._model.cuda()
        _logger.info(
            "BertEmbedder initialised: model=%s, device=%s, pooling=%s",
            self.config.model_name,
            self.config.device,
            self.config.pooling_strategy,
        )

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Processes in batches of ``config.batch_size`` for memory efficiency.

        Parameters
        ----------
        texts : list[str]
            Raw text strings to embed.

        Returns
        -------
        np.ndarray
            Array of shape ``(len(texts), embedding_dim)``.
        """
        all_embeddings: List[np.ndarray] = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            inputs = self._tokenizer(
                batch,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_length,
                padding=True,
            )
            if self.config.device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._model(**inputs)

            if self.config.pooling_strategy == "cls":
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            else:  # mean pooling
                mask = inputs["attention_mask"].unsqueeze(-1).float()
                token_embeddings = outputs.last_hidden_state
                if self.config.device == "cuda" and torch.cuda.is_available():
                    mask = mask.cuda()
                summed = (token_embeddings * mask).sum(dim=1)
                counts = mask.sum(dim=1).clamp(min=1e-9)
                embeddings = (summed / counts).cpu().numpy()

            all_embeddings.append(embeddings)

        return np.vstack(all_embeddings)

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of the output embeddings."""
        return self._model.config.hidden_size


# ------------------------------------------------------------------
# Classification Pipeline
# ------------------------------------------------------------------


class BertClassificationPipeline:
    """BERT embedding + sklearn classifier pipeline.

    Generates dense embeddings via a pretrained transformer, then
    trains / predicts with a lightweight sklearn classifier.  Models
    are persisted through the existing :class:`ModelRegistry`.

    Parameters
    ----------
    config : AnalysisConfig, optional
        General analysis configuration.
    bert_config : BertConfig, optional
        BERT-specific configuration.
    registry : ModelRegistry, optional
        Model persistence backend.
    """

    def __init__(
        self,
        config: Optional[AnalysisConfig] = None,
        bert_config: Optional[BertConfig] = None,
        registry: Optional[ModelRegistry] = None,
    ) -> None:
        _require_bert()
        _require_sklearn()
        self.config = config or AnalysisConfig()
        self.bert_config = bert_config or BertConfig()
        self._embedder = BertEmbedder(self.bert_config)
        self._registry = registry or ModelRegistry(self.config.model_dir / "registry")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        texts: List[str],
        labels: List[str],
        classifier_type: ClassifierType = ClassifierType.RANDOM_FOREST,
        model_name: Optional[str] = None,
    ) -> ModelEntry:
        """Train: embed texts with BERT, train sklearn classifier, persist.

        Parameters
        ----------
        texts : list[str]
            Training texts.
        labels : list[str]
            Corresponding class labels.
        classifier_type : ClassifierType
            Sklearn classifier algorithm.
        model_name : str, optional
            Unique name for the persisted model.

        Returns
        -------
        ModelEntry
            Metadata for the saved model.
        """
        if model_name is None:
            model_name = (
                f"bert_{classifier_type.value}"
                f"_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
            )
        _logger.info(
            "Training BERT+%s '%s' on %d samples",
            classifier_type.value,
            model_name,
            len(texts),
        )

        X = self._embedder.embed_texts(texts)

        le = LabelEncoder()
        y = le.fit_transform(np.array(labels))

        hp_cfg = self.config.hyperparams
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=hp_cfg.test_size,
            random_state=hp_cfg.random_state,
            stratify=y,
        )

        classifier = self._create_classifier(classifier_type)
        try:
            classifier.fit(X_train, y_train)
        except Exception as exc:
            raise SafetyClassificationError.training_failed(
                str(exc), cause=exc
            ) from exc

        # Evaluate
        y_pred = classifier.predict(X_test)
        y_test_labels = le.inverse_transform(y_test)
        y_pred_labels = le.inverse_transform(y_pred)
        f1 = float(f1_score(y_test_labels, y_pred_labels, average="weighted"))
        report = classification_report(y_test_labels, y_pred_labels, output_dict=True)
        metrics: Dict[str, float] = {"f1_weighted": f1}
        metrics.update(
            {
                f"class_{k}": v.get("f1-score", 0.0)
                for k, v in report.items()
                if isinstance(v, dict)
            }
        )

        # Persist
        entry = ModelEntry(
            model_name=model_name,
            classifier_type=classifier_type.value,
            feature_type=FeatureType.BERT.value,
            metrics=metrics,
            params={
                "bert_model": self.bert_config.model_name,
                "pooling": self.bert_config.pooling_strategy,
            },
            model_path=Path("placeholder"),
        )
        entry = self._registry.save_model(model=classifier, entry=entry)

        # Save label encoder alongside model
        import joblib as _jl

        _jl.dump(le, entry.model_path.parent / "label_encoder.joblib")

        _logger.info("BERT model '%s' trained (f1_weighted=%.4f)", model_name, f1)
        return entry

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
    ) -> List[ClassificationResult]:
        """Embed texts with BERT, predict with saved classifier.

        Parameters
        ----------
        texts : list[str]
            Texts to classify.
        model_name : str, optional
            Registry model name.  Uses best model when ``None``.

        Returns
        -------
        list[ClassificationResult]
        """
        model, entry = self._load_or_fail(model_name)
        le = self._load_label_encoder(entry)
        X = self._embedder.embed_texts(texts)
        raw_preds = model.predict(X)
        preds = le.inverse_transform(raw_preds) if le is not None else raw_preds
        probas = self._get_probabilities(model, X, le)
        results: List[ClassificationResult] = []
        for i, text in enumerate(texts):
            prob_dict = probas[i] if probas else None
            results.append(
                ClassificationResult(
                    text=text,
                    predicted_label=str(preds[i]),
                    confidence=max(prob_dict.values()) if prob_dict else 0.0,
                    model_name=entry.model_name,
                    feature_type=FeatureType.BERT.value,
                    probabilities=prob_dict,
                )
            )
        return results

    def predict_single(
        self, text: str, model_name: Optional[str] = None
    ) -> ClassificationResult:
        """Classify a single text string."""
        return self.predict([text], model_name=model_name)[0]

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        texts: List[str],
        labels: List[str],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate model on labelled test data.

        Returns dict with classification_report, confusion_matrix,
        and f1_weighted.
        """
        model, entry = self._load_or_fail(model_name)
        le = self._load_label_encoder(entry)
        X = self._embedder.embed_texts(texts)
        raw_pred = model.predict(X)
        y_pred = le.inverse_transform(raw_pred) if le is not None else raw_pred
        y_true = np.array(labels)
        return {
            "model_name": entry.model_name,
            "classification_report": classification_report(
                y_true, y_pred, output_dict=True
            ),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
            "f1_weighted": float(f1_score(y_true, y_pred, average="weighted")),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _create_classifier(classifier_type: ClassifierType) -> Any:
        """Instantiate a sklearn classifier with sensible defaults."""
        if classifier_type == ClassifierType.RANDOM_FOREST:
            return RandomForestClassifier(
                n_estimators=100, random_state=42, class_weight="balanced"
            )
        if classifier_type == ClassifierType.LOGISTIC_REGRESSION:
            return LogisticRegression(
                max_iter=1000, random_state=42, class_weight="balanced"
            )
        raise SafetyClassificationError(
            message=(f"Unsupported classifier for BERT pipeline: {classifier_type}"),
            code="UNSUPPORTED_CLASSIFIER",
        )

    def _load_or_fail(self, model_name: Optional[str] = None):
        """Load model from registry; uses best model when name is None."""
        if model_name:
            return self._registry.load_model(model_name)
        return self._registry.get_best_model(metric="f1_weighted")

    @staticmethod
    def _load_label_encoder(entry: ModelEntry):
        """Load the label encoder saved alongside the model, if present."""
        import joblib as _jl

        encoder_path = Path(entry.model_path).parent / "label_encoder.joblib"
        if encoder_path.exists():
            return _jl.load(encoder_path)
        return None

    @staticmethod
    def _get_probabilities(
        model: Any, X: np.ndarray, label_encoder=None
    ) -> Optional[List[Dict[str, float]]]:
        """Extract per-class probabilities if the model supports predict_proba."""
        if not hasattr(model, "predict_proba"):
            return None
        try:
            proba = model.predict_proba(X)
            classes = list(model.classes_)
            if label_encoder is not None:
                classes = list(label_encoder.inverse_transform(classes))
            return [
                {str(classes[j]): float(proba[i, j]) for j in range(len(classes))}
                for i in range(proba.shape[0])
            ]
        except Exception:
            return None
