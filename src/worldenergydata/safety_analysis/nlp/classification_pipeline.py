# ABOUTME: Main ML classification pipeline with hyperparameter optimisation for safety text.
"""Classification Pipeline for Safety Analysis.

End-to-end: preprocess -> vectorize -> optimise -> train -> evaluate -> persist.
Supports Random Forest, XGBoost, and Logistic Regression with TF-IDF features.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union

if TYPE_CHECKING:
    import pandas as pd

import yaml

from worldenergydata.common import get_logger
from worldenergydata.safety_analysis.config import AnalysisConfig
from worldenergydata.safety_analysis.constants import ClassifierType
from worldenergydata.safety_analysis.core.models import ClassificationResult
from worldenergydata.safety_analysis.exceptions import (
    OptionalDependencyError,
    SafetyClassificationError,
)
from worldenergydata.safety_analysis.nlp.model_registry import (
    ModelEntry,
    ModelRegistry,
)
from worldenergydata.safety_analysis.nlp.text_preprocessing import (
    TextPreprocessor,
)
from worldenergydata.safety_analysis.nlp.tfidf_vectorizer import (
    SafetyTfidfVectorizer,
)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.preprocessing import LabelEncoder

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

try:
    from xgboost import XGBClassifier

    _HAS_XGBOOST = True
except ImportError:
    _HAS_XGBOOST = False

try:
    from hyperopt import STATUS_OK, Trials, fmin, hp, tpe

    _HAS_HYPEROPT = True
except ImportError:
    _HAS_HYPEROPT = False

_logger = get_logger(__name__)
_CONFIG_DIR = Path(__file__).parent.parent / "data" / "config"
_MODEL_PARAMS_FILE = _CONFIG_DIR / "model_params.yaml"

_INT_PARAM_KEYS = {
    "n_estimators",
    "max_depth",
    "min_samples_split",
    "min_samples_leaf",
    "max_iter",
}


def _require_sklearn() -> None:
    if not _HAS_SKLEARN:
        raise OptionalDependencyError.missing("scikit-learn", "safety-ml")


def _load_model_params() -> Dict[str, Any]:
    """Load hyperparameter search-space definitions from YAML."""
    if not _MODEL_PARAMS_FILE.exists():
        _logger.warning("model_params.yaml not found; using empty search space")
        return {}
    with open(_MODEL_PARAMS_FILE, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _cast_int_params(params: Dict[str, Any]) -> None:
    """In-place cast of known integer hyperparameters."""
    for k in _INT_PARAM_KEYS:
        if k in params and params[k] is not None:
            params[k] = int(params[k])


class ClassificationPipeline:
    """End-to-end classification pipeline for safety text."""

    def __init__(
        self,
        config: AnalysisConfig | None = None,
        registry: ModelRegistry | None = None,
    ) -> None:
        _require_sklearn()
        self.config = config or AnalysisConfig()
        self._preprocessor = TextPreprocessor(self.config.nlp)
        self._vectorizer: SafetyTfidfVectorizer | None = None
        self._registry = registry or ModelRegistry(self.config.model_dir / "registry")
        self._model_params = _load_model_params()

    @staticmethod
    def _create_classifier(classifier_type: ClassifierType, params: Dict) -> Any:
        """Instantiate a classifier from type and params."""
        if classifier_type == ClassifierType.RANDOM_FOREST:
            return RandomForestClassifier(**params)
        if classifier_type == ClassifierType.XGBOOST:
            if not _HAS_XGBOOST:
                raise OptionalDependencyError.missing("xgboost", "safety-ml")
            return XGBClassifier(
                use_label_encoder=False, eval_metric="mlogloss", **params
            )
        if classifier_type == ClassifierType.LOGISTIC_REGRESSION:
            return LogisticRegression(**params)
        raise SafetyClassificationError(
            message=f"Unsupported classifier type: {classifier_type}",
            code="UNSUPPORTED_CLASSIFIER",
        )

    def _build_search_space(self, classifier_type: ClassifierType) -> Dict:
        """Convert YAML param definitions into hyperopt hp objects."""
        if not _HAS_HYPEROPT:
            return {}
        raw = self._model_params.get(classifier_type.value, {})
        space: Dict[str, Any] = {}
        for name, spec in raw.items():
            ptype = spec.get("type", "choice")
            if ptype == "choice":
                space[name] = hp.choice(name, spec["options"])
            elif ptype == "uniform":
                space[name] = hp.uniform(name, spec["low"], spec["high"])
            elif ptype == "loguniform":
                space[name] = hp.loguniform(name, spec["low"], spec["high"])
            else:
                _logger.warning("Unknown param type '%s' for %s", ptype, name)
        return space

    def _optimize_hyperparams(
        self, X_train, y_train, classifier_type: ClassifierType
    ) -> Dict[str, Any]:
        """Run hyperparameter optimisation; falls back to random search without hyperopt."""
        hp_cfg = self.config.hyperparams
        if _HAS_HYPEROPT:
            search_space = self._build_search_space(classifier_type)
            if not search_space:
                return {}

            def _objective(params: Dict) -> Dict:
                _cast_int_params(params)
                clf = self._create_classifier(classifier_type, params)
                scores = cross_val_score(
                    clf,
                    X_train,
                    y_train,
                    cv=hp_cfg.cv_folds,
                    scoring=hp_cfg.scoring_metric,
                )
                return {"loss": -scores.mean(), "status": STATUS_OK}

            best = fmin(
                fn=_objective,
                space=search_space,
                algo=tpe.suggest,
                max_evals=hp_cfg.max_evals,
                trials=Trials(),
                rstate=random.Random(hp_cfg.random_state),
                show_progress_bar=False,
            )
            # Resolve hp.choice indices back to actual values
            raw = self._model_params.get(classifier_type.value, {})
            resolved: Dict[str, Any] = {}
            for k, v in best.items():
                spec = raw.get(k, {})
                resolved[k] = (
                    spec["options"][int(v)] if spec.get("type") == "choice" else v
                )
            _logger.info("Best hyperparams: %s", resolved)
            return resolved

        return self._random_search(X_train, y_train, classifier_type)

    def _random_search(
        self, X_train, y_train, classifier_type: ClassifierType
    ) -> Dict[str, Any]:
        """Lightweight random search fallback when hyperopt is missing."""
        raw = self._model_params.get(classifier_type.value, {})
        hp_cfg = self.config.hyperparams
        rng = random.Random(hp_cfg.random_state)
        best_score, best_params = -1.0, {}

        for _ in range(min(hp_cfg.max_evals, 20)):
            params: Dict[str, Any] = {}
            for name, spec in raw.items():
                ptype = spec.get("type", "choice")
                if ptype == "choice":
                    params[name] = rng.choice(spec["options"])
                elif ptype == "uniform":
                    params[name] = rng.uniform(spec["low"], spec["high"])
                elif ptype == "loguniform":
                    params[name] = math.exp(
                        rng.uniform(math.log(spec["low"]), math.log(spec["high"]))
                    )
            _cast_int_params(params)
            try:
                clf = self._create_classifier(classifier_type, params)
                scores = cross_val_score(
                    clf,
                    X_train,
                    y_train,
                    cv=hp_cfg.cv_folds,
                    scoring=hp_cfg.scoring_metric,
                )
                if scores.mean() > best_score:
                    best_score, best_params = scores.mean(), params
            except Exception:
                _logger.debug("Random search iteration failed, skipping")
        _logger.info("Random search best: %s (score=%.4f)", best_params, best_score)
        return best_params

    def train(
        self,
        texts: Union["pd.Series", List[str]],
        labels: Union["pd.Series", List[str]],
        classifier_type: ClassifierType = ClassifierType.RANDOM_FOREST,
        model_name: str | None = None,
    ) -> ModelEntry:
        """Full training pipeline: preprocess, vectorize, optimise, train, persist."""
        import numpy as np

        if model_name is None:
            model_name = (
                f"{classifier_type.value}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}"
            )
        _logger.info(
            "Training %s '%s' on %d samples",
            classifier_type.value,
            model_name,
            len(texts),
        )

        cleaned = [self._preprocessor.preprocess(str(t)) for t in texts]
        self._vectorizer = SafetyTfidfVectorizer(
            config=self.config.nlp, stop_words=self._preprocessor.stop_words
        )
        X = self._vectorizer.fit_transform(cleaned)

        # Encode labels to integers (required by XGBoost, harmless for others)
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

        try:
            best_params = self._optimize_hyperparams(X_train, y_train, classifier_type)
        except Exception as exc:
            _logger.warning("Hyperparameter optimisation failed: %s", exc)
            best_params = {}

        try:
            classifier = self._create_classifier(classifier_type, best_params)
            classifier.fit(X_train, y_train)
        except Exception as exc:
            raise SafetyClassificationError.training_failed(
                str(exc), cause=exc
            ) from exc

        y_pred = classifier.predict(X_test)
        # Decode back to original labels for reporting
        y_test_labels = le.inverse_transform(y_test)
        y_pred_labels = le.inverse_transform(y_pred)
        f1 = float(f1_score(y_test_labels, y_pred_labels, average="weighted"))
        report = classification_report(y_test_labels, y_pred_labels, output_dict=True)
        metrics = {"f1_weighted": f1}
        metrics.update(
            {
                f"class_{k}": v.get("f1-score", 0.0)
                for k, v in report.items()
                if isinstance(v, dict)
            }
        )

        entry = ModelEntry(
            model_name=model_name,
            classifier_type=classifier_type.value,
            feature_type="tfidf",
            metrics=metrics,
            params=best_params,
            model_path=Path("placeholder"),
        )
        entry = self._registry.save_model(
            model=classifier, entry=entry, vectorizer=self._vectorizer._vectorizer
        )

        # Save label encoder alongside model
        import joblib as _jl

        _jl.dump(le, entry.model_path.parent / "label_encoder.joblib")

        _logger.info("Model '%s' trained (f1_weighted=%.4f)", model_name, f1)
        return entry

    def predict(
        self,
        texts: Union["pd.Series", List[str]],
        model_name: str | None = None,
    ) -> List[ClassificationResult]:
        """Batch prediction. Loads model from registry by name or best model."""
        model, entry = self._load_or_fail(model_name)
        vectorizer = self._load_vectorizer(entry)
        le = self._load_label_encoder(entry)
        X = vectorizer.transform([self._preprocessor.preprocess(str(t)) for t in texts])
        raw_preds = model.predict(X)
        preds = le.inverse_transform(raw_preds) if le is not None else raw_preds
        probas = self._get_probabilities(model, X, le)
        results: List[ClassificationResult] = []
        for i, text in enumerate(texts):
            prob_dict = probas[i] if probas else None
            results.append(
                ClassificationResult(
                    text=str(text),
                    predicted_label=str(preds[i]),
                    confidence=max(prob_dict.values()) if prob_dict else 0.0,
                    model_name=entry.model_name,
                    feature_type=entry.feature_type,
                    probabilities=prob_dict,
                )
            )
        return results

    def predict_single(
        self, text: str, model_name: str | None = None
    ) -> ClassificationResult:
        """Classify a single text string."""
        return self.predict([text], model_name=model_name)[0]

    def evaluate(
        self,
        texts: Union["pd.Series", List[str]],
        labels: Union["pd.Series", List[str]],
        model_name: str | None = None,
    ) -> Dict[str, Any]:
        """Evaluate a model; returns classification_report and confusion_matrix."""
        import numpy as np

        model, entry = self._load_or_fail(model_name)
        vectorizer = self._load_vectorizer(entry)
        le = self._load_label_encoder(entry)
        X = vectorizer.transform([self._preprocessor.preprocess(str(t)) for t in texts])
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

    def cross_validate(
        self,
        texts: Union["pd.Series", List[str]],
        labels: Union["pd.Series", List[str]],
        classifier_type: ClassifierType = ClassifierType.RANDOM_FOREST,
        cv: int | None = None,
    ) -> Dict[str, Any]:
        """K-fold cross-validation without persisting a model."""
        import numpy as np

        hp_cfg = self.config.hyperparams
        folds = cv or hp_cfg.cv_folds
        cleaned = [self._preprocessor.preprocess(str(t)) for t in texts]
        vec = SafetyTfidfVectorizer(
            config=self.config.nlp, stop_words=self._preprocessor.stop_words
        )
        X = vec.fit_transform(cleaned)
        le = LabelEncoder()
        y = le.fit_transform(np.array(labels))
        scores = cross_val_score(
            self._create_classifier(classifier_type, {}),
            X,
            y,
            cv=folds,
            scoring=hp_cfg.scoring_metric,
        )
        return {
            "classifier_type": classifier_type.value,
            "cv_folds": folds,
            "scores": scores.tolist(),
            "mean_score": float(scores.mean()),
            "std_score": float(scores.std()),
        }

    def _load_or_fail(self, model_name: str | None) -> tuple:
        """Load model from registry; uses best model when name is None."""
        if model_name:
            return self._registry.load_model(model_name)
        return self._registry.get_best_model()

    def _load_vectorizer(self, entry: ModelEntry):
        """Load the sklearn vectorizer associated with a model entry."""
        import joblib as _jl

        if entry.vectorizer_path and Path(entry.vectorizer_path).exists():
            return _jl.load(entry.vectorizer_path)
        if self._vectorizer is not None:
            return self._vectorizer._vectorizer
        raise SafetyClassificationError(
            message=f"No vectorizer found for model '{entry.model_name}'",
            code="VECTORIZER_MISSING",
        )

    @staticmethod
    def _load_label_encoder(entry: ModelEntry):
        """Load the label encoder saved alongside the model, if present."""
        import joblib as _jl

        encoder_path = Path(entry.model_path).parent / "label_encoder.joblib"
        if encoder_path.exists():
            return _jl.load(encoder_path)
        return None

    @staticmethod
    def _get_probabilities(model: Any, X, label_encoder=None) -> list | None:
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
