"""NLP and classification components for safety analysis.

Optional heavy dependencies (scikit-learn, torch, transformers) are
gated behind try/except imports. Install extras as needed:

    pip install worldenergydata[safety-ml]     # scikit-learn, xgboost, hyperopt
    pip install worldenergydata[safety-bert]   # torch, transformers
"""

from worldenergydata.modules.safety_analysis.nlp.classification_pipeline import (
    ClassificationPipeline,
)
from worldenergydata.modules.safety_analysis.nlp.model_registry import (
    ModelEntry,
    ModelRegistry,
)
from worldenergydata.modules.safety_analysis.nlp.text_preprocessing import (
    TextPreprocessor,
)
from worldenergydata.modules.safety_analysis.nlp.tfidf_vectorizer import (
    SafetyTfidfVectorizer,
)

__all__ = [
    "TextPreprocessor",
    "SafetyTfidfVectorizer",
    "ModelEntry",
    "ModelRegistry",
    "ClassificationPipeline",
]
